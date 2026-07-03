# /db-change — 数据库变更命令

用于模型变更、迁移文件、回滚风险、数据兼容性检查。

## ⚠️ 重要警告

数据库变更是**高风险操作**。执行前必须：
1. 确认当前在正确的 git 分支
2. 确认数据库已备份（或确认可接受数据丢失）
3. 获得用户明确确认

---

## 执行流程

### 第 1 步：分析变更需求

向用户确认：
- 要新增/修改/删除哪个表或字段？
- 字段的类型、约束、默认值是什么？
- 是否需要索引？
- 是否涉及外键关系？
- 新字段是否可以为 NULL（向后兼容）？

### 第 2 步：评估影响范围

在修改模型之前，分析受影响的所有文件：

| 层级 | 受影响的文件 | 需要的变更 |
|------|------------|-----------|
| Model | `model/*.py` | 新增/修改字段定义 |
| Model `__init__` | `model/__init__.py` | 如果有新模型，需导出 |
| DAO | `dao/*_dao.py` | 新字段的查询/创建/更新逻辑 |
| Service | `service/*_service.py` | 使用新字段的业务逻辑 |
| Controller | `controller/*_controller.py` | 新字段的输入校验 |
| Template | `view/*.html` | 如果新字段需在页面展示 |
| Migration | `migrations/versions/*.py` | 自动生成 + 手动审查 |

向用户展示评估结果，等待确认。

### 第 3 步：修改模型

1. **添加字段**：优先使用 `nullable=True` + `default` 以保持向后兼容
2. **修改字段**：尽量用 `alter_column` 而非删除重建
3. **删除字段**：先确认没有代码在使用该字段
4. 更新 `model/__init__.py`（如有新模型）

### 第 4 步：生成迁移文件

```bash
flask --app run db migrate -m "描述性迁移信息"
```

**重要**：生成后必须检查 `migrations/versions/` 中最新的迁移文件：
- `upgrade()` 是否正确创建/修改了表结构
- `downgrade()` 是否可安全回滚
- 是否有数据丢失风险（如 `nullable=False` 对已有表）

### 第 5 步：兼容性检查

- **新增 NOT NULL 字段**：必须设置 default 值，或先设 nullable 再迁移数据
- **删除字段**：确认 DAO/Service/Controller/Template 中无引用
- **重命名字段**：Alembic 可能不会自动检测重命名，需手动编辑迁移脚本
- **修改字段类型**：可能不兼容，需在迁移脚本中写明 `ALTER COLUMN ... USING ...`
- **外键变更**：检查关联表数据完整性

### 第 6 步：执行迁移

```bash
flask --app run db upgrade
```

执行后：
1. 检查是否有错误输出
2. 验证表结构：`docker exec mysql mysql -uroot -p123456 -e "DESCRIBE campus_rag.<table>;"`
3. 验证应用正常运行

### 第 7 步：更新 DAO 和 Service

根据新字段更新对应的 DAO 和 Service 层代码，确保所有使用该模型的代码都能正确处理新字段。

---

## 回滚操作

如果迁移出了问题：

```bash
# 回滚到上一个版本
flask --app run db downgrade

# 回滚到指定版本
flask --app run db downgrade <revision_id>
```

---

## 当前数据库状态

| 表名 | 当前字段 | 迁移版本 |
|------|---------|----------|
| `users` | id, username, password, email, role, created_at | 57570f3e4b7b |
| `documents` | id, title, filename, file_type, file_path, chunk_count, status, uploaded_by, created_at | 8a7a72654d24 |
| `conversations` | id, user_id, title, created_at, updated_at | 8a7a72654d24 |
| `qa_records` | id, user_id, conversation_id, document_id, question, answer, sources, created_at | 8a7a72654d24 |

---

## 禁止操作

- ❌ 不要直接修改数据库表结构（手动 SQL），必须通过 migration
- ❌ 不要在 migration 文件中写业务逻辑
- ❌ 不要删除 migration 历史文件
- ❌ 不要在生产环境执行 `db downgrade` 而不先备份
- ❌ 不要提交未测试过的 migration 文件
