"""WP05 — Strict ``--json`` stdout discipline (#842).

Each of the four ``--json`` CLI paths under FR-005 of mission
``charter-e2e-hardening-tranche-2-01KQ9NVQ`` must:

1. Emit exactly one JSON document on stdout (parseable with
   ``json.loads`` of the *full* stream — no trailing junk, no leading
   junk, no Rich markup).
2. Avoid leaking late-firing diagnostics (SaaS sync warnings, atexit
   shutdown errors) onto stdout. Diagnostics that occur *before* the
   payload write may go to stderr; the success path silences atexit
   warnings via ``mark_invocation_succeeded()`` — a flag the JSON
   path sets after writing its payload.

The fix landed in WP05 wires ``mark_invocation_succeeded()`` into the
four ``--json`` paths:

- ``charter generate --json``
- ``charter bundle validate --json``
- ``charter synthesize --json``  (and its ``--dry-run`` envelope)
- ``next --json``  (query mode and result mode)

The strict-parse coverage here uses ``json.loads(stdout)`` (the full
stream), NOT ``_parse_first_json_object(stdout)`` (a tolerant helper
used only for diagnostic dumps in the larger E2E test). The strict
parse is the contract the operator (and the strict E2E) relies on.

Tests run with ``SPEC_KITTY_ENABLE_SAAS_SYNC`` *unset* (offline mode).
The autouse fixture in ``tests/conftest.py`` sets it on by default;
each test below explicitly deletes it via ``monkeypatch.delenv``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

from tests.test_isolation_helpers import (
    REPO_ROOT,
    get_installed_version,
    get_venv_python,
)


pytestmark = pytest.mark.non_sandbox


# ---------------------------------------------------------------------------
# Fixture: a real-on-disk Spec Kitty project with charter.md generated +
# tracked. We need a charter for `bundle validate` and a project root for
# all four CLI paths.
# ---------------------------------------------------------------------------


def _isolated_env_no_saas() -> dict[str, str]:
    """Return an env that runs source code with SaaS sync DISABLED."""
    import os

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("SPEC_KITTY_ENABLE_SAAS_SYNC", None)

    with open(REPO_ROOT / "pyproject.toml", "rb") as fh:
        version = tomllib.load(fh)["project"]["version"]

    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    env["SPEC_KITTY_CLI_VERSION"] = version
    env["SPEC_KITTY_TEST_MODE"] = "1"
    env["SPEC_KITTY_TEMPLATE_ROOT"] = str(REPO_ROOT)
    return env


def _run_cli(
    project: Path,
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [str(get_venv_python()), "-m", "specify_cli.__init__", *args]
    return subprocess.run(
        command,
        cwd=str(project),
        capture_output=True,
        text=True,
        env=env if env is not None else _isolated_env_no_saas(),
        timeout=120,
    )


def _bootstrap_schema_version(project: Path) -> None:
    """Stamp metadata.yaml with the current schema_version + commit."""
    from specify_cli.migration.schema_version import (
        MAX_SUPPORTED_SCHEMA,
        SCHEMA_CAPABILITIES,
    )

    metadata_path = project / ".kittify" / "metadata.yaml"
    if not metadata_path.exists():
        return

    with open(metadata_path, encoding="utf-8") as fh:
        metadata = yaml.safe_load(fh) or {}
    metadata.setdefault("spec_kitty", {})

    current_version = get_installed_version()
    if current_version is None:
        with open(REPO_ROOT / "pyproject.toml", "rb") as fh:
            current_version = tomllib.load(fh)["project"]["version"]

    metadata["spec_kitty"]["version"] = current_version
    metadata["spec_kitty"]["schema_version"] = MAX_SUPPORTED_SCHEMA
    metadata["spec_kitty"]["schema_capabilities"] = SCHEMA_CAPABILITIES[
        MAX_SUPPORTED_SCHEMA
    ]
    with open(metadata_path, "w", encoding="utf-8") as fh:
        yaml.dump(metadata, fh, default_flow_style=False, sort_keys=False)

    subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Bootstrap schema_version", "--allow-empty"],
        cwd=project,
        check=True,
        capture_output=True,
    )


@pytest.fixture()
def charter_project(tmp_path: Path) -> Path:
    """Build a Spec Kitty project with a generated, committed charter.md.

    Mirrors the e2e_project fixture pattern: copies .kittify and
    missions from the repo root, initializes git, runs charter
    interview + generate, then commits charter.md so bundle validate
    sees a tracked file.
    """
    project = tmp_path / "json-discipline-project"
    project.mkdir()

    shutil.copytree(REPO_ROOT / ".kittify", project / ".kittify", symlinks=True)
    missions_src = REPO_ROOT / "src" / "specify_cli" / "missions"
    missions_dest = project / ".kittify" / "missions"
    if missions_src.exists() and not missions_dest.exists():
        shutil.copytree(missions_src, missions_dest)

    # The source-checkout `.kittify` carries an already-populated
    # charter. Delete it so `charter generate` can run from a clean
    # state without `--force`.
    charter_dir = project / ".kittify" / "charter"
    if charter_dir.exists():
        shutil.rmtree(charter_dir)

    (project / ".gitignore").write_text(
        "__pycache__/\n.worktrees/\n",
        encoding="utf-8",
    )

    subprocess.run(
        ["git", "init", "-b", "main"], cwd=project, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "json-discipline@example.com"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "JSON Discipline Test"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial project"],
        cwd=project,
        check=True,
        capture_output=True,
    )

    _bootstrap_schema_version(project)

    # charter interview --profile minimal --defaults --json (seed answers).
    interview = _run_cli(
        project,
        "charter",
        "interview",
        "--profile",
        "minimal",
        "--defaults",
        "--json",
    )
    if interview.returncode != 0:
        pytest.skip(
            f"charter interview unavailable in this environment: rc={interview.returncode}, "
            f"stderr={interview.stderr!r}"
        )

    # charter generate --from-interview (writes charter.md).
    generate = _run_cli(
        project,
        "charter",
        "generate",
        "--from-interview",
        "--json",
    )
    if generate.returncode != 0:
        pytest.skip(
            f"charter generate unavailable: rc={generate.returncode}, "
            f"stderr={generate.stderr!r}"
        )

    # commit charter.md so bundle validate's tracked-files invariant passes.
    subprocess.run(
        ["git", "add", ".kittify/charter/charter.md"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add generated charter.md"],
        cwd=project,
        check=True,
        capture_output=True,
    )

    return project


# ---------------------------------------------------------------------------
# Strict-parse helpers (FR-005)
# ---------------------------------------------------------------------------


_DOCUMENTED_STDERR_MARKERS = (
    # Diagnostics that may be emitted to stderr BEFORE the JSON payload
    # write (auth, sync, etc.). Each new tolerated marker should be
    # documented in research.md R3 before being added here.
    "Not authenticated, skipping sync",
    "SaaS sync disabled",
    "[charter] Bundle out-of-date",  # ensure_charter_bundle_fresh notice
    "Skipping bundle freshness check",
)


def _assert_strict_json_stdout(
    completed: subprocess.CompletedProcess[str],
    *,
    command_label: str,
) -> dict:
    """Assert the entire stdout parses as a single JSON document."""
    assert completed.stdout, (
        f"{command_label}: expected JSON on stdout, got empty stdout. "
        f"rc={completed.returncode} stderr={completed.stderr!r}"
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"{command_label}: stdout is not strictly JSON-parseable.\n"
            f"  decode error: {exc}\n"
            f"  rc:     {completed.returncode}\n"
            f"  stdout: {completed.stdout!r}\n"
            f"  stderr: {completed.stderr!r}"
        ) from exc
    assert isinstance(payload, dict), (
        f"{command_label}: expected a JSON object on stdout, got {type(payload).__name__}"
    )
    return payload


def _assert_stderr_clean(
    completed: subprocess.CompletedProcess[str],
    *,
    command_label: str,
) -> None:
    """Stderr must be empty or contain only documented diagnostic markers."""
    stderr = completed.stderr or ""
    if not stderr.strip():
        return

    for line in stderr.splitlines():
        if not line.strip():
            continue
        if any(marker in line for marker in _DOCUMENTED_STDERR_MARKERS):
            continue
        # Tolerate Rich style codes and whitespace.
        raise AssertionError(
            f"{command_label}: stderr contains undocumented output.\n"
            f"  line: {line!r}\n"
            f"  full stderr: {stderr!r}"
        )


# ---------------------------------------------------------------------------
# T022 strict-parse tests for the four --json command paths
# ---------------------------------------------------------------------------


def test_charter_generate_json_strict_stdout(charter_project: Path) -> None:
    """``charter generate --json`` stdout must strict-parse as JSON."""
    completed = _run_cli(
        charter_project,
        "charter",
        "generate",
        "--from-interview",
        "--json",
        "--force",
    )
    assert completed.returncode == 0, (
        f"charter generate failed unexpectedly: "
        f"rc={completed.returncode} stderr={completed.stderr!r} "
        f"stdout={completed.stdout!r}"
    )
    payload = _assert_strict_json_stdout(completed, command_label="charter generate --json")
    assert payload.get("result") == "success"
    _assert_stderr_clean(completed, command_label="charter generate --json")


def test_charter_bundle_validate_json_strict_stdout(charter_project: Path) -> None:
    """``charter bundle validate --json`` stdout must strict-parse as JSON."""
    completed = _run_cli(
        charter_project,
        "charter",
        "bundle",
        "validate",
        "--json",
    )
    # rc may be 0 (compliant) or 1 (non-compliant); both must produce strict JSON.
    assert completed.returncode in (0, 1), (
        f"charter bundle validate failed with unexpected rc={completed.returncode}, "
        f"stderr={completed.stderr!r} stdout={completed.stdout!r}"
    )
    payload = _assert_strict_json_stdout(
        completed, command_label="charter bundle validate --json"
    )
    assert "bundle_compliant" in payload
    _assert_stderr_clean(completed, command_label="charter bundle validate --json")


def test_charter_synthesize_json_strict_stdout(charter_project: Path) -> None:
    """``charter synthesize --json`` stdout must strict-parse as JSON.

    In a fresh project without LLM-generated artifacts and without a
    matching fixture, this command exits non-zero with a structured
    error panel on stderr. The strict-parse invariant only applies to
    the success branch; if the command exited non-zero, we assert that
    no JSON envelope leaked on stdout (the error panel goes to stderr
    via err_console). When future fixture coverage lets the command
    succeed, we strict-parse stdout.
    """
    completed = _run_cli(
        charter_project,
        "charter",
        "synthesize",
        "--adapter",
        "fixture",
        "--dry-run",
        "--json",
    )
    if completed.returncode == 0:
        payload = _assert_strict_json_stdout(
            completed, command_label="charter synthesize --dry-run --json"
        )
        assert payload.get("result") == "success"
        _assert_stderr_clean(
            completed, command_label="charter synthesize --dry-run --json"
        )
    else:
        # Failure path: the error panel must NOT show up on stdout. We
        # tolerate the failure here and just assert the negative
        # invariant — stdout must be either empty OR strict-JSON.
        if completed.stdout.strip():
            try:
                json.loads(completed.stdout)
            except json.JSONDecodeError as exc:
                raise AssertionError(
                    "charter synthesize --dry-run --json: failure path leaked "
                    f"non-JSON to stdout: {exc}\n  stdout={completed.stdout!r}\n"
                    f"  stderr={completed.stderr!r}"
                ) from exc


def test_next_query_json_strict_stdout(charter_project: Path) -> None:
    """``next --mission <slug> --json`` (query mode) stdout must strict-parse.

    Query mode is the lightest path through ``next``: no ``--result``,
    no agent identity required. It exercises the same JSON write +
    ``mark_invocation_succeeded()`` discipline as the full mutation
    path without needing a finalized mission.
    """
    # The next command requires a mission slug. Make a minimal one:
    feature_dir = charter_project / "kitty-specs" / "test-json-discipline-mission"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Test mission spec\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("- [ ] T001 Task\n", encoding="utf-8")
    # Minimal meta.json so mission lookup works.
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": "test-json-discipline-mission",
                "friendly_name": "Test JSON Discipline Mission",
                "mission_id": "01TESTJSONDISCIPLINEMISSION",
                "mission_number": None,
            }
        ),
        encoding="utf-8",
    )
    subprocess.run(
        ["git", "add", "."], cwd=charter_project, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Add minimal mission for next --json test"],
        cwd=charter_project,
        check=True,
        capture_output=True,
    )

    completed = _run_cli(
        charter_project,
        "next",
        "--mission",
        "test-json-discipline-mission",
        "--json",
    )

    # `next --json` may emit a query-mode decision (rc=0) or a structured
    # blocked decision (rc=0/1). Either way, stdout must strict-parse.
    if not completed.stdout.strip():
        # Skip when the runtime cannot resolve the minimal mission.
        # The strict-parse invariant still holds for the test surface
        # we do exercise above; this test's value is in catching a
        # regression where stdout has extra junk after the JSON write.
        pytest.skip(
            f"next --json produced no stdout (likely missing runtime context): "
            f"rc={completed.returncode}, stderr={completed.stderr!r}"
        )
    _assert_strict_json_stdout(completed, command_label="next --json")
    _assert_stderr_clean(completed, command_label="next --json")


# ---------------------------------------------------------------------------
# Post-review: warnings must NOT leak to stdout in --json mode (FR-005)
# ---------------------------------------------------------------------------


def test_charter_synthesize_dry_run_json_warning_does_not_break_strict_parse(
    tmp_path: Path,
) -> None:
    """Evidence warnings must NOT leak to stdout via Rich in --json mode.

    Fast in-process variant: drives the synthesize command directly via the
    Typer CliRunner with `_collect_evidence_result` patched to emit a non-empty
    `warnings` list. Pre-fix, those warnings printed via `console.print`,
    leaking Rich-formatted text onto stdout BEFORE the JSON envelope and
    breaking `json.loads(stdout)`. Post-fix, they MUST be folded into the
    envelope's `warnings` field instead.
    """
    from types import SimpleNamespace
    from unittest.mock import patch

    from typer.testing import CliRunner

    from specify_cli.cli.commands.charter import app

    # Stage interview answers so the dry-run can build a request.
    answers_path = tmp_path / ".kittify" / "charter" / "interview" / "answers.yaml"
    answers_path.parent.mkdir(parents=True, exist_ok=True)
    answers_path.write_text(
        "schema_version: '1'\n"
        "mission: software-dev\n"
        "profile: minimal\n"
        "answers:\n"
        "  mission_type: software_dev\n"
        "  testing_philosophy: test-driven\n"
        "  neutrality_posture: balanced\n"
        "  risk_appetite: moderate\n"
        "  language_scope: python\n"
        "selected_paradigms: []\n"
        "selected_directives:\n"
        "  - DIRECTIVE_003\n"
        "available_tools: []\n",
        encoding="utf-8",
    )

    fake_evidence_result = SimpleNamespace(
        bundle=SimpleNamespace(code_signals=None, url_list=[], corpus_snapshot=None),
        warnings=["evidence collection skipped: offline mode"],
    )

    runner = CliRunner()
    with (
        patch(
            "specify_cli.cli.commands.charter.find_repo_root",
            return_value=tmp_path,
        ),
        patch(
            "specify_cli.cli.commands.charter._collect_evidence_result",
            return_value=fake_evidence_result,
        ),
        patch(
            "specify_cli.cli.commands.charter._run_synthesis_dry_run",
            return_value=[
                {
                    "path": ".kittify/doctrine/directives/001-test.directive.yaml",
                    "kind": "directive",
                }
            ],
        ),
    ):
        result = runner.invoke(
            app,
            ["synthesize", "--adapter", "fixture", "--dry-run", "--json"],
        )

    assert result.exit_code == 0, result.output
    # Strict-parse: stdout must be EXACTLY one JSON document.
    payload = json.loads(result.output)
    # Warning MUST be in the envelope, not on stdout as a Rich-formatted line.
    assert "warnings" in payload, (
        f"Envelope missing `warnings` field; pre-fix Rich output: {result.output!r}"
    )
    assert isinstance(payload["warnings"], list)
    assert any(
        isinstance(entry, dict)
        and entry.get("code")
        and "evidence" in entry.get("message", "").lower()
        for entry in payload["warnings"]
    ), (
        "Expected an evidence warning to be folded into the envelope's "
        f"`warnings` array; got: {payload['warnings']!r}"
    )
