# 校园知识库 RAG 系统 (Campus Knowledge Base RAG)

基于 Flask 的 RAG (Retrieval-Augmented Generation) 校园知识库系统，支持文档上传、向量化存储、智能问答。

> **架构类型**: Flask + Jinja2 服务端渲染，非前后端分离。
> **最后更新**: 2026-07-03

---

## 项目结构

```
flask项目/
├── app.py                     # Flask 应用工厂 (create_app)
├── run.py                     # 开发服务器入口
├── config.py                  # 应用配置（从 .env 加载）
├── extensions.py              # Flask 扩展实例 (SQLAlchemy, Migrate)
├── exceptions.py              # 自定义异常类
├── requirements.txt           # Python 依赖
│
├── model/                     # 数据模型层 (ORM)
│   ├── __init__.py            # 模型导出
│   ├── user.py                # 用户模型 (User)
│   ├── document.py            # 文档模型 (Document)
│   ├── conversation.py        # 对话模型 (Conversation)
│   └── qa_record.py           # 问答记录模型 (QARecord)
│
├── dao/                       # 数据访问层 (Data Access Object)
│   ├── __init__.py
│   ├── user_dao.py            # 用户数据操作
│   ├── document_dao.py        # 文档数据操作
│   ├── conversation_dao.py    # 对话数据操作
│   └── qa_record_dao.py       # 问答记录数据操作
│
├── service/                   # 业务逻辑层
│   ├── __init__.py
│   ├── auth_service.py        # 认证服务
│   ├── document_service.py    # 文档管理服务
│   ├── qa_service.py          # 问答服务
│   ├── rag_service.py         # RAG 检索增强生成
│   ├── deepseek_service.py    # DeepSeek LLM 调用
│   ├── chunker.py             # 文本分块器
│   ├── document_parser.py     # 文档解析 (PDF/DOCX/TXT/MD)
│   ├── embedder.py            # 文本嵌入向量化 (BGE)
│   └── vector_store.py        # ChromaDB 向量存储
│
├── controller/                # 控制器层（请求处理 + 视图逻辑）
│   ├── __init__.py
│   ├── auth_controller.py     # 认证相关
│   ├── document_controller.py # 文档管理
│   ├── conversation_controller.py # 对话管理
│   ├── qa_controller.py       # 问答处理
│   ├── admin_controller.py    # 管理后台
│   └── page_controller.py     # 页面路由
│
├── routers/                   # 路由定义层 (Blueprint)
│   ├── __init__.py
│   ├── router.py              # 路由注册入口
│   ├── auth_router.py
│   ├── document_router.py
│   ├── conversation_router.py
│   ├── qa_router.py
│   ├── admin_router.py
│   └── page_router.py
│
├── middleware/                 # 中间件
│   ├── __init__.py
│   ├── auth_middleware.py     # 认证中间件 (JWT + Cookie)
│   └── error_handler.py       # 全局错误处理
│
├── dto/                       # 数据传输对象
│   ├── __init__.py
│   └── response.py            # 统一响应格式 (ok/fail + status_code)
│
├── utils/                     # 工具函数
│   ├── auth.py                # JWT 工具
│   ├── decorators.py          # 装饰器 (@public)
│   └── text_helpers.py        # 文本处理工具
│
├── view/                      # 前端模板 (Jinja2)
│   ├── index.html             # 首页
│   ├── login.html             # 登录
│   ├── register.html          # 注册
│   ├── upload.html            # 文档上传
│   ├── qa.html                # 问答界面
│   ├── coze.html              # 小红书生成
│   └── admin_vectors.html     # 向量管理
│
├── migrations/                # 数据库迁移 (Alembic/Flask-Migrate)
│   ├── alembic.ini
│   ├── env.py
│   └── versions/              # 迁移版本文件
│
├── scripts/                   # 辅助脚本
│   ├── run_chromadb_mcp.sh    # ChromaDB MCP 服务
│   └── run_mysql_mcp.sh       # MySQL MCP 服务
│
├── .claude/                   # Claude Code 配置
│   ├── settings.json          # 项目级设置（安全限制等）
│   ├── settings.local.json    # 本地设置（不入 git）
│   └── commands/              # 自定义命令
│       ├── audit.md
│       ├── feature.md
│       ├── bugfix.md
│       ├── db-change.md
│       └── review.md
│
├── .env                       # 环境变量（敏感，不入 git）
├── .env.example               # 环境变量模板
├── .gitignore
├── CLAUDE.md                  # 本文件 — AI 协作规范
├── download_model.py          # HuggingFace 模型下载脚本
├── check_vectors.py           # 向量数据检查工具
├── clear_all_data.py          # 数据清理工具
├── red_book.py                # 小红书生成脚本
└── 校园知识库测试文档.md       # 测试文档
```

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| **Web 框架** | Flask 3.1 | Python Web 框架，app factory 模式 |
| **前端** | Jinja2 模板 + 原生 JS | **服务端渲染，非前后端分离** |
| **数据库** | MySQL 8.0 (Docker) | 关系型数据库，SQLAlchemy ORM |
| **数据库迁移** | Alembic / Flask-Migrate | 数据库版本管理 |
| **向量数据库** | ChromaDB | PersistentClient 本地持久化 |
| **嵌入模型** | BGE-small-zh-v1.5 | 本地加载，512 维中文向量 |
| **LLM** | DeepSeek (API) | RAG 回答生成 |
| **认证** | JWT + Cookie | 用户认证与会话管理 |

