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
  - [请求与响应模型：app/schemas.py](#app-schemas)
  - [数据库操作：app/repository.py](#app-repository)
- [数据库迁移函数](#数据库迁移函数)
  - [Alembic 运行入口](#migration-env)
  - [Alembic 文件模板](#migration-template)
  - [首次 migration](#migration-0001)
- [测试函数](#测试函数)
  - [配置测试](#test-config)
  - [健康检查测试](#test-health)
  - [数据模型测试](#test-models)
  - [请求模型测试](#test-schemas)
  - [数据库操作测试](#test-repository)
  - [通知 API 测试](#test-notifications-api)

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
| [app/api.py](#app-api) | `health_check()`、`create_notification()`、`get_notification_status()` |
| [app/schemas.py](#app-schemas) | `normalize_method()`、`validate_headers()` |
| [app/repository.py](#app-repository) | `request_matches_job()`、`get_notification()`、`get_notification_by_idempotency_key()`、`resolve_existing_notification()`、`create_notification()` |
| [migrations/env.py](#migration-env) | `run_migrations_offline()`、`do_run_migrations()`、`run_async_migrations()`、`run_migrations_online()` |
| [migrations/script.py.mako](#migration-template) | `upgrade()`、`downgrade()` migration 模板 |
| [migrations/versions/0001_create_notification_jobs.py](#migration-0001) | `upgrade()`、`downgrade()` |
| [tests/test_config.py](#test-config) | `test_settings_reads_environment_variables()` |
| [tests/test_health.py](#test-health) | `test_health_returns_ok_when_database_is_ready()`、`test_health_returns_503_when_database_is_unavailable()` |
| [tests/test_models.py](#test-models) | `test_notification_job_table_contains_required_fields()`、`test_notification_status_values_are_stable()` |
| [tests/test_schemas.py](#test-schemas) | `test_notification_create_normalizes_method_and_url()`、`test_notification_create_rejects_invalid_input()` |
| [tests/test_repository.py](#test-repository) | `make_job()`、`test_request_matches_job_compares_outbound_content()`、`test_resolve_existing_notification_rejects_different_request()`、`test_create_notification_commits_before_returning()` |
| [tests/test_notifications_api.py](#test-notifications-api) | `override_session()`、`make_job()`、8 个通知 API 测试函数 |

## 主要类和数据结构

这些类本身没有项目自定义方法，但理解函数时会用到：

| 类 | 位置 | 用途 |
|---|---|---|
| `Settings` | `app/config.py` | 保存应用名称、运行环境和数据库连接等配置 |
| `NotificationStatus` | `app/models.py` | 集中定义五种合法任务状态 |
| `Base` | `app/models.py` | 汇总 SQLAlchemy 表结构，供 migration 使用 |
| `NotificationJob` | `app/models.py` | 表示数据库中的一条通知任务 |
| `HealthResponse` | `app/api.py` | 约束健康检查成功时的 JSON 格式 |
| `HTTPMethod` | `app/schemas.py` | 定义 MVP 允许使用的四种 HTTP 方法 |
| `NotificationCreate` | `app/schemas.py` | 校验创建通知时传入的 URL、方法、Header 和 Body |
| `NotificationAccepted` | `app/schemas.py` | 约束任务被接收后的简短响应 |
| `NotificationStatusResponse` | `app/schemas.py` | 约束查询任务状态时的完整响应 |
| `IdempotencyConflictError` | `app/repository.py` | 表示同一个幂等 key 被用于不同请求 |
| `CreateNotificationResult` | `app/repository.py` | 同时返回任务和“是否为本次新建”的结果 |

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

#### `create_notification(request, response, session, idempotency_key)`

- **用途**：实现 `POST /notifications`，把一个合法通知可靠地写入数据库。
- **输入**：已校验的通知内容、HTTP 响应对象、数据库 session，以及可选的 `Idempotency-Key`。
- **返回**：任务 UUID 和初始状态 `pending`，HTTP 状态码为 `202`。
- **主要过程**：清理幂等 key，调用 repository 完成写入，再把数据库对象转换成响应。
- **失败情况**：空白 key 返回 `422`；同 key 不同请求返回 `409`；数据库提交失败时错误继续向上抛出，绝不会返回 `202`。
- **副作用**：可能在 PostgreSQL 中新增一条通知任务；重复请求不会新增。

#### `get_notification_status(notification_id, session)`

- **用途**：实现 `GET /notifications/{id}`，查询一条任务目前的状态。
- **输入**：URL 中的通知 UUID 和数据库 session。
- **返回**：任务状态、尝试次数、下次执行时间、最近错误和时间戳。
- **主要过程**：按主键查询任务，找到后转换成标准响应。
- **失败情况**：UUID 格式错误时 FastAPI 返回 `422`；数据库中不存在时返回 `404`。
- **副作用**：只读查询 PostgreSQL，不修改任务。

---

<a id="app-schemas"></a>

### 请求与响应模型：`app/schemas.py`

#### `normalize_method(cls, value)`

- **用途**：让调用方可以写 `post` 或 `POST`，内部统一保存为大写。
- **输入**：尚未完成校验的 method 值。
- **返回**：字符串会转成大写，其他类型原样交给后续校验。
- **主要过程**：在 `HTTPMethod` 枚举校验前做一次简单标准化。
- **失败情况**：不在允许列表中的值随后由 Pydantic 拒绝。
- **副作用**：无。

#### `validate_headers(cls, headers)`

- **用途**：防止非法 Header 名称和换行注入。
- **输入**：Header 名称和值组成的字典。
- **返回**：校验通过后的原字典。
- **主要过程**：逐项检查名称格式，并确认值中没有回车或换行符。
- **失败情况**：发现非法名称或值时抛出 Pydantic 可转换的校验错误，API 返回 `422`。
- **副作用**：无。

---

<a id="app-repository"></a>

### 数据库操作：`app/repository.py`

#### `request_matches_job(job, request)`

- **用途**：判断新请求和数据库中的旧任务是否代表完全相同的外部调用。
- **输入**：一个已有任务和一个创建请求。
- **返回**：URL、方法、Header、Body 全部相同时返回 `True`，否则返回 `False`。
- **主要过程**：对四个会影响外部请求的字段逐项比较。
- **失败情况**：无；只做内存比较。
- **副作用**：无。

#### `get_notification(session, notification_id)`

- **用途**：根据公开 UUID 读取一条通知任务。
- **输入**：数据库 session 和任务 UUID。
- **返回**：找到时返回 `NotificationJob`，否则返回 `None`。
- **主要过程**：使用 SQLAlchemy 主键查询。
- **失败情况**：数据库连接或查询失败时向上抛出数据库错误。
- **副作用**：只读查询 PostgreSQL。

#### `get_notification_by_idempotency_key(session, idempotency_key)`

- **用途**：查找某个幂等 key 之前创建的任务。
- **输入**：数据库 session 和已经清理过的幂等 key。
- **返回**：已有任务或 `None`。
- **主要过程**：对唯一的 `idempotency_key` 字段执行查询。
- **失败情况**：数据库查询失败时向上抛错。
- **副作用**：只读查询 PostgreSQL。

#### `resolve_existing_notification(session, idempotency_key, request)`

- **用途**：统一处理“这个 key 是否已经使用过”的判断。
- **输入**：数据库 session、幂等 key 和本次请求。
- **返回**：没有旧任务时返回 `None`；相同请求时返回原任务。
- **主要过程**：按 key 查询旧任务，再调用 `request_matches_job()` 比较内容。
- **失败情况**：同一个 key 对应不同内容时抛出 `IdempotencyConflictError`。
- **副作用**：只读查询 PostgreSQL。

#### `create_notification(session, request, idempotency_key)`

- **用途**：在事务成功提交后返回新任务，或返回相同幂等请求的原任务。
- **输入**：数据库 session、已校验请求和可选幂等 key。
- **返回**：`CreateNotificationResult`，包含任务以及本次是否真正新建。
- **主要过程**：先检查旧 key；需要新建时加入 session、提交并刷新数据库默认值。
- **失败情况**：唯一约束竞争时先回滚，再读取并比较胜出的任务；其他数据库错误继续向上抛出。
- **副作用**：可能新增并提交一条 PostgreSQL 记录，也可能因重复请求只读取旧记录。

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

---

<a id="test-schemas"></a>

### 请求模型测试：`tests/test_schemas.py`

#### `test_notification_create_normalizes_method_and_url()`

- **用途**：确认合法请求会被整理成一致的内部格式。
- **输入**：无；测试内构造小写 `post` 请求。
- **返回**：无。
- **主要过程**：创建模型并核对 method 和 URL。
- **失败情况**：没有转成 `POST` 或 URL 被错误修改时测试失败。
- **副作用**：无。

#### `test_notification_create_rejects_invalid_input(field, value)`

- **用途**：确认错误 URL、方法、Header 和 Body 都会被拒绝。
- **输入**：pytest 依次提供五组字段和值。
- **返回**：无。
- **主要过程**：把错误值放入正常请求，并期待 `ValidationError`。
- **失败情况**：任一非法输入被错误接受时测试失败。
- **副作用**：无。

---

<a id="test-repository"></a>

### 数据库操作测试：`tests/test_repository.py`

#### `make_job(**overrides)`

- **用途**：为 repository 测试快速创建字段完整的内存任务。
- **输入**：需要覆盖的任意任务字段。
- **返回**：一个未写入数据库的 `NotificationJob`。
- **主要过程**：先填入正常默认值，再应用测试指定的覆盖值。
- **失败情况**：传入不存在的字段时 SQLAlchemy 构造函数会报错。
- **副作用**：无。

#### `test_request_matches_job_compares_outbound_content()`

- **用途**：确认幂等比较会检查所有外部请求内容。
- **输入**：无。
- **返回**：无。
- **主要过程**：先比较完全相同的请求，再改变 Body 比较一次。
- **失败情况**：相同请求不匹配或不同请求被当成相同时测试失败。
- **副作用**：无。

#### `test_resolve_existing_notification_rejects_different_request(monkeypatch)`

- **用途**：确认同 key 不同内容会产生幂等冲突。
- **输入**：pytest 的 `monkeypatch`。
- **返回**：无。
- **主要过程**：模拟数据库返回内容不同的旧任务，并期待冲突异常。
- **失败情况**：没有抛出 `IdempotencyConflictError` 时测试失败。
- **副作用**：不访问真实数据库。

#### `test_create_notification_commits_before_returning(monkeypatch)`

- **用途**：确认新任务必须完成 commit 和 refresh 才返回。
- **输入**：pytest 的 `monkeypatch`。
- **返回**：无。
- **主要过程**：使用 mock session 创建任务，检查 add、commit、refresh 的调用。
- **失败情况**：漏掉任一持久化步骤时测试失败。
- **副作用**：不访问真实数据库。

---

<a id="test-notifications-api"></a>

### 通知 API 测试：`tests/test_notifications_api.py`

#### `override_session()`

- **用途**：API 单元测试 mock repository 时提供假的数据库依赖。
- **输入**：无。
- **返回**：异步产生一个占位对象。
- **主要过程**：替代 FastAPI 的 `get_session()`。
- **失败情况**：若未正确覆盖依赖，测试可能错误连接真实数据库。
- **副作用**：无。

#### `make_job()`

- **用途**：为 API 响应测试创建一条字段完整的 pending 任务。
- **输入**：无。
- **返回**：一个内存中的 `NotificationJob`。
- **主要过程**：生成 UUID、当前时间和所有响应必需字段。
- **失败情况**：模型字段变化但 helper 未更新时相关测试失败。
- **副作用**：无。

#### `test_create_notification_returns_202_after_storage(monkeypatch)`

- **用途**：确认成功保存后 API 返回 `202`、UUID 和 `pending`。
- **输入**：pytest 的 `monkeypatch`。
- **返回**：无。
- **主要过程**：模拟 repository 成功，提交完整 HTTP 请求并检查响应。
- **失败情况**：状态码、响应或传给 repository 的 key 不正确时测试失败。
- **副作用**：不访问真实数据库或网络。

#### `test_create_notification_marks_idempotent_replay(monkeypatch)`

- **用途**：确认重复请求返回原任务并带有 replay Header。
- **输入**：pytest 的 `monkeypatch`。
- **返回**：无。
- **主要过程**：模拟 `created=False`，检查 ID 和 `Idempotent-Replayed`。
- **失败情况**：API 新建 ID 或漏加 Header 时测试失败。
- **副作用**：不访问真实数据库或网络。

#### `test_create_notification_returns_409_for_key_conflict(monkeypatch)`

- **用途**：确认 repository 的幂等冲突会转换成清楚的 HTTP `409`。
- **输入**：pytest 的 `monkeypatch`。
- **返回**：无。
- **主要过程**：模拟冲突异常并检查错误响应。
- **失败情况**：状态码或错误文字不符合约定时测试失败。
- **副作用**：不访问真实数据库或网络。

#### `test_create_notification_does_not_accept_database_failure(monkeypatch)`

- **用途**：确认数据库写入失败时绝不会返回 `202`。
- **输入**：pytest 的 `monkeypatch`。
- **返回**：无。
- **主要过程**：模拟未处理的数据库故障并让测试客户端查看 HTTP `500`。
- **失败情况**：API 错误确认任务已接收时测试失败。
- **副作用**：不访问真实数据库或网络。

#### `test_create_notification_returns_422_for_invalid_request()`

- **用途**：确认非法 URL 和 method 在写数据库前被拒绝。
- **输入**：无。
- **返回**：无。
- **主要过程**：发送带 FTP URL 和 TRACE method 的请求，检查两个字段错误。
- **失败情况**：状态码不是 `422` 或错误字段不完整时测试失败。
- **副作用**：不访问真实数据库或网络。

#### `test_get_notification_status_returns_job(monkeypatch)`

- **用途**：确认已知 UUID 可以返回数据库中的任务状态。
- **输入**：pytest 的 `monkeypatch`。
- **返回**：无。
- **主要过程**：模拟找到任务，调用查询接口并核对 ID 与次数。
- **失败情况**：响应内容和任务不一致时测试失败。
- **副作用**：不访问真实数据库或网络。

#### `test_get_notification_status_returns_404(monkeypatch)`

- **用途**：确认不存在的 UUID 返回 HTTP `404`。
- **输入**：pytest 的 `monkeypatch`。
- **返回**：无。
- **主要过程**：模拟查询结果为 `None` 并检查错误响应。
- **失败情况**：状态码或错误文字不正确时测试失败。
- **副作用**：不访问真实数据库或网络。

#### `test_notification_routes_appear_in_openapi()`

- **用途**：确认两个通知接口都出现在自动生成的 API 文档中。
- **输入**：无。
- **返回**：无。
- **主要过程**：读取 `/openapi.json`，检查 POST 创建和 GET 查询路径。
- **失败情况**：路由没有注册或 HTTP 方法错误时测试失败。
- **副作用**：不访问真实数据库或外部网络。
