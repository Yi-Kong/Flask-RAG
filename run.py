"""Flask 主入口 — 校园知识库 RAG 问答系统.

使用 app factory 模式创建应用，所有配置和 Blueprint 注册
委托给 ``app.create_app()`` 处理，保持入口文件简洁。
"""

import os

from app import create_app

# ── 创建应用实例 ──────────────────────────────────────────────────
app = create_app()

if __name__ == "__main__":
    app.run(
        debug=os.getenv("FLASK_DEBUG", "").strip().lower() in ("true", "1", "yes"),
        port=int(os.getenv("FLASK_PORT", "5001")),
    )
