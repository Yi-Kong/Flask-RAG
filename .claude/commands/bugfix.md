# /bugfix — Bug 修复命令

定位问题、提出原因、最小化修改并补测试。

## 执行流程

### 第 1 步：理解问题

1. **复述 bug**：向用户确认你理解的 bug 现象
2. **收集信息**：
   - 哪个页面/API 出问题？
   - 什么操作触发的？
   - 有错误日志吗？
   - 什么时间开始出现的？（最近改了什么？）

### 第 2 步：定位根因（只读分析）

按以下顺序排查：

1. **查看错误日志**：读取 `chroma.log`、终端输出、Flask 错误响应
2. **追踪请求路径**：从路由 → 控制器 → 服务 → DAO 逐层排查
3. **检查数据状态**：数据库记录是否正确、向量库数据是否同步
4. **对比最近变更**：`git log --oneline -10` 查看最近的提交
5. **考虑常见 Flask 陷阱**：
   - `request.form` vs `request.get_json()` 混用
   - Cookie 未设置 `httpOnly`/`samesite`
   - 请求上下文 (`flask.g`) 在非请求线程中使用
   - 模板变量未传递导致 `jinja2.exceptions.UndefinedError`
   - 文件上传后未刷新 `db.session`

### 第 3 步：提出假设

向用户说明：
- **根因假设**：你认为 bug 的原因是什么
- **证据**：支持这个假设的日志/代码引用
- **修复方案**：最小的代码改动是什么
- **副作用评估**：修复是否会影响其他功能

等待用户确认后再修改。

### 第 4 步：最小化修改

修复原则：
1. **只改必要的代码**，不要顺手重构
2. **修改行数尽可能少**
3. **保持与现有代码风格一致**
4. 如果涉及多个文件，一次改完并说明关联关系

### 第 5 步：补测试（如适用）

- 为修复的 bug 添加一个回归测试
- 测试应能复现原 bug 场景
- 如果有 `tests/` 目录，放入对应模块的测试文件

### 第 6 步：验证

1. 语法检查修复的文件
2. 说明如何手动验证修复（curl 命令或浏览器操作）
3. 如果有测试，运行确认通过

---

## 常见问题速查

| 症状 | 常见原因 | 排查文件 |
|------|---------|----------|
| 401 未授权 | JWT 过期/Cookie 未设置/中间件配置 | `middleware/auth_middleware.py`, `utils/auth.py` |
| 500 服务器错误 | 数据库连接/外键约束/向量库连接 | `extensions.py`, `service/vector_store.py` |
| 模板渲染异常 | 变量未传递/过滤器错误 | `controller/page_controller.py`, 对应模板 |
| 文件上传失败 | 扩展名校验/文件大小限制/磁盘空间 | `controller/document_controller.py`, `config.py` |
| RAG 回答不准 | chunk 大小/检索 top_k/模型温度 | `service/rag_service.py`, `service/chunker.py` |
| 数据不同步 | 事务未提交/ChromaDB 与 MySQL 不一致 | `dao/*_dao.py`, `service/document_service.py` |
