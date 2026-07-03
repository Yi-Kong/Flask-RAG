"""向量库管理 API — 视图函数."""

from flask import request

from dto.response import ok_without_data
from exceptions import ServiceException, ValidationException
from service.vector_store import (chunks_paginated_service,
                                  collections_overview_service,
                                  search_similar_service)


def vectors_overview_controller():
    """获取 ChromaDB 概览信息."""
    try:
        overview = collections_overview_service()
        return ok_without_data(**overview)
    except Exception as e:
        raise ServiceException(f"连接 ChromaDB 失败: {str(e)}")


def vectors_chunks_controller():
    """获取 ChromaDB 中的分块列表（支持分页和按文档筛选）."""
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    doc_filter = request.args.get("document_id", type=int)

    try:
        result = chunks_paginated_service(
            page=page,
            page_size=page_size,
            document_id=doc_filter,
        )
        return ok_without_data(**result)
    except Exception as e:
        raise ServiceException(f"连接 ChromaDB 失败: {str(e)}")


def vectors_search_controller():
    """在向量库中语义搜索."""
    query = request.args.get("q", "").strip()
    if not query:
        raise ValidationException("请输入搜索关键词")

    top_k = request.args.get("top_k", 5, type=int)

    try:
        result = search_similar_service(query_text=query, top_k=top_k)
        return ok_without_data(**result)
    except ServiceException:
        raise
    except Exception as e:
        raise ServiceException(f"搜索失败: {str(e)}")
