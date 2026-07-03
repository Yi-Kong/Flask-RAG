"""Application factory — 校园知识库 RAG 系统.

提供 ``create_app()`` 工厂函数，创建并配置 Flask 应用实例。
与 ``run.py`` 分离后，可以通过传入不同的配置类来实现测试配置注入。

Usage::

    from app import create_app
    app = create_app()
"""

import logging
import os

from flask import Flask

from config import Config, validate_config
from extensions import db, migrate
from middleware import register_error_handlers
from routers.router import register_all_blueprints

logger = logging.getLogger(__name__)


def create_app(config_class=Config) -> Flask:
    """创建并配置 Flask 应用.

    Args:
        config_class: 配置类，默认使用 ``Config``。测试时可传入自定义类。

    Returns:
        配置完成的 Flask 应用实例，可用于 ``app.run()`` 或 ``app.test_client()``.
    """
    # ── 校验必需配置（.env 已在 config.py 导入时加载）────────────
    validate_config()

    # ── 创建 Flask 实例 ──────────────────────────────────────────
    app = Flask(__name__, template_folder="view")
    app.config.from_object(config_class)
    app.secret_key = config_class.SECRET_KEY

    # ── 初始化扩展 ───────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)

    # ── 确保上传目录存在 ─────────────────────────────────────────
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ── 注册 Blueprint（委托给 routers/router.py）────────────────
    register_all_blueprints(app)

    # ── 注册错误处理器 ────────────────────────────────────────────
    register_error_handlers(app)

    return app
