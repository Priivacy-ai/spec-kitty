"""End-to-end golden-path test for the Charter epic (#827 tranche 2 / WP08).

Strict regression gate. Every PR-#838 diagnostic-spine bypass has been
stripped (WP08). Any regression in WP02..WP07 fixes will cause this
test to fail loudly:

  - WP02 (#840): `spec-kitty init` stamps `spec_kitty.schema_version`
    and `spec_kitty.schema_capabilities` in `.kittify/metadata.yaml`.
  - WP03 (#839): `charter synthesize --adapter fixture --json` writes
    canonical `.kittify/doctrine/` artifacts when
    `SPEC_KITTY_FIXTURE_AUTO_STUB=1` is in env.
  - WP04 (#841): `charter generate --json` emits `next_step.action ==
    "git_add"` (untracked) or `"no_action_required"` (tracked).
  - WP05 (#842): `--json` paths suppress atexit diagnostics; stdout is
    exactly one JSON document parsable via `json.loads(stdout)`.
  - WP06 (#844/#336): `next --json` issued steps always carry a
    non-empty resolvable `prompt_file`; OR the envelope explicitly
    declares `kind == "blocked"` with a non-empty `reason`.
  - WP07 (#843): Composed actions write paired `started`/`completed`
    records under `.kittify/events/profile-invocations/` with canonical
    outcomes from `{done, failed, abandoned}`.

This test does not call any private helper and does not monkeypatch
the dispatcher, executor, DRG resolver, or frozen-template loader.
Every CLI command is invoked via subprocess against the public CLI.

Composed mission pin: software-dev (per mission research R-001).
Charter synthesize uses --adapter fixture with `SPEC_KITTY_FIXTURE_AUTO_STUB=1`
because the default 'generated' adapter requires LLM-authored YAML
that an unattended automated test cannot provide.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tests.e2e.conftest import (
    REPO_ROOT,
    SourcePollutionBaseline,
    assert_no_source_pollution,
    capture_source_pollution_baseline,
    format_subprocess_failure,
)
from tests.test_isolation_helpers import get_source_version, get_venv_python


pytestmark = [pytest.mark.e2e, pytest.mark.slow]

# Type alias for the run_cli fixture's callable shape (tests/conftest.py).
RunCli = Callable[..., subprocess.CompletedProcess[str]]


# ---------------------------------------------------------------------------
# Strict full-stream JSON / success helpers
# ---------------------------------------------------------------------------


def _expect_success(
    *,
    command: list[str],
    cwd: Path,
    completed: subprocess.CompletedProcess[str],
    parse_json: bool = True,
) -> dict[str, Any] | None:
    """Assert subprocess exited 0 and parse stdout as a JSON dict.

    FR-008/FR-009: parsing uses ``json.loads(stdout)`` against the
    full stdout stream. WP05 guarantees `--json` paths emit exactly
    one JSON document on stdout; any trailing text is a regression.
    """
    if completed.returncode != 0:
        raise AssertionError(
            format_subprocess_failure(
                command=command, cwd=cwd, completed=completed,
            )
        )
    if not parse_json:
        return None
    stdout = completed.stdout
    # FR-009 strict full-stream parse — no first-object trick, no
    # trailing-data allow-list. WP05 ensures stdout is a single JSON
    # document; trailing whitespace is fine for `json.loads`, but any
    # non-whitespace tail will raise here.
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as err:
        raise AssertionError(
            "FR-009: --json output not parseable as a single JSON document.\n"
            f"{format_subprocess_failure(command=command, cwd=cwd, completed=completed)}\n"
            f"  parse error: {err}"
        ) from err
    if not isinstance(payload, dict):
        raise AssertionError(
            "FR-009: --json output did not parse as a JSON object.\n"
            f"{format_subprocess_failure(command=command, cwd=cwd, completed=completed)}\n"
            f"  parsed: {payload!r}"
        )
    return payload


def _is_truthy_state(value: Any) -> bool:
    """Treat common 'success' state-like values as success."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"success", "ok", "valid", "passed", "clean", "pass"}
    return False


