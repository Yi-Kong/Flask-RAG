"""LangChain RAG 链 — 基于 LCEL 的检索增强生成管线.

提供:
  1. ChromaRetriever — 适配现有 ChromaDB vector_store 的 LangChain Retriever
  2. build_rag_chain() — 构建完整 RAG 链（含历史感知检索）
  3. format_docs() — 将检索到的 Document 列表拼接为 Prompt 上下文

与 rag_service.py 的分工：
  - rag_chain.py:   检索 + 上下文组装 + LLM 回答（LCEL 管道）
  - rag_service.py: 置信度分类 + 前后处理 + 记录持久化
"""
import logging
from typing import Any, Dict, List, Optional

from langchain.chains import create_history_aware_retriever

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnablePassthrough
from pydantic import Field

from config import Config

logger = logging.getLogger(__name__)

# ── Retriever Input Schema ─────────────────────────────────────────────

# 用于 create_history_aware_retriever 的 input schema（源码级兼容）


# ── 自定义 ChromaDB Retriever ──────────────────────────────────────────

class ChromaRetriever(BaseRetriever):
    """适配现有 ChromaDB vector_store 的 LangChain Retriever.

    内部调用 service/embedder.py 和 service/vector_store.py，
    保持 per_document / cross-collection 搜索逻辑不变。
    """

    document_id: Optional[int] = Field(default=None, description="限定检索的文档 ID")
    top_k: int = Field(default=5, ge=1, le=20, description="检索返回的文档块数量")
    relevance_threshold: float = Field(
        default=0.7, description="余弦距离上限，超过此值的块被丢弃"
    )

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        """执行向量检索并返回 LangChain Document 列表.

        Args:
            query: 用户问题文本（可能已被 history_aware_retriever 改写）.

        Returns:
            LangChain Document 列表，每个 Document 的 metadata 包含原检索结果的所有字段.
        """
        from service.embedder import embed_query_service
        from service.vector_store import search_service

        # 1. 向量化
        query_embedding = embed_query_service(query)

        # 2. ChromaDB 检索
        search_results = search_service(
            query_embedding,
            top_k=self.top_k,
            document_id=self.document_id,
        )

        # 3. 余弦距离过滤
        docs = []
        for r in search_results:
            distance = r.get("score", float("inf"))
            if distance > self.relevance_threshold:
                continue

            title = r.get("title", "未知文档")
            chunk_idx = r.get("chunk_index", 0)
            content = r.get("text", "")

            if not content or not content.strip():
                continue

            doc = Document(
                page_content=content,
                metadata={
                    "document_id": r.get("document_id"),
                    "document_title": title,
                    "chunk_index": chunk_idx,
                    "distance": round(distance, 4),
                    "source": f"{title} - 第{chunk_idx}块",
                },
            )
            docs.append(doc)

        logger.info(
            "ChromaRetriever: query='%s' → %d results → %d after filtering (threshold=%.2f)",
            query[:60], len(search_results), len(docs), self.relevance_threshold,
        )
        return docs


# ── 文档格式化 ─────────────────────────────────────────────────────────

def format_docs(docs: List[Document]) -> str:
    """将检索到的 Document 列表拼接为 Prompt 参考资料文本.

    Args:
        docs: LangChain Document 列表.

    Returns:
        格式化后的参考资料字符串.
    """
    parts = []
    for i, doc in enumerate(docs, 1):
        title = doc.metadata.get("document_title", "未知文档")
        chunk_idx = doc.metadata.get("chunk_index", "?")
        content = doc.page_content.strip()
        if content:
            parts.append(f"[资料{i}] 来源：《{title}》（第{chunk_idx}块）\n{content}")
    return "\n\n".join(parts)


# ── Prompt 模板 ────────────────────────────────────────────────────────

# 查询改写 System Prompt（将多轮追问转为独立问题）
_CONTEXTUALIZE_SYSTEM_PROMPT = """你是一个查询改写助手。你的任务是结合对话历史，将用户的追问改写为一个语义完整的独立问题。

规则：
1. 如果用户问题本身已经是完整独立的，直接返回原问题
2. 如果用户问题包含指代词（如"它"、"这个"、"那个"、"除此之外"、"刚才说的"等），结合历史将其替换为具体内容
3. 只输出改写后的问题，不要加任何解释、引号或额外文字
4. 改写后的问题必须保持用户原始意图"""

