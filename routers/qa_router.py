"""问答路由注册 — /api/qa/*（需要 JWT 认证）."""

from flask import Blueprint

from controller.qa_controller import qa_ask_controller, qa_history_controller
from middleware.auth_middleware import AuthMiddleware

api_qa_bp = Blueprint("api_qa", __name__, url_prefix="/api/qa")

api_qa_bp.add_url_rule("/ask", "qa_ask_controller", qa_ask_controller, methods=["POST"])
api_qa_bp.add_url_rule("/history", "qa_history_controller", qa_history_controller, methods=["GET"])

api_qa_bp.before_request(AuthMiddleware())
