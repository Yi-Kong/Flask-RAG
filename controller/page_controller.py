"""页面渲染 — 视图函数."""

from flask import g, redirect, render_template, request

from red_book import red_coze


def index_page():
    """校园知识库主页（需登录）."""
    name = g.current_user.get("username", "未知")
    return render_template("index.html", name=name)


def coze_page():
    """Coze 工作流演示页面（公开访问）."""
    if request.method == "POST":
        content = request.form.get("content")
        res = red_coze(content)
        return redirect("/red", code=res)
    return render_template("coze.html")


def upload_page_page():
    """文档上传页面."""
    return render_template("upload.html")


def qa_page_page():
    """智能问答页面."""
    return render_template("qa.html")


def admin_vectors_page():
    """向量库可视化管理页面."""
    return render_template("admin_vectors.html")
