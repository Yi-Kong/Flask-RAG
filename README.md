# 校园知识库 RAG 系统 (Campus Knowledge Base RAG)

基于 Flask 的 RAG (Retrieval-Augmented Generation) 校园知识库系统，支持文档上传、向量化存储、智能问答。

> **架构类型**: Flask + Jinja2 服务端渲染，非前后端分离。

---

## 功能特性

- 📄 **文档管理** — 支持上传 PDF / DOCX / TXT / Markdown 文档，自动解析文本内容并建立向量索引
- 🔍 **语义检索** — 基于 BGE 中文嵌入模型 + ChromaDB 向量数据库，实现语义级别的文档检索
- 🤖 **智能问答** — 结合 DeepSeek 大模型，基于检索到的文档内容生成准确回答
- 💬 **对话管理** — 支持多轮对话，保存历史问答记录
- 🔐 **用户认证** — JWT + Cookie 认证，支持注册/登录
- 📝 **小红书生成** — 基于文档内容自动生成小红书风格文案

---

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| **Web 框架** | Flask 3.1 | Python Web 框架，app factory 模式 |
| **前端** | Jinja2 模板 + 原生 JS | 服务端渲染，非前后端分离 |
| **数据库** | MySQL 8.0 | 关系型数据库，SQLAlchemy ORM |
| **数据库迁移** | Alembic / Flask-Migrate | 数据库版本管理 |
| **向量数据库** | ChromaDB | HttpClient 客户端-服务器模式，需单独启动服务 |
| **嵌入模型** | BGE-small-zh-v1.5 | 本地加载，512 维中文向量 |
| **LLM** | DeepSeek (API) | RAG 回答生成 |
| **认证** | JWT + Cookie | 用户认证与会话管理 |

---

## 项目结构

```
flask项目/
├── app.py                     # Flask 应用工厂 (create_app)
├── run.py                     # 开发服务器入口
├── config.py                  # 应用配置（从 .env 加载）
├── extensions.py              # Flask 扩展实例
├── exceptions.py              # 自定义异常类
├── requirements.txt           # Python 依赖
│
├── model/                     # 数据模型层 (ORM)
│   ├── user.py                # 用户模型
│   ├── document.py            # 文档模型
│   ├── conversation.py        # 对话模型
│   └── qa_record.py           # 问答记录模型
│
├── dao/                       # 数据访问层
├── service/                   # 业务逻辑层（含 RAG/DeepSeek/嵌入/向量存储）
├── controller/                # 控制器层
├── routers/                   # 路由定义层 (Blueprint)
├── middleware/                 # 中间件（认证 + 错误处理）
├── dto/                       # 数据传输对象 (统一响应格式 ok/fail)
├── utils/                     # 工具函数
├── view/                      # 前端模板 (Jinja2)
├── migrations/                # 数据库迁移 (Alembic)
├── scripts/                   # 辅助脚本
│
├── download_model.py          # 模型下载脚本
├── check_vectors.py           # 向量数据检查工具
├── clear_all_data.py          # 数据清理工具
└── red_book.py                # 小红书生成脚本
```

### 架构分层

```
请求 → router → middleware(auth) → controller → service → dao → model(ORM) → MySQL
                                                          → vector_store → ChromaDB(客户端-服务器)
                                                          → deepseek → DeepSeek API
页面 → router → controller → render_template → Jinja2 模板
```

### API 统一响应格式

所有 API 返回统一的 JSON 格式，通过 `dto/response.py` 构建：

```json
// 成功响应
{ "success": true, "data": {...}, "message": "..." }

// 失败响应
{ "success": false, "message": "错误信息" }
```

| 函数 | 默认状态码 | 用途 |
|------|-----------|------|
| `ok(data, status_code=200, **extra)` | 200 | 成功响应，可覆盖为 201 等 |
| `ok_without_data(status_code=200, **extra)` | 200 | 成功响应（data 字段平铺） |
| `fail(message, status_code=400)` | 400 | 失败响应 |

---

## 功能页面

| 功能 | 地址 | 说明 |
|-----|------|------|
| 首页 | `/` | 登录后可见主页 |
| 注册 | `/register` | 创建新用户账号 |
| 登录 | `/login` | 用户登录入口 |
| 上传文档 | `/upload` | 上传 PDF/DOCX/TXT/MD 文件，自动解析并建立向量索引 |
| 智能问答 | `/qa` | 基于已上传文档进行 RAG 问答 |
| 对话管理 | `/conversations` | 管理历史对话记录 |
| 向量库管理 | `/admin/vectors` | 查看 ChromaDB 中已索引的分块详情 |
| 小红书生成 | `/coze` | 基于文档内容生成小红书风格文案 |

