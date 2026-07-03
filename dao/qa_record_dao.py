"""问答记录数据访问层."""
import logging

from extensions import db
from model import QARecord

logger = logging.getLogger(__name__)


def create_qa_record(user_id, conversation_id, question, answer, sources_json, document_id=None, confidence=None):
    """创建问答记录.

    Args:
        user_id: 用户 ID.
        conversation_id: 对话 ID.
        question: 用户问题.
        answer: AI 回答.
        sources_json: 来源 JSON 字符串.
        document_id: 可选，限定文档 ID.
        confidence: 可选，可信度级别 (high/medium/general).

    Returns:
        创建的 QARecord 对象.

    Raises:
        RuntimeError: 数据库写入失败时抛出.
    """
    record = QARecord(
        user_id=user_id,
        conversation_id=conversation_id,
        document_id=document_id,
        question=question,
        answer=answer,
        sources=sources_json,
        confidence=confidence,
    )
    try:
        db.session.add(record)
        db.session.commit()
        logger.info("问答记录已保存: qa_id=%d, conversation_id=%d", record.id, conversation_id)
    except Exception as e:
        db.session.rollback()
        logger.error("保存问答记录失败: %s", e)
        raise RuntimeError(f"问答记录保存失败: {str(e)}")
    return record


def get_qa_history(user_id, conversation_id=None, document_id=None, page=1, page_size=20):
    """分页获取问答历史记录.

    Args:
        user_id: 用户 ID.
        conversation_id: 可选，按对话筛选.
        document_id: 可选，按文档筛选.
        page: 页码，从 1 开始.
        page_size: 每页数量.

    Returns:
        (records, total) 元组.
    """
    query = QARecord.query.filter_by(user_id=user_id)

    if conversation_id:
        query = query.filter_by(conversation_id=conversation_id)
    if document_id:
        query = query.filter_by(document_id=document_id)

    query = query.order_by(QARecord.created_at.desc())

    total = query.count()
    records = query.offset((page - 1) * page_size).limit(page_size).all()

    return records, total


def get_conversation_messages(conversation_id):
    """获取指定对话的所有问答消息（按时间正序）.

    Args:
        conversation_id: 对话 ID.

    Returns:
        QARecord 列表.
    """
    return (
        QARecord.query
        .filter_by(conversation_id=conversation_id)
        .order_by(QARecord.created_at.asc())
        .all()
    )
