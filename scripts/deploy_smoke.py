from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("SKIP_STARTUP_TASKS", "1")

from app.main import app  # noqa: E402


class AssetReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.asset_refs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag == "script" and attr_map.get("src"):
            self.asset_refs.append(attr_map["src"])
        if tag == "link" and attr_map.get("href"):
            self.asset_refs.append(attr_map["href"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run lightweight delivery smoke checks against CAPS AI build artifacts and backend health surfaces.",
    )
    parser.add_argument(
        "--frontend-dist",
        default=str(ROOT / "frontend" / "dist"),
        help="Path to a built frontend dist directory.",
    )
    parser.add_argument(
        "--frontend-url",
        default="",
        help="Optional deployed frontend URL to verify over HTTP.",
    )
    parser.add_argument(
        "--backend-health-url",
        default="",
        help="Optional deployed backend health URL to verify over HTTP.",
    )
    parser.add_argument(
        "--json-out",
        help="Optional path for a machine-readable smoke report.",
    )
    return parser.parse_args()


def _fail(message: str) -> None:
    raise SystemExit(message)


def _load_html(path: Path) -> str:
    if not path.exists():
        _fail(f"Deploy smoke failed: missing frontend entrypoint at {path}.")
    return path.read_text(encoding="utf-8")


def _check_frontend_dist(dist_path: Path) -> dict[str, Any]:
    index_path = dist_path / "index.html"
    html = _load_html(index_path)
    parser = AssetReferenceParser()
    parser.feed(html)
    asset_refs = [ref for ref in parser.asset_refs if ref.startswith("./") or ref.startswith("/assets/") or ref.startswith("assets/")]
    if not asset_refs:
        _fail("Deploy smoke failed: no built asset references were found in frontend dist index.html.")

    missing_assets: list[str] = []
    for ref in asset_refs:
        normalized = ref.lstrip("./")
        normalized = normalized.lstrip("/")
        asset_path = dist_path / normalized
        if not asset_path.exists():
            missing_assets.append(ref)

    if missing_assets:
        _fail("Deploy smoke failed: built frontend references missing assets: " + ", ".join(missing_assets))

    if "/src/" in html or "localhost:" in html:
        _fail("Deploy smoke failed: frontend dist still contains development-only references.")

    return {
        "index_exists": True,
        "asset_reference_count": len(asset_refs),
        "missing_assets": missing_assets,
        "has_root_mount": 'id="root"' in html or "id='root'" in html,
        "ok": not missing_assets and ('id="root"' in html or "id='root'" in html),
    }


def _remote_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url)
    request.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status != 200:
                _fail(f"Deploy smoke failed: {url} returned HTTP {response.status}.")
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        _fail(f"Deploy smoke failed: {url} returned HTTP {exc.code}.")
    except urllib.error.URLError as exc:
        _fail(f"Deploy smoke failed: could not reach {url}: {exc}.")


def _remote_text(url: str) -> str:
    request = urllib.request.Request(url)
    request.add_header("Accept", "text/html")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status != 200:
                _fail(f"Deploy smoke failed: {url} returned HTTP {response.status}.")
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        _fail(f"Deploy smoke failed: {url} returned HTTP {exc.code}.")
    except urllib.error.URLError as exc:
        _fail(f"Deploy smoke failed: could not reach {url}: {exc}.")


def _check_local_backend() -> dict[str, Any]:
    with TestClient(app) as client:
        health_response = client.get("/health")
        root_response = client.get("/")
    if health_response.status_code != 200 or health_response.json().get("status") != "ok":
        _fail("Deploy smoke failed: local backend /health check did not return ok.")
    if root_response.status_code != 200:
        _fail("Deploy smoke failed: local backend root check did not return 200.")
    return {
        "mode": "local",
        "health_status_code": health_response.status_code,
        "root_status_code": root_response.status_code,
        "ok": True,
    }


def _check_remote_backend(health_url: str) -> dict[str, Any]:
    payload = _remote_json(health_url)
    if payload.get("status") not in {"ok", "healthy"}:
        _fail("Deploy smoke failed: remote backend health response was not ok-style.")
    return {
        "mode": "remote",
        "health_url": health_url,
        "status": payload.get("status"),
        "ok": True,
    }


def _check_remote_frontend(frontend_url: str) -> dict[str, Any]:
    html = _remote_text(frontend_url)
    if ('id="root"' not in html) and ("id='root'" not in html):
        _fail("Deploy smoke failed: remote frontend did not return the expected root mount.")
    return {
        "url": frontend_url,
        "has_root_mount": True,
        "ok": True,
    }


def main() -> int:
    args = parse_args()
    frontend_report = _check_frontend_dist(Path(args.frontend_dist))
    backend_report = _check_remote_backend(args.backend_health_url) if args.backend_health_url else _check_local_backend()
    remote_frontend_report = _check_remote_frontend(args.frontend_url) if args.frontend_url else None

    report = {
        "frontend_dist": frontend_report,
        "backend": backend_report,
        "remote_frontend": remote_frontend_report,
        "ok": frontend_report["ok"] and backend_report["ok"] and (remote_frontend_report["ok"] if remote_frontend_report else True),
    }

    if args.json_out:
        output_path = Path(args.json_out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["ok"]:
        _fail("Deploy smoke failed.")
    print("Deploy smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
