"""认证服务 — 注册 & 登录业务逻辑."""
import logging

from werkzeug.security import check_password_hash, generate_password_hash

from dao.user_dao import create_user, get_user_by_email, get_user_by_username
from exceptions import (AuthenticationException, DuplicateResourceException,
                        ValidationException)
from utils.auth import create_token

logger = logging.getLogger(__name__)


def register_service(username: str, password: str, email: str, role: str = "student"):
    """校验输入 → 查重 → 哈希密码 → 创建用户.

    Args:
        username: 用户名.
        password: 明文密码（调用方已确认两次输入一致）.
        email: 邮箱.
        role: 角色，默认 "student".

    Returns:
        创建的 User 对象.

    Raises:
        ValidationException: 输入校验失败.
        DuplicateResourceException: 用户名或邮箱已存在.
    """
    # 1. 输入校验
    if not username or len(username) < 2 or len(username) > 50:
        raise ValidationException("用户名长度应为 2-50 个字符")

    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValidationException("请输入有效的邮箱地址")

    if len(password) < 6:
        raise ValidationException("密码长度不能少于 6 位")

    # 2. 查重
    if get_user_by_username(username):
        raise DuplicateResourceException("该用户名已被注册")

    if get_user_by_email(email):
        raise DuplicateResourceException("该邮箱已被注册")

    # 3. 哈希 & 创建
    hashed_pwd = generate_password_hash(password)
    user = create_user(
        username=username,
        password=hashed_pwd,
        email=email,
        role=role,
    )
    logger.info("新用户注册成功: %s (role=%s)", username, role)
    return user


def authenticate_service(username: str, password: str) -> dict:
    """查用户 → 验密码 → 生成 JWT.

    Args:
        username: 用户名.
        password: 明文密码.

    Returns:
        {"user": User对象, "token": JWT字符串}.

    Raises:
        AuthenticationException: 用户不存在或密码错误.
    """
    user = get_user_by_username(username)
    if not user or not check_password_hash(user.password, password):
        raise AuthenticationException("用户名或密码错误")

    token = create_token(user_id=user.id, username=user.username, role=user.role)
    logger.info("用户登录成功: %s (role=%s)", username, user.role)
    return {"user": user, "token": token}