## 数据库表

| 表名 | 说明 | 主要字段 |
|------|------|----------|
| `users` | 用户表 | id, username, password, email, role |
| `documents` | 文档表 | id, title, filename, file_type, status, uploaded_by |
| `conversations` | 对话表 | id, user_id, title, created_at, updated_at |
| `qa_records` | 问答记录表 | id, user_id, conversation_id, document_id, question, answer |

## 架构分层

```
请求 → router → middleware(auth) → controller → service → dao → model(ORM) → MySQL
                                                          → vector_store → ChromaDB
                                                          → deepseek → DeepSeek API
页面 → router → controller → render_template → Jinja2 模板
```

---

## ⛔ 本项目禁止事项

以下行为**绝对禁止**，除非用户明确书面要求：

1. **禁止引入前后端分离框架**
   - 不要引入 React、Vue、Angular、Next.js、Nuxt、Svelte 等
   - 不要添加 webpack、vite、esbuild 等前端构建工具
   - 不要添加 npm/package.json 前端依赖管理
   - 前端保持 Jinja2 模板 + 原生 JS + 内联 CSS 方式

2. **禁止引入大型新框架**
   - 不要引入 Django、FastAPI、Tornado 等替代框架
   - 不要引入 Celery、Redis、RabbitMQ 等消息队列（除非明确要求）
   - 不要引入 Docker Compose、Kubernetes 等容器编排
   - 小型工具库（如 python-dotenv、httpx）除外

3. **禁止随意修改数据库 schema**
   - 不要在模型文件中直接添加/删除/修改字段
   - 必须先讨论变更影响，生成 migration，再执行
   - 禁止直接在生产数据库执行 DDL

4. **禁止泄露敏感信息**
   - 不要把 secret、token、API key、数据库密码写进代码
   - 不要提交 `.env` 文件
   - 不要在日志中打印完整 API key 或 token
   - 不要在注释中写真实密码

5. **禁止删除现有业务代码**
   - 除非明确要求，不要删除任何 .py 文件或模板
   - 不要重命名现有核心目录（model/, service/, controller/ 等）
   - 重构时先备份或使用 git 分支

6. **禁止擅自大重构**
   - 不要改变项目分层架构
   - 不要统一重命名函数/类命名风格
   - 不要引入 type hints 大规模改造
   - 发现混乱只给建议，不擅自执行

---

## 开发规范

### 路由修改规范

当需要添加或修改路由时，必须同时检查以下 5 项：

| 检查项 | 说明 |
|--------|------|
| 路由定义 | `routers/*_router.py` — 路由 URL、methods、Blueprint 注册 |
| 控制器 | `controller/*_controller.py` — 请求参数校验、响应格式 |
| 模板 | `view/*.html` — 对应的 Jinja2 模板是否需更新 |
| 权限 | `middleware/auth_middleware.py` — 认证模式（公开/受保护） |
| 测试 | 是否有对应的测试覆盖新路由 |

### 模板修改规范

