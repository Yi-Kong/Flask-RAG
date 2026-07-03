"""RAG 智能问答主流程服务.

串联：向量检索 → LLM 相关性校验 → Prompt 构造 → DeepSeek 调用 → 后处理 → 记录保存
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional

from config import Config
from dao.qa_record_dao import create_qa_record

logger = logging.getLogger(__name__)

# ── 可信度级别 ──────────────────────────────────────────────────────

class ConfidenceLevel:
    """RAG 回答可信度级别."""
    HIGH = "high"         # 参考资料高度相关，能直接回答问题
    MEDIUM = "medium"     # 参考资料部分相关，可作参考
    GENERAL = "general"   # 参考资料不相关或缺失，使用通用知识


# ── RAG Prompt 模板 ──────────────────────────────────────────────────

RAG_SYSTEM_PROMPT = """你是一个校园智能问答助手。

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
# 匹配「基于/根据通用知识...暂无直接依据...仅供参考」及其变体
_FALLBACK_DISCLAIMER_RE = re.compile(
    r'(?:⚠️\s*)?'
    r'(?:以下回答)?'
    r'(?:基于|根据)通用知识[,，]?\s*'
    r'校园资料库中暂无(?:直接)?依据[,，]?\s*'
    r'(?:仅供参考)?'
    r'[：:。.、]?\s*',
)


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

    Args:
        question: 用户原始问题.
        filtered_results: 经过余弦距离过滤的检索结果列表.

    Returns:
        {"level": "high|medium|general", "reason": "..."}

    Raises:
        ValueError: API Key 未配置.
        ConnectionError: 网络连接失败.
        TimeoutError: 请求超时.
        RuntimeError: API 返回错误或解析失败.
    """
    from service.deepseek_service import chat_service

    # 构造参考资料文本（复用已有的格式化逻辑）
    chunks_text = format_context_from_sources(filtered_results)
    if not chunks_text.strip():
        logger.warning("相关性校验：过滤后的参考资料文本为空，直接判定为 GENERAL")
        return {"level": ConfidenceLevel.GENERAL, "reason": "参考资料文本为空"}

    messages = _build_relevance_check_messages(question, chunks_text)

    logger.info("LLM 相关性校验开始: question=%s..., chunks_count=%d", question[:50], len(filtered_results))

    # 轻量调用：max_tokens 设为 150（只需解析一个简短 JSON）
    response = chat_service(messages, temperature=0.0, max_tokens=150)

    logger.info("LLM 相关性校验原始响应: %s", response[:200])

    # 解析 JSON 响应
    try:
        result = _parse_relevance_response(response)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("LLM 相关性校验响应解析失败: %s, 原始响应: %s", e, response[:200])
        raise RuntimeError(f"相关性校验响应解析失败: {e}")

    # 校验 level 值有效性
    valid_levels = {ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.GENERAL}
    if result.get("level") not in valid_levels:
        logger.warning("LLM 相关性校验返回无效 level: %s, 回退为 GENERAL", result.get("level"))
        result["level"] = ConfidenceLevel.GENERAL

    logger.info("LLM 相关性校验结果: level=%s, reason=%s", result.get("level"), result.get("reason"))
    return result


def _parse_relevance_response(response: str) -> Dict[str, str]:
    """从 LLM 响应中解析相关性评估 JSON.

    兼容 LLM 可能添加的 markdown 代码块标记。
    """
    # 去除首尾空白
    text = response.strip()

    # 尝试提取 markdown 代码块中的 JSON
    code_block_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if code_block_match:
        text = code_block_match.group(1).strip()

    # 尝试提取第一个 { } 包裹的 JSON 对象
    json_match = re.search(r'\{[^{}]*"level"[^{}]*\}', text, re.DOTALL)
    if json_match:
        text = json_match.group(0)

    result = json.loads(text)
    return {"level": result.get("level", ConfidenceLevel.GENERAL), "reason": result.get("reason", "")}


def strip_fallback_disclaimer(answer: str, confidence_level: str) -> str:
    """HIGH/MEDIUM 模式下，从回答中移除可能被 LLM 误加的免责声明.

    使用正则匹配「基于/根据通用知识...暂无依据...仅供参考」及其各种变体。

    Args:
        answer: LLM 原始回答文本.
        confidence_level: 可信度级别.

    Returns:
        清理后的回答文本.
    """
    if confidence_level not in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM):
        return answer

    original = answer
    answer = _FALLBACK_DISCLAIMER_RE.sub("", answer).strip()

    if answer != original:
        logger.info("已从 %s 置信度回答中剥离免责声明", confidence_level)

    return answer


def build_rag_prompt(context: str, question: str, confidence_level: str = ConfidenceLevel.GENERAL) -> str:
    """构造 RAG 用户提示词，根据可信度级别区分指令.

    Args:
        context: 拼接后的参考资料文本.
        question: 用户原始问题.
        confidence_level: 可信度级别 (high/medium/general).

    Returns:
        完整的用户提示词字符串.
    """
    level_instructions = {
        ConfidenceLevel.HIGH: "🔵 高可信度模式：参考资料与问题高度相关，请严格依据资料回答并注明来源。",
        ConfidenceLevel.MEDIUM: "🟡 中可信度模式：参考资料部分相关，可结合资料并做适当延伸，请区分资料信息和延伸说明。",
        ConfidenceLevel.GENERAL: "🔴 通用知识模式：参考资料中未找到直接相关内容，请基于自有知识回答并加免责声明。",
    }
    instruction = level_instructions.get(confidence_level, level_instructions[ConfidenceLevel.GENERAL])

    return f"""【可信度级别】{instruction}

