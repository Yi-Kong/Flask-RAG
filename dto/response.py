"""数据传输对象 — 统一响应格式.

提供 success/fail 两个基础响应构建函数，
Controller 层可直接调用生成一致的 JSON 响应.
"""
import json


def ok(data=None, status_code=200, **extra):
    """构建成功响应 (dict, status_code) 元组.

    Usage:
        ok()                                          # 200
        ok(data=[...])                                # 200
        ok(data=obj, message="操作成功")               # 200
        ok(data=obj, status_code=201)                 # 201 创建成功
        ok(total=10, page=1, chunks=[...])            # 200
    """
    result = {"success": True}
    if data is not None:
        result["data"] = data
    result.update(extra)
    return result, status_code


def ok_without_data(status_code=200, **extra):
    """构建成功响应（不包含 data 字段）.

    Usage:
        ok_without_data(total=10, page=1, chunks=[...])
        # {"success": true, "total": 10, "page": 1, "chunks": [...]}
    """
    result = {"success": True}
    result.update(extra)
    return result, status_code


def fail(message, status_code=400):
    """构建失败响应 (dict, status_code) 元组.

    Usage:
        return fail("请选择文件")            # 400
        return fail("用户不存在", 401)       # 401
    """
    return {"success": False, "message": message}, status_code


def parse_sources(sources_raw):
    """将 sources JSON 字符串解析为列表.

    在 Controller/Service 层统一使用此函数解析 QARecord.sources 字段，
    避免在多处重复 json.loads + try/except 模式。

    Args:
        sources_raw: JSON 字符串或 None/空值.

    Returns:
        解析后的列表，解析失败或为空时返回 [].
    """
    if not sources_raw:
        return []
    try:
        return json.loads(sources_raw)
    except (json.JSONDecodeError, TypeError):
        return []
