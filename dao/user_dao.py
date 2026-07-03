"""用户数据访问层."""
from extensions import db
from model import User


def get_user_by_username(username):
    """根据用户名查询用户."""
    return User.query.filter_by(username=username).first()


def get_user_by_email(email):
    """根据邮箱查询用户."""
    return User.query.filter_by(email=email).first()


def get_user_by_id(user_id):
    """根据 ID 查询用户."""
    return User.query.get(user_id)


def create_user(username, password, email, role="student"):
    """创建新用户.

    Returns:
        创建的 User 对象.
    """
    user = User(
        username=username,
        password=password,
        email=email,
        role=role,
    )
    db.session.add(user)
    db.session.commit()
    return user
