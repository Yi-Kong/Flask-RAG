"""LLM 调用服务（LangChain 兼容层）.

保留原有 chat_service / chat_with_prompt_service 接口签名，
内部委托给 LangChain ChatOpenAI 执行实际调用。

所有 LLM 调用统一通过此文件，便于：
  - 切换模型（修改 .env 中的 LLM_DEFAULT_PROFILE 即可）
  - 获取准确 token 统计（通过 LangChain callback）
  - 未来扩展流式输出（.stream() 方法）
"""
import logging
from typing import Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from service.llm_factory import create_chat_model, get_rag_llm

logger = logging.getLogger(__name__)

# ── 消息格式转换 ──────────────────────────────────────────────────────

_ROLE_MAP = {
    "user": HumanMessage,
    "system": SystemMessage,
    "assistant": AIMessage,
}


def _dict_to_lc_messages(messages: list) -> list:
    """将 dict 格式的消息列表转为 LangChain Message 对象.

    Args:
        messages: [{"role": "user", "content": "..."}, ...]

    Returns:
        [HumanMessage(...), SystemMessage(...), ...]
    """
    lc_messages = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        msg_cls = _ROLE_MAP.get(role, HumanMessage)
        lc_messages.append(msg_cls(content=content))
    return lc_messages


def _build_llm_kwargs(
    llm: ChatOpenAI,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> dict:
    """构建调用参数，允许调用方覆盖默认的 temperature/max_tokens."""
    kwargs = {}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    return kwargs


# ── 公开 API（保持旧接口签名不变）─────────────────────────────────────

def chat_service(
    messages: list,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """调用 LLM Chat API 获取回复（兼容旧接口）.

    Args:
        messages: 消息列表，格式 [{"role": "user"|"system"|"assistant", "content": "..."}].
        temperature: 覆盖默认温度参数.
        max_tokens: 覆盖默认最大 token 数.

    Returns:
        模型回复文本.

    Raises:
        RuntimeError: LLM profile 未配置.
    """
    llm = get_rag_llm()
    lc_messages = _dict_to_lc_messages(messages)
    kwargs = _build_llm_kwargs(llm, temperature, max_tokens)

    response = llm.invoke(lc_messages, **kwargs)
    content = response.content if hasattr(response, "content") else str(response)

    # 记录 token 用量
    usage = getattr(response, "response_metadata", {}).get("token_usage", {})
    if usage:
        logger.info(
            "LLM 调用完成: model=%s, prompt_tokens=%s, completion_tokens=%s, total_tokens=%s",
            getattr(llm, "model_name", "?"),
            usage.get("prompt_tokens", "?"),
            usage.get("completion_tokens", "?"),
            usage.get("total_tokens", "?"),
        )

    return content


def chat_with_prompt_service(
    system_prompt: str,
    user_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """使用 system + user 双消息调用 LLM（兼容旧接口）.

    Args:
        system_prompt: 系统提示词.
        user_prompt: 用户提示词（含参考资料 + 用户问题）.
        temperature: 覆盖默认温度参数.
        max_tokens: 覆盖默认最大 token 数.

    Returns:
        模型回复文本.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    return chat_service(messages, temperature=temperature, max_tokens=max_tokens)
