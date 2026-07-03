"""文档路由注册 — /api/documents/*（需要 JWT 认证）."""

from flask import Blueprint

from controller.document_controller import (document_list_controller,
                                            upload_document_controller)
from middleware.auth_middleware import AuthMiddleware

api_documents_bp = Blueprint("api_documents", __name__, url_prefix="/api/documents")

api_documents_bp.add_url_rule(
    "/upload", "upload_document_controller", upload_document_controller, methods=["POST"]
)
api_documents_bp.add_url_rule(
    "/", "document_list_controller", document_list_controller, methods=["GET"]
)

api_documents_bp.before_request(AuthMiddleware())
