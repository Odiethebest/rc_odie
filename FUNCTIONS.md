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
  - [HTTP 投递：app/delivery.py](#app-delivery)
  - [Worker 数据库状态：app/worker_repository.py](#app-worker-repository)
  - [Worker 循环：app/worker.py](#app-worker)
  - [本地 Mock Vendor：app/mock_vendor.py](#app-mock-vendor)
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
  - [HTTP 投递测试](#test-delivery)
  - [Worker 数据库测试](#test-worker-repository)
  - [Worker 循环测试](#test-worker)
  - [Mock Vendor 测试](#test-mock-vendor)

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
| [app/delivery.py](#app-delivery) | `classify_status_code()`、`build_outbound_headers()`、`bound_error_message()`、`deliver_notification()` |
| [app/worker_repository.py](#app-worker-repository) | `retry_delay()`、`claim_due_notifications()`、`record_delivery_result()`、`recover_stale_notifications()` |
| [app/worker.py](#app-worker) | `process_claimed_notification()`、`run_worker_cycle()`、`wait_for_next_cycle()`、`worker_loop()`、`request_shutdown()`、`install_signal_handlers()`、`run_worker()`、`main()` |
| [app/mock_vendor.py](#app-mock-vendor) | `remember_request()`、`health_check()`、`accept_notification()`、`reject_temporarily()`、`reject_permanently()`、`get_received_notification()` |
| [migrations/env.py](#migration-env) | `run_migrations_offline()`、`do_run_migrations()`、`run_async_migrations()`、`run_migrations_online()` |
| [migrations/script.py.mako](#migration-template) | `upgrade()`、`downgrade()` migration 模板 |
| [migrations/versions/0001_create_notification_jobs.py](#migration-0001) | `upgrade()`、`downgrade()` |
| [tests/test_config.py](#test-config) | `test_settings_reads_environment_variables()` |
| [tests/test_health.py](#test-health) | `test_health_returns_ok_when_database_is_ready()`、`test_health_returns_503_when_database_is_unavailable()` |
| [tests/test_models.py](#test-models) | `test_notification_job_table_contains_required_fields()`、`test_notification_status_values_are_stable()` |
| [tests/test_schemas.py](#test-schemas) | `test_notification_create_normalizes_method_and_url()`、`test_notification_create_rejects_invalid_input()` |
| [tests/test_repository.py](#test-repository) | `make_job()`、`test_request_matches_job_compares_outbound_content()`、`test_resolve_existing_notification_rejects_different_request()`、`test_create_notification_commits_before_returning()` |
| [tests/test_notifications_api.py](#test-notifications-api) | `override_session()`、`make_job()`、8 个通知 API 测试函数 |
| [tests/test_delivery.py](#test-delivery) | `make_job()`、9 个投递测试函数 |
| [tests/test_worker_repository.py](#test-worker-repository) | 2 个 helper 和 5 个 Worker 数据库测试函数 |
| [tests/test_worker.py](#test-worker) | 4 个 helper、10 个嵌套 helper 和 7 个 Worker 循环测试函数 |
| [tests/test_mock_vendor.py](#test-mock-vendor) | 1 个清理 fixture 和 5 个 Mock Vendor 测试函数 |

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
| `DeliveryOutcome` | `app/delivery.py` | 定义成功、可重试失败和永久失败三种投递结果 |
| `DeliveryResult` | `app/delivery.py` | 保存一次投递的分类、HTTP 状态码和有限长度错误信息 |
| `FakeSessionContext` | `tests/test_worker.py` | 在 Worker 单元测试中模拟异步数据库 session 上下文 |

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

<a id="app-delivery"></a>

### HTTP 投递：`app/delivery.py`

#### `classify_status_code(status_code)`

- **用途**：把外部 API 状态码转换成 Worker 能直接处理的结果类别。
- **输入**：一个 HTTP 状态码。
- **返回**：成功、可重试失败或永久失败。
- **主要过程**：`2xx` 成功；`408`、`429`、`5xx` 可重试；其余状态永久失败。
- **失败情况**：无；无法识别为成功或临时错误的状态会安全地归为永久失败。
- **副作用**：无。

#### `build_outbound_headers(job)`

- **用途**：准备外部请求 Header，并保证通知 ID 由本服务控制。
- **输入**：一条 `NotificationJob`。
- **返回**：新的 Header 字典。
- **主要过程**：复制原 Header，删除调用方提供的同名通知 ID，再写入任务 UUID。
- **失败情况**：无；任务 Header 已在创建 API 中完成格式校验。
- **副作用**：无，不会修改任务原有 Header。

#### `bound_error_message(message)`

- **用途**：防止很长的网络错误被原样保存到数据库。
- **输入**：原始错误文字。
- **返回**：最多 500 个字符的错误文字；截断时以 `...` 结尾。
- **主要过程**：短文字原样返回，长文字保留前部并添加截断标记。
- **失败情况**：无。
- **副作用**：无。

#### `deliver_notification(job, client)`

- **用途**：向目标地址发送一次通知，并返回结构化结果。
- **输入**：通知任务和可复用的 `httpx.AsyncClient`。
- **返回**：`DeliveryResult`，包含结果类别、状态码和错误文字。
- **主要过程**：构造请求、设置 10 秒超时且不跟随跳转、发送请求，再分类状态码。
- **失败情况**：连接错误和超时会转换成可重试结果；其他意外编程错误继续抛出。
- **副作用**：发送一次外部 HTTP(S) 请求；不查询或修改数据库，也不保存响应 Body。

---

<a id="app-worker-repository"></a>

### Worker 数据库状态：`app/worker_repository.py`

#### `retry_delay(attempt_count)`

- **用途**：根据当前尝试次数计算下一次重试要等待多久。
- **输入**：已经开始的投递次数。
- **返回**：1、2、4 或 8 分钟的 `timedelta`，超过第四次后仍保持 8 分钟。
- **主要过程**：把次数映射到固定退避表，并限制索引范围。
- **失败情况**：零或负数会安全地使用第一档 1 分钟。
- **副作用**：无。

#### `claim_due_notifications(session, limit, now)`

- **用途**：安全领取一批已到执行时间的任务。
- **输入**：数据库 session、批次上限和当前时间。
- **返回**：已经变成 `processing` 的任务列表。
- **主要过程**：用 `FOR UPDATE SKIP LOCKED` 查询 `pending/retrying`，设置租约并增加尝试次数，然后提交事务。
- **失败情况**：查询或提交失败时向上抛出数据库错误，不会开始网络调用。
- **副作用**：修改任务状态、`locked_at` 和 `attempt_count` 并提交 PostgreSQL。

#### `record_delivery_result(session, notification_id, locked_at, result, now)`

- **用途**：把一次外部调用结果安全地写回仍由当前 Worker 持有的任务。
- **输入**：数据库 session、任务 ID、领取时的租约时间、投递结果和当前时间。
- **返回**：成功记录返回 `True`；租约已失效返回 `False`。
- **主要过程**：锁定任务并核对租约；成功改为 `succeeded`，临时失败安排重试，永久失败或第五次失败改为 `dead`。
- **失败情况**：过期 Worker 的结果会回滚并忽略；数据库错误继续抛出。
- **副作用**：可能更新状态、下一次时间、状态码和错误信息并提交 PostgreSQL。

#### `recover_stale_notifications(session, stale_before, now, limit)`

- **用途**：恢复 Worker 崩溃后长期停在 `processing` 的任务。
- **输入**：数据库 session、租约过期界线、当前时间和单次恢复上限。
- **返回**：本次恢复的任务数量。
- **主要过程**：锁定过期任务；未到第五次的立即改为 `retrying`，已用完次数的改为 `dead`。
- **失败情况**：数据库错误继续抛出；并发恢复通过 `SKIP LOCKED` 避免重复处理。
- **副作用**：清除过期租约、记录恢复原因并提交 PostgreSQL。

---

<a id="app-worker"></a>

### Worker 循环：`app/worker.py`

#### `process_claimed_notification(job, client, session_maker, clock)`

- **用途**：投递一条已经完成数据库领取提交的任务，并记录结果。
- **输入**：已领取任务、HTTP client、session factory 和时钟函数。
- **返回**：无。
- **主要过程**：确认租约存在，发送外部请求，再用新 session 写回结果。
- **失败情况**：缺少租约会抛出 `ValueError`；过期结果只写警告，不覆盖新状态。
- **副作用**：发送 HTTP 请求，并可能更新 PostgreSQL。

#### `run_worker_cycle(client, session_maker, settings, clock)`

- **用途**：执行一轮“恢复过期任务、领取到期任务、并发投递”。
- **输入**：HTTP client、session factory、Worker 配置和时钟。
- **返回**：本轮领取并处理的任务数。
- **主要过程**：先单独提交恢复事务，再单独提交领取事务，最后并发处理本批任务；单条意外失败留给租约恢复，不影响其他任务。
- **失败情况**：未处理异常向上抛出，使进程失败并由租约恢复保护任务。
- **副作用**：查询和修改数据库，发送零到多次 HTTP 请求。

#### `wait_for_next_cycle(stop_event, seconds)`

- **用途**：等待下一轮轮询，同时允许停止信号立即唤醒 Worker。
- **输入**：停止事件和等待秒数。
- **返回**：无。
- **主要过程**：等待事件，超时表示正常进入下一轮。
- **失败情况**：正常超时会被忽略；取消等其他异常继续抛出。
- **副作用**：暂停当前异步任务，但不阻塞事件循环。

#### `worker_loop(stop_event, client, session_maker, settings, clock)`

- **用途**：持续运行 Worker，直到收到停止请求。
- **输入**：停止事件以及可替换的 HTTP、数据库、配置和时钟依赖。
- **返回**：无。
- **主要过程**：检查停止状态、执行一轮、等待；停止后不再领取新批次。
- **失败情况**：一轮中的未处理异常会退出循环，已领取任务由租约机制恢复。
- **副作用**：持续访问数据库并向供应商发送请求。

#### `request_shutdown(stop_event)`

- **用途**：把进程信号转换成 Worker 能识别的停止事件。
- **输入**：Worker 使用的 `asyncio.Event`。
- **返回**：无。
- **主要过程**：调用事件的 `set()`。
- **失败情况**：无。
- **副作用**：改变内存中的停止状态。

#### `install_signal_handlers(stop_event)`

- **用途**：让 SIGINT 和 SIGTERM 可以触发正常停止。
- **输入**：Worker 的停止事件。
- **返回**：无。
- **主要过程**：在当前事件循环中为两个进程信号注册回调。
- **失败情况**：运行平台不支持事件循环信号处理时会抛出平台相关错误。
- **副作用**：修改当前进程的信号处理配置。

#### `run_worker()`

- **用途**：创建正式 Worker 所需资源并启动循环。
- **输入**：无。
- **返回**：无。
- **主要过程**：建立停止事件、安装信号、创建共享 httpx client 并运行循环。
- **失败情况**：初始化或循环错误向上抛出，进程退出。
- **副作用**：安装信号处理、打开 HTTP 连接池并运行 Worker。

#### `main()`

- **用途**：提供 `python -m app.worker` 命令行入口。
- **输入**：无。
- **返回**：无。
- **主要过程**：配置基本日志，再通过 `asyncio.run()` 启动 Worker。
- **失败情况**：Worker 错误会使命令以失败状态退出。
- **副作用**：启动长期运行的 Worker 进程。

---

<a id="app-mock-vendor"></a>

### 本地 Mock Vendor：`app/mock_vendor.py`

这个文件只用于本地 Docker 演示，不属于生产通知服务接口。

#### `remember_request(request)`

- **用途**：记录 mock vendor 收到的安全请求信息，供 Smoke Test 查询。
- **输入**：FastAPI `Request`。
- **返回**：请求中的 `X-Notification-Id`。
- **主要过程**：检查通知 ID，解析 JSON Body，只保存 ID、方法和 Body。
- **失败情况**：缺少通知 ID 返回 `400`；非 JSON Body 用固定占位文字表示。
- **副作用**：写入 mock 进程内存；不会记录 Authorization 等 Header。

#### `health_check()`

- **用途**：供 Docker Compose 判断 mock vendor 是否可以接收请求。
- **输入**：无。
- **返回**：`{"status": "ok"}`。
- **主要过程**：直接返回固定结果。
- **失败情况**：无。
- **副作用**：无。

#### `accept_notification(request)`

- **用途**：模拟供应商成功处理通知。
- **输入**：POST、PUT、PATCH 或 DELETE 请求。
- **返回**：HTTP `204` 空响应。
- **主要过程**：先记录安全请求信息，再返回成功。
- **失败情况**：缺少通知 ID 时由 `remember_request()` 返回 `400`。
- **副作用**：把安全请求信息写入 mock 进程内存。

#### `reject_temporarily(request)`

- **用途**：模拟供应商暂时不可用。
- **输入**：支持的 HTTP 通知请求。
- **返回**：HTTP `503`。
- **主要过程**：记录请求，再返回固定临时故障。
- **失败情况**：缺少通知 ID 时返回 `400`。
- **副作用**：把安全请求信息写入 mock 进程内存。

#### `reject_permanently(request)`

- **用途**：模拟供应商永久拒绝当前请求。
- **输入**：支持的 HTTP 通知请求。
- **返回**：HTTP `400`。
- **主要过程**：记录请求，再返回固定永久错误。
- **失败情况**：缺少通知 ID 时同样返回 `400`。
- **副作用**：把安全请求信息写入 mock 进程内存。

#### `get_received_notification(notification_id)`

- **用途**：让 Smoke Test 确认指定通知确实到达 mock vendor。
- **输入**：通知 ID 字符串。
- **返回**：之前记录的 ID、HTTP 方法和 Body。
- **主要过程**：从进程内存按 ID 查找。
- **失败情况**：没有收到该 ID 时返回 `404`。
- **副作用**：无，只读取进程内存。

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
- **主要过程**：临时设置应用、数据库和三个 Worker 环境变量，创建 `Settings`，再核对解析结果。
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

---

<a id="test-delivery"></a>

### HTTP 投递测试：`tests/test_delivery.py`

#### `make_job(**overrides)`

- **用途**：为投递测试创建字段完整的内存任务。
- **输入**：需要覆盖的任务字段。
- **返回**：未写入数据库的 `NotificationJob`。
- **主要过程**：填入正常 URL、Header、Body 和时间，再应用覆盖值。
- **失败情况**：字段名称错误时 SQLAlchemy 构造函数会报错。
- **副作用**：无。

#### `test_classify_status_code_marks_2xx_success(status_code)`

- **用途**：确认所有代表值范围内的 `2xx` 都被视为成功。
- **输入**：pytest 提供的四个状态码。
- **返回**：无。
- **主要过程**：逐个调用分类函数并检查结果。
- **失败情况**：任一 `2xx` 未归为成功时测试失败。
- **副作用**：无。

#### `test_classify_status_code_marks_temporary_failures_retryable(status_code)`

- **用途**：确认超时、限流和服务端错误可以重试。
- **输入**：`408`、`429` 和三个 `5xx` 代表值。
- **返回**：无。
- **主要过程**：逐个检查分类结果。
- **失败情况**：任一临时错误未归为可重试时测试失败。
- **副作用**：无。

#### `test_classify_status_code_marks_other_failures_permanent(status_code)`

- **用途**：确认跳转和普通客户端错误不会原样重复发送。
- **输入**：`301` 及四个普通 `4xx` 代表值。
- **返回**：无。
- **主要过程**：逐个检查永久失败分类。
- **失败情况**：任一状态被错误归为成功或可重试时测试失败。
- **副作用**：无。

#### `test_build_outbound_headers_enforces_stable_notification_id()`

- **用途**：确认调用方不能覆盖本服务生成的通知 ID。
- **输入**：无；测试内创建带伪造 ID 的任务。
- **返回**：无。
- **主要过程**：构建 Header，并核对伪造值已被任务 UUID 替换。
- **失败情况**：下游收到调用方伪造值时测试失败。
- **副作用**：无。

#### `test_bound_error_message_limits_stored_text()`

- **用途**：确认短错误不变，长错误最多保留 500 字符。
- **输入**：无。
- **返回**：无。
- **主要过程**：分别传入短文字和超长文字并检查长度与省略号。
- **失败情况**：信息被无故修改或超出限制时测试失败。
- **副作用**：无。

#### `test_deliver_notification_forwards_request_with_timeout()`

- **用途**：确认外部请求的方法、URL、Header、JSON 和超时都正确。
- **输入**：无；使用 httpx MockTransport 接收请求。
- **返回**：无。
- **主要过程**：投递 PATCH 任务，检查实际请求和成功结果。
- **失败情况**：字段未转发、超时不是 10 秒、响应 Body 被保存或结果错误时测试失败。
- **副作用**：只访问内存 mock，不访问互联网。

#### `test_deliver_notification_classifies_http_failures(status_code, expected_outcome)`

- **用途**：确认真实投递入口正确处理 `429`、`503` 和 `400`。
- **输入**：pytest 提供状态码和预期结果。
- **返回**：无。
- **主要过程**：mock 外部响应并检查状态码、错误文字和结果分类。
- **失败情况**：分类错误或敏感响应 Body 出现在结果中时测试失败。
- **副作用**：只访问内存 mock。

#### `test_deliver_notification_converts_transport_errors_to_retryable(transport_error)`

- **用途**：确认连接失败和读取超时不会让投递流程崩溃。
- **输入**：pytest 提供的两种 httpx 网络异常。
- **返回**：无。
- **主要过程**：让 MockTransport 抛错，再检查可重试结果和有限错误信息。
- **失败情况**：异常逃出函数或被归为永久失败时测试失败。
- **副作用**：只访问内存 mock。

#### `test_notification_id_is_unchanged_across_attempts()`

- **用途**：确认同一任务多次发送时始终使用同一个下游幂等 ID。
- **输入**：无。
- **返回**：无。
- **主要过程**：让同一任务先收到 `503` 再收到 `200`，比较两次请求 Header。
- **失败情况**：两次 ID 不同或结果分类错误时测试失败。
- **副作用**：只访问内存 mock。

---

<a id="test-worker-repository"></a>

### Worker 数据库测试：`tests/test_worker_repository.py`

#### `make_job(**overrides)`

- **用途**：创建 Worker 数据库测试使用的完整内存任务。
- **输入**：可选字段覆盖值。
- **返回**：一个 `NotificationJob`。
- **主要过程**：填入正常默认字段后应用覆盖值。
- **失败情况**：错误字段会导致模型构造失败。
- **副作用**：无。

#### `fake_session_with_scalars(items)`

- **用途**：模拟返回指定任务列表的异步数据库 session。
- **输入**：希望查询返回的对象列表。
- **返回**：带有 execute、commit 和 rollback mock 的 session。
- **主要过程**：搭建 SQLAlchemy 查询结果的 `scalars()` 调用链。
- **失败情况**：mock 接口与生产代码不一致时测试会失败。
- **副作用**：无。

#### `test_retry_delay_uses_capped_exponential_backoff(attempt_count, expected_minutes)`

- **用途**：验证退避顺序为 1、2、4、8 分钟并封顶。
- **输入**：pytest 提供的尝试次数和期望分钟数。
- **返回**：无。
- **主要过程**：比较 `retry_delay()` 的结果。
- **失败情况**：任何档位不一致时测试失败。
- **副作用**：无。

#### `test_claim_due_notifications_marks_and_commits_jobs()`

- **用途**：验证领取会设置状态、租约和尝试次数并提交。
- **输入**：无。
- **返回**：无。
- **主要过程**：让 mock 查询返回两个任务，再检查修改和 commit。
- **失败情况**：领取没有持久化或字段错误时测试失败。
- **副作用**：只操作 mock。

#### `test_record_delivery_result_applies_state_transition(delivery_result, attempt_count, expected_status, expected_delay)`

- **用途**：验证成功、重试、永久失败和次数耗尽四种转换。
- **输入**：pytest 提供的结果、次数、状态和延迟。
- **返回**：无。
- **主要过程**：记录结果并检查任务全部相关字段。
- **失败情况**：状态、时间或错误信息不正确时测试失败。
- **副作用**：只操作 mock。

#### `test_record_delivery_result_ignores_expired_lease()`

- **用途**：验证迟到 Worker 不能覆盖已更换租约的任务。
- **输入**：无。
- **返回**：无。
- **主要过程**：传入旧租约，检查函数回滚且没有 commit。
- **失败情况**：旧结果被写入时测试失败。
- **副作用**：只操作 mock。

#### `test_recover_stale_notifications_retries_or_kills_jobs()`

- **用途**：验证过期任务按剩余次数进入 retrying 或 dead。
- **输入**：无。
- **返回**：无。
- **主要过程**：恢复一条未到上限和一条已到上限的任务。
- **失败情况**：状态、时间、租约或原因不正确时测试失败。
- **副作用**：只操作 mock。

---

<a id="test-worker"></a>

### Worker 循环测试：`tests/test_worker.py`

#### `FakeSessionContext.__aenter__()`

- **用途**：模拟进入 `async with session_maker()`。
- **输入**：无。
- **返回**：一个 mock session。
- **主要过程**：创建并返回 `MagicMock`。
- **失败情况**：无。
- **副作用**：无。

#### `FakeSessionContext.__aexit__(exc_type, exc_value, traceback)`

- **用途**：模拟退出异步 session 上下文。
- **输入**：可能出现的异常类型、值和回溯。
- **返回**：`False`，表示不吞掉异常。
- **主要过程**：直接返回固定值。
- **失败情况**：无。
- **副作用**：无。

#### `fake_session_maker()`

- **用途**：为 Worker 单元测试创建假的 session 上下文。
- **输入**：无。
- **返回**：`FakeSessionContext`。
- **主要过程**：构造一个新上下文对象。
- **失败情况**：无。
- **副作用**：无。

#### `make_claimed_job()`

- **用途**：创建已经带租约的 processing 任务。
- **输入**：无。
- **返回**：完整的 `NotificationJob`。
- **主要过程**：填入 UUID、当前时间和领取后的状态。
- **失败情况**：模型字段变化未同步时测试失败。
- **副作用**：无。

#### `test_process_claimed_notification_delivers_then_records(monkeypatch)`

- **用途**：验证单任务处理先发送，再记录结果。
- **输入**：pytest 的 `monkeypatch`。
- **返回**：无。
- **主要过程**：用两个嵌套 helper 记录事件顺序并检查租约参数。
- **失败情况**：顺序或参数错误时测试失败。
- **副作用**：不访问数据库或网络。

#### `fake_deliver(notification, client)`

- **用途**：上一个测试中模拟外部投递并记录事件。
- **输入**：通知和 HTTP client 占位值。
- **返回**：一个投递结果 mock。
- **主要过程**：加入 `delivered` 事件。
- **失败情况**：无。
- **副作用**：修改测试事件列表。

#### `fake_record(session, **kwargs)`

- **用途**：上一个测试中模拟结果落库并核对任务与租约。
- **输入**：session 占位值和结果参数。
- **返回**：`True`。
- **主要过程**：加入 `recorded` 事件并执行断言。
- **失败情况**：任务 ID 或租约错误时断言失败。
- **副作用**：修改测试事件列表。

#### `test_run_worker_cycle_claims_before_network(monkeypatch)`

- **用途**：验证领取提交完成后才开始网络阶段。
- **输入**：pytest 的 `monkeypatch`。
- **返回**：无。
- **主要过程**：替换恢复、领取和处理函数，检查事件严格排序。
- **失败情况**：网络先于领取完成时测试失败。
- **副作用**：不访问数据库或网络。

#### `fake_recover(session, **kwargs)`

- **用途**：上一测试中模拟恢复阶段。
- **输入**：session 和参数占位值。
- **返回**：恢复数量 `0`。
- **主要过程**：加入 `recovered` 事件。
- **失败情况**：无。
- **副作用**：修改测试事件列表。

#### `fake_claim(session, **kwargs)`

- **用途**：上一测试中模拟已经提交的领取阶段。
- **输入**：session 和领取参数。
- **返回**：一条测试任务。
- **主要过程**：加入 `claim_committed` 事件。
- **失败情况**：无。
- **副作用**：修改测试事件列表。

#### `fake_process(notification, **kwargs)`

- **用途**：上一测试中模拟网络处理并检查前一步是领取提交。
- **输入**：通知和依赖参数。
- **返回**：无。
- **主要过程**：断言事件顺序并加入 `network_started`。
- **失败情况**：领取未先完成时断言失败。
- **副作用**：修改测试事件列表。

#### `test_run_worker_cycle_processes_claimed_batch_concurrently(monkeypatch)`

- **用途**：验证同一批任务会并发开始，慢请求不会让后续任务租约空等。
- **输入**：pytest 的 `monkeypatch`。
- **返回**：无。
- **主要过程**：让两个任务互相等待“都已开始”事件，只有并发实现才能在超时前完成。
- **失败情况**：任务按顺序运行或有任务未开始时测试失败。
- **副作用**：不访问数据库或网络。

#### `fake_recover_for_concurrency(session, **kwargs)`

- **用途**：并发测试中模拟无过期任务的恢复阶段。
- **输入**：session 和参数占位值。
- **返回**：`0`。
- **主要过程**：直接返回。
- **失败情况**：无。
- **副作用**：无。

#### `fake_claim_for_concurrency(session, **kwargs)`

- **用途**：并发测试中返回两条已领取任务。
- **输入**：session 和参数占位值。
- **返回**：测试准备的任务列表。
- **主要过程**：直接返回列表。
- **失败情况**：无。
- **副作用**：无。

#### `blocking_process(notification, **kwargs)`

- **用途**：并发测试中让每条任务等待整批都已开始。
- **输入**：当前通知和依赖占位值。
- **返回**：无。
- **主要过程**：增加开始计数，第二条启动时设置事件，再等待该事件。
- **失败情况**：若实现是串行，第一条会在 0.2 秒后超时。
- **副作用**：修改测试计数和事件。

#### `test_worker_loop_does_not_claim_after_stop(monkeypatch)`

- **用途**：验证一轮中收到停止信号后不会开始下一轮。
- **输入**：pytest 的 `monkeypatch`。
- **返回**：无。
- **主要过程**：第一轮设置停止事件，再检查只执行一轮且没有等待。
- **失败情况**：再次领取或等待时测试失败。
- **副作用**：只修改测试停止事件。

#### `stop_during_first_cycle(**kwargs)`

- **用途**：上一测试中模拟执行一轮时收到停止请求。
- **输入**：Worker cycle 参数。
- **返回**：处理数量 `0`。
- **主要过程**：设置停止事件。
- **失败情况**：无。
- **副作用**：改变测试停止事件。

#### `test_worker_loop_with_preexisting_stop_does_nothing(monkeypatch)`

- **用途**：验证启动前已有停止信号时不领取任务。
- **输入**：pytest 的 `monkeypatch`。
- **返回**：无。
- **主要过程**：预先设置事件并检查 cycle 从未调用。
- **失败情况**：Worker 仍开始工作时测试失败。
- **副作用**：无外部副作用。

#### `test_wait_for_next_cycle_wakes_on_stop()`

- **用途**：验证 60 秒轮询等待可以被停止事件立即唤醒。
- **输入**：无。
- **返回**：无。
- **主要过程**：并发等待和设置事件，再检查事件状态。
- **失败情况**：等待未及时结束时测试超时或失败。
- **副作用**：只修改测试事件。

#### `request_stop()`

- **用途**：上一测试中在让出一次事件循环后设置停止事件。
- **输入**：无。
- **返回**：无。
- **主要过程**：短暂 yield 后调用 `set()`。
- **失败情况**：无。
- **副作用**：改变测试停止事件。

#### `test_process_claimed_notification_requires_lease()`

- **用途**：验证没有租约的任务不会被误发。
- **输入**：无。
- **返回**：无。
- **主要过程**：清除 `locked_at` 并期待 `ValueError`。
- **失败情况**：函数继续发送任务时测试失败。
- **副作用**：不访问数据库或网络。

---

<a id="test-mock-vendor"></a>

### Mock Vendor 测试：`tests/test_mock_vendor.py`

#### `clear_received_requests()`

- **用途**：防止不同 mock vendor 测试共享内存记录。
- **输入**：无；pytest 自动在每个测试前调用。
- **返回**：无。
- **主要过程**：清空 `received_requests`。
- **失败情况**：无。
- **副作用**：删除测试进程中的 mock 请求记录。

#### `test_mock_vendor_health_check()`

- **用途**：验证容器健康接口返回可用状态。
- **输入**：无。
- **返回**：无。
- **主要过程**：通过内存 ASGI client 请求 `/health`。
- **失败情况**：状态码或 JSON 不正确时测试失败。
- **副作用**：不访问真实网络。

#### `test_success_endpoint_records_safe_request_details(method)`

- **用途**：验证四种 HTTP 方法都成功，并且只记录安全字段。
- **输入**：pytest 提供的 POST、PUT、PATCH、DELETE。
- **返回**：无。
- **主要过程**：发送带 Body 和 Authorization 的请求，再查询 inspection 接口。
- **失败情况**：不是 `204`、内容不一致或 Authorization 泄露时测试失败。
- **副作用**：写入并读取测试进程内存。

#### `test_failure_endpoints_return_expected_status(path, expected_status)`

- **用途**：验证临时和永久故障端点分别返回 `503` 与 `400`。
- **输入**：pytest 提供的路径和期望状态码。
- **返回**：无。
- **主要过程**：提交通知并确认状态与接收记录。
- **失败情况**：状态码错误或没有记录通知时测试失败。
- **副作用**：写入测试进程内存。

#### `test_mock_vendor_requires_notification_id()`

- **用途**：验证绕过通知服务、缺少通知 ID 的请求会被拒绝。
- **输入**：无。
- **返回**：无。
- **主要过程**：不带 ID 请求成功端点并检查 `400`。
- **失败情况**：请求被错误接受或错误信息变化时测试失败。
- **副作用**：不访问真实网络。

#### `test_inspection_returns_404_for_unknown_notification()`

- **用途**：验证查询未收到的通知会返回 `404`。
- **输入**：无。
- **返回**：无。
- **主要过程**：查询固定未知 ID 并检查响应。
- **失败情况**：状态码或错误信息不正确时测试失败。
- **副作用**：不访问真实网络。