- 保持 **Jinja2 服务端渲染**方式，不要引入前端框架
- 所有 CSS 和 JS 内联在 `<style>` / `<script>` 标签中
- 模板中使用 `{{ g.current_user }}` 访问当前用户
- 使用 `{{ url_for('blueprint.function') }}` 生成 URL，不要硬编码路径
- Flash 消息使用 `{{ get_flashed_messages() }}` 显示

### 数据库变更规范

见 `/db-change` 命令。核心原则：
1. 先改 `model/*.py` → 2. 生成 migration → 3. 检查迁移脚本 → 4. 执行升级 → 5. 更新 DAO

### 安全规则

1. **配置文件**：所有敏感配置从 `.env` 读取，通过 `config.py` 访问
2. **密码处理**：使用 `werkzeug.security.generate_password_hash` / `check_password_hash`
3. **JWT**：使用 `utils/auth.py` 中的 `create_token`，不要在业务代码中手写 JWT
4. **SQL 注入**：使用 SQLAlchemy ORM，禁止拼接 SQL 字符串
5. **XSS**：Jinja2 默认自动转义，不要使用 `|safe` 过滤器处理用户输入
6. **文件上传**：校验扩展名白名单，使用 UUID 重命名，限制文件大小
7. **日志**：打印 API key 时必须截断（只显示前 8 位 + `***`）

### 配置访问规范

项目所有配置集中定义在 [config.py](config.py) 的 `Config` 类中，通过 `app.config.from_object(Config)` 加载到 Flask 配置字典。根据代码所在层级选择对应的访问方式：

| 场景 | 访问方式 | 示例 |
|------|---------|------|
| **Flask 请求上下文内**（controller 层） | `current_app.config["KEY"]` | `current_app.config["CHUNK_SIZE"]` |
| **请求上下文外**（service 层、工具脚本、中间件） | `Config.KEY` | `Config.DEEPSEEK_API_KEY` |

**为什么有两种方式？**

- `Config.KEY` 是类属性，**无需 Flask 上下文**即可访问，适合 service 层初始化、独立脚本等场景
- `current_app.config["KEY"]` 是 Flask 标准方式，适合 controller 层（在 `app.config.from_object()` 之后所有 `Config` 属性已自动同步到 `current_app.config`）

**规则：**
1. 新增配置项时，在 `Config` 类中添加属性，然后两种方式自动可用
2. controller 层**优先**用 `current_app.config`，不要在 controller 中直接 `from config import Config`
3. service 层和工具脚本**优先**用 `Config.KEY`，不需要 Flask 上下文
4. `load_dotenv()` **只在 `config.py` 模块级别调用一次**，其他文件不要再调用

### 统一响应格式

所有 API 响应通过 [dto/response.py](dto/response.py) 中的函数构建，确保返回格式一致。

| 函数 | 签名 | 默认状态码 | 返回格式 |
|------|------|-----------|---------|
| `ok()` | `ok(data=None, status_code=200, **extra)` | 200 | `({"success": True, ...}, status_code)` |
| `ok_without_data()` | `ok_without_data(status_code=200, **extra)` | 200 | `({"success": True, ...}, status_code)` |
| `fail()` | `fail(message, status_code=400)` | 400 | `({"success": False, "message": ...}, status_code)` |

**使用示例：**

```python
from dto.response import ok, fail, ok_without_data

# 查询成功（默认 200）
return ok(data=documents)
return ok(data=detail, message="操作成功")

# 创建资源（覆盖为 201）
return ok(data=obj.to_dict(), status_code=201)
return ok(message="创建成功", status_code=201)

# 无 data 包装的成功响应
return ok_without_data(total=10, page=1, chunks=[...])

# 失败响应
return fail("请选择文件")              # 400
return fail("用户不存在", 401)         # 401
return fail("权限不足", 403)           # 403
```

**规则：**
1. Controller 层**统一使用** `ok()` / `fail()` 构建响应，不要手写 dict
2. `data` 参数用于返回主体数据（列表、对象等），会自动包在 `"data"` 键中
3. 额外的顶级字段（如 `message`、`total`、`page`）通过 `**extra` 传入，平铺在响应中
4. 需要自定义状态码时传入 `status_code` 参数，不要在外面包一层元组
5. `fail()` 的 `status_code` 是位置参数，`ok()` 的是关键字参数 — 不要混淆

