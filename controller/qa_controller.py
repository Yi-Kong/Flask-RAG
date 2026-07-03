"""智能问答 API — 视图函数."""

from flask import request

from dto.response import ok
from exceptions import AuthenticationException
from service.qa_service import ask_question_service, qa_history_service
from utils.auth import get_current_user_id


def qa_ask_controller():
    """提交问题，执行 RAG 问答."""
    data = request.get_json(silent=True) or {}

    question = (data.get("question") or "").strip()
    conversation_id = data.get("conversation_id")
    document_id = data.get("document_id")
    top_k = data.get("top_k", 5)

    if not isinstance(top_k, int) or top_k < 1:
        top_k = 5
    if top_k > 20:
        top_k = 20

    user_id = get_current_user_id()
    if not user_id:
        raise AuthenticationException("用户不存在")

    result = ask_question_service(
        question=question,
        user_id=user_id,
        conversation_id=conversation_id,
        document_id=document_id,
        top_k=top_k,
    )

    return ok(data=result)


def qa_history_controller():
    """获取当前用户的问答历史（支持分页和筛选）."""
    user_id = get_current_user_id()
    if not user_id:
        raise AuthenticationException("用户不存在")

    conversation_id = request.args.get("conversation_id", type=int)
    document_id = request.args.get("document_id", type=int)
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)

    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100

    result = qa_history_service(
        user_id=user_id,
        conversation_id=conversation_id,
        document_id=document_id,
        page=page,
        page_size=page_size,
    )

    return ok(data=result)
