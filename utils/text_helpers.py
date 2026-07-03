"""文本处理工具函数."""


def normalize_answer(text: str) -> str:
    """规范化回答文本：去除首尾空白，统一换行符."""
    if not text:
        return ""
    return text.strip().replace("\r\n", "\n").replace("\r", "\n")
