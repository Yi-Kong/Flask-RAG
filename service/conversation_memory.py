"""对话记忆管理 — 基于 LangChain ChatMessageHistory + tiktoken 精确计数.

替代原有的 format_conversation_history() 文本拼接方式，
使用原生 LangChain Message 对象（HumanMessage/AIMessage），
让 LLM 能真正理解多轮对话结构。

特性：
  - 从 MySQL QARecord 列表加载历史消息
  - 使用 tiktoken 精确计算 token 数（替代 len(text)*0.5 粗略估算）
  - 支持按 token 预算自动裁剪旧消息
  - 与 LangChain RunnableWithMessageHistory 兼容
"""
import logging
from typing import List, Optional, Sequence

import tiktoken
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

logger = logging.getLogger(__name__)

# DeepSeek / OpenAI 默认使用 cl100k_base 编码
_DEFAULT_ENCODING = "cl100k_base"
# 单次对话历史最大 token 数（可通过参数覆盖）
_DEFAULT_MAX_HISTORY_TOKENS = 12000


# ── Token 计数 ────────────────────────────────────────────────────────

def count_tokens(text: str, encoding_name: str = _DEFAULT_ENCODING) -> int:
    """使用 tiktoken 精确计算文本 token 数.

    Args:
        text: 输入文本.
        encoding_name: tiktoken 编码名称，默认 cl100k_base.

    Returns:
        token 数量.
    """
    try:
        enc = tiktoken.get_encoding(encoding_name)
        return len(enc.encode(text))
    except Exception as e:
        logger.warning("tiktoken 计数失败，回退到粗略估算: %s", e)
        return max(1, int(len(text) * 0.5))


def count_message_tokens(
    messages: Sequence[BaseMessage],
    encoding_name: str = _DEFAULT_ENCODING,
) -> int:
    """计算一组 LangChain Message 的总 token 数.

    计入每个消息的 role/format 开销（约 4 tokens/消息）。

    Args:
        messages: LangChain Message 列表.
        encoding_name: tiktoken 编码名称.

    Returns:
        总 token 数.
    """
    total = 0
    for msg in messages:
        # 每个消息的 role + formatting 约 4 tokens
        total += 4
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        total += count_tokens(content, encoding_name)
    return total


# ── 对话记忆管理器 ────────────────────────────────────────────────────

