"""Architectural guard — the TID251 banned-API ban is *enforced*, not advisory.

ADR ``docs/adr/3.x/2026-05-28-1-ci-dependency-resolution-and-test-surface-consistency.md``
(Gap 3 / Gap 5, Decision Outcome) commits to "automated enforcement rather than
convention": tests must not reimplement the charter hash algorithm
(``hashlib.sha256``) nor catch ``click.exceptions.*`` directly, and that rule must
*fail the build* — not merely produce an advisory comment.

A previous state of PR #1395 shipped the rule as configuration only:

* the sole CI ruff step was advisory (``continue-on-error: true``) and omitted
  ``--select TID251``, so a live violation sat on a green build; and
* whole-directory ``per-file-ignores`` (``tests/charter/**`` etc.) silently disarmed
  the rule for every present and future file in 10 test trees, making the documented
  "new sha256 still requires a ``# noqa``" policy unenforceable.

This guard pins the enforcement so neither regression can recur:

1. ``pyproject.toml`` has no whole-directory ``tests/**`` ``per-file-ignore`` that lists
   ``TID251`` (the scope hole stays closed).
2. Functionally, with the repository's real ruff config, an unannotated raw
   ``hashlib.sha256`` in a *formerly-exempt* directory (``tests/charter/``) is flagged,
   while the same call carrying ``# noqa: TID251`` is allowed.
3. The production ``src/**`` tree has no file-level TID251 exemptions, so Gap-5
   ``click.exceptions.*`` usage is enforced even in raw-SHA owner files.

Retired (planning#57): point (1) of the original four-point list — "the sole
CI ruff step must run ``--select TID251`` and not be ``continue-on-error``" —
was verified LIVE against ``.github/workflows/ci-quality.yml``, the leftover
pre-programme GitHub Actions YAML deleted per PROGRAM.md §2. GitHub Actions'
``continue-on-error: true`` was the only mechanism that could ever make this
rule advisory-only; a local ``make lint`` / ``uv run ruff check`` has no
equivalent knob, so with no workflow YAML left to parse, that check (and its
``_lint_job_steps()`` helper) has no remaining subject matter and was removed
with the file. Enforcement itself is unaffected: TID251 is selected in
``[tool.ruff.lint]`` (below) with no ``exit-zero``/advisory escape, so running
ruff at all — locally or however this programme now gates merges — enforces
it; points (2)-(4) below never depended on the workflow file and stay.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO_ROOT / "pyproject.toml"


def test_no_whole_dir_tid251_exemption_for_tests() -> None:
    """No ``tests/**`` per-file-ignore may disable TID251 (F2 / F5 scope hole)."""
    config = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    per_file = config["tool"]["ruff"]["lint"]["per-file-ignores"]
    offenders = {
        pattern: codes
        for pattern, codes in per_file.items()
        if pattern.startswith("tests") and "TID251" in codes
    }
    assert not offenders, (
        "Whole-directory per-file-ignores re-introduce the TID251 scope hole for "
        f"test trees: {offenders}. Annotate individual call sites with "
        "`# noqa: TID251 — <justification>` instead of disabling the rule wholesale."
    )


def test_no_blanket_src_tid251_exemption() -> None:
    """No ``src/**`` per-file-ignore may disable Gap-5 for all production code."""
    config = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    per_file = config["tool"]["ruff"]["lint"]["per-file-ignores"]
    offenders = {
        pattern: codes
        for pattern, codes in per_file.items()
        if pattern.rstrip("/") in {"src", "src/**"} and "TID251" in codes
    }
    assert not offenders, (
        "Whole-tree src TID251 ignores make the click.exceptions ban dead config "
        f"for production code: {offenders}. Keep exceptions scoped to exact "
        "raw-SHA owner files."
    )


def test_no_src_file_level_tid251_exemptions() -> None:
    """Production raw-SHA exceptions must be inline, not file-level."""
    config = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    per_file = config["tool"]["ruff"]["lint"]["per-file-ignores"]
    offenders = {
        pattern: codes
        for pattern, codes in per_file.items()
        if pattern.startswith("src/") and "TID251" in codes
    }
    assert not offenders, (
        "File-level src TID251 ignores also disable the click.exceptions ban "
        f"inside raw-SHA owner files: {offenders}. Keep raw-SHA exceptions inline."
    )


def _ruff_probe(snippet: str, stdin_filename: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--config",
            str(_PYPROJECT),
            "--select",
            "TID251",
            "--no-cache",
            "--stdin-filename",
            stdin_filename,
            "-",
        ],
        input=snippet,
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_raw_sha256_in_formerly_exempt_dir_is_flagged() -> None:
    """With the real config, a bare sha256 under tests/charter/ now fails (F2)."""
    proc = _ruff_probe(
        'import hashlib\nhashlib.sha256(b"x").hexdigest()\n',
        "tests/charter/synthesizer/_tid251_probe.py",
    )
    assert proc.returncode != 0, (
        "Unannotated hashlib.sha256 under tests/charter/ was NOT flagged — the "
        f"whole-directory exemption appears to be back.\nstdout:\n{proc.stdout}"
    )
    assert "TID251" in proc.stdout


def test_annotated_sha256_is_allowed() -> None:
    """The documented escape hatch (# noqa: TID251) suppresses the ban."""
    proc = _ruff_probe(
        'import hashlib\nhashlib.sha256(b"x").hexdigest()  # noqa: TID251 - probe\n',
        "tests/charter/synthesizer/_tid251_probe.py",
    )
    assert proc.returncode == 0, (
        f"`# noqa: TID251` did not suppress the ban.\nstdout:\n{proc.stdout}\n"
        f"stderr:\n{proc.stderr}"
    )


def test_click_exceptions_probe_in_src_is_flagged() -> None:
    """Gap-5 must be live for production files, not just tests."""
    proc = _ruff_probe(
        "import click\nraise click.exceptions.UsageError('bad')\n",
        "src/specify_cli/orchestrator_api/_tid251_probe.py",
    )
    assert proc.returncode != 0, (
        "Bare click.exceptions.UsageError under src/ was NOT flagged — "
        f"Gap-5 enforcement is dead for production code.\nstdout:\n{proc.stdout}"
    )
    assert "TID251" in proc.stdout


def test_click_exceptions_probe_in_raw_sha_owner_file_is_flagged() -> None:
    """Gap-5 must stay live in files that also own legitimate raw SHA calls."""
    proc = _ruff_probe(
        "import click\nraise click.exceptions.UsageError('bad')\n",
        "src/specify_cli/sync/body_upload.py",
    )
    assert proc.returncode != 0, (
        "Bare click.exceptions.UsageError inside a raw-SHA owner file was NOT "
        f"flagged.\nstdout:\n{proc.stdout}"
    )
    assert "TID251" in proc.stdout
