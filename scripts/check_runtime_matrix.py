from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PYTHON = "3.11"
EXPECTED_NODE = "20"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify that documented and automated runtime versions stay aligned across CAPS AI.",
    )
    parser.add_argument(
        "--json-out",
        help="Optional path for a machine-readable validation report.",
    )
    return parser.parse_args()


def _fail(message: str) -> None:
    raise SystemExit(message)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _find_matches(pattern: str, text: str) -> list[str]:
    return re.findall(pattern, text, flags=re.MULTILINE)


def _check_ci(ci_text: str) -> dict[str, Any]:
    python_versions = _find_matches(r'python-version:\s*"([^"]+)"', ci_text)
    node_versions = _find_matches(r'node-version:\s*"([^"]+)"', ci_text)
    python_ok = bool(python_versions) and all(version == EXPECTED_PYTHON for version in python_versions)
    node_ok = bool(node_versions) and all(version == EXPECTED_NODE for version in node_versions)
    return {
        "python_versions": python_versions,
        "node_versions": node_versions,
        "python_ok": python_ok,
        "node_ok": node_ok,
    }


def _check_backend_dockerfile(text: str) -> dict[str, Any]:
    match = re.search(r"^FROM python:([^\s]+)", text, flags=re.MULTILINE)
    image = match.group(1) if match else None
    return {
        "image": image,
        "ok": bool(image) and image.startswith(f"{EXPECTED_PYTHON}."),
    }


def _check_frontend_dockerfile(text: str) -> dict[str, Any]:
    match = re.search(r"^FROM node:([^\s]+)\s+AS build", text, flags=re.MULTILINE)
    image = match.group(1) if match else None
    return {
        "image": image,
        "ok": bool(image) and image.startswith(f"{EXPECTED_NODE}"),
    }


def _check_package_json(text: str) -> dict[str, Any]:
    payload = json.loads(text)
    node_engine = ((payload.get("engines") or {}).get("node"))
    return {
        "node_engine": node_engine,
        "ok": node_engine == f"{EXPECTED_NODE}.x",
    }


def _check_nvmrc(text: str) -> dict[str, Any]:
    version = text.strip()
    return {
        "version": version,
        "ok": version == EXPECTED_NODE,
    }


def _check_readme(text: str) -> dict[str, Any]:
    python_ok = f"Python {EXPECTED_PYTHON}.x" in text
    node_ok = f"Node.js {EXPECTED_NODE}.x" in text
    return {
        "python_ok": python_ok,
        "node_ok": node_ok,
    }


def build_report() -> dict[str, Any]:
    ci_report = _check_ci(_read(ROOT / ".github" / "workflows" / "ci.yml"))
    backend_docker_report = _check_backend_dockerfile(_read(ROOT / "backend" / "Dockerfile"))
    frontend_docker_report = _check_frontend_dockerfile(_read(ROOT / "frontend" / "Dockerfile"))
    package_report = _check_package_json(_read(ROOT / "frontend" / "package.json"))
    nvmrc_report = _check_nvmrc(_read(ROOT / ".nvmrc"))
    readme_report = _check_readme(_read(ROOT / "README.md"))

    checks = {
        "ci": ci_report,
        "backend_dockerfile": backend_docker_report,
        "frontend_dockerfile": frontend_docker_report,
        "frontend_package": package_report,
        "nvmrc": nvmrc_report,
        "readme": readme_report,
    }
    ok = all(
        item.get("ok", item.get("python_ok", False) and item.get("node_ok", False))
        for item in checks.values()
    )
    return {
        "expected_python_major_minor": EXPECTED_PYTHON,
        "expected_node_major": EXPECTED_NODE,
        "checks": checks,
        "ok": ok,
    }


def main() -> int:
    args = parse_args()
    report = build_report()
    if args.json_out:
        output_path = Path(args.json_out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["ok"]:
        _fail("Runtime matrix validation failed. See report output for mismatches.")
    print("Runtime matrix validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
