"""对话数据访问层."""
import logging

from extensions import db
from model import Conversation

logger = logging.getLogger(__name__)


def get_conversation_by_id(conversation_id):
    """根据 ID 查询对话."""
    return Conversation.query.get(conversation_id)


def get_user_conversations(user_id):
    """获取用户的所有对话列表（按更新时间倒序）."""
    return (
        Conversation.query
        .filter_by(user_id=user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


def create_conversation(user_id, title="新对话"):
    """创建新对话.

    Returns:
        创建的 Conversation 对象.
    """
    conversation = Conversation(user_id=user_id, title=title)
    db.session.add(conversation)
    db.session.commit()
    return conversation


def update_conversation_timestamp(conversation):
    """更新对话的 updated_at 时间戳."""
    from datetime import datetime

    conversation.updated_at = datetime.utcnow()
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
