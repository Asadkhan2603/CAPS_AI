#!/usr/bin/env python3
"""Lightweight secret scanner for tracked or local repo files.

This checker is intentionally conservative:

- It always detects explicit high-risk token formats and private keys.
- It scans config-like files for suspicious secret assignments.
- By default it scans tracked files only, which makes it stable in CI.
- Developers can opt into `--all-files` to scan local, untracked env files too.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MAX_FILE_SIZE_BYTES = 1_000_000
SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "coverage",
    "htmlcov",
    "out",
    "uploads",
}
CONFIG_SUFFIXES = {
    ".env",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".properties",
}
SENSITIVE_KEY_PATTERN = re.compile(
    r"(?i)\b("
    r"api[_-]?key|secret|token|password|private[_-]?key|jwt[_-]?secret|"
    r"cloudinary[_-]?api[_-]?(?:key|secret)|openai[_-]?api[_-]?key"
    r")\b"
)
ASSIGNMENT_PATTERN = re.compile(
    r"""^\s*([A-Za-z0-9_.-]+)\s*[:=]\s*["']?([^"'#\s][^"'#\r\n]{7,})"""
)
EXPLICIT_SECRET_PATTERNS = [
    ("openai_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("github_pat", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA|DSA|EC|OPENSSH|PGP)? ?PRIVATE KEY-----")),
]
PLACEHOLDER_VALUES = {
    "change_me",
    "changeme",
    "your_secret_here",
    "your-secret-here",
    "your_api_key",
    "placeholder",
    "example",
    "example-value",
    "dummy",
    "dummy-value",
    "test",
    "test-value",
    "ci-secret",
    "student@123",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan the repository for likely secrets.")
    parser.add_argument(
        "--all-files",
        action="store_true",
        help="Scan local files recursively instead of only tracked files.",
    )
    parser.add_argument(
        "--tracked-only",
        action="store_true",
        help="Scan only tracked files (default).",
    )
    return parser.parse_args()


def should_scan_as_config(path: Path) -> bool:
    if path.name.startswith(".env"):
        return True
    return path.suffix.lower() in CONFIG_SUFFIXES


def is_placeholder(value: str) -> bool:
    normalized = value.strip().strip("\"'").lower()
    if normalized in PLACEHOLDER_VALUES:
        return True
    if normalized.startswith("${") and normalized.endswith("}"):
        return True
    return any(
        token in normalized
        for token in (
            "placeholder",
            "example",
            "dummy",
            "your_",
            "sample",
            "replace_with",
            "change_me_with",
        )
    )


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [REPO_ROOT / line for line in result.stdout.splitlines() if line.strip()]


def all_files() -> list[Path]:
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        files.append(path)
    return files


def iter_candidate_files(scan_all_files: bool) -> list[Path]:
    candidates = all_files() if scan_all_files else tracked_files()
    filtered: list[Path] = []
    for path in candidates:
        if not path.exists() or not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        try:
            if path.stat().st_size > MAX_FILE_SIZE_BYTES:
                continue
        except OSError:
            continue
        filtered.append(path)
    return filtered


def scan_text_file(path: Path) -> list[str]:
    findings: list[str] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return findings

    for label, pattern in EXPLICIT_SECRET_PATTERNS:
        for match in pattern.finditer(content):
            line_number = content.count("\n", 0, match.start()) + 1
            findings.append(f"{path.relative_to(REPO_ROOT)}:{line_number}: explicit {label} pattern")

    if not should_scan_as_config(path):
        return findings

    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = ASSIGNMENT_PATTERN.match(raw_line)
        if not match:
            continue
        key, value = match.groups()
        if not SENSITIVE_KEY_PATTERN.search(key):
            continue
        if is_placeholder(value):
            continue
        findings.append(f"{path.relative_to(REPO_ROOT)}:{line_number}: suspicious secret assignment for {key}")

    return findings


def main() -> int:
    args = parse_args()
    scan_all_files = bool(args.all_files and not args.tracked_only)
    findings: list[str] = []

    for path in iter_candidate_files(scan_all_files=scan_all_files):
        findings.extend(scan_text_file(path))

    if findings:
        print("Potential secrets detected:")
        for finding in findings:
            print(f"  - {finding}")
        print("\nUse placeholder/example values in tracked files, and keep real secrets out of the repository.")
        return 1

    mode = "all local files" if scan_all_files else "tracked files"
    print(f"No likely secrets detected in {mode}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
