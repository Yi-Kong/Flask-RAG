"""文档服务 — 上传管道编排 & 列表查询.

上传流程：写入DB → 解析 → 分块 → 嵌入 → 向量存储 → 状态更新
（文件校验和保存由 Controller 层负责）
失败时自动回滚 DB 记录并清理文件。
"""
import logging
import os

from dao.document_dao import (create_document, get_all_documents,
                               rollback_document, update_document_status)
from exceptions import NotFoundException, ServiceException, ValidationException

logger = logging.getLogger(__name__)


def _cleanup_files(save_path: str) -> None:
    """清理上传文件和解析文本文件（best-effort）."""
    for path in (save_path, save_path + ".parsed.txt"):
        try:
            os.remove(path)
        except OSError:
            pass


def upload_document_service(
    save_path: str,
    ext: str,
    original_filename: str,
    title_override: str,
    uploaded_by: int,
    config: dict,
):
    """完整文档上传管道.

    Args:
        save_path: 已保存到磁盘的文件路径（由 Controller 层负责保存）.
        ext: 文件扩展名（不含点号，如 "pdf"）.
        original_filename: 安全化处理后的原始文件名.
        title_override: 用户指定的标题（可为空，回退到文件名）.
        uploaded_by: 上传用户的 ID.
        config: 配置字典 {CHUNK_SIZE, CHUNK_OVERLAP}.

    Returns:
        Document 对象（status="ready"）.

    Raises:
        ValidationException: 解析/分块为空.
        ServiceException: DB/解析/分块/嵌入/向量存储失败.
    """
    # ── 1. 确定标题 ──
    title = title_override.strip()
    if not title:
        title = original_filename.rsplit(".", 1)[0] if "." in original_filename else original_filename

    # ── 2. 创建数据库记录 ──
    try:
        document = create_document(
            title=title,
            filename=original_filename,
            file_type=ext,
            file_path=os.path.basename(save_path),
            uploaded_by=uploaded_by,
        )
    except Exception as e:
        logger.error("数据库写入失败: %s", e)
        _cleanup_files(save_path)
        raise ServiceException("文档记录保存失败")

    # ── 3. 文档解析 ──
    from service.document_parser import parse_document_service

    try:
        full_text = parse_document_service(save_path, ext)
    except Exception as e:
        update_document_status(document, "failed")
        logger.error("文档解析失败: %s", e)
        raise ServiceException(f"文档解析失败: {str(e)}")

    if not full_text:
        update_document_status(document, "failed")
        raise ValidationException("文档内容为空，无法解析")

    # 保存解析结果（调试/审计用）
    with open(save_path + ".parsed.txt", "w", encoding="utf-8") as f:
        f.write(full_text)

    # ── 4. 文本分块 ──
    from service.chunker import chunk_text_service

    chunk_size = config["CHUNK_SIZE"]
    chunk_overlap = config["CHUNK_OVERLAP"]
    try:
        chunks = chunk_text_service(full_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    except Exception as e:
        update_document_status(document, "failed")
        logger.error("文本分块失败: %s", e)
        raise ServiceException(f"文本分块失败: {str(e)}")

    if not chunks:
        update_document_status(document, "failed")
        raise ValidationException("文档分块结果为空")

    # ── 5. 向量嵌入 ──
    from service.embedder import embed_texts_service

    try:
        chunk_texts = [c["text"] for c in chunks]
        embeddings = embed_texts_service(chunk_texts)
    except Exception as e:
        update_document_status(document, "failed")
        logger.error("向量嵌入失败: %s", e)
        raise ServiceException(f"向量嵌入失败: {str(e)}")

    # ── 6. 存入向量数据库 ──
    from service.vector_store import add_chunks_service, delete_document_service

    try:
        # 先清理旧分块（确保幂等）
        delete_document_service(document.id)
        chunk_count = add_chunks_service(
            document_id=document.id,
            chunks=chunks,
            embeddings=embeddings,
            title=title,
            file_type=ext,
        )
        update_document_status(document, "ready", chunk_count=chunk_count)
    except Exception as e:
        # 向量存储失败 → 回滚 DB 记录 + 清理文件
        rollback_document(document)
        _cleanup_files(save_path)
        logger.error("向量存储失败，已回滚上传: %s", e)
        raise ServiceException(f"向量存储失败: {str(e)}")

    logger.info("文档上传完成: '%s' (id=%d, chunks=%d)", title, document.id, chunk_count)
    return document


def list_documents_service() -> list:
    """获取全部文档列表（转为 dict）."""
    documents = get_all_documents()
    return [d.to_dict() for d in documents]
