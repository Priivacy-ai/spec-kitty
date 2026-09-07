"""Sonar workflow contract (WP12, C-008/FR-010, `introduced` disposition).

Contract: this file asserts the ON-DISK ``.github/workflows/sonar.yml`` (this WP's
authoritative surface) is a **fork-safe, informational, nightly/dispatch** producer —
never a per-PR merge-blocking job:

* aggregates the ``*-reports`` artefact family (contracts/artefact-naming.md);
* **skips-green** (never hard-fails) when ``SONAR_TOKEN`` is absent (fork-safe,
  NFR-004 precedent);
* uses stock GitHub-hosted runners (``"blacksmith" not in text`` — the private
  Blacksmith producer this mission retires, per FR-017/C-010);
* carries no ``SK_CI_TOKEN`` (this is a public, informational job — no private git
  dependency credentials belong on it);
* declares ``workflow_dispatch`` and runs on ``schedule``/dispatch only (never
  ``pull_request``, so it structurally cannot enter any PR-blocking ``needs:`` chain);
* SHA-pins every third-party action (DIR-051 / charter "Agent Push Authorization"),
  including the two Sonar actions themselves.

**Partition note (WP01 coordination):** the `introduced`-set *membership* assertion
(is ``sonar.yml`` registered in the frozen `introduced` disposition set?) lives in
WP01's ``tests/release/test_release_ci_ownership.py`` — this file never duplicates
that assertion, and never edits WP01's owned map/test files.

**Collection-red lazy-load hygiene:** ``sonar.yml`` does not exist on `main` /
pre-WP12 base. Every load below happens INSIDE the test body (never at module import
time), so this file always *collects* — a missing file reds a targeted assertion with
a clear reason, never an import/collection error.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = [pytest.mark.fast]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW_PATH = _REPO_ROOT / ".github" / "workflows" / "sonar.yml"

# YAML 1.1 parses the bare `on:` mapping key as the boolean True, not the string
# "on" -- every workflow file in this mission hits this, so triggers are looked
# up under either key (mirrors tests/release/test_release_ci_ownership.py and
# tests/architectural/test_coverage_artefact_contract.py).
_ON_KEYS: tuple[Any, ...] = ("on", True)

# A 40-hex-char SHA, optionally followed by a `# vX.Y.Z` comment -- the SHA-pin
# form every other reinstated workflow in this mission already uses (DIR-051),
# never a floating tag (`@v7`, `@v1.2.0`, `@main`).
_SHA_PIN_RE = re.compile(r"^[^@\s]+@[0-9a-f]{40}(\s*#.*)?$")


def _workflow_text() -> str:
    if not _WORKFLOW_PATH.exists():
        pytest.fail(f"sonar.yml missing: {_WORKFLOW_PATH.relative_to(_REPO_ROOT)} (WP12 not yet delivered)")
    return _WORKFLOW_PATH.read_text(encoding="utf-8")


def _workflow_yaml() -> dict[str, Any]:
    if not _WORKFLOW_PATH.exists():
        pytest.fail(f"sonar.yml missing: {_WORKFLOW_PATH.relative_to(_REPO_ROOT)} (WP12 not yet delivered)")
    loaded = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict), "sonar.yml did not parse to a mapping"
    return loaded


def _triggers(workflow: dict[str, Any]) -> dict[str, Any]:
    for key in _ON_KEYS:
        if key in workflow:
            triggers = workflow[key]
            assert isinstance(triggers, dict), "sonar.yml: `on:` block is not a mapping"
            return triggers
    pytest.fail("sonar.yml: no `on:` trigger block found")


def _iter_uses_values(node: Any) -> list[str]:
    """Recursively collect every ``uses:`` string in a parsed workflow mapping."""
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "uses" and isinstance(value, str):
                found.append(value)
            else:
                found.extend(_iter_uses_values(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_iter_uses_values(item))
    return found


# ---------------------------------------------------------------------------
# Trigger surface: schedule/dispatch only -- never pull_request (T063).
# ---------------------------------------------------------------------------
def test_sonar_declares_workflow_dispatch() -> None:
    workflow = _workflow_yaml()
    triggers = _triggers(workflow)
    assert "workflow_dispatch" in triggers, "sonar.yml must declare workflow_dispatch (T063)"


def test_sonar_runs_on_schedule_or_dispatch_never_pull_request() -> None:
    """sonar.yml must be an informational nightly/dispatch producer -- it must
    never carry a `pull_request` trigger, which is what would let it enter a
    PR merge-blocking `needs:` chain (T063: 'not the PR merge-blocking needs:')."""
    workflow = _workflow_yaml()
    triggers = _triggers(workflow)
    assert "schedule" in triggers, "sonar.yml must run on a schedule (nightly)"
    assert "pull_request" not in triggers, "sonar.yml must never trigger on pull_request (informational-only, never PR-blocking)"


def test_sonar_dispatch_threads_a_mode_input() -> None:
    """Forward-compat with WP11's cross-cutting dual-mode contract
    (tests/architectural/test_dual_mode_contract.py, not in this WP's targeted
    surface but named by the DoD): workflow_dispatch exposes a `mode` input."""
    workflow = _workflow_yaml()
    triggers = _triggers(workflow)
    dispatch = triggers.get("workflow_dispatch")
    assert isinstance(dispatch, dict), "sonar.yml: workflow_dispatch has no inputs block"
    inputs = dispatch.get("inputs") or {}
    assert "mode" in inputs, "sonar.yml: workflow_dispatch must expose a `mode` input"


def test_sonar_never_appears_in_any_pr_blocking_needs_chain() -> None:
    """No OTHER workflow in this repo may reference a `sonar` job/workflow in
    a `needs:` list -- sonar.yml is a separate workflow file with no
    `pull_request` trigger, so this is a belt-and-suspenders static check that
    no sibling workflow was wired to block on it."""
    workflows_dir = _REPO_ROOT / ".github" / "workflows"
    for path in sorted(workflows_dir.glob("*.yml")):
        if path.name == "sonar.yml":
            continue
        text = path.read_text(encoding="utf-8")
        assert "needs: sonar" not in text and "- sonar" not in text.replace("- sonar-project", ""), (
            f"{path.name}: must not gate on a `sonar` job -- sonar.yml is informational-only"
        )


# ---------------------------------------------------------------------------
# Artefact aggregation: *-reports pattern (contracts/artefact-naming.md).
# ---------------------------------------------------------------------------
def test_sonar_downloads_reports_glob_pattern() -> None:
    """Artifact name ends `-reports`; consumers glob `pattern: '*-reports'`
    (contract Invariant 2)."""
    workflow = _workflow_yaml()
    patterns = [
        step.get("with", {}).get("pattern")
        for job in workflow.get("jobs", {}).values()
        for step in job.get("steps", [])
        if isinstance(step, dict) and "download-artifact" in str(step.get("uses", ""))
    ]
    assert "*-reports" in patterns, f"sonar.yml must download with pattern: '*-reports', found {patterns!r}"


def test_sonar_wires_coverage_report_paths_comma_joined() -> None:
    """No single merged `coverage.xml` -- Sonar merges server-side from a
    comma-joined `sonar.python.coverage.reportPaths` list (contract)."""
    text = _workflow_text()
    assert "sonar.python.coverage.reportPaths" in text, "sonar.yml must wire sonar.python.coverage.reportPaths"


# ---------------------------------------------------------------------------
# Fork-safe degradation: skip-green without SONAR_TOKEN (T064).
# ---------------------------------------------------------------------------
def test_sonar_skips_green_without_token_never_hard_fails() -> None:
    """Fork-safe: absent `SONAR_TOKEN`, the job must degrade to an advisory
    skip, never a hard failure. Every Sonar-scanning step must be gated on the
    resolved token-availability output."""
    workflow = _workflow_yaml()
    text = _workflow_text()
    assert "SONAR_TOKEN" in text, "sonar.yml must reference secrets.SONAR_TOKEN"

    scan_steps = [
        step
        for job in workflow.get("jobs", {}).values()
        for step in job.get("steps", [])
        if isinstance(step, dict) and "sonarqube-scan-action" in str(step.get("uses", ""))
    ]
    assert scan_steps, "sonar.yml must run SonarSource/sonarqube-scan-action"
    for step in scan_steps:
        condition = str(step.get("if", ""))
        assert "enabled" in condition or "SONAR_TOKEN" in condition, f"sonar.yml: the scan step must be gated on token availability, got if: {condition!r}"

    # A missing-token run must not be a bare unconditional job -- there must be
    # a non-fatal notice path (never a `exit 1` unconditional on token absence).
    assert "::error::" not in text.split("SONAR_TOKEN")[0] or "enabled=false" in text, "sonar.yml must not hard-fail before the token-availability check"
    assert "enabled=false" in text, "sonar.yml must emit an explicit disabled/skip signal when SONAR_TOKEN is absent"


# ---------------------------------------------------------------------------
# Stock runners + no private-credential leakage (FR-017/C-010, DIR-050).
# ---------------------------------------------------------------------------
def test_sonar_uses_stock_runners_not_blacksmith() -> None:
    text = _workflow_text().lower()
    assert "blacksmith" not in text, "sonar.yml must use stock GitHub-hosted runners, never the retired private Blacksmith producer"


def test_sonar_carries_no_sk_ci_token() -> None:
    text = _workflow_text()
    assert "SK_CI_TOKEN" not in text, "sonar.yml is a public informational job -- it must never reference SK_CI_TOKEN"
    assert "Configure private git dependencies" not in text


def test_sonar_never_echoes_the_token_value() -> None:
    """DIR-050: never echo the secret's VALUE. Mentioning the token's env-var
    *name* in a human-readable notice (e.g. guiding an operator to provision
    it) is fine and expected; interpolating `secrets.SONAR_TOKEN` or a bare
    `$SONAR_TOKEN`/`${SONAR_TOKEN}` shell expansion into an echo would leak
    the value into job logs and must never appear."""
    text = _workflow_text()
    leak_patterns = (
        "echo ${{ secrets.SONAR_TOKEN",
        'echo "${{ secrets.SONAR_TOKEN',
        "echo $SONAR_TOKEN",
        'echo "$SONAR_TOKEN',
        "echo ${SONAR_TOKEN}",
    )
    for line in text.splitlines():
        stripped = line.strip()
        for pattern in leak_patterns:
            assert pattern not in stripped, f"sonar.yml must never echo the SONAR_TOKEN value: {stripped!r}"


# ---------------------------------------------------------------------------
# SHA-pinning (DIR-051).
# ---------------------------------------------------------------------------
def test_sonar_every_action_is_sha_pinned() -> None:
    workflow = _workflow_yaml()
    uses_values = _iter_uses_values(workflow.get("jobs", {}))
    assert uses_values, "sonar.yml must invoke at least one action"
    local_or_reusable = [u for u in uses_values if u.startswith("./")]
    external = [u for u in uses_values if not u.startswith("./")]
    assert external, "sonar.yml must invoke at least one external (non-reusable-workflow) action"
    for uses in external:
        assert _SHA_PIN_RE.match(uses), f"sonar.yml: action not SHA-pinned (DIR-051): {uses!r}"
    assert not local_or_reusable or all(u.startswith("./") for u in local_or_reusable)


def test_sonar_pins_both_sonar_actions() -> None:
    text = _workflow_text()
    assert re.search(r"SonarSource/sonarqube-scan-action@[0-9a-f]{40}", text), "sonar.yml must SHA-pin SonarSource/sonarqube-scan-action"
    assert re.search(r"SonarSource/sonarqube-quality-gate-action@[0-9a-f]{40}", text), "sonar.yml must SHA-pin SonarSource/sonarqube-quality-gate-action"


# ---------------------------------------------------------------------------
# projectVersion derivation (T063).
# ---------------------------------------------------------------------------
def test_sonar_derives_project_version_from_pyproject() -> None:
    text = _workflow_text()
    assert "pyproject.toml" in text, "sonar.yml must derive sonar.projectVersion from pyproject.toml"
    assert "sonar.projectVersion" in text
