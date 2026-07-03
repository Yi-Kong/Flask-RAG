# /feature — 新功能开发命令

为 Flask 项目添加新功能时的标准流程。

## 执行流程

请严格按以下 5 步执行，每步完成后再进入下一步：

### 第 1 步：理解现有结构（只读）

在修改任何代码之前，必须先了解：

1. **相关路由**：阅读 `routers/` 中相关的 Blueprint 文件，了解现有路由结构
2. **相关控制器**：阅读 `controller/` 中对应的控制器，了解请求处理流程
3. **相关模板**：阅读 `view/` 中相关的 Jinja2 模板，了解前端展示方式
4. **相关服务**：阅读 `service/` 中相关的业务逻辑
5. **相关模型**：阅读 `model/` 中相关的数据模型和 `dao/` 中的数据操作
6. **权限模型**：了解路由是公开还是受保护（检查 `routers/router.py`）

### 第 2 步：给出方案（先讨论，不写代码）

向用户说明：

- **改动范围**：要修改哪些文件（列表）
- **改动原因**：每个文件的改动目的
- **API 设计**（如果是新 API）：URL、method、请求参数、响应格式
- **模板变更**：需要新增或修改的 HTML 模板
- **数据库影响**：是否需要新表/新字段，是否需要 migration
- **权限影响**：新功能是否需要登录/管理员权限
- **潜在风险**：可能影响现有功能的地方

等待用户确认后再继续。

### 第 3 步：联动修改（同时检查 5 个层级）

根据改动类型，必须联动检查：

| 改动类型 | 必须检查的文件 |
|----------|---------------|
| 新增 API 路由 | `routers/*_router.py` → `controller/*_controller.py` → `middleware/auth_middleware.py`（权限） |
| 新增页面路由 | `routers/page_router.py` → `controller/page_controller.py` → `view/*.html` |
| 新增业务逻辑 | `controller/*_controller.py` → `service/*_service.py` → `dao/*_dao.py` |
| 新增数据表 | `model/*.py` → `dao/*_dao.py` → `migrations/` → 更新 `model/__init__.py` |
| 修改模板 | `view/*.html` → 检查对应的 controller（确认传给模板的变量） |
| 修改权限 | `middleware/auth_middleware.py` → 检查所有受影响的 Blueprint |

### 第 4 步：实现代码

代码规范：
- 新 API 使用 `dto/response.py` 中的 `ok()` / `fail()` 统一格式
- 异常使用 `exceptions.py` 中的自定义异常类
- 文件上传使用 UUID 重命名，校验扩展名白名单
- 模板中 URL 使用 `url_for()`，不硬编码路径
- 所有用户输入在 controller 层校验
- 保持 Jinja2 服务端渲染方式，不引入前端框架
- 注释使用中文

### 第 5 步：验证

完成后：
1. 运行语法检查：`python -c "import py_compile; py_compile.compile('修改的文件.py', doraise=True)"`
2. 如果有测试，运行相关测试
3. 说明应如何手动测试（curl 命令或浏览器操作步骤）
4. 如果有数据库变更，确认 migration 文件已生成

---

## 常见功能开发参考

### 新增一个页面

```
1. routers/page_router.py  → 添加路由
2. controller/page_controller.py → 添加视图函数
3. view/new_page.html → 创建 Jinja2 模板
4. routers/router.py → 确认 Blueprint 注册和权限模式
```

### 新增一个 API

```
1. routers/xxx_router.py → 定义 Blueprint + 路由
2. controller/xxx_controller.py → 请求处理 + 参数校验
3. service/xxx_service.py → 业务逻辑（如需要）
4. dao/xxx_dao.py → 数据操作（如需要）
5. routers/router.py → 注册新 Blueprint（如新建了 Blueprint）
```

### 新增一个数据表

使用 `/db-change` 命令的标准流程。

---

## 禁止事项（再次强调）

- ❌ 不要把项目改成 React/Vue/Next.js 等前后端分离架构
- ❌ 不要引入大型新框架（Celery、Redis、Docker Compose 等）
- ❌ 不要随意改数据库 schema 而不生成 migration
- ❌ 不要把 secret、token、数据库密码写进代码
- ❌ 不要删除现有业务代码
- ❌ 不要重命名现有核心目录