class ConversationMemoryManager:
    """封装 LangChain ChatMessageHistory，提供 DB 加载 & token 裁剪.

    用法:
        manager = ConversationMemoryManager()
        manager.load_from_db(qa_records)       # 从 MySQL 加载历史
        messages = manager.get_messages()       # 获取 LangChain Message 列表
        manager.add_turn(question, answer)      # 记录新一轮对话

    messages 可直接传给 LangChain Chain 的 chat_history 参数。
    """

    def __init__(
        self,
        max_tokens: int = _DEFAULT_MAX_HISTORY_TOKENS,
        encoding_name: str = _DEFAULT_ENCODING,
    ):
        """初始化对话记忆管理器.

        Args:
            max_tokens: 对话历史的最大 token 预算.
            encoding_name: tiktoken 编码名称.
        """
        self._max_tokens = max_tokens
        self._encoding_name = encoding_name
        self._messages: List[BaseMessage] = []

    # ── 属性 ──────────────────────────────────────────────────────

    @property
    def messages(self) -> List[BaseMessage]:
        """获取当前记忆中的所有消息."""
        return list(self._messages)

    @property
    def token_count(self) -> int:
        """当前记忆的 token 总量."""
        return count_message_tokens(self._messages, self._encoding_name)

    @property
    def is_empty(self) -> bool:
        """是否为空记忆."""
        return len(self._messages) == 0

    # ── 加载与操作 ────────────────────────────────────────────────

    def load_from_db(self, qa_records: list) -> None:
        """从 MySQL QARecord 列表加载对话历史.

        QARecord 按 created_at 正序排列，每个 record 包含 question/answer 字段。

        Args:
            qa_records: QARecord 对象列表（已按时间排序）.
        """
        self._messages.clear()
        if not qa_records:
            return

        for record in qa_records:
            question = getattr(record, "question", "") or ""
            answer = getattr(record, "answer", "") or ""
            if question.strip():
                self._messages.append(HumanMessage(content=question))
            if answer.strip():
                self._messages.append(AIMessage(content=answer))

        before_count = len(self._messages)
        self._trim_to_budget()
        after_count = len(self._messages)

        logger.info(
            "从 DB 加载对话历史: %d 条记录 → %d 条消息 → 裁剪后 %d 条消息, "
            "token 数=%d (预算=%d)",
            len(qa_records), before_count, after_count,
            self.token_count, self._max_tokens,
        )

    def add_turn(self, question: str, answer: str) -> None:
        """添加一轮新的问答到记忆中.

        Args:
            question: 用户问题.
            answer: 助手回答.
        """
        if question.strip():
            self._messages.append(HumanMessage(content=question))
        if answer.strip():
            self._messages.append(AIMessage(content=answer))
        self._trim_to_budget()

    def get_messages(self) -> List[BaseMessage]:
        """获取 LangChain 格式的消息列表（用于传给 Chain）."""
        return list(self._messages)

    def format_as_text(self) -> str:
        """将消息格式化为纯文本（兼容旧代码中需要文本的地方）.

        Returns:
            格式化的对话历史文本，无历史时返回空字符串.
        """
        if not self._messages:
            return ""

        parts = []
        i = 0
        while i < len(self._messages):
            user_msg = None
            assistant_msg = None
            if isinstance(self._messages[i], HumanMessage):
                user_msg = self._messages[i].content
                if i + 1 < len(self._messages) and isinstance(self._messages[i + 1], AIMessage):
                    assistant_msg = self._messages[i + 1].content
                    i += 2
                else:
                    i += 1
            else:
                i += 1

            if user_msg:
                part = f"用户：{user_msg}"
                if assistant_msg:
                    part += f"\n助手：{assistant_msg}"
                parts.append(part)

        if not parts:
            return ""

        return "【对话历史】\n" + "\n\n".join(parts)

    # ── 内部方法 ──────────────────────────────────────────────────

    def _trim_to_budget(self) -> None:
        """裁剪旧消息使总 token 数不超过 max_tokens 预算.

        从最早的消息开始丢弃，优先保留最近的对话。
        至少保留最近一轮完整的 Q&A。
        """
        if not self._messages:
            return

        total = self.token_count
        if total <= self._max_tokens:
            return

        # 找到最后一条 HumanMessage（最近一次提问）的位置
        last_human_idx = -1
        for i in range(len(self._messages) - 1, -1, -1):
            if isinstance(self._messages[i], HumanMessage):
                last_human_idx = i
                break

        # 从前往后丢弃，但至少保留最后一轮
        while len(self._messages) > 0 and self.token_count > self._max_tokens:
            # 如果只剩最后一条 HumanMessage 及之后的内容，保留
            if last_human_idx >= 0 and len(self._messages) <= len(self._messages) - last_human_idx:
                # 仍然超预算：截断最后一个 answer
                keep_start = last_human_idx
                self._messages = self._messages[keep_start:]
                if self.token_count > self._max_tokens and len(self._messages) > 1:
                    # 截断最后一个 AI 回答
                    last_ai = self._messages[-1]
                    if isinstance(last_ai, AIMessage):
                        enc = tiktoken.get_encoding(self._encoding_name)
                        # 计算可保留的 token 数
                        overhead = sum(
                            4 + len(enc.encode(m.content if isinstance(m.content, str) else str(m.content)))
                            for m in self._messages[:-1]
                        )
                        available = max(50, self._max_tokens - overhead)
                        tokens = enc.encode(last_ai.content)
                        if len(tokens) > available:
                            truncated = enc.decode(tokens[:available]) + "..."
                            self._messages[-1] = AIMessage(content=truncated)
                break

            # 成对删除：HumanMessage + AIMessage
            if len(self._messages) >= 2:
                self._messages.pop(0)  # HumanMessage
                if self._messages and isinstance(self._messages[0], AIMessage):
                    self._messages.pop(0)  # AIMessage
            else:
                self._messages.pop(0)

        logger.info(
            "对话历史裁剪完成: token=%d/%d, 保留 %d 条消息",
            self.token_count, self._max_tokens, len(self._messages),
        )
