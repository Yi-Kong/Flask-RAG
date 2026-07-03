"""文档实体模型."""
from datetime import datetime

from extensions import db


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    chunk_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="processing")  # processing/ready/failed
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    qa_records = db.relationship("QARecord", backref="document", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "filename": self.filename,
            "file_type": self.file_type,
            "chunk_count": self.chunk_count,
            "status": self.status,
            "uploaded_by": self.uploaded_by,
            "uploader_name": self.uploader.username if self.uploader else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
