"""文档数据访问层."""
from extensions import db
from model import Document


def get_all_documents():
    """获取全部文档列表（按创建时间倒序）."""
    return (
        Document.query
        .order_by(Document.created_at.desc())
        .all()
    )


def get_document_by_id(document_id):
    """根据 ID 查询文档."""
    return Document.query.get(document_id)


def create_document(title, filename, file_type, file_path, uploaded_by):
    """创建文档记录.

    Returns:
        创建的 Document 对象.
    """
    document = Document(
        title=title,
        filename=filename,
        file_type=file_type,
        file_path=file_path,
        chunk_count=0,
        status="processing",
        uploaded_by=uploaded_by,
    )
    db.session.add(document)
    db.session.commit()
    return document


def update_document_status(document, status, chunk_count=None):
    """更新文档状态和分块数.

    Args:
        document: Document 模型实例.
        status: 新状态 (processing/ready/failed).
        chunk_count: 可选，分块数量.
    """
    document.status = status
    if chunk_count is not None:
        document.chunk_count = chunk_count
    db.session.commit()


def delete_document_record(document):
    """删除文档记录（不回滚事务，由调用方管理事务）."""
    db.session.delete(document)
    db.session.commit()


def rollback_document(document):
    """向量存储失败时回滚数据库记录.

    仅处理 DB 层面的回滚和删除，文件清理由 Service 层负责。

    Args:
        document: Document 模型实例.
    """
    db.session.rollback()
    db.session.delete(document)
    db.session.commit()
