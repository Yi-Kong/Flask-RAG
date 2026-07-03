"""问答记录实体模型."""
from datetime import datetime

from extensions import db
from utils.text_helpers import normalize_answer


class QARecord(db.Model):
    __tablename__ = "qa_records"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    conversation_id = db.Column(
        db.Integer, db.ForeignKey("conversations.id"), nullable=True, index=True
    )
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    sources = db.Column(db.Text, nullable=True)  # JSON string
    confidence = db.Column(db.String(20), nullable=True, default=None)  # high/medium/general
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "username": self.user.username if self.user else None,
            "document_id": self.document_id,
            "question": self.question,
            "answer": normalize_answer(self.answer),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