---

## 环境要求

- **Python** 3.9 ~ 3.12（推荐 3.10 / 3.11）
- **MySQL** 8.0
- **磁盘空间** 约 3GB（含 PyTorch 和嵌入模型）

---

## 安装依赖（所有平台通用）

项目依赖通过 `requirements.txt` 管理，包含 Flask、SQLAlchemy、ChromaDB、PyTorch、sentence-transformers 等核心库。

### 1. 创建虚拟环境（推荐）

```bash
# macOS / Linux / WSL2
python3 -m venv venv
source venv/bin/activate

# Windows (cmd)
python -m venv venv
venv\Scripts\activate

# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1
```

激活成功后，终端提示符前会出现 `(venv)` 标识。

### 2. 安装 requirements.txt

```bash
# 一键安装所有依赖
pip install -r requirements.txt
```

**`requirements.txt` 包含的主要依赖：**

| 类别 | 包名 | 用途 |
|------|------|------|
| Web 框架 | `Flask`, `Flask-Login`, `Flask-SQLAlchemy`, `Flask-Migrate` | Web 应用、认证、ORM、数据库迁移 |
| 数据库驱动 | `PyMySQL` | 连接 MySQL 数据库 |
| 向量数据库 | `chromadb` | 本地向量存储与检索 |
| 嵌入模型 | `sentence-transformers`, `torch`, `transformers` | 文本向量化 |
| LLM 调用 | `requests`, `httpx` | 调用 DeepSeek API |
| 文档解析 | `PyPDF2`, `python-docx`, `lxml` | 解析 PDF/DOCX/TXT 文档 |
| 认证 | `PyJWT`, `bcrypt` | JWT 生成与密码哈希 |
| 工具 | `python-dotenv` | 加载 .env 环境变量 |

### 3. 更换 PyTorch 版本（可选）

`requirements.txt` 中的 `torch` 默认是 GPU 版（约 2.5GB+）。如果不需要 GPU 加速，可替换为 CPU 版以节省磁盘空间和下载时间：

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### 4. 使用国内镜像加速（可选）

如果下载速度慢，可使用国内 PyPI 镜像：

```bash
# 清华镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 阿里云镜像
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 中科大镜像
pip install -r requirements.txt -i https://pypi.mirrors.ustc.edu.cn/simple/
```

### 5. 验证安装

```bash
# 验证关键包是否安装成功
python -c "import flask; print('Flask:', flask.__version__)"
python -c "import chromadb; print('ChromaDB:', chromadb.__version__)"
python -c "from sentence_transformers import SentenceTransformer; print('Sentence-Transformers OK')"
python -c "import torch; print('PyTorch:', torch.__version__)"
```

