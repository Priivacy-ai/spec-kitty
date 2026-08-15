"""Structural guard for the regen-assets workflow (mission #3447, WP04).

RED-first: fails on the planning base because the workflow does not exist. Pins
the trust-tier invariants that make the regen automation fork-safe (research D2):

- every pull request runs a CHECK-ONLY job (no push, no secrets) — a fork PR's
  read-only token cannot commit back, so it must only fail-with-remediation;
- auto-commit only fires on same-repo push / workflow_dispatch, canonical-repo
  guarded;
- the privileged PAT-push path is gated behind the `regen` label AND an
  enable flag (ships DISABLED pending the NFR-003 security sign-off) AND only
  ever runs under pull_request_target — never under the untrusted pull_request
  event.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architectural

_WORKFLOW = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "regen-assets.yml"
)


def _load() -> dict[str, Any]:
    return yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))


def _on_section(data: dict[str, Any]) -> dict[str, Any]:
    # PyYAML parses the bare ``on:`` key as the boolean True (YAML 1.1).
    section = data.get("on", data.get(True))
    assert isinstance(section, dict), "regen-assets must declare a mapping `on:`"
    return section


def _job(data: dict[str, Any], name: str) -> dict[str, Any]:
    job = data["jobs"][name]
    assert isinstance(job, dict)
    return job


def _job_text(job: dict[str, Any]) -> str:
    """All ``run:`` script text of a job, joined."""
    return "\n".join(
        str(step.get("run", ""))
        for step in job.get("steps", [])
        if isinstance(step, dict)
    )


def test_regen_assets_workflow_exists_and_parses() -> None:
    assert _WORKFLOW.exists(), "regen-assets.yml is missing"
    data = _load()
    assert set(data["jobs"]) >= {"check", "auto-commit", "label-pat-push"}


def test_every_pull_request_runs_check_only() -> None:
    """The universal gate: `pull_request` triggers a check-only job that runs
    `regen --check`, never pushes, and needs no secrets (fork-safe)."""
    data = _load()
    assert "pull_request" in _on_section(data)
    check = _job(data, "check")
    assert "github.event_name == 'pull_request'" in str(check.get("if", ""))
    text = _job_text(check)
    assert "regen --check" in text
    # Fork-safe: no push, no token/secret anywhere in the check job.
    assert "git push" not in text
    assert "secrets." not in yaml.safe_dump(check)


def test_auto_commit_is_same_repo_and_canonical_guarded() -> None:
    """Auto-commit only on same-repo push / dispatch, canonical-repo guarded."""
    data = _load()
    auto = _job(data, "auto-commit")
    guard = str(auto.get("if", ""))
    assert "github.event_name == 'push'" in guard
    assert "workflow_dispatch" in guard
    assert "github.repository == 'Priivacy-ai/spec-kitty'" in guard
    # It is the only job that requests write and pushes.
    assert auto.get("permissions", {}).get("contents") == "write"
    assert "git push" in _job_text(auto)


def test_pat_push_ships_disabled_behind_label_and_enable_flag() -> None:
    """The privileged fork-push path is gated on the label AND an enable flag,
    so it ships DISABLED until the NFR-003 sign-off, and only ever runs under
    pull_request_target (never the untrusted pull_request event)."""
    data = _load()
    assert "pull_request_target" in _on_section(data)
    pat = _job(data, "label-pat-push")
    guard = str(pat.get("if", ""))
    assert "github.event_name == 'pull_request_target'" in guard
    assert "github.event.label.name == 'regen'" in guard
    # Disabled-by-default: an opt-in repo variable must be true to run.
    assert "vars.REGEN_PAT_PUSH_ENABLED == 'true'" in guard
    assert "github.repository == 'Priivacy-ai/spec-kitty'" in guard
    # It must NOT be reachable via the untrusted pull_request event.
    assert "pull_request'" not in guard.replace("pull_request_target'", "")


def test_pat_push_uses_trusted_base_tooling_over_pr_data() -> None:
    """pull_request_target safety: base-repo tooling is checked out from the
    base ref and runs against the PR's data — PR-supplied code is not executed
    as the tool."""
    data = _load()
    pat = _job(data, "label-pat-push")
    dumped = yaml.safe_dump(pat)
    # Base tooling from the base ref; PR head checked out only as data ('pr').
    assert "github.event.pull_request.base.ref" in dumped
    assert "path: tooling" in dumped
    assert "path: pr" in dumped
    # The regen step runs the BASE tooling (../tooling) against the PR checkout,
    # isolated from any attacker-controlled uv config in the pr/ cwd.
    text = _job_text(pat)
    assert "--project ../tooling" in text and "spec-kitty regen" in text
    assert "--no-sync" in text and "--isolated" in text
    # REGEN_PAT must not be persisted into pr/.git/config.
    assert "persist-credentials: false" in yaml.safe_dump(pat)


def test_privileged_pushes_do_not_interpolate_refs_into_run_scripts() -> None:
    """Security F1 (review): a fork-controlled ref must never be interpolated
    into a ``run:`` script (command-injection sink) — refs are passed via
    ``env:`` and referenced as ``"$VAR"`` instead. Guards both privileged/write
    jobs against reintroduction."""
    data = _load()
    for job_name in ("label-pat-push", "auto-commit"):
        text = _job_text(_job(data, job_name))
        assert "${{ github.event.pull_request" not in text, (
            f"{job_name}: run: scripts must not interpolate PR-controlled refs; "
            'pass them via env: and reference "$VAR"'
        )
        assert "${{ github.ref_name }}" not in text, (
            f"{job_name}: pass github.ref_name via env:, not inline in run:"
        )
