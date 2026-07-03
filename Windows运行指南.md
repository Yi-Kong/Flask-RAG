# 校园知识库 RAG 系统 — Windows 环境完整运行指南

> **本项目依赖项**：Python + Flask + MySQL + ChromaDB（嵌入式） + PyTorch(Sentence-Transformers) + DeepSeek API。
> 以下提供**两种运行方式**，请根据自身情况选择其一。**推荐方式一（WSL2）**，因为 MySQL、PyTorch 等组件在 Linux 环境下兼容性更好、配置更简单。

---

## 方式选择

| 条件 | 推荐方式 |
|------|---------|
| 你的 Windows 10/11 版本 ≥ 2004（或已开启 WSL2） | **方式一（WSL2，推荐）** |
| 无法使用 WSL2（如公司策略限制、系统版本过低） | **方式二（纯 Windows）** |

---

## 方式一：基于 WSL2 运行（推荐）

WSL2（Windows Subsystem for Linux 2）让你在 Windows 上运行一个完整的 Linux 内核，所有服务（MySQL、Flask）都在同一个 Linux 环境内运行，避免了跨平台兼容问题。

> **注意**：本项目的 ChromaDB 已改为**嵌入式模式**（PersistentClient），数据直接存储在本地磁盘，**无需单独启动 ChromaDB 服务**，也不用 Docker。

---

### 一、安装 WSL2 并安装 Ubuntu

1. 以**管理员身份**打开 PowerShell（右键开始菜单 → 终端管理员 / Windows PowerShell管理员）。

2. 执行以下命令，一键安装 WSL2 + Ubuntu 发行版：
   ```powershell
   wsl --install
   ```
   > 该命令会自动启用虚拟化平台、安装 WSL2 内核，并默认安装 Ubuntu 发行版。执行完毕后需要**重启电脑**。

3. 重启后，系统会自动弹出 Ubuntu 终端窗口，首次启动需要等待几分钟来完成初始化。

4. 设置你的 **Linux 用户名**和**密码**（这是 WSL 内部的账号，与 Windows 账号无关，建议设简单好记的）。

5. 更新 Ubuntu 系统包：
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

6. 验证 WSL 版本（在 PowerShell 中执行）：
   ```powershell
   wsl --list --verbose
   ```
   确保 `VERSION` 列显示为 `2`。如果是 `1`，执行以下命令升级：
   ```powershell
   wsl --set-version Ubuntu 2
   ```

---

### 二、在 WSL2 中安装 Python

打开 **Ubuntu 终端**（可在开始菜单搜索 "Ubuntu"），依次执行：

```bash
sudo apt install python3 python3-pip python3-venv -y
```

验证安装：
```bash
python3 --version
pip3 --version
```

---

### 三、在 WSL2 中安装并配置 MySQL

1. 安装 MySQL Server：
   ```bash
   sudo apt install mysql-server -y
   ```

2. 启动 MySQL 服务：
   ```bash
   sudo service mysql start
   ```

3. 进入 MySQL：
   ```bash
   sudo mysql
   ```

4. 在 MySQL 命令行中执行以下操作：

   ```sql
   -- 创建数据库
   CREATE DATABASE campus_rag CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

   -- 修改 root 密码为 123456（与 .env 中的 DATABASE_URL 配置匹配；如果你改了密码，.env 中也要对应修改）
   ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '123456';
   FLUSH PRIVILEGES;

   EXIT;
   ```

   > 如果你使用了不同的密码，请将上面 `'123456'` 替换为你的实际密码，并在后续 `.env` 配置中保持一致。

5. 验证：用新密码重新登录 MySQL 测试：
   ```bash
   mysql -u root -p
   ```
   输入密码后能进入 MySQL 命令行即为成功。输入 `exit` 退出。

---

### 四、获取项目代码

将项目代码放置在 WSL2 中。有两种方式：

**方式 A（推荐）：将项目文件夹放在 WSL2 内部**

直接在 WSL2 的 Ubuntu 终端中操作：

