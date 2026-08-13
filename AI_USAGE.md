# AI Use Disclosure

This project was built with assistance from the Codex coding agent. AI was used throughout requirement analysis, design, implementation, testing, container setup, and documentation. Its output was treated as a draft: the author reviewed the proposed behavior, corrected inconsistencies, and verified the final system before accepting it.

## Tools Used

- **Codex coding agent**: helped inspect the assignment, discuss design options, draft code and tests, update documentation, and run repository checks.
- **Local development tools**: pytest, Ruff, Docker Compose, Git, and command-line HTTP checks were used to verify the generated and edited work.

No AI service is called by the notification application at runtime. AI was a development tool only and is not part of the deployed architecture.

## Where AI Helped

AI helped turn the assignment into a small implementation plan built around three responsibilities: accepting a notification, storing it durably, and delivering it from a separate worker. It also helped compare PostgreSQL row locking with dedicated queue systems and identify failure cases such as request timeouts, ambiguous delivery results, duplicate submissions, concurrent workers, and worker crashes.

During implementation, AI drafted parts of the FastAPI API, SQLAlchemy model, Alembic migration, delivery module, worker lifecycle, tests, Docker configuration, and documentation. The work was completed in small batches so each part could be reviewed and tested before moving to the next one.

AI also helped perform the final consistency audit by comparing the original assignment, README claims, executable code, automated tests, container behavior, and Git state.

## Suggestions Not Adopted

Several possible designs were considered during the AI-assisted design process but were intentionally excluded:

- **Redis and Celery** were not adopted because PostgreSQL already provides the required persistence, transactions, and safe row claiming for this MVP.
- **Kafka and RabbitMQ** were not adopted because the assignment gives no throughput or integration requirement that justifies operating another distributed system.
- **Exactly-once delivery** was not claimed because an ordinary HTTP receiver may process a request even when its response is lost. The sender cannot safely distinguish that case from a failed delivery.
- **Unlimited retries** were rejected because a permanently unavailable vendor could grow the queue forever and hide broken integrations.
- **Vendor plugins, a web dashboard, multi-region deployment, and workflow orchestration** were deferred because they do not prove the core reliable-delivery path.

These exclusions keep the first version small enough to understand, operate, and test while leaving clear paths for future growth.

## AI Output That Required Correction

AI-generated work was not assumed to be correct. The final audit found and corrected several concrete problems:

- The README initially listed structured logging as implemented even though the code only used basic application logging. The unsupported claim was removed.
- An early smoke-test description implied that the same idempotency key could be reused after changing the target URL. The real API correctly returns `409 Conflict` for that request, so the instructions were corrected to require a new key.
- The initial configuration included an `ENVIRONMENT` setting that did not affect application behavior. It was removed instead of keeping unused configuration.
- SQL statement echo was initially configurable. Because SQL parameters could include stored authorization headers, the final version disables SQL echo to reduce the risk of credentials appearing in logs.

These corrections came from checking documentation against real behavior rather than trusting generated text or code in isolation.

## Decisions Made by the Author

The author selected FastAPI and PostgreSQL at the start and required the design to remain simple and easy to explain. The author chose PostgreSQL as both the durable system of record and the first-version work queue because this avoids introducing another service before scale proves it necessary.

The author approved at-least-once delivery as the honest HTTP delivery contract, a stable `X-Notification-Id` for downstream deduplication, five bounded attempts with exponential delays, and visible `dead` jobs instead of infinite retries. The author also required every function to be documented in plain Chinese and organized the implementation into reviewable batches with explicit commits.

Authentication, SSRF protection, secret-manager integration, alerting, and manual replay were intentionally kept outside the demo implementation. They are documented as production requirements rather than silently treated as solved.

AI helped explore and implement these choices, but the author determined the project scope, accepted or rejected design options, requested corrections, and owns the final result.

## How the Final Result Was Verified

The final repository was checked with both automated tests and a real local container workflow:

- `uv sync --check` confirmed that the locked environment was reproducible.
- Ruff linting and formatting checks passed.
- All 74 pytest cases passed with 90% application-code coverage.
- A fresh Docker Compose project successfully built the image, migrated an empty PostgreSQL database, and started the API, worker, and mock vendor.
- Real HTTP checks produced `succeeded`, `retrying`, and `dead` jobs for the expected vendor responses.
- Idempotent replay returned the original job, while changed content with the same key returned `409 Conflict`.
- A pending job remained stored across API and worker restarts and was delivered after the worker returned.
- A test authorization value did not appear in container logs.
- The project files and Git patch history were scanned for common credential patterns.

The isolated validation containers and database volume were removed after the checks completed.
