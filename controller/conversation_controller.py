"""对话管理 API — 视图函数."""

from flask import request

from dto.response import ok
from exceptions import AuthenticationException
from service.qa_service import (create_conversation_service,
                                conversation_detail_service,
                                list_conversations_service)
from utils.auth import get_current_user_id


def conversations_controller():
    """GET: 获取当前用户对话列表; POST: 创建新对话."""
    user_id = get_current_user_id()
    if not user_id:
        raise AuthenticationException("用户不存在")

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "").strip() or "新对话"
        conversation = create_conversation_service(user_id=user_id, title=title)
        return ok(data=conversation.to_dict()), 201

    conversations = list_conversations_service(user_id)
    return ok(data=conversations)


def conversation_detail_controller(conversation_id):
    """获取对话详情（含所有问答记录）."""
    user_id = get_current_user_id()
    if not user_id:
        raise AuthenticationException("用户不存在")

    detail = conversation_detail_service(user_id, conversation_id)
    return ok(data=detail)
