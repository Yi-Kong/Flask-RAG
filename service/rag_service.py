"""RAG 智能问答主流程服务.

串联：向量检索 → LLM 相关性校验 → LCEL RAG 链 → 后处理 → 记录保存

LangChain 重构后：
  - 对话历史管理：service/conversation_memory.py (LangChain ChatMessageHistory)
  - 检索链路：service/rag_chain.py (ChromaRetriever + LCEL chain)
  - LLM 调用：service/deepseek_service.py（兼容层，委托 LangChain ChatOpenAI）
  - 本文件负责：置信度分类 + 流程编排 + 后处理 + 持久化
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import BaseMessage

from config import Config
from dao.qa_record_dao import create_qa_record

logger = logging.getLogger(__name__)

# ── 可信度级别 ──────────────────────────────────────────────────────

class ConfidenceLevel:
    """RAG 回答可信度级别."""
    HIGH = "high"         # 参考资料高度相关，能直接回答问题
    MEDIUM = "medium"     # 参考资料部分相关，可作参考
    GENERAL = "general"   # 参考资料不相关或缺失，使用通用知识


# ── RAG Prompt 模板（保留，供 rag_chain.py 使用）─────────────────────

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


# ── LLM 相关性校验 Prompt ──────────────────────────────────────────

RELEVANCE_CHECK_USER_PROMPT = """请判断以下【参考资料】是否能有效回答【用户问题】。

评估标准：
- "high": 资料包含能直接回答问题的关键信息
- "medium": 资料包含相关背景信息，可部分参考但不能完整回答
- "general": 资料与问题不相关，或信息完全不足以回答

【用户问题】
{question}

【参考资料】
{chunks}

