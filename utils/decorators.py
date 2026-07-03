"""路由装饰器 — 标记路由的访问控制属性."""


def public(f):
    """标记路由为公开访问（无需 JWT 认证）.

    认证中间件通过检测被装饰函数的 ``_is_public`` 属性来决定是否跳过
    JWT 校验。只需在不需要认证的路由上添加 ``@public`` 即可，
    无需修改中间件代码。

    Usage::

        @auth_bp.route("/login")
        @public
        def login():
            ...
    """
    f._is_public = True
    return f
