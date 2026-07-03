"""集中式异常处理器 — 将所有 AppException 子类转换为统一 JSON 响应.

Controller 层从此可以直接 ``raise ValidationException("...")``，
而无需在每个路由中手动 try/except 并调用 ``fail()``。
"""

from flask import Flask, request

from dto.response import fail
from exceptions import (AppException, AuthenticationException,
                        DuplicateResourceException, ForbiddenException,
                        NotFoundException, ServiceException,
                        ValidationException)

# ── 所有 AppException 子类 → HTTP 状态码映射 ──────────────────────
_EXCEPTION_CLASSES = (
    ValidationException,
    AuthenticationException,
    ForbiddenException,
    NotFoundException,
    DuplicateResourceException,
    ServiceException,
)


def register_error_handlers(app: Flask) -> None:
    """注册全局错误处理器，捕获所有自定义异常并返回统一 JSON 响应."""

    # ── 自定义业务异常 ──────────────────────────────────────────
    for exc_class in _EXCEPTION_CLASSES:
        app.register_error_handler(exc_class, _handle_app_exception)

    # ── HTTP 404（路由不存在）────────────────────────────────────
    @app.errorhandler(404)
    def handle_404(e):
        # API 请求返回 JSON，页面请求让 Flask 默认处理
        if _is_api_request():
            return fail("资源不存在", 404)
        return e

    # ── HTTP 500（未捕获的内部错误）──────────────────────────────
    @app.errorhandler(500)
    def handle_500(e):
        if _is_api_request():
            return fail("服务器内部错误", 500)
        return e


def _handle_app_exception(e: AppException):
    """将 AppException 子类转换为 fail() 响应."""
    return fail(e.message, e.status_code)


def _is_api_request() -> bool:
    """判断当前请求是否为 API 请求（返回 JSON）."""
    path = request.path
    # 以 /api/ 开头 或 请求头期望 JSON
    if path.startswith("/api/"):
        return True
    if request.headers.get("Accept") == "application/json":
        return True
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return True
    return False
