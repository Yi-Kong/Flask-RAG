"""文本分块服务 — 面向中文的递归分块策略.

支持三级递归分块：段落 → 句子 → 字符级滑动窗口。
每个分块包含文本内容、索引、字符数和来源类型。
"""
import logging
import re
from typing import List, Dict

logger = logging.getLogger(__name__)


def chunk_text_service(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> List[Dict]:
    """将长文本递归拆分为指定大小的分块.

    Args:
        text: 待分块的原始文本.
        chunk_size: 每个分块的最大字符数.
        chunk_overlap: 相邻分块之间的重叠字符数.

    Returns:
        分块列表，每个元素为 dict:
            - text: 分块文本内容
            - index: 0-based 分块序号
            - char_count: 分块字符数
            - source_type: "paragraph" | "sentence" | "character"
    """
    if not text or not text.strip():
        return []

    # 预处理：统一换行符，压缩多余空行
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    if not text:
        return []

    chunks: List[Dict] = []

    # ── 第一级：按段落拆分 ──
    paragraphs = text.split("\n\n")
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(para) <= chunk_size:
            chunks.append(para)
        else:
            # 段落过长，交给句子级拆分
            _split_by_sentence(para, chunk_size, chunk_overlap, chunks)

    # ── 最终编号 ──
    result = []
    for i, chunk_text_content in enumerate(chunks):
        # 计算来源类型
        if "\n" in chunk_text_content.strip():
            source_type = "paragraph"
        elif any(p in chunk_text_content for p in ".。！？；!?;"):
            source_type = "sentence"
        else:
            source_type = "character"

        result.append({
            "text": chunk_text_content,
            "index": i,
            "char_count": len(chunk_text_content),
            "source_type": source_type,
        })

    logger.info(
        "文本分块完成：总计 %d 个分块（paragraph=%d, sentence=%d, character=%d），chunk_size=%d, overlap=%d",
        len(result),
        sum(1 for c in result if c["source_type"] == "paragraph"),
        sum(1 for c in result if c["source_type"] == "sentence"),
        sum(1 for c in result if c["source_type"] == "character"),
        chunk_size,
        chunk_overlap,
    )

    return result


# ── 内部辅助函数 ────────────────────────────────────────────────


def _split_by_sentence(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    out_chunks: List[str],
) -> None:
    """按中文/英文标点拆分句子，尽量保持语义完整."""
    # 按句末标点拆分（中英文）
    sentences = re.split(r"(?<=[.。！？；!?;])\s*", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return

    current = ""
    for sentence in sentences:
        # 如果单个句子就超过 chunk_size，交给字符级拆分
        if len(sentence) > chunk_size:
            # 先保存当前累积的文本
            if current:
                out_chunks.append(current.strip())
                current = ""
            _split_by_character(sentence, chunk_size, chunk_overlap, out_chunks)
            continue

        # 尝试合并句子
        candidate = (current + " " + sentence).strip() if current else sentence

        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                out_chunks.append(current.strip())
            current = sentence

    # 残留文本
    if current:
        out_chunks.append(current.strip())


def _split_by_character(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    out_chunks: List[str],
) -> None:
    """字符级滑动窗口拆分 — 最终兜底策略."""
    if len(text) <= chunk_size:
        out_chunks.append(text)
        return

    step = chunk_size - chunk_overlap
    if step <= 0:
        step = chunk_size  # 防止无效步长

    for start in range(0, len(text), step):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            out_chunks.append(chunk)
