# 函数说明文档

这份文档用简单中文解释项目中的每一个函数。它的目的不是重复代码，而是让第一次阅读项目的人快速知道：这个函数为什么存在、接收什么、返回什么，以及失败时会发生什么。

## 快速导航

- [维护规则](#维护规则)
- [记录格式](#记录格式)
- [当前函数目录](#当前函数目录)
- [主要类和数据结构](#主要类和数据结构)
- [应用代码函数](#应用代码函数)
  - [配置：app/config.py](#app-config)
  - [数据库连接：app/database.py](#app-database)
  - [API：app/api.py](#app-api)
- [数据库迁移函数](#数据库迁移函数)
  - [Alembic 运行入口](#migration-env)
  - [Alembic 文件模板](#migration-template)
  - [首次 migration](#migration-0001)
- [测试函数](#测试函数)
  - [配置测试](#test-config)
  - [健康检查测试](#test-health)
  - [数据模型测试](#test-models)

## 维护规则

- 新增函数时，在同一次修改中补充对应说明。
- 修改函数行为时，同步更新说明，避免文档与代码不一致。
- 删除函数时，删除对应条目。
- API 路由、后台任务、普通辅助函数和测试函数都需要记录。
- 说明以实际代码为准，不记录尚未实现的函数。
- 尽量使用日常语言；只有在影响理解时才使用专业术语。

## 记录格式

每个函数使用下面的简短格式：

```markdown
#### `function_name(parameter)`

- **位置**：`app/example.py`
- **用途**：用一句话说明这个函数解决什么问题。
- **输入**：说明每个参数代表什么；没有参数时写“无”。
- **返回**：说明返回值代表什么；没有返回值时写“无”。
- **主要过程**：按照实际执行顺序，用简单语言说明关键步骤。
- **失败情况**：说明可能出现的错误，以及函数如何处理。
- **副作用**：说明是否会修改数据库、发送网络请求、写日志或改变外部状态；没有时写“无”。
```

如果函数非常简单，可以合并“主要过程”和“失败情况”，但不能省略用途、输入和返回值。

## 当前函数目录

| 文件 | 函数 |
|---|---|
| [app/config.py](#app-config) | `get_settings()` |
| [app/database.py](#app-database) | `get_session()`、`database_is_ready()` |
| [app/api.py](#app-api) | `health_check()` |
| [migrations/env.py](#migration-env) | `run_migrations_offline()`、`do_run_migrations()`、`run_async_migrations()`、`run_migrations_online()` |
| [migrations/script.py.mako](#migration-template) | `upgrade()`、`downgrade()` migration 模板 |
| [migrations/versions/0001_create_notification_jobs.py](#migration-0001) | `upgrade()`、`downgrade()` |
| [tests/test_config.py](#test-config) | `test_settings_reads_environment_variables()` |
| [tests/test_health.py](#test-health) | `test_health_returns_ok_when_database_is_ready()`、`test_health_returns_503_when_database_is_unavailable()` |
| [tests/test_models.py](#test-models) | `test_notification_job_table_contains_required_fields()`、`test_notification_status_values_are_stable()` |

## 主要类和数据结构

这些类本身没有项目自定义方法，但理解函数时会用到：

| 类 | 位置 | 用途 |
|---|---|---|
| `Settings` | `app/config.py` | 保存应用名称、运行环境和数据库连接等配置 |
| `NotificationStatus` | `app/models.py` | 集中定义五种合法任务状态 |
| `Base` | `app/models.py` | 汇总 SQLAlchemy 表结构，供 migration 使用 |
| `NotificationJob` | `app/models.py` | 表示数据库中的一条通知任务 |
| `HealthResponse` | `app/api.py` | 约束健康检查成功时的 JSON 格式 |

---

## 应用代码函数

<a id="app-config"></a>

### 配置：`app/config.py`

#### `get_settings()`

- **用途**：取得当前进程使用的应用配置。
- **输入**：无；配置来自环境变量或项目根目录的 `.env`。
- **返回**：一个 `Settings` 对象。
- **主要过程**：第一次调用时读取并校验配置，之后重复使用同一个缓存对象。
- **失败情况**：配置值格式不合法时，Pydantic 会抛出清楚的校验错误。
- **副作用**：第一次调用时读取环境配置；不访问数据库。

---

<a id="app-database"></a>

### 数据库连接：`app/database.py`

#### `get_session()`

- **用途**：为一次 API 操作提供独立的异步数据库 session。
- **输入**：无。
- **返回**：异步产生一个 `AsyncSession`。
- **主要过程**：创建 session，交给调用方使用，并在使用结束后自动关闭。
- **失败情况**：连接或 SQL 操作失败时，错误交给实际调用数据库的业务函数处理。
- **副作用**：可能打开和关闭 PostgreSQL 连接。

#### `database_is_ready()`

- **用途**：判断 PostgreSQL 当前是否可以正常响应。
- **输入**：无。
- **返回**：可以执行 `SELECT 1` 时返回 `True`，否则返回 `False`。
- **主要过程**：临时取得连接并执行一条最简单的查询。
- **失败情况**：捕获 SQLAlchemy 数据库错误并返回 `False`，不会让健康检查直接崩溃。
- **副作用**：向 PostgreSQL 发送一次只读查询。

---

<a id="app-api"></a>

### API：`app/api.py`

#### `health_check()`

- **用途**：实现 `GET /health`，同时检查 API 和数据库是否可用。
- **输入**：无。
- **返回**：健康时返回 `{"status": "ok", "database": "ok"}`。
- **主要过程**：调用 `database_is_ready()`，根据结果生成 HTTP 响应。
- **失败情况**：数据库不可用时返回 HTTP `503` 和 `Database unavailable`。
- **副作用**：通过 `database_is_ready()` 查询一次数据库。

---

## 数据库迁移函数

<a id="migration-env"></a>

### Alembic 运行入口：`migrations/env.py`

#### `run_migrations_offline()`

- **用途**：在不连接数据库时生成 migration SQL。
- **输入**：无；使用 Alembic 当前配置和 SQLAlchemy metadata。
- **返回**：无。
- **主要过程**：配置离线 migration 上下文，然后生成待执行 SQL。
- **失败情况**：配置或 migration 文件不合法时由 Alembic 报错。
- **副作用**：生成 SQL 输出，不修改数据库。

#### `do_run_migrations(connection)`

- **用途**：通过已经建立的连接真正执行 migration。
- **输入**：Alembic 可使用的同步 `connection` 包装。
- **返回**：无。
- **主要过程**：把连接和表结构交给 Alembic，并在事务中执行 migration。
- **失败情况**：SQL 执行失败时事务回滚，错误继续交给 Alembic 显示。
- **副作用**：可能创建、修改或删除数据库结构。

#### `run_async_migrations()`

- **用途**：让 Alembic 可以通过项目的 asyncpg 数据库地址执行 migration。
- **输入**：无；读取当前 `DATABASE_URL`。
- **返回**：无。
- **主要过程**：创建临时异步 engine，取得连接，调用 `do_run_migrations()`，最后释放 engine。
- **失败情况**：连接或 migration 失败时向上抛错，命令以失败状态结束。
- **副作用**：连接 PostgreSQL，并可能修改数据库结构。

#### `run_migrations_online()`

- **用途**：从 Alembic 的同步入口启动异步 migration 流程。
- **输入**：无。
- **返回**：无。
- **主要过程**：使用 `asyncio.run()` 执行 `run_async_migrations()`。
- **失败情况**：异步 migration 的错误会继续向上抛出。
- **副作用**：间接连接并修改 PostgreSQL 结构。

---

<a id="migration-template"></a>

### Alembic 文件模板：`migrations/script.py.mako`

这个文件是 Alembic 创建新 migration 时使用的模板，不会作为应用代码直接运行。

#### `upgrade()`

- **用途**：为新 migration 生成“向前升级”函数的位置。
- **输入**：无；模板内容由 Alembic 生成命令填入。
- **返回**：无。
- **主要过程**：新 migration 生成后，函数体会包含需要增加的数据库结构操作。
- **失败情况**：模板本身不执行；生成后的 migration 失败时由 Alembic 报错。
- **副作用**：模板阶段无；生成后的函数可能修改数据库结构。

#### `downgrade()`

- **用途**：为新 migration 生成“撤销升级”函数的位置。
- **输入**：无；模板内容由 Alembic 生成命令填入。
- **返回**：无。
- **主要过程**：新 migration 生成后，函数体会包含对应的回退操作。
- **失败情况**：模板本身不执行；生成后的 migration 失败时由 Alembic 报错。
- **副作用**：模板阶段无；生成后的函数可能删除或还原数据库结构。

---

<a id="migration-0001"></a>

### 首次 migration：`migrations/versions/0001_create_notification_jobs.py`

#### `upgrade()`

- **用途**：创建第一版 `notification_jobs` 表。
- **输入**：无；由 Alembic 调用。
- **返回**：无。
- **主要过程**：创建 15 个字段、状态和次数约束、幂等键唯一约束，以及待处理任务索引。
- **失败情况**：数据库不支持操作或已有冲突结构时 migration 失败并回滚。
- **副作用**：创建数据库表和索引。

#### `downgrade()`

- **用途**：撤销第一版 migration。
- **输入**：无；由 Alembic 调用。
- **返回**：无。
- **主要过程**：先删除待处理任务索引，再删除 `notification_jobs` 表。
- **失败情况**：目标结构不存在或数据库拒绝操作时 migration 失败。
- **副作用**：删除表及其中的数据，只应在明确需要回退时使用。

---

## 测试函数

<a id="test-config"></a>

### 配置测试：`tests/test_config.py`

#### `test_settings_reads_environment_variables(monkeypatch)`

- **用途**：确认环境变量可以覆盖开发环境默认配置。
- **输入**：pytest 提供的 `monkeypatch`。
- **返回**：无；断言失败时测试失败。
- **主要过程**：临时设置四个环境变量，创建 `Settings`，再核对解析结果。
- **失败情况**：任一配置没有正确读取或转换时断言失败。
- **副作用**：只在当前测试期间临时修改环境变量。

---

<a id="test-health"></a>

### 健康检查测试：`tests/test_health.py`

#### `test_health_returns_ok_when_database_is_ready(monkeypatch)`

- **用途**：确认数据库正常时健康接口返回 HTTP `200` 和预期 JSON。
- **输入**：pytest 提供的 `monkeypatch`。
- **返回**：无；断言失败时测试失败。
- **主要过程**：把数据库检查替换为成功结果，通过内存中的 ASGI 客户端调用 `/health`。
- **失败情况**：状态码或响应内容不符合约定时测试失败。
- **副作用**：不访问真实网络或数据库。

#### `test_health_returns_503_when_database_is_unavailable(monkeypatch)`

- **用途**：确认数据库故障会被清楚地反映为 HTTP `503`。
- **输入**：pytest 提供的 `monkeypatch`。
- **返回**：无；断言失败时测试失败。
- **主要过程**：把数据库检查替换为失败结果，再调用 `/health`。
- **失败情况**：接口没有返回约定的 `503` 或错误信息时测试失败。
- **副作用**：不访问真实网络或数据库。

---

<a id="test-models"></a>

### 数据模型测试：`tests/test_models.py`

#### `test_notification_job_table_contains_required_fields()`

- **用途**：防止任务表的重要字段、约束或索引被意外删除。
- **输入**：无。
- **返回**：无；断言失败时测试失败。
- **主要过程**：读取 SQLAlchemy metadata，核对 15 个字段、四个命名约束和一个索引。
- **失败情况**：模型结构与预期不一致时测试失败。
- **副作用**：无；不连接数据库。

#### `test_notification_status_values_are_stable()`

- **用途**：保证 Python 中的任务状态与数据库约束使用相同的五个值。
- **输入**：无。
- **返回**：无；断言失败时测试失败。
- **主要过程**：收集 `NotificationStatus` 的所有值并与固定集合比较。
- **失败情况**：状态缺失、多出或拼写改变时测试失败。
- **副作用**：无。
