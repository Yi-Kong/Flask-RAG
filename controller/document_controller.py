"""文档 API — 视图函数."""

import os
import uuid

from flask import current_app, request
from werkzeug.utils import secure_filename

from dto.response import ok
from exceptions import AuthenticationException, ValidationException
from service.document_service import (delete_document_service,
                                       list_documents_service,
                                       upload_document_service)
from utils.auth import get_current_user_id


def upload_document_controller():
    """上传文档（登录用户均可上传）."""
    if "file" not in request.files:
        raise ValidationException("请选择要上传的文件")

    file = request.files["file"]
    raw_filename = file.filename or ""

    # ── Controller 层：文件校验 ──
    if not file or not raw_filename.strip():
        raise ValidationException("请选择要上传的文件")

    ext = raw_filename.rsplit(".", 1)[-1].lower() if "." in raw_filename else ""
    allowed = current_app.config["ALLOWED_EXTENSIONS"]
    if not ext or ext not in allowed:
        raise ValidationException(
            f"不支持的文件格式，仅支持 {'、'.join(sorted(allowed))}"
        )

    # ── Controller 层：文件名安全化 & 保存到磁盘 ──
    original_filename = secure_filename(raw_filename)
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    server_filename = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(upload_folder, server_filename)
    file.save(save_path)

    title_override = (request.form.get("title", "") or "").strip()

    user_id = get_current_user_id()
    if not user_id:
        raise AuthenticationException("用户不存在")

    config = {
        "CHUNK_SIZE": current_app.config["CHUNK_SIZE"],
        "CHUNK_OVERLAP": current_app.config["CHUNK_OVERLAP"],
    }

    document = upload_document_service(
        save_path=save_path,
        ext=ext,
        original_filename=original_filename,
        title_override=title_override,
        uploaded_by=user_id,
        config=config,
    )

    return ok(
        message=f"文件上传并索引成功，共生成 {document.chunk_count} 个分块",
        document=document.to_dict(),
    )


def delete_document_controller(document_id):
    """删除文档（登录用户均可删除）."""
    user_id = get_current_user_id()
    if not user_id:
        raise AuthenticationException("用户不存在")

    result = delete_document_service(document_id, current_app.config["UPLOAD_FOLDER"])
    return ok(message=f"文档「{result['title']}」已删除，共清理 {result['deleted_chunks']} 个向量分块")


def document_list_controller():
    """获取文档列表."""
    documents = list_documents_service()
    return ok(data=documents)