```bash
# 进入你的 WSL 用户主目录
cd ~
# 如果代码在 Windows 上，可以复制过来（将 <Windows路径> 替换为实际路径）
# 例如：cp -r /mnt/d/Projects/flask项目 ~/flask项目
```

> Windows 的 C 盘在 WSL2 中对应 `/mnt/c/`，D 盘对应 `/mnt/d/`，依此类推。

**方式 B：直接在 Windows 路径下操作**

项目代码留在 Windows 目录下（如 `D:\Projects\flask项目`），在 WSL2 中通过 `/mnt/d/Projects/flask项目` 访问。**注意**：跨文件系统访问性能会较低，且某些 Python 库在跨文件系统时可能出现权限问题，不推荐。

后续步骤假设你的项目目录路径为 `~/flask项目`（在 WSL2 用户主目录下），请替换为你的实际路径。

---

### 五、创建 Python 虚拟环境

在 Ubuntu 终端中：

```bash
cd ~/flask项目
python3 -m venv venv
source venv/bin/activate
```

激活成功后，命令行前面出现 `(venv)` 标识。

---

### 六、安装 Python 依赖

确保虚拟环境已激活，然后：

#### 方案一：一键安装（强烈推荐）

```bash
pip install -r requirements.txt
```

执行完毕后，由于 `requirements.txt` 中的 `torch` 默认是 GPU 版（体积约 2.5GB+），如果你的 WSL2 不需要 GPU 加速，建议替换为 CPU 版以节省空间：

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

> **如果遇到 `onnxruntime` 等包报错**，可能是跨平台版本问题，单独重新安装即可：
> ```bash
> pip install onnxruntime --upgrade
> ```

#### 方案二：逐条安装（备选）

```bash
python3 -m pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install flask flask-login flask-sqlalchemy flask-migrate pymysql
pip install sentence-transformers chromadb
pip install PyPDF2 python-docx python-dotenv PyJWT
pip install requests lxml
```

---

### 七、配置环境变量（.env 文件）

项目所有配置通过 `.env` 文件管理，**不再直接修改 `config.py`**。

1. 复制示例配置文件：
   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env` 文件（可使用 `nano` 或 `vim`）：
   ```bash
   nano .env
   ```

3. 需要填写/修改的关键配置项：

   | 配置项 | 说明 | 示例值 |
   |--------|------|--------|
   | `DATABASE_URL` | MySQL 连接地址 | `mysql+pymysql://root:123456@127.0.0.1:3306/campus_rag?charset=utf8mb4` |
   | `SECRET_KEY` | Flask 密钥（随机字符串） | 随便输入一串英文字母数字 |
   | `JWT_SECRET_KEY` | JWT 签名密钥（随机字符串） | 随便输入一串英文字母数字 |
   | `DEEPSEEK_API_KEY` | DeepSeek API Key | `sk-你的APIKey` |
   | `DEEPSEEK_BASE_URL` | DeepSeek API 地址 | `https://api.deepseek.com` |
   | `DEEPSEEK_MODEL` | DeepSeek 模型名 | `deepseek-chat` |
   | `UPLOAD_FOLDER` | 文件上传目录 | `uploads` |
   | `CHROMA_DATA_PATH` | ChromaDB 数据目录 | `chroma_data` |
   | `EMBEDDING_MODEL` | 嵌入模型路径 | `embedding_models/bge-small-zh-v1.5` |

   > **ChromaDB 已改为嵌入式模式**，不再需要 `CHROMA_HOST` / `CHROMA_PORT` 配置，也无需单独启动 ChromaDB 服务。数据直接存储在 `CHROMA_DATA_PATH` 指定的本地目录中。

4. 按 `Ctrl+O` 保存，`Ctrl+X` 退出。

