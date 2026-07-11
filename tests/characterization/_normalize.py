"""Normalization helpers for the coord-authority-trio characterization suite.

WP01 (coord-authority-trio-degod-01KX7094): the trio (``workflow.py`` /
``implement.py`` / ``acceptance/__init__.py``) emits output that embeds
non-deterministic values -- git SHAs, ISO timestamps, absolute filesystem
paths, process ids, correlation ids, worktree/lane identifiers. A
characterization test that asserts these raw values verbatim is not pinning
*behaviour*, it is pinning *noise* -- it will flake on every run and mask a
real regression the next time it happens to line up.

Every characterization test in this package MUST route captured text/JSON
through these helpers before asserting equality (or asserting on a normalized
substring). Do not assert raw SHAs, timestamps, absolute paths, pids, or
worktree ids anywhere in this suite.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Regex patterns for the non-deterministic value classes named in the WP
# ---------------------------------------------------------------------------

# Full-length (7-40 char) hex git SHAs. Ordered longest-first so a 40-char SHA
# is not partially matched by a shorter alternative.
_SHA_RE = re.compile(r"\b[0-9a-f]{40}\b|\b[0-9a-f]{7,39}\b")

# ISO-8601 UTC timestamps, e.g. "2026-07-11T05:59:22Z" or with offset/micros.
_ISO_TS_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})\b"
)

# Bare process ids appear in frontmatter as shell_pid: "128230" (quoted or not).
_PID_RE = re.compile(r"\bshell_pid[\"']?\s*[:=]\s*[\"']?(\d{2,7})[\"']?")

# ULID-shaped identifiers (26 Crockford-base32 chars) -- mission_id, event_id.
_ULID_RE = re.compile(r"\b[0-9A-HJKMNP-TV-Z]{26}\b")

# orchestrator-api / CLI correlation ids, e.g. "corr-<uuid>".
_CORRELATION_ID_RE = re.compile(r"\bcorr-[0-9a-fA-F-]{8,}\b")

# Lane worktree / branch disambiguators: "<slug>-lane-<id>" or "-lane-a" etc.
_WORKTREE_ID_RE = re.compile(r"\blane-[a-z0-9]+\b")


def normalize_sha(text: str) -> str:
    """Replace hex git SHAs (short or full) with a stable token."""
    return _SHA_RE.sub("<SHA>", text)


def normalize_timestamp(text: str) -> str:
    """Replace ISO-8601 UTC timestamps with a stable token."""
    return _ISO_TS_RE.sub("<TIMESTAMP>", text)


def normalize_pid(text: str) -> str:
    """Replace ``shell_pid`` values with a stable token."""
    return _PID_RE.sub("shell_pid: <PID>", text)


def normalize_ulid(text: str) -> str:
    """Replace ULID-shaped identifiers (mission_id, event_id) with a stable token."""
    return _ULID_RE.sub("<ULID>", text)


def normalize_correlation_id(text: str) -> str:
    """Replace ``corr-...`` correlation ids with a stable token."""
    return _CORRELATION_ID_RE.sub("<CORRELATION_ID>", text)


def normalize_worktree_id(text: str) -> str:
    """Replace ``lane-<id>`` worktree/branch disambiguators with a stable token."""
    return _WORKTREE_ID_RE.sub("lane-<ID>", text)


def normalize_abs_paths(text: str, *roots: Path | str) -> str:
    """Replace absolute filesystem paths rooted at *roots* with a stable token.

    ``tmp_path``-derived roots (repo checkouts, worktrees) are the dominant
    source of absolute-path noise in this suite -- every test runs in a fresh
    tmp dir, so the literal path differs on every invocation/OS/CI runner.
    """
    normalized = text
    for root in roots:
        root_str = str(root)
        if not root_str:
            continue
        normalized = normalized.replace(root_str, "<REPO_ROOT>")
    return normalized


def normalize_envelope(text: str, *roots: Path | str) -> str:
    """Apply every text-level normalization in a fixed, safe order.

    Order matters: paths first (they may contain hex-looking path segments
    that would otherwise be mangled by the SHA pattern), then timestamps,
    then pids, then ULIDs, then correlation ids, then worktree ids, then
    trailing bare SHAs.
    """
    normalized = normalize_abs_paths(text, *roots)
    normalized = normalize_timestamp(normalized)
    normalized = normalize_pid(normalized)
    normalized = normalize_ulid(normalized)
    normalized = normalize_correlation_id(normalized)
    normalized = normalize_worktree_id(normalized)
    normalized = normalize_sha(normalized)
    return normalized


# ---------------------------------------------------------------------------
# JSON envelope normalization -- walks a decoded structure and normalizes
# both known noisy keys and any string value that matches a noise pattern.
# ---------------------------------------------------------------------------

_NOISY_KEYS = frozenset(
    {
        "timestamp",
        "at",
        "correlation_id",
        "event_id",
        "mission_id",
        "commit_sha",
        "parent_commit",
        "accept_commit",
        "accepted_at",
        "base_commit",
        "shell_pid",
    }
)


def _normalize_scalar(key: str | None, value: Any, roots: tuple[Path | str, ...]) -> Any:
    if isinstance(value, str):
        if key in _NOISY_KEYS and value:
            return f"<{key.upper()}>"
        return normalize_envelope(value, *roots)
    return value


def normalize_json_value(value: Any, *roots: Path | str, key: str | None = None) -> Any:
    """Recursively normalize a decoded JSON value (dict/list/scalar).

    Known noisy keys (see ``_NOISY_KEYS``) are replaced outright regardless
    of shape (some emit shortened SHAs that ``normalize_sha`` would not
    fully catch, e.g. a 6-char abbreviation). Every other string value still
    passes through the general text-level normalizer so incidental noise
    (an absolute path embedded in a message string) is caught too.
    """
    if isinstance(value, dict):
        return {k: normalize_json_value(v, *roots, key=k) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_json_value(item, *roots, key=key) for item in value]
    return _normalize_scalar(key, value, roots)


def normalize_json_text(text: str, *roots: Path | str) -> dict[str, Any] | list[Any]:
    """Parse *text* as JSON and return the normalized structure."""
    data: Any = json.loads(text)
    result: dict[str, Any] | list[Any] = normalize_json_value(data, *roots)
    return result


def parse_last_json_object(output: str) -> dict[str, Any]:
    """Return the last brace-delimited JSON object found in *output*.

    CLI output under test frequently interleaves banner/log noise around a
    single JSON payload line; this mirrors the convention already used by
    ``tests/agent/test_json_envelope_contract_integration.py``.
    """
    for line in reversed(output.strip().splitlines()):
        candidate = line.strip()
        if candidate.startswith("{"):
            parsed: dict[str, Any] = json.loads(candidate)
            return parsed
    raise AssertionError(f"No JSON object found in output:\n{output}")
