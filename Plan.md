# 项目实现计划

这份计划按照依赖关系把项目拆成多个小批次。每一批都应该做到：代码可以运行、测试通过、文档同步更新，然后再进入下一批。

## 执行原则

- 一次只完成一批，不同时铺开多个未完成模块。
- 每批先实现最小闭环，再补该批需要的异常处理。
- 每新增、修改或删除一个函数，都同步更新 `FUNCTIONS.md`。
- 只有代码真实支持的功能才能写进 `README.md`。
- 每批结束时运行测试和代码检查，并创建一个小而清楚的 Git commit。
- 不提前加入 Redis、Celery、Kafka、管理后台等 MVP 不需要的组件。

## 批次总览

| 批次 | 目标 | 完成后能做到什么 |
|---|---|---|
| 0 | 项目初始化 | 有 Git、Python 环境、依赖锁和设计文档 |
| 1 | 应用与数据库基础 | API 可以启动，数据库可以迁移，健康检查可用 |
| 2 | 通知任务 API | 可以创建任务并查询任务状态 |
| 3 | 单次 HTTP 投递 | 可以正确发送一次外部请求并判断结果 |
| 4 | Worker 与重试 | 可以后台取任务、重试失败任务并恢复卡住任务 |
| 5 | Docker 与端到端验证 | 可以一条命令启动完整系统并完成真实流程 |
| 6 | 最终检查与交付 | 代码、测试、README 和 AI 说明保持一致 |

---

## Batch 0：项目初始化

**状态：已完成**

### 本批内容

- 初始化 Git 仓库和 `main` 分支。
- 使用 Python 3.11 创建 `.venv`。
- 在 `pyproject.toml` 中声明运行和开发依赖。
- 生成 `uv.lock`，确保依赖版本可重复安装。
- 添加 `.gitignore`、`README.md` 和 `FUNCTIONS.md`。
- 配置进入项目目录时自动激活 `.venv`。

### 完成标准

- `uv sync --check` 不需要修改环境。
- FastAPI、SQLAlchemy、asyncpg 和 httpx 可以正常导入。
- `.venv`、本地配置和 IDE 文件不会被 Git 跟踪。

---

## Batch 1：应用骨架与数据库基础

**状态：已完成**

**目标：先让空系统稳定启动，并确认数据库连接和迁移流程正常。**

### 要完成的事情

- 创建 `app/` Python 包。
- 在 `config.py` 中集中读取环境变量。
- 在 `database.py` 中创建异步 PostgreSQL engine 和 session。
- 在 `models.py` 中定义通知任务表和状态。
- 初始化 Alembic，并创建第一份数据库迁移。
- 实现 `GET /health` 健康检查。
- 添加 `.env.example`，只放示例值，不放真实密码。
- 在 Docker Compose 中先提供 PostgreSQL 服务。

### 重点测试

- 配置可以从环境变量正确读取。
- FastAPI 应用可以启动。
- `GET /health` 返回成功。
- Alembic 可以在空数据库上升级到最新版本，也可以正常回退。
- 数据表字段、默认值和必要约束正确。

### 完成标准

```bash
uv run ruff check .
uv run pytest
uv run alembic upgrade head
```

三条命令都通过，并且 `FUNCTIONS.md` 已记录本批新增函数。

### 建议提交

```text
feat: add application and database foundation
```

---

## Batch 2：创建与查询通知任务

**状态：已完成**

**目标：完成业务系统与通知服务之间的最小 API 闭环。**

### 要完成的事情

- 定义创建任务的请求和响应模型。
- 实现 `POST /notifications`。
- 任务成功写入 PostgreSQL 后返回 `202 Accepted`。
- 实现 `GET /notifications/{id}`。
- 找不到任务时返回 `404 Not Found`。
- 验证 URL、HTTP 方法、Header 和 JSON Body。
- 支持可选的 `Idempotency-Key`：
  - 相同 key 和相同请求返回原任务；
  - 相同 key 但不同请求返回 `409 Conflict`。

### 重点测试

- 合法请求可以创建 `pending` 任务。
- 数据库写入失败时不能返回 `202`。
- 可以按 ID 查询任务。
- 无效 URL、方法或请求结构返回清楚的 `4xx`。
- 幂等 key 的重复提交和冲突行为正确。

### 完成标准

- API 测试全部通过。
- OpenAPI 页面能看到两个通知接口。
- 日志中不打印 Authorization 等敏感 Header。
- `README.md` 中的 API 示例与真实响应一致。
- `FUNCTIONS.md` 已记录本批新增函数。

### 建议提交

```text
feat: add notification submission and status API
```

---

## Batch 3：单次 HTTP 投递

**状态：已完成**

**目标：把“如何发送一次请求、如何判断成功或失败”做成独立且可测试的模块。**

### 要完成的事情

- 使用 httpx 发送目标 HTTP(S) 请求。
- 转发任务中的方法、Header 和 JSON Body。
- 自动添加稳定的 `X-Notification-Id`。
- 设置 10 秒请求超时。
- 按以下规则分类结果：
  - `2xx`：成功；
  - 网络错误、超时、`408`、`429`、`5xx`：可以重试；
  - 其他 `4xx`：永久失败。