### 6. 常见安装问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `pip install` 超时 | 网络连接 PyPI 慢 | 使用国内镜像（见上方第 4 步） |
| `onnxruntime` 报错 | 跨平台版本不匹配 | `pip install onnxruntime --upgrade` |
| `torch` 安装失败 | 磁盘空间不足或版本不兼容 | 替换为 CPU 版（见上方第 3 步） |
| Windows 下 `sentence-transformers` 失败 | 缺少 VC++ 运行时 | 安装 [vc_redist.x64.exe](https://aka.ms/vs/17/release/vc_redist.x64.exe) |
| `chromadb` 安装报错 | Python 版本过低 | 升级到 Python 3.9+ |

---

## macOS 下运行

### 1. 安装 Python

```bash
# 使用 Homebrew 安装
brew install python@3.11

# 验证安装
python3 --version
pip3 --version
```

### 2. 安装并配置 MySQL

```bash
# 使用 Homebrew 安装
brew install mysql@8.0

# 启动 MySQL 服务
brew services start mysql@8.0

# 登录 MySQL（首次无需密码）
mysql -u root

# 创建数据库
CREATE DATABASE campus_rag CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 设置 root 密码（与 .env 中保持一致）
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '123456';
FLUSH PRIVILEGES;
EXIT;

# 验证新密码
mysql -u root -p
```

> 如果使用了不同的密码，后续 `.env` 中的 `DATABASE_URL` 需对应修改。

### 3. 获取项目代码

```bash
cd <项目根目录路径>
```

### 4. 创建虚拟环境并安装依赖

参考上方 [安装依赖](#安装依赖所有平台通用) 章节，创建虚拟环境并执行：

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env 文件
nano .env
```

需要填写的关键配置项：

| 配置项 | 说明 | 示例值 |
|--------|------|--------|
| `DATABASE_URL` | MySQL 连接地址 | `mysql+pymysql://root:123456@127.0.0.1:3306/campus_rag?charset=utf8mb4` |
| `SECRET_KEY` | Flask 密钥（随机字符串） | 任意英文字母数字组合 |
| `JWT_SECRET_KEY` | JWT 签名密钥（随机字符串） | 任意英文字母数字组合 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | `sk-你的APIKey` |
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | DeepSeek 模型名 | `deepseek-chat` |
| `UPLOAD_FOLDER` | 文件上传目录 | `uploads` |
| `CHROMA_HOST` | ChromaDB 服务地址 | `127.0.0.1` |
| `CHROMA_PORT` | ChromaDB 服务端口 | `8000` |
| `EMBEDDING_MODEL` | 嵌入模型路径 | `embedding_models/bge-small-zh-v1.5` |

> 🔑 获取 DeepSeek API Key：[platform.deepseek.com](https://platform.deepseek.com)

### 6. 初始化数据库

```bash
# 执行数据库迁移
flask --app run db upgrade
```

> 如果迁移失败，可尝试手动建表：
> ```bash
> python3 -c "
> from run import app, db
> with app.app_context():
>     db.create_all()
>     print('建表成功')
> "
> ```

### 7. 下载嵌入模型

```bash
# 国内用户推荐使用镜像站
HF_ENDPOINT=https://hf-mirror.com python download_model.py

# 或直接下载（需能访问 Hugging Face）
python download_model.py
```

模型约 100MB，下载到 `embedding_models/bge-small-zh-v1.5/` 目录。

### 8. 启动应用

```bash
python run.py
```

启动成功后访问：**http://127.0.0.1:5001**

> ChromaDB 使用客户端-服务器模式，启动 Flask 前需先启动 ChromaDB 服务。

### 9. 使用流程

1. 访问 `/register` 注册账号 → `/login` 登录
2. 进入「上传文档」页面上传文档（PDF/DOCX/TXT/MD）
3. 上传成功后文档状态变为 `ready`，表示已建立向量索引
4. 进入「智能问答」页面提问（如"图书馆的开放时间是什么？"）
5. 系统自动：问题向量化 → ChromaDB 语义检索 → DeepSeek 生成回答

---

## Windows 下运行

Windows 用户有两种方式可选：

| 条件 | 推荐方式 |
|------|---------|
| Windows 10/11 版本 ≥ 2004（支持 WSL2） | **方式一：WSL2（推荐）** |
| 无法使用 WSL2（公司策略限制、系统版本过低） | **方式二：纯 Windows** |

> ChromaDB 使用客户端-服务器模式，启动项目前需先启动 ChromaDB 服务（详见下方各平台说明）。

### 方式一：WSL2（推荐）

MySQL、PyTorch 等组件在 Linux 环境下兼容性更好，推荐使用 WSL2。

#### 安装 WSL2

以**管理员身份**打开 PowerShell，执行：

```powershell
wsl --install
```

重启电脑后，按提示设置 Linux 用户名和密码，然后更新系统：

```bash
sudo apt update && sudo apt upgrade -y
```

#### 安装 Python

```bash
sudo apt install python3 python3-pip python3-venv -y
```

#### 安装 MySQL

```bash
sudo apt install mysql-server -y
sudo service mysql start

sudo mysql
```

在 MySQL 命令行中执行：

```sql
CREATE DATABASE campus_rag CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '123456';
FLUSH PRIVILEGES;
EXIT;
```

#### 获取代码并安装

```bash
# 将项目复制到 WSL 内部（推荐，避免跨文件系统性能问题）
# 假设项目在 Windows 的 D:\Projects\flask项目，对应 WSL 中 /mnt/d/Projects/flask项目
cp -r /mnt/<盘符>/<项目路径> ~/flask项目
cd ~/flask项目

# 创建虚拟环境并安装依赖（详见上方「安装依赖」章节）
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 配置并启动

后续步骤（配置 .env、初始化数据库、下载模型、启动）与 macOS 步骤 5-8 完全相同。访问时在 Windows 浏览器中打开 **http://127.0.0.1:5001**（WSL2 自动转发）。

> ⚠️ **每次重启电脑后**，需手动启动 MySQL：打开 Ubuntu 终端，执行 `sudo service mysql start`。

---

### 方式二：纯 Windows

#### 安装 Python

1. 前往 [python.org](https://www.python.org/downloads/) 下载 Python 3.9~3.12（推荐 3.10/3.11）Windows 64 位安装包
2. 安装时**务必勾选**「Add Python to PATH」
3. 验证：`python --version` 和 `pip --version`

#### 安装 Visual C++ 运行时

PyTorch、onnxruntime 依赖 VC++ 运行库，下载安装：[vc_redist.x64.exe](https://aka.ms/vs/17/release/vc_redist.x64.exe)

#### 安装 MySQL

1. 前往 [dev.mysql.com/downloads/mysql](https://dev.mysql.com/downloads/mysql/) 下载 MySQL Community Server 8.0.x Windows x64 Installer
2. 安装类型选 **Developer Default** 或 **Server only**，按向导完成
3. 记下设置的 root 密码
4. 打开 MySQL 命令行客户端，登录后执行：

```sql
CREATE DATABASE campus_rag CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

#### 安装项目

打开**命令提示符（cmd）**：

```cmd
cd /d <项目根目录路径>

:: 创建虚拟环境并安装依赖（详见上方「安装依赖」章节）
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

#### 配置 .env

```cmd
copy .env.example .env
```

用记事本或 VS Code 编辑 `.env`，配置项与 macOS 步骤 5 相同。注意 `DATABASE_URL` 中的密码改为你在 MySQL 安装时设置的密码。

#### 初始化与启动

```cmd
:: 初始化数据库
flask --app run db upgrade

:: 下载嵌入模型（国内推荐设置镜像）
set HF_ENDPOINT=https://hf-mirror.com
python download_model.py

:: 启动应用
python run.py
```

浏览器访问 **http://127.0.0.1:5001**。

> 确保 Windows 服务中的 `MySQL80` 状态为「正在运行」。

---

## 停止服务

1. 在终端按 **Ctrl + C** 停止 Flask
2. 输入 `deactivate` 退出虚拟环境
3. 如需停止 MySQL：
   - macOS：`brew services stop mysql@8.0`
   - WSL2：`sudo service mysql stop`
   - Windows：在服务管理器中停止 `MySQL80` 服务

---

## 常用命令

```bash
# 启动开发服务器
python run.py

# 数据库迁移
flask --app run db migrate -m "描述"    # 生成迁移文件
flask --app run db upgrade             # 执行迁移升级
flask --app run db downgrade           # 回滚上一次迁移

# 工具脚本
python check_vectors.py overview       # 查看向量库概览
python check_vectors.py stats          # 按文档查看向量统计
python check_vectors.py search         # 交互式语义搜索
python clear_all_data.py               # 清除所有数据（需确认）
python download_model.py               # 下载嵌入模型
```

---

## 常见问题

| 问题 | 解决方案 |
|-----|---------|
| **向量模型加载失败** | 确认 `embedding_models/bge-small-zh-v1.5/` 目录存在且包含模型文件。运行 `python download_model.py` 重新下载（国内推荐 `HF_ENDPOINT=https://hf-mirror.com python download_model.py`） |
| **MySQL 连接失败** | ① 确认 MySQL 服务已启动 ② 确认 `.env` 中 `DATABASE_URL` 的用户名密码正确 ③ 确认 `campus_rag` 数据库已创建 |
| **数据库迁移报错** | 依次执行 `flask --app run db stamp head` → `flask --app run db upgrade`，或手动建表 |
| **缺少必需配置项** | 确认 `.env` 中 `SECRET_KEY`、`JWT_SECRET_KEY`、`DATABASE_URL` 均已填写 |
| **pip 安装报错** | 检查 Python 版本是否为 3.9~3.12；Windows 需安装 VC++ 运行时；尝试国内镜像源 |
| **端口 5001 被占用** | 在 `.env` 中设置 `FLASK_PORT=5002` |
| **DeepSeek API 返回错误** | 检查 `.env` 中 `DEEPSEEK_API_KEY` 是否正确、是否还有余额 |
| **ChromaDB 初始化失败** | 确认 ChromaDB 服务已启动: `chroma run --host 127.0.0.1 --port 8000 --path ./chroma_data` |
