"""文档解析服务 — 从 PDF / Word / TXT / Markdown 提取全文文本."""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def parse_document_service(file_path: str, file_type: str) -> Optional[str]:
    """根据文件类型解析文档，返回提取的全文文本.

    Args:
        file_path: 服务器上文件的绝对/相对路径.
        file_type: 文件类型 (pdf / docx / txt / md / markdown).

    Returns:
        提取到的文本内容；解析失败返回 None.
    """
    file_type = file_type.lower()

    parsers = {
        "pdf": _parse_pdf,
        "docx": _parse_docx,
        "txt": _parse_txt,
        "md": _parse_txt,
        "markdown": _parse_txt,
    }

    parser = parsers.get(file_type)
    if not parser:
        logger.warning("不支持的文件类型: %s", file_type)
        return None

    try:
        return parser(file_path)
    except Exception as e:
        logger.error("解析文档失败 [%s] %s: %s", file_type, file_path, e)
        return None


# ── 各类型解析器 ──────────────────────────────────────────────


def _parse_pdf(file_path: str) -> str:
    """使用 PyPDF2 提取 PDF 文本."""
    from PyPDF2 import PdfReader

    reader = PdfReader(file_path)
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def _parse_docx(file_path: str) -> str:
    """使用 python-docx 提取 Word 文本."""
    from docx import Document as DocxDocument

    doc = DocxDocument(file_path)
    paragraphs: list[str] = []
    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text.strip())
    return "\n".join(paragraphs)


def _parse_txt(file_path: str) -> str:
    """读取纯文本文件（TXT / Markdown），自动尝试常见编码."""
    # 按优先级尝试多种编码
    encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030", "latin-1"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    # 最后兜底：用 utf-8 忽略错误
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()