> 获取 DeepSeek API Key：[platform.deepseek.com](https://platform.deepseek.com)

---

### 八、初始化数据库表结构

确保在项目目录下且虚拟环境已激活：

```bash
cd ~/flask项目
flask --app run db upgrade
```

成功输出类似：
```
INFO  [alembic.runtime.migration] Running upgrade ...
```

> **如果报错**，尝试备选方案：
> ```bash
> flask --app run db stamp head
> flask --app run db upgrade
> ```
> 或手动建表：
> ```bash
> python3
> >>> from run import app, db
> >>> with app.app_context():
> ...     db.create_all()
> ...     print("建表成功")
> >>> exit()
> ```

---

### 九、下载嵌入模型（如需要）

模型文件应存放在 `embedding_models/bge-small-zh-v1.5/` 目录下。如果该目录为空或不存在，运行：

```bash
# 国内用户推荐使用镜像站
HF_ENDPOINT=https://hf-mirror.com python download_model.py

# 或直接下载（需要能访问 Hugging Face）
python download_model.py
```

模型约 100MB，下载完成后会自动验证可用性。

---

### 十、启动 Flask 应用

```bash
cd ~/flask项目
python3 run.py
```

启动成功后显示：
```
 * Running on http://127.0.0.1:5001
```

> **注意**：ChromaDB 使用嵌入式模式，**无需单独启动**。Flask 应用启动时会自动初始化 ChromaDB 并连接到本地数据目录。

---

### 十一、访问系统

在 Windows 浏览器中访问：**http://127.0.0.1:5001**

> WSL2 会自动将 `127.0.0.1` 转发到 Ubuntu 内部，所以直接在 Windows 浏览器中访问即可。

---

### WSL2 专属补充说明

| 事项 | 说明 |
|------|------|
| **每次重启电脑后** | WSL2 中的 MySQL 服务不会自动启动。打开 Ubuntu 终端，执行 `sudo service mysql start` 启动 MySQL。 |
| **设置 MySQL 开机自启（可选）** | 在 Ubuntu 中执行 `sudo systemctl enable mysql`（某些 WSL2 版本可能不支持 systemd，如果没有效果则每次都手动启动即可）。 |
| **向量模型** | 模型需放在 `embedding_models/bge-small-zh-v1.5/` 目录下（约 100MB）。如果目录为空，运行 `HF_ENDPOINT=https://hf-mirror.com python download_model.py` 下载。 |
| **端口冲突** | 如果 5001 端口已被占用，在 `.env` 中设置 `FLASK_PORT=5002` 或直接修改 `run.py`。 |
| **停止服务** | 在终端窗口中按 `Ctrl+C` 停止 Flask，然后输入 `deactivate` 退出虚拟环境。 |

---

## 方式二：纯 Windows 运行

如果你的 Windows 版本不支持 WSL2 或不希望安装 WSL2，可以使用以下纯 Windows 方案。

---

### 一、安装 Python

1. 前往 [python.org](https://www.python.org/downloads/) 下载 **Python 3.9 ~ 3.12** 的 Windows 64 位安装包（推荐 **3.10** 或 **3.11**，兼容性最好）。
2. 运行安装程序，**务必勾选底部**「**Add Python to PATH**」，然后点击「Install Now」。
3. 安装完成后，打开 **命令提示符（cmd）** 或 **PowerShell**，验证安装：
   ```
   python --version
   pip --version
   ```

---

### 二、安装 Visual C++ 运行时（PyTorch 依赖）

PyTorch、onnxruntime 等库依赖系统级的 Visual C++ 运行库。如果系统缺少该运行时，后续 `pip install` 可能失败。

1. 访问：[https://aka.ms/vs/17/release/vc_redist.x64.exe](https://aka.ms/vs/17/release/vc_redist.x64.exe)
2. 下载后运行，勾选同意条款 → 安装。完成后建议重启电脑。

---

### 三、安装并配置 MySQL

1. 前往 [dev.mysql.com/downloads/mysql](https://dev.mysql.com/downloads/mysql/) 下载 **MySQL Community Server**（推荐 **8.0.x**，选择 Windows x64 Installer）。
2. 运行安装程序，安装类型选 **Developer Default** 或 **Server only**，按向导完成。
3. **记住**安装过程中设置的 **root 密码**。
4. 打开 **MySQL 命令行客户端**（开始菜单搜索 "MySQL"），输入密码登录。
5. 执行以下 SQL 创建数据库：
   ```sql
   CREATE DATABASE campus_rag CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
6. 输入 `exit` 退出。

---

### 四、获取项目代码

确保项目完整代码已放在本地某个目录下（应包含 `run.py`、`app.py`、`config.py`、`requirements.txt`、`.env.example` 等）。记下该目录路径。

---

### 五、创建 Python 虚拟环境

打开命令提示符（cmd），切换到项目根目录：

```
cd /d <项目根目录路径>
python -m venv venv
venv\Scripts\activate
```

---

### 六、安装 Python 依赖

#### 方案一：一键安装（强烈推荐）

```bash
pip install -r requirements.txt
```

> 如果 `requirements.txt` 中的 torch 版本与 Windows 不兼容或体积过大，替换为 CPU 版：
> ```
> pip install torch --index-url https://download.pytorch.org/whl/cpu
> ```

#### 方案二：逐条安装（备选）

```bash
python -m pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install flask flask-login flask-sqlalchemy flask-migrate pymysql
pip install sentence-transformers chromadb
pip install PyPDF2 python-docx python-dotenv PyJWT
pip install requests lxml
```

---

### 七、配置环境变量（.env 文件）

项目所有配置通过 `.env` 文件管理，**不再直接修改 `config.py`**。

1. 复制示例配置文件：
   ```
   copy .env.example .env
   ```

2. 用文本编辑器（记事本或 VS Code）打开 `.env`，填写以下关键配置：

   | 配置项 | 说明 | 示例值 |
   |--------|------|--------|
   | `DATABASE_URL` | MySQL 连接地址（改为你实际设置的密码） | `mysql+pymysql://root:你的密码@127.0.0.1:3306/campus_rag?charset=utf8mb4` |
   | `SECRET_KEY` | Flask 密钥（随便输入一串字符） | `my-secret-key-abc123` |
   | `JWT_SECRET_KEY` | JWT 签名密钥（随便输入一串字符） | `my-jwt-secret-xyz789` |
   | `DEEPSEEK_API_KEY` | DeepSeek API Key | `sk-你的APIKey` |
   | `DEEPSEEK_BASE_URL` | DeepSeek API 地址 | `https://api.deepseek.com` |
   | `DEEPSEEK_MODEL` | DeepSeek 模型名 | `deepseek-chat` |
   | `UPLOAD_FOLDER` | 文件上传目录 | `uploads` |
   | `CHROMA_DATA_PATH` | ChromaDB 数据目录 | `chroma_data` |
   | `EMBEDDING_MODEL` | 嵌入模型路径 | `embedding_models/bge-small-zh-v1.5` |

   > **ChromaDB 已改为嵌入式模式**，不再需要单独启动 ChromaDB 服务。数据直接存储在 `CHROMA_DATA_PATH` 指定的本地目录中，Flask 启动时自动连接。

3. 保存并关闭。

---

### 八、初始化数据库表结构

```
flask --app run db upgrade
```

> 如果失败，尝试：
> ```
> flask --app run db stamp head
> flask --app run db upgrade
> ```
> 或手动执行：
> ```
> python
> >>> from run import app, db
> >>> with app.app_context():
> ...     db.create_all()
> >>> exit()
> ```

---

### 九、下载嵌入模型（如需要）

模型文件应存放在 `embedding_models/bge-small-zh-v1.5/` 目录下。如果该目录为空或不存在：

```
python download_model.py
```

> 国内用户可设置镜像站环境变量后再运行：
> ```
> set HF_ENDPOINT=https://hf-mirror.com
> python download_model.py
> ```

---

### 十、启动 Flask 应用

```
cd /d <项目根目录路径>
python run.py
```

看到 `Running on http://127.0.0.1:5001` 即为成功。

> **注意**：不再需要单独启动 ChromaDB 服务。ChromaDB 使用嵌入式模式（PersistentClient），Flask 启动时会自动初始化。

---

### 十一、访问系统

浏览器访问 **http://127.0.0.1:5001**。

---

### 纯 Windows 方式补充说明

| 事项 | 说明 |
|------|------|
| **向量模型** | 模型需放在 `embedding_models/bge-small-zh-v1.5/` 目录下（约 100MB）。如果目录为空，运行 `python download_model.py` 下载（国内推荐先 `set HF_ENDPOINT=https://hf-mirror.com`）。 |
| **MySQL 服务** | 确保 Windows 服务中的 `MySQL80` 状态为「正在运行」。 |
| **pip 安装慢** | 使用清华镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`。 |
| **端口冲突** | 在 `.env` 中设置 `FLASK_PORT=5002` 或修改 `run.py` 中的端口号。 |
| **停止服务** | 在命令提示符窗口中按 `Ctrl+C`，然后输入 `deactivate` 退出虚拟环境。 |

---

## 两种方式公共步骤

以下内容对**方式一（WSL2）和方式二（纯 Windows）均适用**。

---

### 项目架构说明

```
请求 → router → middleware(auth) → controller → service → dao → model(ORM) → MySQL
                                                          → vector_store → ChromaDB(嵌入式)
                                                          → deepseek → DeepSeek API
页面 → router → controller → render_template → Jinja2 模板
```

ChromaDB 使用 **PersistentClient 嵌入式模式**，数据持久化到本地 `chroma_data/` 目录，无需单独启动服务进程。

---

### 各功能模块及访问地址

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

### 完整使用流程

1. 注册账号 → 登录系统。
2. 进入「上传文档」页面，上传校园相关文档（PDF/DOCX/TXT/MD）。
3. 上传成功后，文档状态变为 `ready`，表示已成功建立向量索引。
4. 进入「智能问答」页面，输入问题（如"图书馆的开放时间是什么？"）。
5. 系统会自动：问题向量化 → ChromaDB 语义检索 → DeepSeek 大模型生成回答 → 返回结果及答案来源。
6. 可在「向量库管理」页面查看所有已索引分块。

---

### 常见问题排查

| 问题 | 解决方案 |
|-----|---------|
| **向量模型加载失败** | 确认项目目录下 `embedding_models/bge-small-zh-v1.5/` 存在且包含 `model.safetensors`（约 100MB）和 `config.json` 等文件。如果缺失，运行 `python download_model.py` 重新下载（国内推荐 `HF_ENDPOINT=https://hf-mirror.com python download_model.py`）。 |
| **ChromaDB 初始化失败** | ① 确认 `.env` 中 `CHROMA_DATA_PATH` 配置的目录有写入权限 ② 确认 `chromadb` 包已正确安装（`pip install chromadb`）③ ChromaDB 使用嵌入式模式，无需单独启动服务，确保没有旧版 ChromaDB 服务占用数据目录。 |
| **MySQL 连接失败** | ① 确认 MySQL 服务已启动 ② 确认 `.env` 中 `DATABASE_URL` 的用户名密码正确 ③ 确认 `campus_rag` 数据库已创建。 |
| **数据库迁移报错** | 依次执行：`flask --app run db stamp head` → `flask --app run db upgrade`。仍失败则手动建表（见第八步备选方案）。 |
| **缺少必需配置项** | 确认 `.env` 文件中 `SECRET_KEY`、`JWT_SECRET_KEY`、`DATABASE_URL` 均已填写，不能为空。参考 `.env.example` 检查是否有遗漏项。 |
| **pip 安装报错** | 检查 Python 版本是否为 3.9~3.12；检查 VC++ 运行时是否已安装；尝试使用国内镜像源。 |
| **端口 5001 被占用** | 在 `.env` 中设置 `FLASK_PORT=5002` 或修改 `run.py` 最后一行的端口号。 |
| **DeepSeek API 返回错误** | 检查 `.env` 中的 `DEEPSEEK_API_KEY` 是否正确、是否还有余额、网络是否能访问 `api.deepseek.com`。 |

---

## 停止所有服务

停止顺序：

1. 在 Flask 运行的终端窗口中按 **Ctrl + C** 停止 Flask。
2. 输入 `deactivate` 退出虚拟环境。
3. （WSL2）如需停止 MySQL：`sudo service mysql stop`。

> ChromaDB 使用嵌入式模式，随 Flask 进程自动启动和关闭，无需单独管理。
