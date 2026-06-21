#!/usr/bin/env python3
"""Run the commit-skill staged secret scan.

This helper is intentionally narrow: it delegates content detection to
Gitleaks and emits sanitized JSON for the commit skill to interpret.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


STATUS_CLEAN = "clean"
STATUS_FINDINGS = "findings"
STATUS_TOOLING_FAILURE = "tooling_failure"


def run_command(
    args: list[str],
    *,
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def resolve_git_root(repo: Path) -> Path:
    candidate = repo.resolve()
    completed = run_command(["git", "rev-parse", "--show-toplevel"], cwd=candidate)
    if completed.returncode == 0 and completed.stdout.strip():
        return Path(completed.stdout.strip()).resolve()
    return candidate


def sanitize_finding(item: Any) -> dict[str, str]:
    if not isinstance(item, dict):
        return {}
    sanitized: dict[str, str] = {}
    for output_key, input_keys in {
        "file": ("File", "file"),
        "rule_id": ("RuleID", "RuleId", "rule_id", "ruleID"),
        "description": ("Description", "description"),
        "fingerprint": ("Fingerprint", "fingerprint"),
        "commit": ("Commit", "commit"),
    }.items():
        for input_key in input_keys:
            value = item.get(input_key)
            if isinstance(value, str) and value:
                sanitized[output_key] = value
                break
    return sanitized


def load_findings(report_path: Path) -> tuple[list[dict[str, str]], str | None]:
    if not report_path.exists():
        return [], None
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [], f"gitleaks report was not valid JSON: {exc}"
    except OSError as exc:
        return [], f"could not read gitleaks report: {exc}"

    if isinstance(payload, list):
        return [finding for item in payload if (finding := sanitize_finding(item))], None
    if isinstance(payload, dict):
        for key in ("findings", "Findings", "leaks", "Leaks"):
            value = payload.get(key)
            if isinstance(value, list):
                return [finding for item in value if (finding := sanitize_finding(item))], None
    return [], None


def result(
    status: str,
    *,
    exit_code: int | None = None,
    message: str,
    findings: list[dict[str, str]] | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "exit_code": exit_code,
        "message": message,
        "findings_count": len(findings or []),
        "findings": findings or [],
        "version": version,
    }


def scan(repo: Path) -> dict[str, Any]:
    root = resolve_git_root(repo)
    if shutil.which("gitleaks") is None:
        return result(
            STATUS_TOOLING_FAILURE,
            message="gitleaks is required. Install it with: brew install gitleaks",
        )

    version_completed = run_command(["gitleaks", "version"], cwd=root)
    version = (version_completed.stdout or version_completed.stderr).strip() or None
    if version_completed.returncode != 0:
        return result(
            STATUS_TOOLING_FAILURE,
            exit_code=version_completed.returncode,
            message="gitleaks version failed",
            version=version,
        )

    with tempfile.TemporaryDirectory(prefix="commit-gitleaks-") as tempdir:
        report_path = Path(tempdir) / "report.json"
        command = [
            "gitleaks",
            "git",
            "--pre-commit",
            "--redact",
            "--staged",
            "--verbose",
            "--exit-code",
            "1",
            "--report-format",
            "json",
            "--report-path",
            str(report_path),
        ]
        completed = run_command(command, cwd=root)
        findings, report_error = load_findings(report_path)

    if completed.returncode == 0:
        return result(STATUS_CLEAN, exit_code=0, message="no staged leaks found", version=version)
    if findings:
        return result(
            STATUS_FINDINGS,
            exit_code=completed.returncode,
            message="gitleaks found staged secret content",
            findings=findings,
            version=version,
        )
    if report_error:
        message = report_error
    elif completed.returncode == 126:
        message = "gitleaks reported an unsupported flag"
    else:
        message = "gitleaks failed without a parseable findings report"
    return result(
        STATUS_TOOLING_FAILURE,
        exit_code=completed.returncode,
        message=message,
        version=version,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        default=".",
        help="repository path to inspect, defaults to the current directory",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    payload = scan(Path(args.repo))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == STATUS_CLEAN else 1


if __name__ == "__main__":
    raise SystemExit(main())
