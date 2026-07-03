"""管理路由注册 — /api/admin/vectors/*（需要 JWT 认证）."""

from flask import Blueprint

from controller.admin_controller import (vectors_chunks_controller,
                                         vectors_overview_controller,
                                         vectors_search_controller)
from middleware.auth_middleware import AuthMiddleware

api_admin_bp = Blueprint(
    "api_admin", __name__, url_prefix="/api/admin/vectors"
)

api_admin_bp.add_url_rule(
    "/overview", "vectors_overview_controller", vectors_overview_controller
)
api_admin_bp.add_url_rule(
    "/chunks", "vectors_chunks_controller", vectors_chunks_controller
)
api_admin_bp.add_url_rule(
    "/search", "vectors_search_controller", vectors_search_controller
)

api_admin_bp.before_request(AuthMiddleware())