请只回复一个 JSON 对象，不要加其他内容：
{{"level": "high或medium或general", "reason": "一句话理由"}}"""


# ── 免责声明剥离 ────────────────────────────────────────────────────

# HIGH/MEDIUM 模式下用于剥离 LLM 误输出的免责声明的正则表达式
_FALLBACK_DISCLAIMER_RE = re.compile(
    r'(?:⚠️\s*)?'
    r'(?:以下回答)?'
    r'(?:基于|根据)通用知识[,，]?\s*'
    r'校园资料库中暂无(?:直接)?依据[,，]?\s*'
    r'(?:仅供参考)?'
    r'[：:。.、]?\s*',
)


# ── 相关性校验（保留原逻辑，仍调用兼容的 chat_service）─────────────

def _build_relevance_check_messages(question: str, chunks_text: str) -> list:
    """构造相关性校验的 messages（system + user）."""
    system_prompt = (
        "你是一个文档相关性评估助手。"
        "你只回复一个 JSON 对象，不添加任何其他文字、解释或 markdown 标记。"
    )
    user_prompt = RELEVANCE_CHECK_USER_PROMPT.format(
        question=question,
        chunks=chunks_text,
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def check_relevance_with_llm(question: str, filtered_results: List[Dict]) -> Dict[str, str]:
    """调用 LLM 判断检索文本块与问题的语义相关性.

    这是一个轻量调用：短 prompt + 短 JSON 回复，
    用于替代纯余弦距离判定的置信度分类。
    """
    from service.deepseek_service import chat_service

    # 构造参考资料文本
    chunks_text = _format_context_from_sources(filtered_results)
    if not chunks_text.strip():
        logger.warning("相关性校验：过滤后的参考资料文本为空，直接判定为 GENERAL")
        return {"level": ConfidenceLevel.GENERAL, "reason": "参考资料文本为空"}

    messages = _build_relevance_check_messages(question, chunks_text)

    logger.info("LLM 相关性校验开始: question=%s..., chunks_count=%d", question[:50], len(filtered_results))

    response = chat_service(messages, temperature=0.0, max_tokens=150)

    logger.info("LLM 相关性校验原始响应: %s", response[:200])

    try:
        result = _parse_relevance_response(response)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("LLM 相关性校验响应解析失败: %s, 原始响应: %s", e, response[:200])
        raise RuntimeError(f"相关性校验响应解析失败: {e}")

    valid_levels = {ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.GENERAL}
    if result.get("level") not in valid_levels:
        logger.warning("LLM 相关性校验返回无效 level: %s, 回退为 GENERAL", result.get("level"))
        result["level"] = ConfidenceLevel.GENERAL

    logger.info("LLM 相关性校验结果: level=%s, reason=%s", result.get("level"), result.get("reason"))
    return result


def _parse_relevance_response(response: str) -> Dict[str, str]:
    """从 LLM 响应中解析相关性评估 JSON."""
    text = response.strip()

    code_block_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if code_block_match:
        text = code_block_match.group(1).strip()

    json_match = re.search(r'\{[^{}]*"level"[^{}]*\}', text, re.DOTALL)
    if json_match:
        text = json_match.group(0)

    result = json.loads(text)
    return {"level": result.get("level", ConfidenceLevel.GENERAL), "reason": result.get("reason", "")}


def strip_fallback_disclaimer(answer: str, confidence_level: str) -> str:
    """HIGH/MEDIUM 模式下，从回答中移除可能被 LLM 误加的免责声明."""
    if confidence_level not in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM):
        return answer

    original = answer
    answer = _FALLBACK_DISCLAIMER_RE.sub("", answer).strip()

    if answer != original:
        logger.info("已从 %s 置信度回答中剥离免责声明", confidence_level)

    return answer


# ── 上下文格式化（轻量，供相关性校验和 rag_chain 使用）─────────────

def _format_context_from_sources(sources: List[Dict]) -> str:
    """将检索结果拼接为 Prompt 上下文."""
    parts = []
    for i, src in enumerate(sources, 1):
        title = src.get("document_title") or src.get("title", "未知文档")
        chunk_idx = src.get("chunk_index", "?")
        content = (src.get("content") or src.get("text", "")).strip()
        if content:
            parts.append(f"[资料{i}] 来源：{title}（第{chunk_idx}块）\n{content}")
    return "\n\n".join(parts)


# ── Sources 标准化 ──────────────────────────────────────────────────

def normalize_sources_for_response(search_results: List[Dict]) -> List[Dict]:
    """将 ChromaDB 搜索结果标准化为前端需要的 sources 格式."""
    normalized = []
    for r in search_results:
        normalized.append({
            "document_id": r.get("document_id"),
            "document_title": r.get("title", "未知文档"),
            "chunk_index": r.get("chunk_index", 0),
            "content": r.get("text", ""),
            "distance": round(r.get("score", 0.0), 4),
            "source": f"{r.get('title', '未知文档')} - 第{r.get('chunk_index', '?')}块",
        })
    return normalized


# ── 余弦距离过滤 ────────────────────────────────────────────────────

def filter_search_results_by_relevance(
    search_results: List[Dict],
    threshold: float,
) -> List[Dict]:
    """按余弦距离阈值过滤检索结果."""
    if not search_results:
        return []
    filtered = [r for r in search_results if r.get("score", float("inf")) <= threshold]
    discarded = len(search_results) - len(filtered)
    if discarded > 0:
        logger.info(
            "相关性过滤：%d/%d 条结果被丢弃（阈值=%.2f）",
            discarded, len(search_results), threshold,
        )
    return filtered


# ── 余弦距离置信度回退 ──────────────────────────────────────────────

def classify_confidence(
    filtered_results: List[Dict],
    high_threshold: float,
) -> str:
    """根据过滤后的检索结果判定可信度级别（纯余弦距离，LLM 校验失败时回退）."""
    if not filtered_results:
        return ConfidenceLevel.GENERAL

    has_high_quality = any(
        r.get("score", float("inf")) <= high_threshold
        for r in filtered_results
    )
    if has_high_quality:
        return ConfidenceLevel.HIGH
    return ConfidenceLevel.MEDIUM


# ── 主流程：RAG 问答 ─────────────────────────────────────────────────

def rag_ask_service(
    question: str,
    user_id: int,
    conversation_id: int,
    document_id: Optional[int] = None,
    top_k: int = 5,
    chat_history: Optional[List[BaseMessage]] = None,
) -> Dict[str, Any]:
    """执行一次完整的 RAG 问答流程.

    流程：
        1. 向量检索 + 余弦距离过滤 + LLM 相关性校验 → 确定可信度级别
        2. 构建 LCEL RAG 链（含历史感知检索）
        3. 调用链获取回答
        4. 后处理剥离误加的免责声明
        5. 保存问答记录到 QARecord

    Args:
        question: 用户原始问题.
        user_id: 当前用户 ID.
        conversation_id: 对话 ID.
        document_id: 限定检索的文档 ID（可选）.
        top_k: 检索返回的文档块数量.
        chat_history: LangChain Message 列表（来自 ConversationMemoryManager）.

    Returns:
        包含 answer, sources, qa_id 等字段的 dict.

    Raises:
        RuntimeError: 检索或 LLM 调用失败时抛出.
    """
    from service.embedder import embed_query_service
    from service.vector_store import search_service
    from service.llm_factory import get_rag_llm
    from service.rag_chain import ChromaRetriever, build_rag_chain, run_rag_chain

    logger.info(
        "RAG 问答开始: user_id=%d, conversation_id=%d, top_k=%d, has_history=%s",
        user_id, conversation_id, top_k, bool(chat_history),
    )

    # ── 阶段 1：向量检索 + 置信度分类 ──

    # 1a. 问题向量化
    try:
        query_embedding = embed_query_service(question)
    except Exception as e:
        logger.error("问题向量化失败: %s", e)
        raise RuntimeError(f"问题向量化失败: {str(e)}")

    # 1b. ChromaDB 检索
    try:
        search_results = search_service(
            query_embedding,
            top_k=top_k,
            document_id=document_id,
        )
    except Exception as e:
        logger.error("ChromaDB 检索失败: %s", e)
        raise RuntimeError(f"文档检索失败: {str(e)}")

    # 1c. 余弦距离过滤 + 置信度分类
    relevance_threshold = getattr(Config, "RAG_RELEVANCE_THRESHOLD", 0.7)
    high_confidence_threshold = getattr(Config, "RAG_HIGH_CONFIDENCE_THRESHOLD", 0.4)

    filtered_results = filter_search_results_by_relevance(search_results, relevance_threshold)

    if not filtered_results:
        confidence_level = ConfidenceLevel.GENERAL
        logger.info("RAG 可信度级别: %s（无过滤后结果）", confidence_level)
    else:
        try:
            relevance_result = check_relevance_with_llm(question, filtered_results)
            confidence_level = relevance_result["level"]
            logger.info("RAG 可信度级别: %s（LLM 语义校验: %s）", confidence_level, relevance_result.get("reason"))
        except Exception as e:
            logger.warning("LLM 相关性校验失败，回退到余弦距离判定: %s", e)
            confidence_level = classify_confidence(filtered_results, high_confidence_threshold)
            logger.info("RAG 可信度级别: %s（余弦距离回退）", confidence_level)

    # 1d. 标准化 sources（供前端展示）
    sources = normalize_sources_for_response(filtered_results)

    # ── 阶段 2：构建 RAG 链并生成回答 ──

    llm = get_rag_llm()
    retriever = ChromaRetriever(
        document_id=document_id,
        top_k=top_k,
        relevance_threshold=relevance_threshold,
    )
    chain = build_rag_chain(llm, retriever)
    history = chat_history or []

    try:
        answer = run_rag_chain(chain, question, history, confidence_level)
    except ValueError as e:
        logger.error("LLM 配置错误: %s", e)
        raise RuntimeError(f"大模型配置错误: {str(e)}")
    except TimeoutError as e:
        logger.error("LLM 调用超时: %s", e)
        raise RuntimeError(f"大模型调用超时: {str(e)}")
    except ConnectionError as e:
        logger.error("LLM 连接失败: %s", e)
        raise RuntimeError(f"大模型连接失败: {str(e)}")
    except RuntimeError:
        raise
    except Exception as e:
        logger.error("LLM 调用失败: %s", e, exc_info=True)
        raise RuntimeError(f"大模型调用失败: {str(e)}")

    # ── 阶段 3：后处理 ──

    answer = strip_fallback_disclaimer(answer, confidence_level)

    # ── 阶段 4：持久化 ──

    sources_json = json.dumps(sources, ensure_ascii=False)
    record = create_qa_record(
        user_id=user_id,
        conversation_id=conversation_id,
        question=question,
        answer=answer,
        sources_json=sources_json,
        document_id=document_id,
        confidence=confidence_level,
    )

    return {
        "qa_id": record.id,
        "question": question,
        "answer": answer,
        "sources": sources,
        "confidence": confidence_level,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
