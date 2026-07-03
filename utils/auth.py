"""JWT 认证工具函数 — token 生成 & 用户身份获取.

认证校验逻辑在 middleware/auth_middleware.py 的 ``AuthMiddleware`` 中实现。
认证成功后 payload 存入 ``flask.g.current_user``，通过 ``get_current_user_id()`` 读取。
"""

import datetime

import jwt
from flask import g
from config import Config

# ── JWT 配置 ──────────────────────────────────────────────────
JWT_SECRET_KEY = Config.JWT_SECRET_KEY
JWT_EXPIRATION_HOURS = Config.JWT_EXPIRATION_HOURS


def create_token(user_id: int, username: str, role: str) -> str:
    """生成 JWT token."""
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": now + datetime.timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": now,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")


def get_current_user_id():
    """从 ``flask.g.current_user`` 中安全获取 user_id，兼容旧 token（无 user_id 字段）.

    新 token 直接取 user_id；旧 token 通过 username 查库回退。
    """
    payload = getattr(g, "current_user", {})
    user_id = payload.get("user_id")
    if user_id is not None:
        return user_id
    # 兼容旧 token（无 user_id）：通过 username 查库
    username = payload.get("username")
    if username:
        from dao.user_dao import get_user_by_username
        user = get_user_by_username(username)
        if user:
            return user.id
    return None
