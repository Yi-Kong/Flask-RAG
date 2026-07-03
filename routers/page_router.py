"""页面路由注册 — 分为公开蓝图和需登录蓝图.

- ``public_page_bp``：无需认证，直接访问（/, /red）
- ``protected_page_bp``：需要 JWT 认证，未登录跳转 /login（/upload, /qa, /admin/vectors）
"""

from flask import Blueprint

from controller.page_controller import (admin_vectors_page,
                                        coze_page, index_page,
                                        qa_page_page, upload_page_page)
from middleware.auth_middleware import AuthMiddleware

# ── 公开页面蓝图（无需认证）──────────────────────────────────────────
public_page_bp = Blueprint("public_page", __name__)

public_page_bp.add_url_rule("/red", "coze_page", coze_page, methods=["GET", "POST"])

# ── 需登录页面蓝图（JWT 认证，失败重定向 /login）─────────────────────
protected_page_bp = Blueprint("protected_page", __name__)

protected_page_bp.add_url_rule("/", "index_page", index_page)
protected_page_bp.add_url_rule("/upload", "upload_page_page", upload_page_page)
protected_page_bp.add_url_rule("/qa", "qa_page_page", qa_page_page)
protected_page_bp.add_url_rule("/admin/vectors", "admin_vectors_page", admin_vectors_page)

protected_page_bp.before_request(AuthMiddleware(redirect_on_fail=True))