【参考资料】
{context}

【用户问题】
{question}

请根据可信度级别对应的策略给出回答："""


def format_context_from_sources(sources: List[Dict]) -> str:
    """将检索结果拼接为 Prompt 上下文.

    Args:
        sources: 检索结果列表，每项含 document_title, chunk_index, content.

    Returns:
        拼接后的上下文字符串.
    """
    parts = []
    for i, src in enumerate(sources, 1):
        # 兼容两种键名：标准化结果用 document_title/content，原始检索结果用 title/text
        title = src.get("document_title") or src.get("title", "未知文档")
        chunk_idx = src.get("chunk_index", "?")
        content = (src.get("content") or src.get("text", "")).strip()
        if content:
            parts.append(f"[资料{i}] 来源：{title}（第{chunk_idx}块）\n{content}")
    return "\n\n".join(parts)


def normalize_sources_for_response(search_results: List[Dict]) -> List[Dict]:
    """将 ChromaDB 搜索结果标准化为前端需要的 sources 格式.

    Args:
        search_results: vector_store.search() 返回的结果列表.

    Returns:
        标准化后的 sources 列表.
    """
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


def filter_search_results_by_relevance(
    search_results: List[Dict],
    threshold: float,
) -> List[Dict]:
    """按余弦距离阈值过滤检索结果.

    Args:
        search_results: vector_store.search() 返回的原始结果列表.
        threshold: 余弦距离上限，distance > threshold 的结果被丢弃.

    Returns:
        过滤后的结果列表（保持原顺序）.
    """
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


def classify_confidence(
    filtered_results: List[Dict],
    high_threshold: float,
) -> str:
    """根据过滤后的检索结果判定可信度级别（纯余弦距离，作为 LLM 校验失败时的回退）.

    Args:
        filtered_results: 经过阈值过滤的检索结果.
        high_threshold: 高可信度距离上限，存在任一结果 distance <= high_threshold 即为 HIGH.

    Returns:
        ConfidenceLevel.HIGH / MEDIUM / GENERAL.
    """
    if not filtered_results:
        return ConfidenceLevel.GENERAL

    has_high_quality = any(
        r.get("score", float("inf")) <= high_threshold
        for r in filtered_results
    )
    if has_high_quality:
        return ConfidenceLevel.HIGH
    return ConfidenceLevel.MEDIUM


def rag_ask_service(
    question: str,
    user_id: int,
    conversation_id: int,
    document_id: Optional[int] = None,
    top_k: int = 5,
) -> Dict[str, Any]:
    """执行一次完整的 RAG 问答流程.

    流程：
        1. 问题向量化
        2. ChromaDB 检索 Top-K 文档块
        3. 余弦距离粗过滤
        4. LLM 语义相关性校验 → 确定最终可信度级别
        5. 构造 RAG Prompt
        6. 调用 DeepSeek API 获取回答
        7. 后处理剥离误加的免责声明
        8. 保存问答记录到 QARecord
        9. 返回前端所需数据

    Args:
        question: 用户问题.
        user_id: 当前用户 ID.
        conversation_id: 对话 ID.
        document_id: 限定检索的文档 ID（可选）.
        top_k: 检索返回的文档块数量.

    Returns:
        包含 answer, sources, qa_id 等字段的 dict.

    Raises:
        RuntimeError: 检索或 LLM 调用失败时抛出.
    """
    from service.embedder import embed_query_service
    from service.vector_store import search_service

    # 1. 问题向量化
    logger.info("RAG 问答开始: user_id=%d, conversation_id=%d, top_k=%d", user_id, conversation_id, top_k)
    try:
        query_embedding = embed_query_service(question)
    except Exception as e:
        logger.error("问题向量化失败: %s", e)
        raise RuntimeError(f"问题向量化失败: {str(e)}")

    # 2. ChromaDB 检索
    try:
        search_results = search_service(
            query_embedding,
            top_k=top_k,
            document_id=document_id,
        )
    except Exception as e:
        logger.error("ChromaDB 检索失败: %s", e)
        raise RuntimeError(f"文档检索失败: {str(e)}")

    # 3. 余弦距离粗过滤
    relevance_threshold = getattr(Config, "RAG_RELEVANCE_THRESHOLD", 0.7)
    high_confidence_threshold = getattr(Config, "RAG_HIGH_CONFIDENCE_THRESHOLD", 0.4)
    logger.info(
        "RAG 过滤参数: relevance_threshold=%.2f, high_confidence_threshold=%.2f",
        relevance_threshold, high_confidence_threshold,
    )

    filtered_results = filter_search_results_by_relevance(search_results, relevance_threshold)

    # 4. 判定可信度级别（LLM 语义校验 + 余弦距离回退）
    if not filtered_results:
        # 无任何相关结果，直接判定为 GENERAL，无需调用 LLM 校验
        confidence_level = ConfidenceLevel.GENERAL
        logger.info("RAG 可信度级别: %s（无过滤后结果，跳过 LLM 校验）", confidence_level)
    else:
        # 尝试 LLM 语义相关性校验
        try:
            relevance_result = check_relevance_with_llm(question, filtered_results)
            confidence_level = relevance_result["level"]
            logger.info("RAG 可信度级别: %s（LLM 语义校验: %s）", confidence_level, relevance_result.get("reason"))
        except Exception as e:
            # LLM 校验失败，回退到余弦距离判定
            logger.warning("LLM 相关性校验失败，回退到余弦距离判定: %s", e)
            confidence_level = classify_confidence(filtered_results, high_confidence_threshold)
            logger.info("RAG 可信度级别: %s（余弦距离回退）", confidence_level)

    # 5. 标准化 sources（返回给前端，反映过滤后的结果）
    sources = normalize_sources_for_response(filtered_results)

    # 6. 构造 Prompt（根据可信度级别决定 context 内容）
    if confidence_level in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM):
        context = format_context_from_sources(filtered_results)
        if not context.strip():
            # 上下文实际为空（所有 content 都为空/空白），降级为 GENERAL
            logger.warning("HIGH/MEDIUM 置信度但格式化后上下文为空，降级为 GENERAL")
            confidence_level = ConfidenceLevel.GENERAL
            context = "（校园资料库中未找到与当前问题直接相关的内容，请切换到通用知识模式回答）"
    else:
        context = "（校园资料库中未找到与当前问题直接相关的内容，请切换到通用知识模式回答）"

    user_prompt = build_rag_prompt(context, question, confidence_level)

    # 7. 调用 DeepSeek API 生成回答
    from service.deepseek_service import chat_with_prompt_service

    try:
        answer = chat_with_prompt_service(RAG_SYSTEM_PROMPT, user_prompt)
    except ValueError as e:
        logger.error("DeepSeek 配置错误: %s", e)
        raise RuntimeError(f"大模型配置错误: {str(e)}")
    except TimeoutError as e:
        logger.error("DeepSeek 调用超时: %s", e)
        raise RuntimeError(f"大模型调用超时: {str(e)}")
    except ConnectionError as e:
        logger.error("DeepSeek 连接失败: %s", e)
        raise RuntimeError(f"大模型连接失败: {str(e)}")
    except RuntimeError:
        raise
    except Exception as e:
        logger.error("DeepSeek 调用失败: %s", e)
        raise RuntimeError(f"大模型调用失败: {str(e)}")

    # 8. 后处理：HIGH/MEDIUM 模式下剥离可能被 LLM 误加的免责声明
    answer = strip_fallback_disclaimer(answer, confidence_level)

    # 9. 保存问答记录（使用 DAO）
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
