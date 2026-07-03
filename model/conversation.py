"""对话实体模型."""
from datetime import datetime

from extensions import db
from model.qa_record import QARecord


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False, default="新对话")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = db.relationship(
        "QARecord",
        backref="conversation",
        lazy="dynamic",
        order_by="QARecord.created_at",
    )

    def to_dict(self, include_messages=False):
        message_count = self.messages.count()
        last_message = self.messages.order_by(QARecord.created_at.desc()).first()
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "message_count": message_count,
            "last_preview": last_message.question[:60] if last_message else "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_messages:
            data["messages"] = [m.to_dict() for m in self.messages.all()]
        return data