# RAG 回答 System Prompt（保留原有逻辑，增加多轮对话能力）
RAG_SYSTEM_PROMPT = """你是一个校园智能问答助手。

【多轮对话规则】
  1. 必须结合对话历史理解用户当前问题中的指代关系
     - 如"除此之外"、"刚才说的"、"那个"、"它"、"第二个"等指代词
     - 根据历史推断用户真正想问的内容
  2. 回答时应自然关联之前的讨论内容，保持对话连贯性
  3. 不要在每次回答中重复介绍已经讨论过的背景知识
  4. 如果用户追问"还有吗"、"继续"、"详细说说"，应基于历史中的话题继续展开

【回答策略】请根据用户消息中标注的「可信度级别」选择对应的回答方式：

■ 高可信度模式 — 参考资料与问题高度相关时：
  1. 严格依据【参考资料】回答，不要编造资料中没有的信息
  2. 在回答中体现依据来源（如"根据《XX》文档第X块..."）
  3. 回答要清晰、准确、适合学生理解
  4. **严格禁止**在回答中使用"基于通用知识"、"暂无直接依据"、"仅供参考"等免责声明表述
  5. **严格禁止**输出任何形式的"以下回答基于通用知识"前缀

■ 中可信度模式 — 参考资料部分相关但不完全匹配时：
  1. 优先结合参考资料中相关的部分进行回答
  2. 如果参考资料提供了有用的背景信息，可以在其基础上做适当延伸
  3. 在回答中尽可能区分「来自资料的信息」和「基于知识的延伸说明」
  4. 回答要清晰、准确、适合学生理解
  5. **严格禁止**在回答中使用"基于通用知识"、"暂无直接依据"等免责声明表述

■ 通用知识模式 — 参考资料不相关或缺失时：
  1. 基于你自己的知识进行回答，不需要参考【参考资料】
  2. 必须在回答开头加上声明：
     「⚠️ 以下回答基于通用知识，校园资料库中暂无直接依据，仅供参考：」
  3. 回答依然要清晰、准确、适合学生理解
  4. 不要编造看似来自校园资料的虚假引用
  5. 如果有「对话历史」，即使参考资料不相关，也应结合历史上下文回答，保持话题连续性

注意：无论哪种模式，都不要输出与问题无关的内容。"""

# 带可信度级别标记的 User Prompt 模板
RAG_USER_PROMPT_TEMPLATE = """{confidence_instruction}

【参考资料】
{context}

【用户问题】
{input}

请根据可信度级别对应的策略给出回答："""


# ── Chain 构建 ────────────────────────────────────────────────────────

def build_rag_chain(
    llm,
    retriever: BaseRetriever,
) -> Any:
    """构建完整的 LCEL RAG 链.

    链结构:
      input → history_aware_retriever(改写查询 + 检索)
            → format_docs(拼接参考资料)
            → RAG prompt + LLM
            → StrOutputParser

    Args:
        llm: LangChain ChatModel 实例（来自 llm_factory.create_chat_model()）.
        retriever: ChromaRetriever 实例.

    Returns:
        可调用的 LCEL Runnable 对象.
    """
    # 1. 查询改写 + 历史感知检索
    contextualize_prompt = ChatPromptTemplate.from_messages([
        ("system", _CONTEXTUALIZE_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_prompt
    )

    # 2. RAG 回答 prompt
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", RAG_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", RAG_USER_PROMPT_TEMPLATE),
    ])

    # 3. 完整 RAG 链
    # 注意：format_docs 已将 List[Document] 转为 str，
    # 因此直接走 prompt + LLM + StrOutputParser，不使用 create_stuff_documents_chain
    # （后者期望 List[Document] 作为 context，会尝试对每个元素调用 .page_content）
    rag_chain = (
        RunnablePassthrough.assign(
            context=history_aware_retriever | format_docs
        )
        | qa_prompt
        | llm
        | StrOutputParser()
    )

    return rag_chain


# ── 便捷调用 ───────────────────────────────────────────────────────────

# 可信度级别对应的前端指令
_CONFIDENCE_INSTRUCTIONS = {
    "high": "🔵 高可信度模式：参考资料与问题高度相关，请严格依据资料回答并注明来源。",
    "medium": "🟡 中可信度模式：参考资料部分相关，可结合资料并做适当延伸，请区分资料信息和延伸说明。",
    "general": "🔴 通用知识模式：参考资料中未找到直接相关内容，请基于自有知识回答并加免责声明。",
}


def run_rag_chain(
    chain: Any,
    question: str,
    chat_history: List[Any],
    confidence_level: str = "general",
) -> str:
    """执行一次 RAG 链调用.

    Args:
        chain: build_rag_chain() 返回的 LCEL Runnable.
        question: 用户原始问题.
        chat_history: LangChain Message 列表（来自 ConversationMemoryManager）.
        confidence_level: 可信度级别 (high/medium/general).

    Returns:
        LLM 生成的回答文本.
    """
    instruction = _CONFIDENCE_INSTRUCTIONS.get(
        confidence_level, _CONFIDENCE_INSTRUCTIONS["general"]
    )

    result = chain.invoke({
        "input": question,
        "chat_history": chat_history,
        "confidence_instruction": instruction,
    })
    return result
