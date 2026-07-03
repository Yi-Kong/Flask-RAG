"""对话路由注册 — /api/conversations/*（需要 JWT 认证）."""

from flask import Blueprint

from controller.conversation_controller import (conversation_detail_controller,
                                                conversations_controller)
from middleware.auth_middleware import AuthMiddleware

api_conversations_bp = Blueprint(
    "api_conversations", __name__, url_prefix="/api/conversations"
)

api_conversations_bp.add_url_rule(
    "/", "conversations_controller", conversations_controller, methods=["GET", "POST"]
)
api_conversations_bp.add_url_rule(
    "/<int:conversation_id>", "conversation_detail_controller",
    conversation_detail_controller, methods=["GET"]
)

api_conversations_bp.before_request(AuthMiddleware())