- 只保存有限长度的错误信息和最新状态码，不保存响应 Body。

### 重点测试

- 正确构造并发送外部请求。
- `2xx`、可重试状态和永久失败状态分类正确。
- 网络超时和连接失败不会让进程崩溃。
- `X-Notification-Id` 在重试时保持不变。
- 测试使用 httpx mock，不依赖真实互联网。

### 完成标准

- 投递模块的单元测试全部通过。
- 该模块不直接修改数据库，职责保持单一。
- `FUNCTIONS.md` 已记录本批新增函数。

### 建议提交

```text
feat: add outbound HTTP delivery
```

---

## Batch 4：Worker、重试与崩溃恢复

**状态：已完成**

**目标：把数据库中的任务自动投递出去，形成完整的可靠投递流程。**

### 要完成的事情

- Worker 定期查找已到执行时间的 `pending` 和 `retrying` 任务。
- 使用 `FOR UPDATE SKIP LOCKED` 安全领取任务。
- 在短事务内把任务改为 `processing`，提交后再发送网络请求。
- 成功时把任务改为 `succeeded`。
- 临时失败时增加尝试次数，并安排下一次执行时间。
- 使用约 1、2、4、8 分钟的退避间隔，总计最多尝试 5 次。
- 永久失败或用完尝试次数时改为 `dead`。
- 通过 `locked_at` 恢复长时间停在 `processing` 的任务。
- 支持 Worker 正常停止，不在退出时领取新任务。

### 重点测试

- 到期任务会被领取，未到期任务不会被领取。
- 两个 Worker 不会同时领取同一任务。
- 外部调用发生在数据库领取事务提交之后。
- 成功、重试、最终失败的状态转换正确。
- Worker 崩溃留下的任务可以恢复。
- 退避时间和最大尝试次数正确。

### 完成标准

- 从 `pending` 到 `succeeded` 的集成测试通过。
- 从临时失败到 `retrying`，再到 `dead` 的集成测试通过。
- Worker 重启不会丢失数据库中的任务。
- `FUNCTIONS.md` 已记录本批新增函数。

### 建议提交

```text
feat: add database worker and retry lifecycle
```

---

## Batch 5：Docker 与端到端验证

**状态：已完成**

**目标：让评审者可以用一条命令启动完整系统并验证主要流程。**

### 要完成的事情

- 添加应用 `Dockerfile`。
- 完成 Docker Compose 中的 PostgreSQL、API 和 Worker 服务。
- 启动时执行数据库迁移。
- 配置服务健康检查和启动依赖。
- 提供一个本地 mock vendor，避免 Smoke Test 依赖互联网。
- 使用真实 HTTP 请求完成“创建任务 -> Worker 投递 -> 查询成功”的流程。
- 验证服务重启后未完成任务仍然存在。

### 重点测试

```bash
docker compose up --build
curl http://localhost:8000/health
curl -X POST http://localhost:8000/notifications ...
curl http://localhost:8000/notifications/<notification-id>
```

### 完成标准

- 新环境按照 `README.md` 可以直接启动。
- 成功通知最终变为 `succeeded`。
- 临时失败通知会进入 `retrying`。
- 永久失败或超过尝试次数的通知会变为 `dead`。
- README 的命令已逐条实际执行，而不是只检查文字。
- `FUNCTIONS.md` 已记录本批新增函数，包括 mock 和测试函数。

### 建议提交

```text
chore: add local container workflow and smoke test
```

---

## Batch 6：最终检查与交付

**目标：确保代码、文档和作业要求完全一致。**

### 要完成的事情

- 检查系统边界、投递语义、失败策略和未来演进是否都已说明。
- 核对 README 中的接口、状态、重试次数和运行命令。
- 检查日志不会泄露 Authorization、Cookie 或其他敏感 Header。
- 检查配置文件和 Git 历史中没有真实密码或 token。
- 更新 AI Use Disclosure：
  - AI 帮助了什么；
  - 哪些 AI 建议没有采用；
  - 哪些决定由作者做出以及原因。
- 清理未使用的依赖、代码和过期文档。
- 完成一次全新环境验证。

### 最终验证

```bash
uv sync --check
uv run ruff check .
uv run pytest --cov=app --cov-report=term-missing
docker compose config
docker compose up --build
git status --short
```

### 完成标准

- 所有自动检查通过。
- 端到端流程通过。
- `README.md`、`FUNCTIONS.md` 和实际代码一致。
- Git 工作区干净。
- 仓库可以提交为 `rc_<your_nickname>`。

### 建议提交

```text
docs: finalize implementation and submission notes
```

---

## 第一版明确不做

以下内容不在上述批次中，除非实际需求或测试证明必须加入：

- Redis、Celery、RabbitMQ 或 Kafka
- Web 管理后台
- 多区域部署
- 供应商插件系统
- 复杂工作流编排
- 恰好一次投递承诺
- 无限重试
- 自动告警和手动重放界面
- 完整生产级认证授权系统

这些功能可以在未来根据真实流量、失败模式和运维需求逐步增加。