---

## 常用命令

```bash
# ===== 开发服务器 =====
python run.py                          # 启动开发服务器 (端口 5001)
flask --app run run --debug            # Flask CLI 方式启动

# ===== 数据库迁移 =====
flask --app run db migrate -m "描述"    # 生成迁移文件（自动检测模型变更）
flask --app run db upgrade             # 执行迁移升级
flask --app run db downgrade           # 回滚上一次迁移
flask --app run db history             # 查看迁移历史
flask --app run db current             # 查看当前迁移版本

# ===== 依赖管理 =====
pip install -r requirements.txt        # 安装依赖
pip freeze > requirements.txt          # 冻结依赖（谨慎使用，不要随意添加包）

# ===== 工具脚本 =====
python check_vectors.py overview       # 查看向量库概览
python check_vectors.py stats          # 按文档查看向量统计
python check_vectors.py search         # 交互式语义搜索
python clear_all_data.py               # 清除所有数据（需确认）
python download_model.py               # 下载嵌入模型到本地

# ===== ChromaDB =====
chroma run --host 127.0.0.1 --port 8000 --path ./chroma_data  # 启动 ChromaDB 服务

# ===== MySQL (Docker) =====
docker run -d --name mysql -p 3306:3306 -e MYSQL_ROOT_PASSWORD=123456 mysql:8.0
docker exec mysql mysql -uroot -p123456 -e "CREATE DATABASE IF NOT EXISTS campus_rag CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# ===== 代码质量 =====
# 本项目暂未配置格式化/lint 工具。建议运行前至少做语法检查：
python -c "import py_compile; py_compile.compile('file.py', doraise=True)"
```

---

## 测试要求

当前项目**暂无测试**。添加测试时的规范：

1. 测试目录：`tests/`，放在项目根目录
2. 测试框架：推荐 `pytest`（已在 requirements.txt 中）
3. 测试命名：`test_<模块名>.py`，如 `tests/test_auth_service.py`
4. 测试分层：
   - 单元测试：service/dao 层，mock 外部依赖
   - 集成测试：controller 层，使用 Flask test client
   - DAO 测试使用测试数据库或 SQLite 内存数据库
5. 运行测试：`pytest` 或 `python -m pytest tests/`

---

## 提交前检查清单

每次提交代码前确认：

- [ ] `.env` 不在暂存区（`git status` 确认）
- [ ] 没有硬编码的密码、token、API key
- [ ] 数据库模型变更时包含 migration 文件
- [ ] 新增路由已设置正确的认证模式（公开/受保护）
- [ ] 新增 API 使用统一的 `ok()`/`fail()` 响应格式
- [ ] 异常使用 `exceptions.py` 中的自定义异常类
- [ ] 文件上传有扩展名和大小校验
- [ ] 代码经过 `python -c "import py_compile..."` 语法检查
- [ ] 提交信息用中文描述变更内容

---

## MCP 服务器

本项目配置了 4 个 MCP (Model Context Protocol) 服务器，Claude Code 可直接调用。

MCP 服务器**结构定义**在 `.mcp.json`（已提交 git），**密钥**从 `.env` 加载（不提交）。

| MCP 服务 | 能力 | 启动方式 |
|----------|------|------|
| `mysql` | 查询/操作 MySQL 数据库（支持读写） | `./scripts/run_mysql_mcp.sh` |
| `chromadb` | 操作 ChromaDB 向量数据库 | `./scripts/run_chromadb_mcp.sh` |
| `github` | GitHub 仓库操作（Issues/PR/内容搜索等） | `./scripts/run_github_mcp.sh` |
| `filesystem` | 读写项目文件 | `npx @modelcontextprotocol/server-filesystem .` |

### 新成员配置

1. `cp .env.example .env`
2. 编辑 `.env`，填入你的密钥：
   - `DATABASE_URL` — MySQL 连接串（mysql MCP + Flask 应用共用）
   - `GITHUB_TOKEN` — GitHub Personal Access Token（github MCP）
   - `CHROMA_HOST` / `CHROMA_PORT` — ChromaDB 服务地址（chromadb MCP）
3. 重启 Claude Code，`.mcp.json` 自动加载 MCP 服务
