"""JWT 认证中间件 — Flask 蓝图级别的 before_request 处理器.

遵循 Flask 框架约定：

- 实现 ``__call__`` 使其可作为 ``blueprint.before_request()`` 的回调
- 认证成功后将 payload 存入 ``flask.g.current_user``（而非直接修改 request 对象）
- 支持两种模式：API 模式（JSON 401）和页面模式（302 重定向）

Usage::

    from middleware.auth_middleware import AuthMiddleware

    # API 蓝图（认证失败返回 401 JSON）
    api_bp = Blueprint("api", __name__, url_prefix="/api/xxx")
    api_bp.before_request(AuthMiddleware())

    # 页面蓝图（认证失败重定向 /login）
    page_bp = Blueprint("page", __name__)
    page_bp.before_request(AuthMiddleware(redirect_on_fail=True))
"""

import jwt
from flask import g, redirect, request

from config import Config
from dto.response import fail


class AuthMiddleware:
    """JWT 认证中间件 — 符合 Flask before_request 规范.

    ``blueprint.before_request`` 要求传入一个无参可调用对象。本类实现 ``__call__``，
    实例化后可直接作为 ``before_request`` 的回调。

    Attributes:
        redirect_on_fail: 认证失败时是否重定向（True=页面模式，False=API 模式）
    """

    def __init__(self, redirect_on_fail: bool = False):
        self.redirect_on_fail = redirect_on_fail
        self._jwt_secret = Config.JWT_SECRET_KEY

    def __call__(self):
        """before_request 回调入口（无参，符合 Flask 规范）."""
        # 1. 静态文件放行
        if request.path.startswith("/static/"):
            return None

        # 2. OPTIONS 预检请求放行（CORS）
        if request.method == "OPTIONS":
            return None

        # 3. 提取 token
        token = self._extract_token()

        # 4. 无 token → 未登录
        if not token:
            return self._unauthorized("请先登录")

        # 5. 校验 token
        try:
            payload = jwt.decode(token, self._jwt_secret, algorithms=["HS256"])
            g.current_user = payload
        except jwt.ExpiredSignatureError:
            return self._unauthorized("token 已过期，请重新登录")
        except jwt.InvalidTokenError:
            return self._unauthorized("token 无效")

        return None

    # ── 内部方法 ──────────────────────────────────────────────────

    def _extract_token(self) -> str | None:
        """从 Cookie 或 Authorization header 提取 token."""
        token = request.cookies.get("token")
        if token:
            return token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        return None

    def _unauthorized(self, message: str):
        """认证失败响应：页面模式重定向，API 模式返回 JSON."""
        if self.redirect_on_fail:
            return redirect("/login")
        return fail(message, 401)
