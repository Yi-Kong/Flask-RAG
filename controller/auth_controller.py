"""登录 & 注册 — 视图函数."""

from flask import (flash, make_response, redirect, render_template,
                   request)

from config import Config
from dto.response import ok
from exceptions import (AuthenticationException, DuplicateResourceException,
                        ValidationException)
from service.auth_service import authenticate_service, register_service


def login_controller():
    """GET: 渲染登录页面; POST: 处理登录表单."""
    if request.method == "POST":
        username = request.form.get("user")
        pwd = request.form.get("pwd")

        try:
            result = authenticate_service(username, pwd)
        except AuthenticationException as e:
            flash(e.message)
            return redirect("/login")

        user = result["user"]
        token = result["token"]

        # AJAX / API 请求 → 返回 JSON
        if (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or request.headers.get("Accept") == "application/json"
        ):
            return ok(token=token, username=user.username, role=user.role)

        # 普通表单提交 → 设置 httpOnly cookie + 跳转
        resp = make_response(redirect("/"))
        resp.set_cookie(
            "token",
            token,
            max_age=Config.COOKIE_MAX_AGE,
            httponly=Config.COOKIE_HTTPONLY,
            samesite=Config.COOKIE_SAMESITE,
        )
        return resp

    return render_template("login.html")


def register_controller():
    """GET: 渲染注册页面; POST: 处理注册表单."""
    if request.method == "POST":
        username = request.form.get("user")
        pwd = request.form.get("pwd")
        pwd_confirm = request.form.get("pwd_confirm")
        email = request.form.get("email", "").strip()
        role = request.form.get("role", "student")

        if not username or not pwd or not email:
            flash("用户名、邮箱和密码不能为空")
            return redirect("/register")

        if pwd != pwd_confirm:
            flash("两次输入的密码不一致")
            return redirect("/register")

        try:
            register_service(username=username, password=pwd, email=email, role=role)
        except ValidationException as e:
            flash(e.message)
            return redirect("/register")
        except DuplicateResourceException as e:
            flash(e.message)
            return redirect("/register")

        flash("注册成功，请登录")
        return redirect("/login")

    return render_template("register.html")
