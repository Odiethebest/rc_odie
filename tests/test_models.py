"""Tests for the notification job database schema."""

from app.models import NotificationJob, NotificationStatus


def test_notification_job_table_contains_required_fields() -> None:
    """The model should expose every field needed by later delivery batches."""

    expected_columns = {
        "id",
        "idempotency_key",
        "target_url",
        "method",
        "headers",
        "body",
        "status",
        "attempt_count",
        "max_attempts",
        "next_attempt_at",
        "locked_at",
        "last_status_code",
        "last_error",
        "created_at",
        "updated_at",
    }

    assert set(NotificationJob.__table__.columns.keys()) == expected_columns
    assert {constraint.name for constraint in NotificationJob.__table__.constraints} >= {
        "ck_notification_jobs_status",
        "ck_notification_jobs_attempt_count",
        "ck_notification_jobs_max_attempts",
        "uq_notification_jobs_idempotency_key",
    }
    assert {index.name for index in NotificationJob.__table__.indexes} == {
        "ix_notification_jobs_due"
    }


def test_notification_status_values_are_stable() -> None:
    """The Python status values should match the database check constraint."""

    assert {status.value for status in NotificationStatus} == {
        "pending",
        "processing",
        "retrying",
        "succeeded",
        "dead",
    }
