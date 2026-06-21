#!/usr/bin/env python3
"""Screen git status for commit-skill staging safety.

This helper is intentionally read-only. It classifies the current git status
and emits JSON that the commit skill can use before staging anything.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


STATUS_CLEAN = "clean"
STATUS_STAGED_ONLY = "staged_only"
STATUS_SAFE_TO_STAGE_ALL = "safe_to_stage_all"
STATUS_SELECTION_REQUIRED = "selection_required"
STATUS_BLOCKED = "blocked"

MODE_NONE = "none"
MODE_KEEP_STAGED = "keep_staged"
MODE_STAGE_ALL = "stage_all"
MODE_ASK = "ask"
MODE_STOP = "stop"

DEFAULT_LARGE_FILE_BYTES = 1_048_576
BROAD_TOP_LEVEL_THRESHOLD = 3

PRIVATE_EXTENSIONS = {
    ".key",
    ".pem",
    ".p12",
    ".pfx",
    ".secret",
    ".token",
}

PRIVATE_SSH_KEY_PREFIXES = (
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
)

RISKY_EXTENSIONS = {
    ".7z",
    ".avi",
    ".bak",
    ".bin",
    ".db",
    ".dmg",
    ".gif",
    ".gz",
    ".jpeg",
    ".jpg",
    ".log",
    ".mov",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".sqlite",
    ".tar",
    ".tgz",
    ".tmp",
    ".wav",
    ".webp",
    ".zip",
}

GENERATED_PARTS = {
    ".cache",
    ".pytest_cache",
    ".nox",
    ".tox",
    ".venv",
    "build",
    "cache",
    "coverage",
    "dist",
    "log",
    "logs",
    "node_modules",
    "out",
    "target",
    "tmp",
    "temp",
    "site-packages",
    "__pycache__",
    "venv",
    "virtualenv",
}

SAFE_EXTENSIONS = {
    ".bash",
    ".cfg",
    ".conf",
    ".css",
    ".go",
    ".html",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".md",
    ".py",
    ".rs",
    ".scss",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
    ".zsh",
}

SAFE_FILENAMES = {
    ".gitignore",
    "AGENTS.md",
    "Brewfile",
    "CLAUDE.md",
    "README",
    "README.md",
    "SKILL.md",
}

ENV_TEMPLATE_NAMES = {
    ".env.defaults",
    ".env.dist",
    ".env.example",
    ".env.sample",
    ".env.template",
}

PRIVATE_AGENT_RUNTIME_FILES = {
    ".claude.json",
}

PRIVATE_AGENT_RUNTIME_COMPONENTS = {
    ".agents",
    ".claude",
    ".codex",
}

AGENT_RUNTIME_STATE_FILES = {
    "auth.json",
    "credentials.json",
    "history.jsonl",
    "oauth.json",
    "state.sqlite",
}

AGENT_RUNTIME_STATE_COMPONENTS = {
    ".cache",
    "__pycache__",
    "cache",
    "caches",
    "log",
    "logs",
    "plugin-cache",
    "sessions",
    "sqlite",
    "tmp",
    "temp",
}

CONFIRM_ALWAYS_REASONS = {
    "codex project source",
}

MANAGED_AGENT_SOURCE_FILES = {
    "agents/.codex/agents.md",
}

MANAGED_AGENT_SOURCE_PREFIXES = ()


@dataclass(frozen=True)
class StatusEntry:
    index: str
    worktree: str
    path: str
    original_path: str | None = None

    @property
    def code(self) -> str:
        return f"{self.index}{self.worktree}"

    @property
    def is_untracked(self) -> bool:
        return self.code == "??"

    @property
    def is_ignored(self) -> bool:
        return self.code == "!!"

    @property
    def is_staged(self) -> bool:
        return self.index not in {" ", "?", "!"}

    @property
    def is_worktree_changed(self) -> bool:
        return self.worktree not in {" ", "!"} or self.is_untracked

    @property
    def introduces_path(self) -> bool:
        return (
            self.is_untracked
            or self.index in {"A", "R", "C"}
            or self.worktree in {"A", "R", "C"}
        )

    @property
    def is_partial_staged(self) -> bool:
        return self.is_staged and self.worktree not in {" ", "!"}

    @property
    def is_pure_deletion(self) -> bool:
        return self.code in {"D ", " D"}


def run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def parse_status_z(output: str) -> list[StatusEntry]:
    fields = output.split("\0")
    entries: list[StatusEntry] = []
    index = 0
    while index < len(fields):
        field = fields[index]
        index += 1
        if not field:
            continue
        if len(field) < 4:
            continue

        code = field[:2]
        path = field[3:]
        original_path: str | None = None
        if code[0] in {"R", "C"}:
            if index < len(fields):
                original_path = fields[index] or None
                index += 1
        entries.append(StatusEntry(code[0], code[1], path, original_path))
    return entries


def path_parts(path: str) -> set[str]:
    return {part for part in Path(path).parts if part not in {"", "."}}


def top_level(path: str) -> str:
    parts = Path(path).parts
    return parts[0] if parts else path


def is_conflict(entry: StatusEntry) -> bool:
    code = entry.code
    return "U" in code or code in {"AA", "DD"}


def is_managed_agent_source(lower_path: str) -> bool:
    return lower_path in MANAGED_AGENT_SOURCE_FILES or lower_path.startswith(
        MANAGED_AGENT_SOURCE_PREFIXES
    )


def lower_posix(path: str) -> str:
    return Path(path).as_posix().lower().rstrip("/")


def posix_path(path: str) -> str:
    return Path(path).as_posix().rstrip("/")


def lower_parts(path: str) -> tuple[str, ...]:
    return tuple(part.lower() for part in Path(path).parts if part not in {"", "."})


def path_starts_with_exact(path: str, prefix: str) -> bool:
    normalized = posix_path(path)
    normalized_prefix = prefix.rstrip("/")
    return normalized == normalized_prefix or normalized.startswith(
        f"{normalized_prefix}/"
    )


def repo_is_home(repo: Path) -> bool:
    try:
        return repo.resolve() == Path.home().resolve()
    except OSError:
        return False


def head_has_file(repo: Path, path: str) -> bool:
    completed = run_git(repo, ["ls-tree", "--name-only", "HEAD", "--", path])
    return completed.returncode == 0 and path in completed.stdout.splitlines()


def repo_relative_cwd(repo: Path, cwd: Path) -> Path | None:
    try:
        return cwd.resolve().relative_to(repo.resolve())
    except (OSError, ValueError):
        return None


def repo_skill_parent_paths(repo: Path, cwd: Path) -> set[str]:
    relative_cwd = repo_relative_cwd(repo, cwd)
    if relative_cwd is None:
        return {".agents/skills"}

    parents: set[str] = set()
    current = relative_cwd
    while True:
        skill_parent = current / ".agents" / "skills"
        parents.add(".agents/skills" if current == Path(".") else skill_parent.as_posix())
        if current == Path("."):
            break
        current = current.parent
    return {posix_path(path) for path in parents}


def skill_root_from_path(path: str, skill_parent_paths: set[str]) -> str | None:
    normalized = posix_path(path)
    parts = Path(path).parts
    for skill_parent in sorted(skill_parent_paths, key=len, reverse=True):
        if normalized == skill_parent or not normalized.startswith(f"{skill_parent}/"):
            continue
        parent_part_count = len(Path(skill_parent).parts)
        if len(parts) <= parent_part_count:
            continue
        return Path(*parts[: parent_part_count + 1]).as_posix()
    return None


def build_repo_skill_roots(
    repo: Path,
    entries: list[StatusEntry],
    skill_parent_paths: set[str],
) -> tuple[set[str], set[str]]:
    if repo_is_home(repo):
        return set(), set()

    staged_skill_roots = {
        posix_path(root)
        for entry in entries
        if not entry.is_ignored and entry.is_staged
        for candidate_path in (entry.path, entry.original_path)
        if candidate_path
        for root in [skill_root_from_path(candidate_path, skill_parent_paths)]
        if root
    }
    introduced_skill_markers: set[str] = set()
    for entry in entries:
        if (
            entry.is_ignored
            or not entry.introduces_path
            or Path(entry.path).name != "SKILL.md"
        ):
            continue
        root = skill_root_from_path(entry.path, skill_parent_paths)
        if not root:
            continue
        if entry.is_staged or posix_path(root) not in staged_skill_roots:
            introduced_skill_markers.add(posix_path(entry.path))
    deleted_skill_markers = {
        posix_path(entry.path)
        for entry in entries
        if not entry.is_ignored
        and (entry.index == "D" or entry.worktree == "D")
        and Path(entry.path).name == "SKILL.md"
    }
    deleted_skill_markers.update(
        posix_path(entry.original_path)
        for entry in entries
        if not entry.is_ignored
        and entry.original_path
        and (entry.index == "R" or entry.worktree == "R")
        and Path(entry.original_path).name == "SKILL.md"
    )

    current_roots: set[str] = set()
    original_roots: set[str] = set()
    head_marker_cache: dict[str, bool] = {}
    for entry in entries:
        if entry.is_ignored:
            continue
        for candidate_path in (entry.path, entry.original_path):
            if not candidate_path:
                continue
            root = skill_root_from_path(candidate_path, skill_parent_paths)
            if not root:
                continue
            skill_marker = f"{root}/SKILL.md"
            if skill_marker not in head_marker_cache:
                head_marker_cache[skill_marker] = head_has_file(repo, skill_marker)
            if head_marker_cache[skill_marker]:
                original_roots.add(posix_path(root))
            existing_tracked_marker_survives = (
                head_marker_cache[skill_marker]
                and skill_marker not in deleted_skill_markers
            )
            if (
                existing_tracked_marker_survives
                or skill_marker in introduced_skill_markers
            ):
                current_roots.add(posix_path(root))
    return current_roots, original_roots


def is_repo_skill_source(path: str, repo_skill_roots: set[str]) -> bool:
    return any(path_starts_with_exact(path, root) for root in repo_skill_roots)


def has_agent_runtime_state_part(path: str) -> str | None:
    parts = set(lower_parts(path))
    runtime_parts = AGENT_RUNTIME_STATE_COMPONENTS.intersection(parts)
    if runtime_parts:
        return sorted(runtime_parts)[0]
    lower_name = Path(path).name.lower()
    if lower_name in AGENT_RUNTIME_STATE_FILES:
        return lower_name
    if Path(path).suffix.lower() == ".log":
        return ".log"
    return None


def repo_skill_relative_path(path: str, repo_skill_roots: set[str]) -> str | None:
    normalized = posix_path(path)
    for root in sorted(repo_skill_roots, key=len, reverse=True):
        if not path_starts_with_exact(path, root):
            continue
        if normalized == root:
            return ""
        return normalized.removeprefix(root).lstrip("/")
    return None


def repo_skill_risky_path(path: str, repo_skill_roots: set[str]) -> str | None:
    parts = Path(path).parts
    for root in sorted(repo_skill_roots, key=len, reverse=True):
        if not path_starts_with_exact(path, root):
            continue
        root_part_count = len(Path(root).parts)
        parent_parts = parts[: max(root_part_count - 3, 0)]
        tail_parts = parts[root_part_count:]
        risky_parts = (*parent_parts, *tail_parts)
        if not risky_parts:
            return Path(path).name
        return Path(*risky_parts).as_posix()
    return None


def repo_skill_runtime_state_part(path: str, repo_skill_roots: set[str]) -> str | None:
    tail = repo_skill_relative_path(path, repo_skill_roots)
    if tail is not None:
        if not tail:
            return None
        return has_agent_runtime_state_part(tail)
    return has_agent_runtime_state_part(path)


def codex_project_source_tail(tail: tuple[str, ...]) -> bool:
    if tail in {("config.toml",), ("hooks.json",)}:
        return True
    if len(tail) >= 2 and tail[0] in {"hooks", "rules"}:
        return True
    if len(tail) == 2 and tail[0] == "agents" and tail[1].endswith(".toml"):
        return True
    return False


def agent_path_risk(
    path: str,
    repo_skill_roots: set[str],
    *,
    allow_agent_marketplace: bool = False,
    allow_codex_project_source: bool = False,
) -> tuple[str, str | None]:
    lower_path = lower_posix(path)
    parts = lower_parts(path)
    lower_name = Path(lower_path).name

    if lower_name in PRIVATE_AGENT_RUNTIME_FILES:
        return "block", "private agent runtime config"
    if is_managed_agent_source(lower_path):
        return "safe", None

    for index, part in enumerate(parts):
        if part not in PRIVATE_AGENT_RUNTIME_COMPONENTS:
            continue

        tail = parts[index + 1 :]
        nested_under_agent_runtime = any(
            previous in PRIVATE_AGENT_RUNTIME_COMPONENTS for previous in parts[:index]
        )

        if part == ".agents":
            if nested_under_agent_runtime:
                return "block", "private agent runtime config"
            if is_repo_skill_source(path, repo_skill_roots):
                runtime_part = repo_skill_runtime_state_part(path, repo_skill_roots)
                if runtime_part:
                    return "block", f"private agent runtime state {runtime_part}"
                continue
            if (
                allow_agent_marketplace
                and index == 0
                and tail == ("plugins", "marketplace.json")
            ):
                return "safe", None
            return "block", "private agent runtime config"

        if part == ".codex":
            if nested_under_agent_runtime:
                return "block", "private agent runtime config"
            if any(component in PRIVATE_AGENT_RUNTIME_COMPONENTS for component in tail):
                return "block", "private agent runtime config"
            runtime_part = has_agent_runtime_state_part(Path(*tail).as_posix())
            if runtime_part:
                return "block", f"private agent runtime state {runtime_part}"
            if Path(path).suffix.lower() == ".log":
                return "block", "private agent runtime state .log"
            if codex_project_source_tail(tail):
                if allow_codex_project_source:
                    return "confirm", "codex project source"
                return "block", "private agent runtime config"
            return "block", "private agent runtime config"

        if part == ".claude":
            return "block", "private agent runtime config"

    return "safe", None


def is_secret_or_private_path(path: str) -> tuple[bool, str | None]:
    candidate = Path(path)
    name = candidate.name
    lower_name = name.lower()
    lower_path = path.lower()
    suffix = candidate.suffix.lower()

    if is_env_template(lower_name):
        return False, None
    if lower_name == ".env" or lower_name.startswith(".env."):
        return True, "environment file"
    if lower_name == ".netrc":
        return True, "netrc credentials"
    if lower_name in PRIVATE_EXTENSIONS:
        return True, f"private filename {lower_name}"
    if suffix in PRIVATE_EXTENSIONS:
        return True, f"private extension {suffix}"
    if lower_name.startswith(PRIVATE_SSH_KEY_PREFIXES):
        return True, "private SSH key"
    if (
        lower_name.endswith(".local")
        or ".local." in lower_name
        or lower_name == ".zshrc.local"
    ):
        return True, "private local override"
    if lower_path.startswith("ssh/.ssh/"):
        if (
            lower_name.startswith("id_")
            or lower_name.startswith("known_hosts")
            or lower_name.endswith(".pub")
        ):
            return True, "ignored SSH material"
    return False, None


def is_env_template(lower_name: str) -> bool:
    if lower_name in ENV_TEMPLATE_NAMES:
        return True
    return lower_name.startswith(".env.") and lower_name.endswith(
        (".example", ".sample", ".template", ".dist")
    )


def is_generated_or_risky_path(path: str) -> tuple[bool, str | None]:
    candidate = Path(path)
    suffix = candidate.suffix.lower()
    parts = {part.lower() for part in path_parts(path)}

    generated = GENERATED_PARTS.intersection(parts)
    if generated:
        return True, f"generated/cache path component {sorted(generated)[0]}"
    if suffix in RISKY_EXTENSIONS:
        return True, f"risky extension {suffix}"
    return False, None


def looks_binary(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            sample = handle.read(8192)
    except OSError:
        return False
    return b"\0" in sample


def is_index_gitlink(repo: Path, path: str) -> bool:
    completed = run_git(repo, ["ls-files", "--stage", "--", path])
    if completed.returncode != 0:
        return False
    return any(line.startswith("160000 ") for line in completed.stdout.splitlines())


def is_committed_gitlink(repo: Path, path: str) -> bool:
    completed = run_git(repo, ["ls-tree", "HEAD", "--", path])
    if completed.returncode != 0:
        return False
    return any(line.startswith("160000 ") for line in completed.stdout.splitlines())


def has_gitmodules_entry(repo: Path, path: str) -> bool:
    gitmodules = repo / ".gitmodules"
    if not gitmodules.is_file():
        return False
    completed = run_git(
        repo,
        ["config", "-f", ".gitmodules", "--get-regexp", r"^submodule\..*\.path$"],
    )
    if completed.returncode != 0:
        return False
    return any(
        line.split(maxsplit=1)[1] == path
        for line in completed.stdout.splitlines()
        if len(line.split(maxsplit=1)) == 2
    )


def is_ignored_by_rules(repo: Path, path: str) -> bool:
    completed = run_git(
        repo,
        ["check-ignore", "--no-index", "--quiet", "--", path],
    )
    return completed.returncode == 0


def tracked_gitlink_confirmation(repo: Path, path: str) -> str | None:
    absolute = repo / path
    if not absolute.is_dir():
        return None
    completed = run_git(
        absolute,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
    )
    if completed.returncode != 0:
        return "tracked submodule status unavailable"
    if completed.stdout:
        return "tracked submodule has dirty or untracked contents"
    return None


def file_risk(
    repo: Path,
    path: str,
    large_file_bytes: int,
    *,
    tracked_gitlink: bool = False,
    repo_skill_roots: set[str] | None = None,
    allow_agent_marketplace: bool = False,
    allow_codex_project_source: bool = False,
) -> tuple[str, str | None]:
    secret, reason = is_secret_or_private_path(path)
    if secret:
        return "block", reason

    agent_risk, reason = agent_path_risk(
        path,
        repo_skill_roots or set(),
        allow_agent_marketplace=allow_agent_marketplace,
        allow_codex_project_source=allow_codex_project_source,
    )
    if agent_risk == "block":
        return "block", reason
    agent_confirm_reason = reason if agent_risk == "confirm" else None

    absolute = repo / path
    if absolute.is_symlink():
        return "confirm", agent_confirm_reason or "symlink"
    if (absolute / ".git").exists() or (absolute / ".git").is_file():
        if tracked_gitlink:
            if agent_confirm_reason:
                return "confirm", agent_confirm_reason
            return "safe", None
        return "block", "embedded git repository"
    if absolute.is_dir():
        try:
            if any(candidate.name == ".git" for candidate in absolute.rglob(".git")):
                return "block", "embedded git repository"
        except OSError:
            pass

    risky_path = repo_skill_risky_path(path, repo_skill_roots or set()) or path

    risky, reason = is_generated_or_risky_path(risky_path)
    if risky:
        return "confirm", agent_confirm_reason or reason

    if absolute.is_file():
        try:
            if absolute.stat().st_size > large_file_bytes:
                return (
                    "confirm",
                    agent_confirm_reason or f"large file over {large_file_bytes} bytes",
                )
        except OSError:
            pass
        if looks_binary(absolute):
            return "confirm", agent_confirm_reason or "binary file"

    if agent_confirm_reason:
        return "confirm", agent_confirm_reason

    return "safe", None


def safe_addition(entry: StatusEntry) -> bool:
    if not entry.introduces_path:
        return False
    path = Path(entry.path)
    return (
        path.name in SAFE_FILENAMES
        or is_env_template(path.name.lower())
        or path.suffix.lower() in SAFE_EXTENSIONS
    )


def finding(path: str, status: str, reason: str, action: str) -> dict[str, str]:
    return {
        "path": path,
        "status": status,
        "reason": reason,
        "action": action,
    }


def classify(
    repo: Path,
    large_file_bytes: int = DEFAULT_LARGE_FILE_BYTES,
    *,
    cwd: Path | None = None,
) -> dict[str, Any]:
    completed = run_git(
        repo,
        [
            "-c",
            "status.renames=true",
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
        ],
    )
    if completed.returncode != 0:
        return {
            "status": STATUS_BLOCKED,
            "staging_mode": MODE_STOP,
            "blockers": [
                finding("", "git", completed.stderr.strip() or "git status failed", "stop")
            ],
            "confirmations": [],
            "safe_additions": [],
            "recommended_question": None,
            "summary": {"path_count": 0},
        }

    entries = parse_status_z(completed.stdout)
    skill_parent_paths = repo_skill_parent_paths(repo, cwd or Path.cwd())
    repo_skill_roots, repo_skill_original_roots = build_repo_skill_roots(
        repo,
        entries,
        skill_parent_paths,
    )
    repo_root_is_home = repo_is_home(repo)
    allow_agent_marketplace = not repo_root_is_home
    allow_codex_project_source = not repo_root_is_home
    blockers: list[dict[str, str]] = []
    confirmations: list[dict[str, str]] = []
    safe_additions: list[str] = []
    has_additions = any(
        not entry.is_ignored and entry.introduces_path
        for entry in entries
    )

    for entry in entries:
        if entry.is_ignored:
            continue

        if is_conflict(entry):
            blockers.append(finding(entry.path, entry.code, "merge conflict", "stop"))
            continue

        if entry.is_pure_deletion:
            risk, reason = file_risk(
                repo,
                entry.path,
                large_file_bytes,
                repo_skill_roots=repo_skill_roots | repo_skill_original_roots,
                allow_agent_marketplace=allow_agent_marketplace,
                allow_codex_project_source=allow_codex_project_source,
            )
            if risk == "confirm" and reason in CONFIRM_ALWAYS_REASONS:
                confirmations.append(
                    finding(
                        entry.path,
                        entry.code,
                        reason or "ambiguous path",
                        "ask before staging",
                    )
                )
            elif has_additions and risk == "block":
                confirmations.append(
                    finding(
                        entry.path,
                        entry.code,
                        (
                            f"{reason or 'blocked path'} deleted while "
                            "additions exist"
                        ),
                        "ask before staging",
                    )
                )
            continue

        index_gitlink = is_index_gitlink(repo, entry.path)
        committed_gitlink = is_committed_gitlink(repo, entry.path)
        new_gitlink = index_gitlink and not committed_gitlink
        known_gitlink = index_gitlink and (
            committed_gitlink or has_gitmodules_entry(repo, entry.path)
        )
        tracked_gitlink_reason = (
            tracked_gitlink_confirmation(repo, entry.path)
            if known_gitlink
            else None
        )
        if tracked_gitlink_reason:
            confirmations.append(
                finding(
                    entry.path,
                    entry.code,
                    tracked_gitlink_reason,
                    "ask before staging",
                )
            )

        risk, reason = file_risk(
            repo,
            entry.path,
            large_file_bytes,
            tracked_gitlink=known_gitlink,
            repo_skill_roots=repo_skill_roots,
            allow_agent_marketplace=allow_agent_marketplace,
            allow_codex_project_source=allow_codex_project_source,
        )
        if risk == "block":
            blockers.append(finding(entry.path, entry.code, reason or "blocked path", "stop"))
            continue
        if entry.original_path:
            original_risk, original_reason = file_risk(
                repo,
                entry.original_path,
                large_file_bytes,
                tracked_gitlink=is_index_gitlink(repo, entry.original_path)
                and (
                    is_committed_gitlink(repo, entry.original_path)
                    or has_gitmodules_entry(repo, entry.original_path)
                ),
                repo_skill_roots=repo_skill_original_roots,
                allow_agent_marketplace=allow_agent_marketplace,
                allow_codex_project_source=allow_codex_project_source,
            )
            if original_risk == "block":
                blockers.append(
                    finding(
                        entry.original_path,
                        entry.code,
                        original_reason or "blocked original path",
                        "stop",
                    )
                )
                continue
            if original_risk == "confirm":
                confirmations.append(
                    finding(
                        entry.original_path,
                        entry.code,
                        original_reason or "ambiguous original path",
                        "ask before staging",
                    )
                )
        risk_requires_confirmation = risk == "confirm" and (
            entry.introduces_path
            or reason == "symlink"
            or reason in CONFIRM_ALWAYS_REASONS
        )
        if risk_requires_confirmation:
            confirmations.append(
                finding(
                    entry.path,
                    entry.code,
                    reason or "ambiguous path",
                    "ask before staging",
                )
            )
        if (
            entry.introduces_path
            and is_ignored_by_rules(repo, entry.path)
        ):
            confirmations.append(
                finding(
                    entry.path,
                    entry.code,
                    "path is ignored by repository rules",
                    "ask before staging",
                )
            )
            continue
        elif new_gitlink:
            confirmations.append(
                finding(
                    entry.path,
                    entry.code,
                    "new gitlink or submodule addition",
                    "ask before staging",
                )
            )
        elif not risk_requires_confirmation and safe_addition(entry):
            safe_additions.append(entry.path)
        elif not risk_requires_confirmation and entry.introduces_path:
            confirmations.append(
                finding(
                    entry.path,
                    entry.code,
                    "unrecognized new path",
                    "ask before staging",
                )
            )

        if entry.is_partial_staged:
            confirmations.append(
                finding(
                    entry.path,
                    entry.code,
                    "path has both staged and unstaged changes",
                    "ask whether to commit staged only, stage all, choose paths, or stop",
                )
            )

    has_staged = any(entry.is_staged for entry in entries if not entry.is_ignored)
    has_worktree = any(entry.is_worktree_changed for entry in entries if not entry.is_ignored)
    has_entries = any(not entry.is_ignored for entry in entries)

    if has_staged and has_worktree:
        for entry in entries:
            if entry.is_ignored or not entry.is_worktree_changed:
                continue
            confirmations.append(
                finding(
                    entry.path,
                    entry.code,
                    "existing staged changes plus unstaged or untracked changes",
                    "ask whether to commit staged only, stage all, choose paths, or stop",
                )
            )

    changed_top_levels = {
        top_level(entry.path)
        for entry in entries
        if not entry.is_ignored and entry.path
    }
    if len(changed_top_levels) > BROAD_TOP_LEVEL_THRESHOLD:
        confirmations.append(
            finding(
                "",
                "mixed",
                f"changes span {len(changed_top_levels)} top-level paths",
                "ask whether this is one commit or should be split",
            )
        )

    blockers = dedupe_findings(blockers)
    confirmations = dedupe_findings(confirmations)
    safe_additions = sorted(set(safe_additions))

    if blockers:
        status = STATUS_BLOCKED
        staging_mode = MODE_STOP
        recommended_question = None
    elif confirmations:
        status = STATUS_SELECTION_REQUIRED
        staging_mode = MODE_ASK
        if has_staged:
            recommended_question = (
                "Choose one staging mode: commit staged only, stage all after "
                "review, stage selected paths, or stop to update ignore rules."
            )
        else:
            recommended_question = (
                "Choose one staging mode: stage all after review, stage selected "
                "paths, or stop to update ignore rules."
            )
    elif not has_entries:
        status = STATUS_CLEAN
        staging_mode = MODE_NONE
        recommended_question = None
    elif has_staged and not has_worktree:
        status = STATUS_STAGED_ONLY
        staging_mode = MODE_KEEP_STAGED
        recommended_question = None
    else:
        status = STATUS_SAFE_TO_STAGE_ALL
        staging_mode = MODE_STAGE_ALL
        recommended_question = None

    return {
        "status": status,
        "staging_mode": staging_mode,
        "blockers": blockers,
        "confirmations": confirmations,
        "safe_additions": safe_additions,
        "recommended_question": recommended_question,
        "summary": {
            "path_count": len([entry for entry in entries if not entry.is_ignored]),
            "staged": has_staged,
            "worktree": has_worktree,
            "top_levels": sorted(changed_top_levels),
        },
    }


def dedupe_findings(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str, str]] = set()
    result: list[dict[str, str]] = []
    for item in items:
        key = (item["path"], item["status"], item["reason"], item["action"])
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        default=".",
        help="repository path to inspect, defaults to the current directory",
    )
    parser.add_argument(
        "--large-file-bytes",
        type=int,
        default=DEFAULT_LARGE_FILE_BYTES,
        help="size threshold that requires confirmation",
    )
    return parser.parse_args(argv)


def resolve_git_root(repo: Path) -> Path:
    candidate = repo.resolve()
    completed = run_git(candidate, ["rev-parse", "--show-toplevel"])
    if completed.returncode == 0 and completed.stdout.strip():
        return Path(completed.stdout.strip()).resolve()
    return candidate


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    payload = classify(
        resolve_git_root(Path(args.repo)),
        args.large_file_bytes,
        cwd=Path.cwd(),
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
