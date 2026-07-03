# /audit — 项目审计命令

对 Flask 项目进行全面的结构和安全检查。

## 检查范围

### 1. 项目结构
- [ ] 确认目录结构完整性（model/ dao/ service/ controller/ routers/ middleware/ view/ utils/ dto/ migrations/ scripts/）
- [ ] 确认入口文件 `app.py`（create_app）和 `run.py` 存在
- [ ] 确认 `config.py` 从 `.env` 加载配置
- [ ] 检查是否有孤立的 .py 文件（未导入、未使用）
- [ ] 检查 `__init__.py` 是否完整

### 2. 路由和蓝图
- [ ] 列出所有 Blueprint 及其注册情况（`routers/router.py`）
- [ ] 确认每个 Blueprint 的认证模式（公开 vs 受保护）
- [ ] 检查是否有未注册到 `register_all_blueprints()` 的 Blueprint
- [ ] 列出所有路由的 URL、methods、对应控制器函数

### 3. 数据库和迁移
- [ ] 检查 `model/` 下所有模型文件
- [ ] 检查 `migrations/versions/` 下所有迁移版本
- [ ] 确认迁移链完整（upgrade/downgrade 路径无断裂）
- [ ] 检查是否有模型变更但未生成迁移文件（运行 `flask --app run db check` 等效检查）
- [ ] 检查是否有数据库连接串硬编码

### 4. 敏感信息扫描
在代码中搜索以下模式：
- `password`、`secret`、`token`、`api_key`、`api_token`
- 硬编码的 URL 含认证信息（如 `mysql://root:password@`）
- JWT secret 硬编码
- 未截断的 API key 日志打印

### 5. 安全问题
- [ ] `.env` 是否在 `.gitignore` 中
- [ ] 是否有 `@public` 装饰器被滥用
- [ ] 文件上传是否有扩展名和大小限制
- [ ] 是否有 SQL 拼接（应使用 ORM）
- [ ] 是否使用了 `|safe` 过滤器处理用户输入
- [ ] 密码是否使用了 werkzeug 哈希
- [ ] JWT token 是否设置了过期时间

### 6. 未完成事项
- [ ] 查找 TODO、FIXME、HACK、XXX 注释
- [ ] 查找被注释掉的代码块
- [ ] 查找 `pass` 或 `raise NotImplementedError`
- [ ] 检查空的 `__init__.py` 或空函数

### 7. 测试覆盖
- [ ] 是否存在 `tests/` 目录
- [ ] 是否存在测试文件
- [ ] 估算代码/测试覆盖率
- [ ] 标记关键路径是否缺少测试（认证、文档上传、RAG 问答）

### 8. 依赖检查
- [ ] `requirements.txt` 中是否有已知漏洞的包
- [ ] 是否有未在 `requirements.txt` 中声明的依赖
- [ ] 是否有过时的关键依赖（Flask、SQLAlchemy 等大版本）

## 输出格式

审计完成后，按以下格式输出报告：

```
## 项目审计报告 — [日期]

### 概览
- 架构类型: [App Factory / Blueprint / 单文件]
- 总文件数: [Python / HTML / 其他]
- 路由数: [总数，其中公开 X 个，受保护 Y 个]
- 数据库表: [N 个表]
- 迁移版本: [N 个]
- 测试文件: [N 个]

### 🔴 严重问题
- [必须立即修复的安全或数据风险]

### 🟡 警告
- [建议修复的问题]

### 🟢 良好实践
- [做得好的地方]

### 🔵 建议
- [可选的改进建议]
```
