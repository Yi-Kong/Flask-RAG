"""自定义异常类 — 业务层向控制器层抛出，控制器据此决定 HTTP 状态码.

所有异常类继承自 AppException，包含 status_code 和 message 属性。
控制器只需捕获这些异常并返回对应的 HTTP 响应，
不再通过字符串匹配错误消息来判断状态码。
"""


class AppException(Exception):
    """应用层异常基类."""
    status_code: int = 500

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)


class ValidationException(AppException):
    """400 — 客户端输入不合法（缺少必填字段、格式错误等）."""
    status_code = 400


class AuthenticationException(AppException):
    """401 — 未认证或凭证错误."""
    status_code = 401


class ForbiddenException(AppException):
    """403 — 已认证但无权限访问（如对话不属于当前用户）."""
    status_code = 403


class NotFoundException(AppException):
    """404 — 资源不存在."""
    status_code = 404


class DuplicateResourceException(AppException):
    """409 — 资源冲突（用户名或邮箱已占用）."""
    status_code = 409


class ServiceException(AppException):
    """500 — 服务层内部错误（嵌入/LLM/DB/向量存储等）."""
    status_code = 500