def _assert_signals_success(payload: dict[str, Any], *, fr_id: str) -> None:
    """Assert payload signals success in some explicit field."""
    candidates: list[Any] = []
    for key in ("result", "status", "ok", "valid", "passed"):
        if key in payload:
            candidates.append(payload[key])
    summary = payload.get("summary")
    if isinstance(summary, dict):
        for key in ("result", "status", "ok", "valid", "passed"):
            if key in summary:
                candidates.append(summary[key])
    if not any(_is_truthy_state(c) for c in candidates):
        errors = payload.get("errors")
        if isinstance(errors, list) and len(errors) == 0:
            return
        raise AssertionError(
            f"{fr_id}: payload did not signal success.\n"
            f"  payload: {json.dumps(payload, indent=2, default=str)}"
        )


def _assert_no_error_state(payload: dict[str, Any], *, fr_id: str) -> None:
    """Assert payload does not declare an error state."""
    for key in ("error", "errors"):
        value = payload.get(key)
        if isinstance(value, list) and value:
            raise AssertionError(
                f"{fr_id}: payload reports {key}: {value!r}\n"
                f"  full payload: {json.dumps(payload, indent=2, default=str)}"
            )
        if isinstance(value, str) and value.strip():
            raise AssertionError(
                f"{fr_id}: payload reports {key}: {value!r}\n"
                f"  full payload: {json.dumps(payload, indent=2, default=str)}"
            )
    state = payload.get("state") or payload.get("status")
    if isinstance(state, str) and state.lower() in {"error", "failed", "broken"}:
        raise AssertionError(
            f"{fr_id}: payload state is {state!r}\n"
            f"  full payload: {json.dumps(payload, indent=2, default=str)}"
        )


# ---------------------------------------------------------------------------
# `next` envelope extractors (lock the live field names here)
# ---------------------------------------------------------------------------


def _extract_step_id(payload: dict[str, Any]) -> str:
    """Return the step/action id from a `next --json` envelope."""
    for key in ("step_id", "action", "action_id", "preview_step", "id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    raise AssertionError(
        "FR-014/FR-016: could not extract step/action id from `next --json` envelope.\n"
        f"  payload: {json.dumps(payload, indent=2, default=str)}"
    )


# ---------------------------------------------------------------------------
# Subprocess helper that injects extra env (for SPEC_KITTY_FIXTURE_AUTO_STUB)
# ---------------------------------------------------------------------------


