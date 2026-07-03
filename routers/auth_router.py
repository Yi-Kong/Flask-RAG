"""认证路由注册 — /login, /register."""

from flask import Blueprint

from controller.auth_controller import login_controller, register_controller

auth_bp = Blueprint("auth", __name__)

auth_bp.add_url_rule("/login", "login_controller", login_controller, methods=["GET", "POST"])
auth_bp.add_url_rule("/register", "register_controller", register_controller, methods=["GET", "POST"])
