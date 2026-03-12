from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("SKIP_STARTUP_TASKS", "1")

from app.core.observability import observability_state  # noqa: E402
from app.main import app  # noqa: E402
from tests.test_main_missing_blocks import _admin_headers  # noqa: E402
from tests.test_auth import _setup_fake_db  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run release-governance health gates against a local test app or a deployed environment.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("RELEASE_GATE_BASE_URL", "").strip(),
        help="Optional deployed API base URL ending at the API root, for example http://host/api/v1",
    )
    parser.add_argument(
        "--bearer-token",
        default=os.getenv("RELEASE_GATE_BEARER_TOKEN", "").strip(),
        help="Bearer token for calling the remote admin health endpoint.",
    )
    parser.add_argument(
        "--allow-high-alerts",
        action="store_true",
        help="Do not fail the gate on high-severity alerts.",
    )
    parser.add_argument(
        "--allow-medium-alerts",
        action="store_true",
        help="Do not fail the gate on medium-severity alerts.",
    )
    return parser.parse_args()


def _fail(message: str) -> int:
    raise SystemExit(message)


def _evaluate_payload(
    payload: dict[str, Any],
    *,
    allow_high_alerts: bool,
    allow_medium_alerts: bool,
) -> dict[str, Any]:
    alerts = payload.get("alerts") or []
    critical_alerts = [alert for alert in alerts if str(alert.get("level")).lower() == "critical"]
    high_alerts = [alert for alert in alerts if str(alert.get("level")).lower() == "high"]
    medium_alerts = [alert for alert in alerts if str(alert.get("level")).lower() == "medium"]

    if payload.get("db_status") != "ok":
        _fail("Release gate failed: database health is not ok.")

    snapshot_store = payload.get("snapshot_store") or {}
    if snapshot_store and not bool(snapshot_store.get("is_within_retention_bound", True)):
        _fail("Release gate failed: system health snapshot store exceeds retention bound.")

    alert_routing = payload.get("alert_routing") or {}
    if alert_routing and not bool(alert_routing.get("enabled", False)):
        _fail("Release gate failed: operational alert routing is disabled.")

    if critical_alerts:
        _fail(
            "Release gate failed: critical alerts present: "
            + ", ".join(str(alert.get("code")) for alert in critical_alerts)
        )
    if high_alerts and not allow_high_alerts:
        _fail(
            "Release gate failed: high alerts present: "
            + ", ".join(str(alert.get("code")) for alert in high_alerts)
        )
    if medium_alerts and not allow_medium_alerts:
        _fail(
            "Release gate failed: medium alerts present: "
            + ", ".join(str(alert.get("code")) for alert in medium_alerts)
        )

    return {
        "alert_count": int(payload.get("alert_count") or 0),
        "critical_alerts": [str(alert.get("code")) for alert in critical_alerts],
        "high_alerts": [str(alert.get("code")) for alert in high_alerts],
        "medium_alerts": [str(alert.get("code")) for alert in medium_alerts],
        "request_count_15m": int(((payload.get("observability") or {}).get("request_metrics") or {}).get("requests_15m") or 0),
        "ai_queue_depth": int(((payload.get("observability") or {}).get("ai_metrics") or {}).get("queued_jobs") or 0),
        "snapshot_rows": int(snapshot_store.get("retained_rows") or 0),
        "alert_routing_enabled": bool(alert_routing.get("enabled", False)),
        "alert_routing_target_user_count": int(alert_routing.get("target_user_count") or 0),
    }


def _remote_json(url: str, *, bearer_token: str | None = None) -> dict[str, Any]:
    request = urllib.request.Request(url)
    request.add_header("Accept", "application/json")
    if bearer_token:
        request.add_header("Authorization", f"Bearer {bearer_token}")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status != 200:
                _fail(f"Release gate failed: {url} returned HTTP {response.status}.")
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        _fail(f"Release gate failed: {url} returned HTTP {exc.code}.")
    except urllib.error.URLError as exc:
        _fail(f"Release gate failed: could not reach {url}: {exc}.")


def run_remote(args: argparse.Namespace) -> dict[str, Any]:
    if not args.base_url:
        _fail("Remote release gate requires --base-url or RELEASE_GATE_BASE_URL.")
    if not args.bearer_token:
        _fail("Remote release gate requires --bearer-token or RELEASE_GATE_BEARER_TOKEN.")

    base_url = args.base_url.rstrip("/")
    health_payload = _remote_json(f"{base_url}/health")
    if health_payload.get("status") not in {"ok", "healthy"}:
        _fail("Release gate failed: /health did not return an ok-style status.")

    payload = _remote_json(f"{base_url}/admin/system/health", bearer_token=args.bearer_token)
    summary = _evaluate_payload(
        payload,
        allow_high_alerts=args.allow_high_alerts,
        allow_medium_alerts=args.allow_medium_alerts,
    )
    summary["mode"] = "remote"
    return summary


def run_local(args: argparse.Namespace) -> dict[str, Any]:
    _setup_fake_db()
    observability_state.reset()
    logging.getLogger("caps_api").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    with TestClient(app) as client:
        health_response = client.get("/health")
        if health_response.status_code != 200:
            _fail("Release gate failed: local /health did not return 200.")

        headers = _admin_headers(client, "admin_release_gate@example.com")
        response = client.get("/api/v1/admin/system/health", headers=headers)
        if response.status_code != 200:
            _fail(f"Release gate failed: local /api/v1/admin/system/health returned {response.status_code}.")
        payload = response.json()

    summary = _evaluate_payload(
        payload,
        allow_high_alerts=args.allow_high_alerts,
        allow_medium_alerts=args.allow_medium_alerts,
    )
    summary["mode"] = "local"
    return summary


def main() -> int:
    args = parse_args()
    summary = run_remote(args) if args.base_url else run_local(args)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print("Release governance gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