def _run_cli_with_env(
    project_path: Path, *args: str, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the CLI in a subprocess with an isolated env plus extras.

    Mirrors the run_cli fixture (PYTHONPATH -> source `src/`,
    SPEC_KITTY_TEMPLATE_ROOT -> REPO_ROOT, SPEC_KITTY_TEST_MODE=1) but
    accepts additional env-var overrides via `extra_env`. Required for
    WP03's `SPEC_KITTY_FIXTURE_AUTO_STUB=1` which the default
    `run_cli` fixture cannot pass through.
    """
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    env["SPEC_KITTY_CLI_VERSION"] = get_source_version()
    env["SPEC_KITTY_TEMPLATE_ROOT"] = str(REPO_ROOT)
    env["SPEC_KITTY_TEST_MODE"] = "1"
    if extra_env:
        env.update(extra_env)
    command = [str(get_venv_python()), "-m", "specify_cli.__init__", *args]
    return subprocess.run(
        command,
        cwd=str(project_path),
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


# ---------------------------------------------------------------------------
# Mission-seed strings (kept inline; do NOT factor into conftest)
# ---------------------------------------------------------------------------

_SEED_SPEC_MD = """# Golden-Path Demo Spec

## Functional Requirements

| ID | Requirement | Acceptance Criteria | Status |
| --- | --- | --- | --- |
| FR-001 | Deliver WP01 hello-world implementation. | WP01 maps to FR-001 and finalizes successfully. | proposed |

## Non-Functional Requirements

| ID | Requirement | Measurable Threshold | Status |
| --- | --- | --- | --- |
| NFR-001 | Finalization remains repeatable. | Running finalize twice yields stable output. | proposed |

## Constraints

| ID | Constraint | Rationale | Status |
| --- | --- | --- | --- |
| C-001 | Keep artifacts under kitty-specs. | Preserve planning workflow conventions. | fixed |
"""


_SEED_TASKS_MD = """# Work Packages

## Work Package WP01: Hello World
**Dependencies**: None
**Requirement Refs**: FR-001, NFR-001, C-001

### Included Subtasks
- T001 Create hello module

---
"""


_SEED_WP01_MD = """---
work_package_id: "WP01"
title: "Hello World"
subtasks:
  - "T001"
phase: "Phase 1"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - at: "2026-04-27T00:00:00Z"
    actor: "system"
    action: "Generated via golden-path E2E"
---

# Work Package Prompt: WP01 -- Hello World

Create a hello module.
"""


# ---------------------------------------------------------------------------
# Phase helpers
# ---------------------------------------------------------------------------


def _assert_init_stamped_schema(project: Path) -> None:
    """FR-001/FR-008 (WP02 lock): fresh init must stamp schema fields.

    Reads `.kittify/metadata.yaml` after `spec-kitty init` ran in the
    fresh-project fixture. Asserts that WP02's product fix wrote both
    `spec_kitty.schema_version` and `spec_kitty.schema_capabilities`.
    No fallback: if either field is missing, this is a WP02 regression.
    """
    import yaml  # type: ignore[import-untyped]

    metadata_path = project / ".kittify" / "metadata.yaml"
    assert metadata_path.is_file(), (
        f"FR-001/WP02: .kittify/metadata.yaml missing after spec-kitty init "
        f"({metadata_path})"
    )
    with open(metadata_path, encoding="utf-8") as fh:
        metadata = yaml.safe_load(fh) or {}
    spec_kitty_section = metadata.get("spec_kitty")
    assert isinstance(spec_kitty_section, dict), (
        f"FR-001/WP02: metadata.yaml has no `spec_kitty` mapping. "
        f"Got: {metadata!r}"
    )
    schema_version = spec_kitty_section.get("schema_version")
    # schema_version is an int (e.g. 3) per migration/schema_version.py.
    assert isinstance(schema_version, int) and schema_version > 0, (
        "FR-001/WP02: `spec_kitty.schema_version` must be a positive integer "
        f"after init. Got: {schema_version!r}\n"
        f"  full spec_kitty section: {spec_kitty_section!r}"
    )
    schema_capabilities = spec_kitty_section.get("schema_capabilities")
    assert schema_capabilities, (
        "FR-001/WP02: `spec_kitty.schema_capabilities` must be present and "
        f"non-empty after init. Got: {schema_capabilities!r}\n"
        f"  full spec_kitty section: {spec_kitty_section!r}"
    )


def _run_charter_flow(project: Path, run_cli: RunCli) -> None:
    """Drive interview -> generate -> bundle validate -> synthesize -> status -> lint."""
    # FR-001 / WP02 lock: fresh init populated schema metadata.
    _assert_init_stamped_schema(project)

    # FR-004 Step 1: charter interview (minimal, defaults).
    cmd = ["charter", "interview", "--profile", "minimal", "--defaults", "--json"]
    _expect_success(command=cmd, cwd=project, completed=run_cli(project, *cmd))

    # FR-004 Step 2: charter generate (from interview).
    cmd = ["charter", "generate", "--from-interview", "--json"]
    payload = _expect_success(
        command=cmd, cwd=project, completed=run_cli(project, *cmd)
    )
    # FR-009: charter.md exists.
    assert (project / ".kittify" / "charter" / "charter.md").is_file(), (
        "FR-009: .kittify/charter/charter.md missing after charter generate"
    )

    # FR-002 / WP04 lock: charter generate --json emits a `next_step`
    # tracking instruction. charter.md is freshly generated and not yet
    # tracked, so the action MUST be `git_add` with non-empty paths.
    assert payload is not None
    next_step = payload.get("next_step")
    assert isinstance(next_step, dict), (
        f"FR-002/WP04: `charter generate --json` must include a `next_step` "
        f"object. Got: {next_step!r}\n"
        f"  payload keys: {sorted(payload.keys())!r}"
    )
    next_action = next_step.get("action")
    assert next_action in {"git_add", "no_action_required"}, (
        f"FR-002/WP04: `next_step.action` must be `git_add` or "
        f"`no_action_required`. Got: {next_action!r}\n"
        f"  next_step: {next_step!r}"
    )
    if next_action == "git_add":
        paths = next_step.get("paths")
        assert isinstance(paths, list) and paths, (
            f"FR-002/WP04: `next_step.action == 'git_add'` requires a "
            f"non-empty `paths` list. Got: {paths!r}\n"
            f"  next_step: {next_step!r}"
        )
        for path_str in paths:
            assert isinstance(path_str, str) and path_str, (
                f"FR-002/WP04: every entry in `next_step.paths` must be a "
                f"non-empty string. Got: {path_str!r}"
            )

    # `charter bundle validate` requires charter.md to be a git-tracked
    # file. Honor WP04's `git_add` instruction explicitly: stage + commit
    # exactly the paths the envelope listed.
    if next_action == "git_add":
        paths_to_add = list(next_step["paths"])
        subprocess.run(
            ["git", "add", *paths_to_add],
            cwd=project, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add generated charter.md (per next_step.git_add)"],
            cwd=project, check=True, capture_output=True,
        )

    # FR-010: bundle validate.
    cmd = ["charter", "bundle", "validate", "--json"]
    payload = _expect_success(
        command=cmd, cwd=project, completed=run_cli(project, *cmd)
    )
    assert payload is not None
    _assert_signals_success(payload, fr_id="FR-010")

    # FR-011 / FR-012 / WP03 lock: real synthesize must succeed when
    # `SPEC_KITTY_FIXTURE_AUTO_STUB=1` is set in env, writing canonical
    # doctrine artifacts under `.kittify/doctrine/`. No `--dry-run-evidence`
    # fallback. No hand-seeded doctrine tree.
    doctrine_path = project / ".kittify" / "doctrine"
    auto_stub_env = {"SPEC_KITTY_FIXTURE_AUTO_STUB": "1"}

    # FR-004 step: real `charter synthesize --adapter fixture --dry-run --json`.
    cmd = ["charter", "synthesize", "--adapter", "fixture", "--dry-run", "--json"]
    completed = _run_cli_with_env(project, *cmd, extra_env=auto_stub_env)
    _expect_success(command=cmd, cwd=project, completed=completed)

    # FR-004 step: real `charter synthesize --adapter fixture --json`.
    cmd = ["charter", "synthesize", "--adapter", "fixture", "--json"]
    completed = _run_cli_with_env(project, *cmd, extra_env=auto_stub_env)
    _expect_success(command=cmd, cwd=project, completed=completed)

    # FR-012/WP03: doctrine tree must exist and contain canonical artifacts.
    assert doctrine_path.is_dir(), (
        f"FR-012/WP03: .kittify/doctrine/ missing after `charter synthesize "
        f"--adapter fixture --json`. WP03's stub path was supposed to write "
        f"canonical artifacts when SPEC_KITTY_FIXTURE_AUTO_STUB=1.\n"
        f"  expected at: {doctrine_path}"
    )
    doctrine_files = sorted(p.name for p in doctrine_path.rglob("*") if p.is_file())
    assert doctrine_files, (
        f"FR-012/WP03: .kittify/doctrine/ exists but contains no files. "
        f"Expected canonical artifacts written by WP03's stub path.\n"
        f"  scanned: {doctrine_path}"
    )

    # FR-013: status reports non-error state.
    cmd = ["charter", "status", "--json"]
    payload = _expect_success(
        command=cmd, cwd=project, completed=run_cli(project, *cmd)
    )
    assert payload is not None
    _assert_no_error_state(payload, fr_id="FR-013 status")

    # FR-013: lint runs successfully or returns documented warning-only status.
    cmd = ["charter", "lint", "--json"]
    completed = run_cli(project, *cmd)
    if completed.returncode == 0:
        payload = _expect_success(command=cmd, cwd=project, completed=completed)
        assert payload is not None
        _assert_no_error_state(payload, fr_id="FR-013 lint")
    else:
        raise AssertionError(
            "FR-013: charter lint returned non-zero. If this is a documented "
            "warning-only exit, widen the assertion; otherwise surface as a "
            "product finding per spec FR-021.\n"
            f"{format_subprocess_failure(command=cmd, cwd=project, completed=completed)}"
        )


def _scaffold_minimal_mission(
    project: Path, run_cli: RunCli
) -> tuple[str, Path]:
    """Create + setup-plan + seed + finalize-tasks. Returns (mission_handle, feature_dir)."""
    mission_slug_human = "golden-path-demo"

    cmd = [
        "agent", "mission", "create", mission_slug_human,
        "--mission-type", "software-dev",
        "--friendly-name", "Golden Path Demo",
        "--purpose-tldr", "Minimal demo mission for the golden-path E2E.",
        "--purpose-context", (
            "This mission exists solely to give the golden-path E2E test a "
            "concrete software-dev mission to advance through `spec-kitty next`. "
            "It is created and discarded inside the test's temp project."
        ),
        "--branch-strategy", "already-confirmed",
        "--json",
    ]
    payload = _expect_success(
        command=cmd, cwd=project, completed=run_cli(project, *cmd)
    )
    assert payload is not None
    assert payload.get("result") == "success", payload
    mission_handle = payload["mission_slug"]
    feature_dir = Path(payload["feature_dir"])
    assert feature_dir.is_dir(), (
        f"feature_dir not created: {feature_dir}\n  payload: {payload!r}"
    )

    # setup-plan
    cmd = [
        "agent", "mission", "setup-plan",
        "--mission", mission_handle,
        "--json",
    ]
    _expect_success(command=cmd, cwd=project, completed=run_cli(project, *cmd))
    assert (feature_dir / "plan.md").is_file(), (
        "setup-plan did not produce plan.md"
    )

    # Seed minimal mission content.
    (feature_dir / "spec.md").write_text(_SEED_SPEC_MD, encoding="utf-8")
    (feature_dir / "tasks.md").write_text(_SEED_TASKS_MD, encoding="utf-8")
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    (tasks_dir / "WP01-hello-world.md").write_text(_SEED_WP01_MD, encoding="utf-8")

    # Patch meta.json: preserve mission_id minted at create time.
    meta_path = feature_dir / "meta.json"
    meta_content: dict[str, Any] = json.loads(meta_path.read_text(encoding="utf-8"))
    meta_content.update(
        {
            "mission_number": None,
            "mission_slug": mission_handle,
            "mission_type": "software-dev",
            "created_at": "2026-04-27T00:00:00Z",
            "vcs": "git",
        }
    )
    meta_path.write_text(json.dumps(meta_content, indent=2), encoding="utf-8")

    subprocess.run(
        ["git", "add", "."], cwd=project, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Seed minimal golden-path demo mission"],
        cwd=project, check=True, capture_output=True,
    )

    # finalize-tasks
    cmd = [
        "agent", "mission", "finalize-tasks",
        "--mission", mission_handle,
        "--json",
    ]
    _expect_success(command=cmd, cwd=project, completed=run_cli(project, *cmd))
    wp01_text = (tasks_dir / "WP01-hello-world.md").read_text(encoding="utf-8")
    assert "dependencies" in wp01_text.lower(), (
        "finalize-tasks did not write the dependencies field into WP01 frontmatter"
    )

    return mission_handle, feature_dir


def _assert_step_or_blocked(
    payload: dict[str, Any], *, fr_id: str, allow_query: bool = False
) -> tuple[str, str | None]:
    """Strict FR-006/FR-011/WP06 assertion on a `next --json` envelope.

    Returns ``(issued_step_id_or_preview, prompt_file_or_none)``.

    Three accepted envelope shapes:
      * ``kind == "step"`` (issued step): MUST carry a non-empty
        resolvable ``prompt_file``. No conditional acceptance.
      * ``kind == "blocked"`` (explicit blocked status): MUST carry a
        non-empty ``reason``.
      * ``kind == "query"`` (preview only, NOT an issued step): only
        accepted when ``allow_query=True``. Returns ``preview_step``
        as the step id and ``None`` as prompt_file. WP06's prompt_file
        contract applies only to issued steps (``kind == "step"``);
        query mode's null prompt_file is documented and acceptable.
    """
    kind = payload.get("kind")
    if kind == "blocked":
        reason = payload.get("reason")
        assert isinstance(reason, str) and reason.strip(), (
            f"{fr_id}/WP06: `kind == 'blocked'` requires a non-empty "
            f"`reason`. Got: {reason!r}\n"
            f"  payload: {json.dumps(payload, indent=2, default=str)}"
        )
        for key in ("step_id", "action", "preview_step"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value, None
        return "", None

    if kind == "query":
        if not allow_query:
            raise AssertionError(
                f"{fr_id}/WP06: unexpected `kind == 'query'` envelope where "
                f"an issued step or blocked decision was expected.\n"
                f"  payload: {json.dumps(payload, indent=2, default=str)}"
            )
        # Query mode: preview only. prompt_file is null by contract.
        preview = payload.get("preview_step")
        if isinstance(preview, str) and preview:
            return preview, None
        return "", None

    # Default: kind == "step" (or legacy advance-mode envelopes that
    # populate step_id/action). FR-006/FR-011/WP06: must carry a
    # non-empty resolvable prompt_file. No conditional acceptance.
    issued_step_id = _extract_step_id(payload)
    prompt_file = payload.get("prompt_file")
    assert isinstance(prompt_file, str) and prompt_file, (
        f"{fr_id}/WP06: issued step `{issued_step_id}` lacks a non-empty "
        f"`prompt_file`. Got: {prompt_file!r}\n"
        f"  payload: {json.dumps(payload, indent=2, default=str)}"
    )
    assert os.path.exists(prompt_file), (
        f"{fr_id}/WP06: issued step `{issued_step_id}` carries `prompt_file` "
        f"that does not exist on disk. Got: {prompt_file!r}\n"
        f"  payload: {json.dumps(payload, indent=2, default=str)}"
    )
    return issued_step_id, prompt_file


def _run_next_and_assert_lifecycle(
    project: Path, run_cli: RunCli, mission_handle: str
) -> None:
    """T037/T038: issue + advance via `next` + STRICT lifecycle assertions.

    No early-return when the profile-invocations dir is absent.
    No conditional prompt-file acceptance.

    The software-dev mission's first state ``discovery`` is a legacy
    pre-action gate (not in ``_COMPOSED_ACTIONS_BY_MISSION``). We advance
    discovery -> specify first, then drive specify (a composed action)
    so WP07's profile-invocation lifecycle records get written.
    """
    issued_actions: set[str] = set()

    # Query mode: preview the first issued step (FR-014). Prompt_file is
    # null by contract in query mode.
    cmd = ["next", "--agent", "test-agent", "--mission", mission_handle, "--json"]
    payload = _expect_success(
        command=cmd, cwd=project, completed=run_cli(project, *cmd)
    )
    assert payload is not None
    _preview_step_id, _query_prompt = _assert_step_or_blocked(
        payload, fr_id="FR-014", allow_query=True
    )

    # Advance discovery -> specify. This is a non-composed transition
    # for the software-dev mission; the composition path engages once
    # `specify` is the active step.
    cmd_advance = [
        "next", "--agent", "test-agent",
        "--mission", mission_handle,
        "--result", "success",
        "--json",
    ]
    payload = _expect_success(
        command=cmd_advance, cwd=project, completed=run_cli(project, *cmd_advance)
    )
    assert payload is not None
    advance1_step_id, _advance1_prompt = _assert_step_or_blocked(
        payload, fr_id="FR-015"
    )
    if advance1_step_id:
        issued_actions.add(advance1_step_id)

    # Second advance: drives the composed `specify` action through
    # StepContractExecutor, which (per WP07) writes paired
    # started+completed records under .kittify/events/profile-invocations/.
    payload = _expect_success(
        command=cmd_advance, cwd=project, completed=run_cli(project, *cmd_advance)
    )
    assert payload is not None
    # The second advance MAY return blocked (e.g. composition guard
    # failure) or step (next composed action issued); either is
    # acceptable as long as WP07 wrote the lifecycle records for the
    # action that just completed.
    advance2_step_id, _advance2_prompt = _assert_step_or_blocked(
        payload, fr_id="FR-015"
    )
    if advance2_step_id:
        issued_actions.add(advance2_step_id)

    # Third advance: report success on the issued composed `specify`
    # (removed debug dumps — the payload-shape print was diagnostic only).
    # action. This is when the composition path closes the trail with
    # a `completed` record (paired with the `started` written at issue
    # time of advance2).
    payload = _expect_success(
        command=cmd_advance, cwd=project, completed=run_cli(project, *cmd_advance)
    )
    assert payload is not None
    advance3_step_id, _advance3_prompt = _assert_step_or_blocked(
        payload, fr_id="FR-015"
    )
    if advance3_step_id:
        issued_actions.add(advance3_step_id)

    # FR-007/FR-010/FR-016/WP07 lock: profile-invocations directory MUST
    # exist with paired started/completed records, canonical outcome, and
    # action identity match. No early-return on missing directory.
    pi_dir = project / ".kittify" / "events" / "profile-invocations"
    assert pi_dir.is_dir(), (
        f"FR-007/FR-010/WP07: `.kittify/events/profile-invocations/` is "
        f"missing after `next --result success`. Composed actions issued by "
        f"next must write paired started/completed records.\n"
        f"  expected at: {pi_dir}"
    )

    started_records: list[dict[str, Any]] = []
    completed_records: list[dict[str, Any]] = []
    jsonl_files = sorted(pi_dir.glob("*.jsonl"))
    assert jsonl_files, (
        f"FR-007/WP07: `.kittify/events/profile-invocations/` exists but is "
        f"empty. Expected at least one paired started/completed record per "
        f"composed action issued by `next`.\n"
        f"  scanned: {pi_dir}"
    )
    for jsonl_file in jsonl_files:
        for line in jsonl_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record: dict[str, Any] = json.loads(line)
            event_value = record.get("event")
            if event_value == "started":
                started_records.append(record)
            elif event_value == "completed":
                completed_records.append(record)
            else:
                raise AssertionError(
                    f"FR-007/WP07: unexpected `event` discriminator in "
                    f"profile-invocation record: {event_value!r}. Expected "
                    f"`started` or `completed`.\n"
                    f"  record: {record!r}\n"
                    f"  source file: {jsonl_file}"
                )

    # Paired records: every started has a matching completed.
    assert len(started_records) >= 1, (
        f"FR-007/WP07: no `started` records found under {pi_dir}. "
        f"Composed actions issued by `next` must write a started record."
    )
    assert len(started_records) == len(completed_records), (
        f"FR-007/WP07: lifecycle records not paired: "
        f"started={len(started_records)} completed={len(completed_records)}.\n"
        f"  scanned: {[str(p) for p in jsonl_files]}"
    )

    # Action identity: every started record carries a non-empty `action`
    # token. Per writer.py the `completed` record intentionally carries
    # action="" (the action is on the started record, paired by
    # invocation_id). FR-007/WP07.
    canonical_outcomes = {"done", "failed", "abandoned"}
    started_actions: set[str] = set()
    for record in started_records:
        action = record.get("action")
        assert isinstance(action, str) and action, (
            f"FR-007/WP07: started record missing non-empty `action` field. "
            f"Got: {action!r}\n  record: {record!r}"
        )
        invocation_id = record.get("invocation_id")
        assert isinstance(invocation_id, str) and invocation_id, (
            f"FR-007/WP07: started record missing `invocation_id`.\n"
            f"  record: {record!r}"
        )
        started_actions.add(action)

    # FR-007/WP07: every completed record carries an invocation_id that
    # matches a started record AND a canonical outcome.
    started_ids = {r.get("invocation_id") for r in started_records}
    for record in completed_records:
        invocation_id = record.get("invocation_id")
        assert invocation_id in started_ids, (
            f"FR-007/WP07: completed record references unknown "
            f"invocation_id {invocation_id!r}. Started ids: {started_ids!r}\n"
            f"  record: {record!r}"
        )
        outcome = record.get("outcome")
        assert outcome in canonical_outcomes, (
            f"FR-007/WP07: `completed` record `outcome` must be in "
            f"{canonical_outcomes!r}. Got: {outcome!r}\n"
            f"  record: {record!r}"
        )

    # Cross-check: at least one started record's action matches an
    # issued action (a `next --result success` step we drove). The
    # composition layer may translate step_ids to canonical action
    # tokens (e.g. role-default mapping) so we tolerate the started
    # set being a superset; we just require non-empty intersection
    # whenever issued_actions is non-empty.
    if issued_actions and not (started_actions & issued_actions):
        raise AssertionError(
            f"FR-007/WP07: no started record's `action` matches any issued "
            f"action.\n"
            f"  issued_actions: {sorted(issued_actions)!r}\n"
            f"  started_actions: {sorted(started_actions)!r}"
        )


def _run_retrospect(project: Path, run_cli: RunCli) -> None:
    """retrospect summary."""
    cmd = ["retrospect", "summary", "--project", str(project), "--json"]
    payload = _expect_success(
        command=cmd, cwd=project, completed=run_cli(project, *cmd)
    )
    assert isinstance(payload, dict), (
        f"FR-007: retrospect summary --json did not return a dict envelope:\n"
        f"  got: {payload!r}"
    )


# ---------------------------------------------------------------------------
# Single end-to-end test
# ---------------------------------------------------------------------------


def _run_golden_path(project: Path, run_cli: RunCli) -> None:
    """Body of the golden path. Split into phase helpers for readability."""
    _run_charter_flow(project, run_cli)
    mission_handle, _feature_dir = _scaffold_minimal_mission(project, run_cli)
    _run_next_and_assert_lifecycle(project, run_cli, mission_handle)
    _run_retrospect(project, run_cli)


def test_charter_epic_golden_path(
    fresh_e2e_project: Path,
    run_cli: RunCli,
) -> None:
    """Strict regression gate for the Charter epic operator path.

    Covers spec FR-001..FR-016 strictly. Pollution guard (FR-017,
    FR-018) runs in the finally block so it fires even when an earlier
    phase fails.
    """
    baseline: SourcePollutionBaseline = capture_source_pollution_baseline(REPO_ROOT)
    try:
        _run_golden_path(fresh_e2e_project, run_cli)
    finally:
        # Pollution guard runs even when an earlier assertion fails.
        assert_no_source_pollution(baseline, REPO_ROOT)
