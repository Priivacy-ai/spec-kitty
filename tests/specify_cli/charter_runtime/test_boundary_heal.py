"""Non-destructive boundary heal that clears stale (WP04,
charter-synthesize-reconciliation-01KZJQN6).

The implement/next boundary reconciler (``_attempt_auto_refresh`` in
``preflight/runner.py``) invokes ``spec-kitty charter synthesize`` flagless
-- no ``--prune``, no ``--dry-run`` -- which is WP01/WP03's
``SynthesizeMode.preserve`` default: a plain run never drops backed content
and exits 0 for backed divergence. This module proves that at the boundary,
end to end against the REAL ``charter.synthesizer`` reconciliation seam (not
a hand-faked stand-in), and pins the companion self-clearing contract
(amendment #2): a successful heal re-stamps the synthesis manifest's
``bundle_content_hash`` (via ``rewrite_manifest``, called unconditionally by
``reconcile_synthesis``), so ``synthesized_drg`` recomputes to ``fresh`` on
its own and a second boundary call is not re-blocked.

Only the ``subprocess.run`` call for ``spec-kitty charter synthesize`` is
faked (no real CLI/subprocess is spawned, matching the existing
``charter_preflight``/``charter_runtime`` test convention) -- but the fake
invokes the real ``charter.synthesizer.orchestrator.synthesize()`` library
entry point in-process with a ``FixtureAdapter``, so the reconciliation,
manifest re-stamp, and freshness recompute this module asserts on are all
production code, not test doubles.

Covers:

* ``test_authoring_only_edit_heals_non_destructively_and_clears_stale``
  (T017/T018/T020): the core boundary-heal contract -- stale -> heal
  (flagless, no --prune/--dry-run) -> 0 nodes/edges lost -> fresh.
* ``test_second_invocation_after_heal_is_not_re_blocked`` (T018/T020): a
  second ``run_charter_preflight(auto_refresh=True)`` call after a
  successful heal is a true no-op -- no re-trigger loop.
* ``test_orphaned_backing_artifact_at_boundary_still_refuses`` /
  ``test_unparseable_overlay_at_boundary_still_refuses`` (post-tasks squad
  amendment #1): the "never silently drops content" guarantee is not a
  "never refuses" guarantee -- these two causes still surface an actionable
  ``blocked_reason``, never a silently-coerced ``passed=True``.
* ``test_references_parity_stub_hook_is_installed_and_invoked_after_a_successful_heal``
  / ``test_references_parity_stub_hook_is_a_true_noop`` (T019): the WP06
  extension point exists, is wired into a successful heal, and is inert.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from charter.synthesizer import FixtureAdapter, SynthesisRequest, SynthesisTarget, synthesize
from charter.synthesizer.reconcile import SynthesizeMode
from specify_cli.charter_runtime.freshness import compute_freshness
from specify_cli.charter_runtime.preflight import run_charter_preflight
from specify_cli.charter_runtime.preflight import runner as runner_module

pytestmark = [pytest.mark.git_repo]

from ..charter_preflight._fixtures import (
    init_git_repo,
    seed_bundle_files,
    seed_charter,
    seed_charter_yaml,
    write_metadata,
)

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_GIT_ENV = {
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "t@x",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "t@x",
    "PATH": "/usr/bin:/bin",
}

# tests/specify_cli/charter_runtime/test_boundary_heal.py -> tests/
_TESTS_ROOT = Path(__file__).resolve().parents[2]
_FIXTURE_ROOT = _TESTS_ROOT / "charter" / "fixtures" / "synthesizer"
_GRAPH_PATH_SUFFIX = Path(".kittify") / "doctrine" / "graph.yaml"


def _fixture_adapter() -> FixtureAdapter:
    return FixtureAdapter(fixture_root=_FIXTURE_ROOT)


def _interview_snapshot() -> dict[str, Any]:
    return {
        "mission_type": "software_dev",
        "language_scope": ["python"],
        "testing_philosophy": "test-driven development with high coverage",
        "neutrality_posture": "balanced",
        "selected_directives": ["DIRECTIVE_003"],
        "risk_appetite": "moderate",
    }


def _doctrine_snapshot() -> dict[str, Any]:
    return {
        "directives": {
            "DIRECTIVE_003": {
                "id": "DIRECTIVE_003",
                "title": "Decision Documentation",
                "body": "Document significant architectural decisions via ADRs.",
            }
        },
        "tactics": {},
        "styleguides": {},
    }


def _drg_snapshot() -> dict[str, Any]:
    return {
        "nodes": [{"urn": "directive:DIRECTIVE_003", "kind": "directive"}],
        "edges": [],
        "schema_version": "1",
    }


def _request(run_id: str) -> SynthesisRequest:
    """Same target + snapshots as ``tests/charter/synthesizer``'s ``_request``
    helper (kind=directive, slug=mission-type-scope-directive) so this module
    resolves to the SAME committed fixture file deterministically -- only
    ``run_id`` differs, which ``compute_inputs_hash`` does not key on
    (mirrors ``test_noop_resynthesis_is_byte_stable_for_graph_and_manifest``).
    """
    target = SynthesisTarget(
        kind="directive",
        slug="mission-type-scope-directive",
        title="Mission Type Scope Directive",
        artifact_id="PROJECT_001",
        source_section="mission_type",
    )
    return SynthesisRequest(
        target=target,
        interview_snapshot=_interview_snapshot(),
        doctrine_snapshot=_doctrine_snapshot(),
        drg_snapshot=_drg_snapshot(),
        run_id=run_id,
        adapter_hints={"language": "python"},
    )


def _load_graph(path: Path) -> dict[str, Any]:
    yaml = YAML(typ="safe")
    data = yaml.load(path.read_text(encoding="utf-8"))
    return dict(data) if data else {}


def _git_commit_all(repo: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=repo, check=True, env=_GIT_ENV)


def _git_status_porcelain(repo: Path) -> str:
    result = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, check=True
    )
    return result.stdout


def _seed_synthesized_and_gone_stale(tmp_path: Path) -> Path:
    """Build a real, committed-clean synthesized repo, then trip
    ``synthesized_drg`` stale via an authoring-only ``charter.yaml`` edit
    (also committed, so the tree is clean going into ``auto_refresh`` --
    FR-008's precondition). Returns the on-disk ``graph.yaml`` path.
    """
    init_git_repo(tmp_path)
    seed_charter_yaml(tmp_path)
    synthesize(_request("01AAAAAAAAAAAAAAAAAAAAAAAAA"), adapter=_fixture_adapter(), repo_root=tmp_path)
    _git_commit_all(tmp_path, "seed synthesized state")

    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"  # baseline sanity

    charter_yaml_path = tmp_path / ".kittify" / "charter" / "charter.yaml"
    charter_yaml_path.write_text(
        charter_yaml_path.read_text(encoding="utf-8") + "# authoring-only edit\n",
        encoding="utf-8",
    )
    _git_commit_all(tmp_path, "authoring-only charter.yaml edit")

    assert compute_freshness(tmp_path).synthesized_drg.state == "stale"  # sanity: trip confirmed
    assert _git_status_porcelain(tmp_path) == ""  # clean going into auto_refresh (FR-008)

    return tmp_path / _GRAPH_PATH_SUFFIX


def _make_heal_subprocess_fake(
    tmp_path: Path, seen_calls: list[list[str]]
) -> Any:
    """Fake ``subprocess.run`` that lets real ``git`` calls through and, for
    ``spec-kitty charter synthesize``, invokes the REAL library entry point
    in-process (``mode=SynthesizeMode.preserve`` -- exactly what the CLI
    selects for a flagless invocation) instead of hand-simulating its output.
    """
    real_run = subprocess.run

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if cmd[:1] == ["git"]:
            return real_run(cmd, **kwargs)
        seen_calls.append(list(cmd))
        if cmd[:3] == ["spec-kitty", "charter", "synthesize"]:
            assert "--prune" not in cmd, "boundary heal must never invoke --prune"
            assert "--dry-run" not in cmd, "boundary heal must never invoke --dry-run"
            synthesize(
                _request("01BBBBBBBBBBBBBBBBBBBBBBBBB"),
                adapter=_fixture_adapter(),
                repo_root=tmp_path,
                mode=SynthesizeMode.preserve,
            )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    return fake_run


# ---------------------------------------------------------------------------
# T017/T018/T020 -- core boundary-heal contract
# ---------------------------------------------------------------------------


def test_authoring_only_edit_heals_non_destructively_and_clears_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    graph_path = _seed_synthesized_and_gone_stale(tmp_path)
    graph_before = _load_graph(graph_path)
    nodes_before = len(graph_before.get("nodes", []))
    edges_before = len(graph_before.get("edges", []))
    assert nodes_before >= 1, "fixture setup expected real synthesized content to protect"

    seen_calls: list[list[str]] = []
    monkeypatch.setattr(subprocess, "run", _make_heal_subprocess_fake(tmp_path, seen_calls))

    result = run_charter_preflight(tmp_path, auto_refresh=True)

    assert result.auto_refresh_applied is True
    assert result.passed is True, f"blocked_reason={result.blocked_reason!r}"

    cmds = [" ".join(c) for c in seen_calls]
    assert any(c.startswith("spec-kitty charter synthesize") for c in cmds), cmds
    assert not any("--prune" in c for c in cmds), "heal must never invoke the prune/refuse path"
    assert not any("--dry-run" in c for c in cmds)

    graph_after = _load_graph(graph_path)
    assert len(graph_after.get("nodes", [])) == nodes_before, "heal lost node(s)"
    assert len(graph_after.get("edges", [])) == edges_before, "heal lost edge(s)"

    assert compute_freshness(tmp_path).synthesized_drg.state == "fresh"


def test_second_invocation_after_heal_is_not_re_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A repo that just healed must not re-trigger the refresh sequence."""
    _seed_synthesized_and_gone_stale(tmp_path)

    seen_calls: list[list[str]] = []
    monkeypatch.setattr(subprocess, "run", _make_heal_subprocess_fake(tmp_path, seen_calls))

    first = run_charter_preflight(tmp_path, auto_refresh=True)
    assert first.passed is True
    assert first.auto_refresh_applied is True
    calls_after_first_heal = len(seen_calls)
    assert calls_after_first_heal > 0

    second = run_charter_preflight(tmp_path, auto_refresh=True)

    assert second.passed is True
    assert second.auto_refresh_applied is False, (
        "a healed repo must not even attempt a second refresh (no re-trigger loop)"
    )
    drg = next(c for c in second.checks if c.name == "synthesized_drg")
    assert drg.state == "fresh"
    assert len(seen_calls) == calls_after_first_heal, "second invocation shelled out again"


# ---------------------------------------------------------------------------
# Post-tasks squad amendment #1 -- boundary-refuse honesty
# ---------------------------------------------------------------------------


def _seed_needs_refresh_repo(tmp_path: Path) -> None:
    """A committed-clean repo whose ``synthesized_drg`` is ``missing`` (no
    manifest/graph yet) -- ``auto_refresh`` will attempt a heal."""
    init_git_repo(tmp_path)
    charter_path, metadata_path = seed_charter(tmp_path)
    write_metadata(metadata_path, charter_path)
    seed_bundle_files(tmp_path)
    seed_charter_yaml(tmp_path)
    _git_commit_all(tmp_path, "seed")


def test_orphaned_backing_artifact_at_boundary_still_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-014: an orphan-refusal from ``charter synthesize`` (exit 1) must
    surface as an actionable ``blocked_reason`` -- the boundary never
    coerces this into ``passed=True`` just because the heal is otherwise
    non-destructive."""
    _seed_needs_refresh_repo(tmp_path)
    real_run = subprocess.run

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if cmd[:1] == ["git"]:
            return real_run(cmd, **kwargs)
        if cmd[:3] == ["spec-kitty", "charter", "synthesize"]:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,
                stdout="",
                stderr=(
                    "Refused: this run would drop orphaned content without --prune:\n"
                    "node directive:PROJECT_999 (backing artifact deleted)\n"
                ),
            )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_charter_preflight(tmp_path, auto_refresh=True)

    assert result.passed is False
    assert result.auto_refresh_applied is True
    assert result.blocked_reason is not None
    assert "orphan" in result.blocked_reason.lower()


def test_unparseable_overlay_at_boundary_still_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-007: an unparseable on-disk doctrine overlay (``DRGLoadError``)
    makes ``charter synthesize`` exit non-zero -- the boundary surfaces that
    as a refusal too, never a silently-coerced pass."""
    _seed_needs_refresh_repo(tmp_path)
    real_run = subprocess.run

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if cmd[:1] == ["git"]:
            return real_run(cmd, **kwargs)
        if cmd[:3] == ["spec-kitty", "charter", "synthesize"]:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,
                stdout="",
                stderr=(
                    "Refused: the on-disk doctrine overlay could not be parsed. "
                    "No write was made.\n"
                ),
            )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_charter_preflight(tmp_path, auto_refresh=True)

    assert result.passed is False
    assert result.auto_refresh_applied is True
    assert result.blocked_reason is not None
    assert "parsed" in result.blocked_reason.lower()


# ---------------------------------------------------------------------------
# T019 -- references-parity extension point (stub only; WP06 implements)
# ---------------------------------------------------------------------------


def test_references_parity_stub_hook_is_installed_and_invoked_after_a_successful_heal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_synthesized_and_gone_stale(tmp_path)

    seen_calls: list[list[str]] = []
    monkeypatch.setattr(subprocess, "run", _make_heal_subprocess_fake(tmp_path, seen_calls))

    hook_calls: list[tuple[Path, str]] = []
    original = runner_module.refresh_references_if_needed

    def spy(repo_root: Path, cause: str) -> None:
        hook_calls.append((repo_root, cause))
        original(repo_root, cause)

    monkeypatch.setattr(runner_module, "refresh_references_if_needed", spy)

    result = run_charter_preflight(tmp_path, auto_refresh=True)

    assert result.passed is True
    assert hook_calls == [(tmp_path, "synthesized_drg")]


def test_references_parity_stub_hook_is_a_true_noop(tmp_path: Path) -> None:
    """Calling the stub directly never raises and never touches the filesystem."""
    result = runner_module.refresh_references_if_needed(tmp_path, cause="synthesized_drg")
    assert result is None
    assert list(tmp_path.iterdir()) == []
