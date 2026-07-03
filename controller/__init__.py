"""控制器层 — 请求处理函数（纯业务逻辑，不含路由注册）.

路由映射由 ``routers/`` 目录统一管理，本目录只定义视图函数。

├── auth_controller.py       — 登录 / 注册
├── page_controller.py       — HTML 页面渲染
├── document_controller.py   — 文档上传 & 列表
├── qa_controller.py         — 智能问答
├── conversation_controller.py — 对话管理
└── admin_controller.py      — 向量库管理
"""
