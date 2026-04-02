import os

from app.services.scheduler import AppScheduler


def test_scheduler_instance_id_uses_hostname_and_pid_by_default(monkeypatch) -> None:
    monkeypatch.delenv("SCHEDULER_INSTANCE_ID", raising=False)
    monkeypatch.setenv("HOSTNAME", "caps-ai-backend-0")

    scheduler = AppScheduler()

    assert scheduler._instance_id == f"caps-ai-backend-0-{os.getpid()}"


def test_scheduler_instance_id_honors_explicit_override(monkeypatch) -> None:
    monkeypatch.setenv("SCHEDULER_INSTANCE_ID", "scheduler-primary")
    monkeypatch.setenv("HOSTNAME", "caps-ai-backend-0")

    scheduler = AppScheduler()

    assert scheduler._instance_id == "scheduler-primary"
