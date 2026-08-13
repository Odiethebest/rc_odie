# Reliable HTTP Notification Service

> A minimal internal service for accepting outbound HTTP(S) notification jobs and delivering them asynchronously with durable storage, automatic retries, and visible terminal failures.

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Durable%20Queue-4169E1?logo=postgresql)](https://www.postgresql.org/)
[![Delivery](https://img.shields.io/badge/Delivery-At%20Least%20Once-orange)](#delivery-semantics)
[![Scope](https://img.shields.io/badge/Scope-MVP-lightgrey)](#scope)

---

## Table of Contents

- [Overview](#overview)
- [Implementation Status](#implementation-status)
- [Architecture](#architecture)
- [Target MVP Capabilities](#target-mvp-capabilities)
- [API](#api)
- [Job Lifecycle](#job-lifecycle)
- [Reliability and Failure Handling](#reliability-and-failure-handling)
- [Data Model](#data-model)
- [Repository Structure](#repository-structure)
- [Implementation Plan](#implementation-plan)
- [Function Documentation](#function-documentation)
- [Getting Started](#getting-started)
- [Quick Smoke Test](#quick-smoke-test)
- [Engineering Decisions and Tradeoffs](#engineering-decisions-and-tradeoffs)
- [Scope](#scope)
- [Future Evolution](#future-evolution)
- [AI Use Disclosure](#ai-use-disclosure)

---

## Overview

Internal business systems often need to notify external vendors after important events. Examples include notifying an advertising platform after a successful registration, updating a CRM after a subscription payment, or informing an inventory system after a purchase.

Calling each vendor directly creates repeated delivery logic in every business system. Each caller would need to handle timeouts, retries, vendor outages, and request tracking.

This project moves that responsibility into one small internal service. A business system submits the target URL, HTTP method, headers, and JSON body. The service stores the job in PostgreSQL and immediately returns a job ID. A background worker then delivers the request and retries temporary failures.

**The caller does not wait for the vendor response. A job is acknowledged only after it has been durably stored.**

---

## Implementation Status

**Batch 1 is complete.** The repository currently includes the FastAPI application skeleton, environment-based configuration, the PostgreSQL job model, an Alembic migration, a database-backed health check, and unit tests.

Notification submission, status lookup, outbound delivery, and the worker lifecycle are target behavior documented below. They will be implemented in the ordered batches defined in [`Plan.md`](Plan.md).

---

## Architecture

The following diagram shows the target MVP architecture. Batch 1 currently implements the FastAPI, PostgreSQL schema, and health-check foundation.

```text
┌─────────────────────┐       POST /notifications
│  Business Systems   │ ───────────────────────────────────┐
└─────────────────────┘                                    │
                                                           ▼
                                             ┌────────────────────────┐
                                             │      FastAPI API       │
                                             │ Validate and store job │
                                             └────────────┬───────────┘
                                                          │
                                                          ▼
                                             ┌────────────────────────┐
                                             │       PostgreSQL       │
                                             │ Jobs, status, retries  │
                                             └────────────┬───────────┘
                                                          │ claim due jobs
                                                          ▼
                                             ┌────────────────────────┐
                                             │   Delivery Worker      │
                                             │ Send, retry, finalize  │
                                             └────────────┬───────────┘
                                                          │ HTTP(S)
                                                          ▼
                                             ┌────────────────────────┐
                                             │  External Vendor APIs  │
                                             └────────────────────────┘
```

The API and worker are separate processes built from the same codebase. PostgreSQL is both the durable system of record and the lightweight job queue.

This keeps the MVP easy to run and understand: there is no Redis, RabbitMQ, Kafka, or Celery dependency.

---

## Target MVP Capabilities

- **Asynchronous submission**: returns `202 Accepted` after a job is stored instead of waiting for the external API.
- **Flexible requests**: accepts a target URL, an allow-listed HTTP method, headers, and a JSON body.
- **Durable jobs**: stores delivery state in PostgreSQL so queued work survives process restarts.
- **Automatic retries**: retries network errors, timeouts, rate limits, and server-side failures.
- **Terminal failure tracking**: preserves the final error when a job exhausts its attempts.
- **Status lookup**: allows callers to inspect a job using its ID.
- **Duplicate-safe submission**: supports an optional `Idempotency-Key` so a caller can safely retry job creation.
- **Safe concurrent workers**: uses PostgreSQL row locking to prevent two workers from claiming the same job at the same time.

---

## API

### Health Check — Implemented

```http
GET /health
```

The endpoint verifies that the API can execute a simple PostgreSQL query.

```json
{
  "status": "ok",
  "database": "ok"
}
```

It returns `503 Service Unavailable` when the database cannot be reached.

### Create a Notification — Planned for Batch 2

```http
POST /notifications
Content-Type: application/json
Idempotency-Key: payment-123-crm
```

```json
{
  "target_url": "https://crm.example.com/contacts/123",
  "method": "POST",
  "headers": {
    "Authorization": "Bearer example-token"
  },
  "body": {
    "status": "paid"
  }
}
```

Successful response:

```http
HTTP/1.1 202 Accepted
```

```json
{
  "id": "f183bf31-53d5-42db-aeb7-42a7bfa48dc2",
  "status": "pending"
}
```

`Idempotency-Key` is optional. If the same key and payload are submitted again, the API returns the original job instead of creating another one. Reusing a key with a different payload returns `409 Conflict`.

### Get Notification Status — Planned for Batch 2

```http
GET /notifications/f183bf31-53d5-42db-aeb7-42a7bfa48dc2
```

Example response:

```json
{
  "id": "f183bf31-53d5-42db-aeb7-42a7bfa48dc2",
  "status": "retrying",
  "attempt_count": 2,
  "next_attempt_at": "2026-08-12T20:30:00Z",
  "last_status_code": 503,
  "last_error": "External API returned HTTP 503",
  "created_at": "2026-08-12T20:20:00Z",
  "updated_at": "2026-08-12T20:25:00Z"
}
```

The API does not store or return external response bodies. They may contain sensitive or unexpectedly large data and are not needed for delivery decisions.

---

## Job Lifecycle

```text
pending ──▶ processing ──▶ succeeded
                │
                ├── temporary failure ──▶ retrying ──▶ processing
                │
                └── permanent failure or attempts exhausted ──▶ dead
```

| Status | Meaning |
|---|---|
| `pending` | Stored and waiting for its first delivery attempt |
| `processing` | Claimed by a worker |
| `retrying` | A temporary failure occurred and another attempt is scheduled |
| `succeeded` | The external API returned a `2xx` response |
| `dead` | The request cannot be retried or has exhausted all attempts |

A recovery check returns jobs that remain in `processing` beyond the worker lease timeout to `retrying`. This prevents a worker crash from leaving jobs permanently stuck.

---

## Reliability and Failure Handling

### Delivery Semantics

The service provides **at-least-once delivery**, not exactly-once delivery.

Once the API returns `202 Accepted`, the job is stored in PostgreSQL and will remain available after an API or worker restart. However, duplicate delivery is still possible. For example, a vendor may process a request successfully while its response is lost on the network. The worker cannot know that the request succeeded, so it must retry.

Every outbound request includes a stable identifier:

```http
X-Notification-Id: f183bf31-53d5-42db-aeb7-42a7bfa48dc2
```

Vendors that support idempotency can use this value to reject duplicate processing.

### Retry Policy

| Result | Action |
|---|---|
| HTTP `2xx` | Mark `succeeded` |
| Network error or timeout | Retry |
| HTTP `408`, `429`, or `5xx` | Retry |
| Other HTTP `4xx` | Mark `dead` because the request is unlikely to succeed unchanged |
| Maximum attempts reached | Mark `dead` and retain the last error |

The MVP makes at most five delivery attempts. Retries use capped exponential delays of approximately 1, 2, 4, and 8 minutes. Each outbound request has a 10-second timeout.

The worker stores only a bounded error message and the latest HTTP status code. Authorization headers are never written to application logs.

### Long Vendor Outages

The service does not retry forever. Indefinite retries would hide broken integrations and allow the queue to grow without limit. A job becomes `dead` after its final attempt and remains queryable for investigation. Manual replay and alerting are reasonable follow-up features, but they are outside the first version.

---

## Data Model

The MVP uses one main PostgreSQL table:

| Field | Purpose |
|---|---|
| `id` | Stable UUID for tracking and downstream idempotency |
| `idempotency_key` | Optional unique key for duplicate-safe submission |
| `target_url` | Destination HTTPS URL |
| `method` | Allow-listed HTTP method |
| `headers` | Request headers stored as `JSONB` |
| `body` | JSON request body stored as `JSONB` |
| `status` | Current lifecycle state |
| `attempt_count` | Number of completed delivery attempts |
| `next_attempt_at` | Earliest time at which the worker may retry |
| `locked_at` | Start time of the current worker lease |
| `last_status_code` | Most recent external HTTP status, when available |
| `last_error` | Bounded description of the most recent failure |
| `created_at`, `updated_at` | Audit timestamps |

Workers claim due rows with `SELECT ... FOR UPDATE SKIP LOCKED`, mark them as `processing`, and commit before making any network request. This keeps database transactions short while preventing two workers from claiming the same job. It is enough for the MVP and also permits multiple workers later without adding a separate message broker.

---

## Repository Structure

```text
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── api.py               # Health endpoint
│   ├── config.py            # Environment-based configuration
│   ├── database.py          # PostgreSQL session setup
│   ├── models.py            # SQLAlchemy job model
├── migrations/
│   └── versions/            # Alembic database revisions
├── tests/                   # Configuration, health, and model tests
├── .env.example             # Local configuration template
├── alembic.ini              # Migration configuration
├── docker-compose.yml       # PostgreSQL service for local development
├── pyproject.toml
├── Plan.md                  # Ordered implementation batches and exit criteria
├── FUNCTIONS.md             # Plain-Chinese explanation of every function
└── README.md
```

---

## Implementation Plan

[`Plan.md`](Plan.md) divides the implementation into small, ordered batches. Each batch defines its scope, tests, completion criteria, documentation updates, and suggested commit before work moves to the next batch.

---

## Function Documentation

[`FUNCTIONS.md`](FUNCTIONS.md) explains every implemented function in plain Chinese, including its purpose, inputs, return value, main steps, failure behavior, and side effects. It is updated together with the code whenever a function is added, changed, or removed.

---

## Getting Started

### Prerequisites

- Docker with Docker Compose, or
- Python 3.11+, [uv](https://docs.astral.sh/uv/), and PostgreSQL 15+

### Local Python Environment

The project pins Python 3.11 in `.python-version` and uses `uv.lock` for reproducible dependencies.

Create or refresh the local virtual environment:

```bash
uv sync --dev
```

Activate it when you want to run commands directly:

```bash
source .venv/bin/activate
```

The `.venv` directory is local-only and is excluded from Git.

### Run the Batch 1 Foundation

Clone the repository and create the local environment file:

```bash
git clone <your-repo-url>
cd rc_<your_nickname>
cp .env.example .env
```

Start PostgreSQL:

```bash
docker compose up -d db
```

Apply the database migration:

```bash
uv run alembic upgrade head
```

Start the API:

```bash
uv run uvicorn app.main:app --reload
```

Default local endpoints:

- API: `http://localhost:8000`
- Interactive API documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### Run Tests

```bash
uv run ruff check .
uv run pytest
```

---

## Quick Smoke Test

With PostgreSQL and the API running, check the current Batch 1 endpoint:

```bash
curl -i http://localhost:8000/health
```

Expected body:

```json
{
  "status": "ok",
  "database": "ok"
}
```

The notification creation and delivery smoke test will be added when those batches are implemented.

---

## Engineering Decisions and Tradeoffs

### Why FastAPI?

FastAPI provides request validation, clear type definitions, asynchronous HTTP support, and generated OpenAPI documentation with little framework code. It keeps the API layer small and easy to review.

An alternative would be Flask. Flask is also suitable, but this project benefits from FastAPI's built-in validation and API schema generation.

### Why PostgreSQL as the Queue?

The system already needs durable storage for job state. Using PostgreSQL for both storage and job claiming removes an additional service from the MVP. Transactions and row-level locks provide the reliability and concurrency control required at the expected first-version scale.

An alternative would be Redis with Celery, RabbitMQ, or a managed queue. Those options provide higher throughput and richer queue features, but add deployment, monitoring, and failure modes that are not justified by the current requirements.

### Why a Separate Worker?

Delivery must not run inside the request handler. An external API may be slow or unavailable, and coupling delivery to the incoming request would increase latency and make failures visible to the business system. A separate worker keeps submission fast and allows delivery to continue independently.

### Why Not Exactly Once?

Exactly-once side effects cannot be guaranteed across an ordinary HTTP boundary. If the vendor processes a request but the response is lost, this service cannot safely determine whether it should retry. At-least-once delivery plus a stable notification ID is the simpler and more honest contract.

---

## Scope

### Included in the MVP

- trusted internal callers
- JSON request bodies
- configurable HTTP(S) destinations and headers
- durable asynchronous delivery
- at-least-once semantics
- retry scheduling and terminal failure records
- duplicate-safe job submission
- status lookup
- basic health checks and structured logs

### Intentionally Excluded

- a web-based operations dashboard
- vendor-specific adapters or workflow orchestration
- Kafka, Redis, RabbitMQ, or Celery
- multi-region deployment and disaster recovery
- exactly-once delivery guarantees
- automatic infinite retries
- payload transformation templates
- per-vendor rate limiting
- manual replay and alerting interfaces

Authentication and authorization are also outside the demo implementation because callers are assumed to be inside a trusted network. A production deployment must add service authentication and access control.

The MVP trusts internal callers and accepts HTTP(S) destinations. A production version should require HTTPS for external traffic, maintain an approved destination list, and block loopback, link-local, and private network targets to reduce server-side request forgery risk.

Request headers are stored in PostgreSQL because they are needed for later delivery. In production, credentials should preferably be referenced from a secret manager or encrypted at rest rather than stored directly in the job row.

---

## Future Evolution

The current design should evolve only when observed load or operational needs justify it:

1. Add metrics and alerts for queue depth, delivery latency, retry volume, and dead jobs.
2. Add an authenticated operations API for inspecting and replaying dead jobs.
3. Add per-vendor concurrency limits and circuit breakers for repeated outages.
4. Partition or archive old job rows as the table grows.
5. Scale worker replicas while continuing to use PostgreSQL row locking.
6. Move job dispatch to a managed queue only when database polling becomes a measured bottleneck.

This path preserves the simple API contract while allowing the delivery implementation to change behind it.

---

## AI Use Disclosure

AI was used as an engineering assistant during requirement analysis and design documentation.

### Where AI Helped

- summarized the assignment into an API, durable job store, and background delivery flow
- compared PostgreSQL-based job claiming with dedicated queue technologies
- identified failure cases such as timeouts, ambiguous delivery outcomes, duplicate requests, and worker crashes
- helped organize the README and make the design easier to review

### Suggestions Not Adopted

- **Redis and Celery** were not adopted because PostgreSQL already provides the durability and locking needed for this MVP.
- **Kafka or RabbitMQ** were not adopted because the assignment provides no throughput requirement that justifies another distributed system.
- **Exactly-once delivery** was not claimed because ordinary HTTP calls cannot provide that guarantee without cooperation from the receiving vendor.
- **Vendor-specific adapters, a dashboard, and multi-region deployment** were deferred because they increase complexity without proving the core delivery path.

### Human Decisions

The author chose FastAPI and PostgreSQL, intentionally limited the first version to one API service and one worker, selected at-least-once delivery, and bounded retries instead of retrying forever. These decisions prioritize a small, testable, and explainable system over a feature-complete platform.

AI-generated suggestions and text were reviewed and may be revised during implementation so that this document remains consistent with the actual code.
