"""问答服务 — 对话管理 & 历史查询业务逻辑."""
import logging

from dao.conversation_dao import (create_conversation as dao_create_conv,
                                   get_conversation_by_id,
                                   get_user_conversations,
                                   update_conversation_timestamp)
from dao.document_dao import get_document_by_id
from dao.qa_record_dao import get_conversation_messages, get_qa_history as dao_get_qa_history
from dto.response import parse_sources
from exceptions import (ForbiddenException, NotFoundException,
                        ServiceException, ValidationException)

logger = logging.getLogger(__name__)


def ask_question_service(
    question: str,
    user_id: int,
    conversation_id: int | None = None,
    document_id: int | None = None,
    top_k: int = 5,
) -> dict:
    """执行一次 RAG 问答.

    处理对话的查找/创建、权限校验，然后调用 RAG 服务完成问答。

    Args:
        question: 用户问题.
        user_id: 当前用户 ID.
        conversation_id: 对话 ID，不传则自动创建.
        document_id: 限定检索的文档 ID（可选）.
        top_k: 检索返回的文档块数量.

    Returns:
        包含 conversation_id, qa_id, question, answer, sources, created_at 的 dict.

    Raises:
        ValidationException: 问题为空.
        NotFoundException: 对话或文档不存在.
        ForbiddenException: 对话不属于当前用户.
        ServiceException: RAG 流程失败.
    """
    if not question.strip():
        raise ValidationException("问题不能为空")

    # ── 处理对话 ──
    if conversation_id:
        conversation = get_conversation_by_id(conversation_id)
        if not conversation:
            raise NotFoundException("对话不存在")
        if conversation.user_id != user_id:
            raise ForbiddenException("无权访问该对话")
    else:
        try:
            conversation = dao_create_conv(user_id=user_id, title="新对话")
        except Exception as e:
            logger.error("创建对话失败: %s", e)
            raise ServiceException("创建对话失败")
        conversation_id = conversation.id

    # ── 校验文档（可选） ──
    if document_id:
        doc = get_document_by_id(document_id)
        if not doc:
            raise NotFoundException("文档不存在")

    # ── 执行 RAG ──
    from service.rag_service import rag_ask_service

    try:
        result = rag_ask_service(
            question=question,
            user_id=user_id,
            conversation_id=conversation_id,
            document_id=document_id,
            top_k=top_k,
        )
    except RuntimeError as e:
        raise ServiceException(str(e))

    # ── 更新对话时间戳 ──
    update_conversation_timestamp(conversation)

    return {
        "conversation_id": conversation_id,
        "qa_id": result["qa_id"],
        "question": result["question"],
        "answer": result["answer"],
        "sources": result["sources"],
        "confidence": result.get("confidence", "general"),
        "created_at": result["created_at"],
    }


def create_conversation_service(user_id: int, title: str = "新对话"):
    """创建新对话.

    Args:
        user_id: 用户 ID.
        title: 对话标题.

    Returns:
        Conversation 对象.

    Raises:
        ServiceException: DB 写入失败.
    """
    try:
        return dao_create_conv(user_id=user_id, title=title)
    except Exception as e:
        logger.error("创建对话失败: %s", e)
        raise ServiceException("创建对话失败")


def list_conversations_service(user_id: int) -> list:
    """获取用户全部对话（转为 dict）."""
    conversations = get_user_conversations(user_id)
    return [c.to_dict() for c in conversations]


def conversation_detail_service(user_id: int, conversation_id: int) -> dict:
    """获取对话详情（含消息列表，sources 已解析）.

    Args:
        user_id: 当前用户 ID.
        conversation_id: 对话 ID.

    Returns:
        dict: 对话信息 + messages 列表.

    Raises:
        NotFoundException: 对话不存在.
        ForbiddenException: 对话不属于当前用户.
    """
    conversation = get_conversation_by_id(conversation_id)
    if not conversation:
        raise NotFoundException("对话不存在")
    if conversation.user_id != user_id:
        raise ForbiddenException("无权访问该对话")

    conv_data = conversation.to_dict()
    messages = get_conversation_messages(conversation_id)

    conv_data["messages"] = []
    for m in messages:
        msg_dict = {
            "id": m.id,
            "question": m.question,
            "answer": m.answer,
            "document_id": m.document_id,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "sources": parse_sources(m.sources),
            "confidence": m.confidence,
        }
        conv_data["messages"].append(msg_dict)

    return conv_data


def qa_history_service(
    user_id: int,
    conversation_id: int | None = None,
    document_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """获取分页问答历史（sources 已解析）.

    Args:
        user_id: 当前用户 ID.
        conversation_id: 按对话筛选（可选）.
        document_id: 按文档筛选（可选）.
        page: 页码.
        page_size: 每页数量.

    Returns:
        dict: {total, page, page_size, total_pages, items}.
    """
    records, total = dao_get_qa_history(
        user_id=user_id,
        conversation_id=conversation_id,
        document_id=document_id,
        page=page,
        page_size=page_size,
    )

    items = []
    for r in records:
        items.append({
            "id": r.id,
            "user_id": r.user_id,
            "conversation_id": r.conversation_id,
            "document_id": r.document_id,
            "question": r.question,
            "answer": r.answer,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "sources": parse_sources(r.sources),
            "confidence": r.confidence,
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "items": items,
    }
