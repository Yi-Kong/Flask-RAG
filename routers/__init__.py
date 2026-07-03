"""路由层 — Blueprint 定义与注册.

每个子路由模块独立定义一个 Blueprint：
  - auth_router.py         — auth_bp（登录/注册）
  - page_router.py         — page_bp（HTML 页面渲染）
  - document_router.py     — api_documents_bp（/api/documents）
  - qa_router.py           — api_qa_bp（/api/qa）
  - conversation_router.py — api_conversations_bp（/api/conversations）
  - admin_router.py        — api_admin_bp（/api/admin/vectors）

统一注册入口：``register_all_blueprints(app)``
"""
