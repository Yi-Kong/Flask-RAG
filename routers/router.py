"""路由注册中心 — 统一注册所有 Blueprint.

Usage::

    from routers.router import register_all_blueprints
    register_all_blueprints(app)
"""

from flask import Flask

from routers.admin_router import api_admin_bp
from routers.auth_router import auth_bp
from routers.conversation_router import api_conversations_bp
from routers.document_router import api_documents_bp
from routers.page_router import protected_page_bp, public_page_bp
from routers.qa_router import api_qa_bp


def register_all_blueprints(app: Flask) -> None:
    """将所有 Blueprint 注册到 Flask 应用.

    认证策略：
    - 无 before_request 的蓝图 → 公开访问（auth_bp, public_page_bp）
    - 有 before_request 的蓝图 → JWT 认证自动生效

    ┌────────────────────────┬──────────────┬──────────┬───────────────────┐
    │ Blueprint              │ URL 前缀      │ 认证      │ 来源              │
    ├────────────────────────┼──────────────┼──────────┼───────────────────┤
    │ auth_bp                │ (无)          │ 公开      │ auth_router.py    │
    │ public_page_bp         │ (无)          │ 公开      │ page_router.py    │
    │ protected_page_bp      │ (无)          │ JWT 页面  │ page_router.py    │
    │ api_documents_bp       │ /api/documents│ JWT API  │ document_router   │
    │ api_qa_bp              │ /api/qa       │ JWT API  │ qa_router.py      │
    │ api_conversations_bp   │ /api/conve... │ JWT API  │ conversation_...  │
    │ api_admin_bp           │ /api/admin/.. │ JWT API  │ admin_router.py   │
    └────────────────────────┴──────────────┴──────────┴───────────────────┘
    """
    # 公开蓝图（无 before_request → 无需认证）
    app.register_blueprint(auth_bp)
    app.register_blueprint(public_page_bp)

    # 受保护蓝图（各蓝图内部已注册 before_request → JWT 认证）
    app.register_blueprint(protected_page_bp)
    app.register_blueprint(api_documents_bp)
    app.register_blueprint(api_qa_bp)
    app.register_blueprint(api_conversations_bp)
    app.register_blueprint(api_admin_bp)
