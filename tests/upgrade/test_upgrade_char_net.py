"""NFR-002 characterization net for the `spec-kitty upgrade` refactor.

Mission: upgrade-command-hardening-01M0N5N4 (WP02, T008-T010).

This module is the **golden behavior-preservation oracle** for the WP03/WP04
restructuring of ``src/specify_cli/cli/commands/upgrade.py`` into shared
seams (writer / commit-decision / consent / finalizer — see
``kitty-specs/upgrade-command-hardening-01M0N5N4/contracts/seam-contracts.md``,
contract C4). It freezes today's (pre-refactor) commit/outcome behavior on
the DEFAULT config path (``auto_commit`` unset/true, migrations pending, no
manual-review preservation) so WP03/WP04 can prove they did not change
observable behavior. **WP03/WP04 MUST keep this test green.**

It is a CALL-LEVEL oracle: rather than driving a real git repository through
``safe_commit``'s full protected-branch guard chain (HEAD-match assertion,
ref-exists check, staging-area backstop, etc. — a large fixture burden that
belongs to ``safe_commit``'s own test suite, not this net), it spies on the
seam boundaries — ``autocommit.safe_commit`` and
``autocommit.commit_touched_checkout`` — and asserts on what they were
*called with* and *how many times*. A regression that changes the commit
count, the message format, the churn-path set, or stops routing the
main-checkout commit through the shared ``commit_touched_checkout`` seam
will fail this test even though no real git history is inspected.

NFR-002 observables pinned (per spec.md's NFR-002 row):
  (a) a commit is created
  (b) exactly one commit
  (c) the commit-message format/text
  (d) the SET of churn paths committed (set-equality, not subset)
  (e) worktree commit behavior — pinned as: the main-checkout commit is
      performed via the SAME shared ``autocommit.commit_touched_checkout``
      seam that ``runner._upgrade_worktrees`` calls for each worktree
      post-refactor (contract C4). Driving an actual worktree upgrade is out
      of scope for this fast net (covered separately by contract C5); the
      call-level pin on the shared seam is the NFR-002-relevant observable.

Environment-derived values (commit SHAs, timestamps) are deliberately NOT
asserted byte-for-byte anywhere in this file — only structure/format is
checked for those. Everything asserted here (versions, message text, path
set, capability) is fully test-controlled, so exact-match assertions on
those are appropriate, not a bug-freeze.

Explicitly NOT pinned (by design): the #3392 divergence between the
JSON-output ``success`` variable (``result.success and not
surface_drift_failed``, upgrade.py's json branch) and the raw
``result.success`` check in ``_display_upgrade_results`` (the human-readable
branch) that decides whether to raise ``typer.Exit(1)``. That divergence is
the defect WP04 fixes. This net only drives the fully-successful path (no
mission-type-activation errors, no surface-drift failure), where both
formulas already agree — so it cannot accidentally freeze the buggy
divergence in place. Do not extend this file to assert exit codes on a
failure/drift-failure scenario; that belongs to WP04's own red-first tests.

WP03 T013 (#4032, mission upgrade-no-migrations-provisioning-fix-01M20NK8):
re-pinned onto a REAL ``spec-kitty init``-ed fixture (``_fixtures.py``'s
``build_initialized_project``), not the config-absent scaffold this file
used before. Two independent findings drove the re-pin:

1. The old config-absent scaffold (``.kittify/metadata.yaml`` only) made
   ``prepare_mission_type_activations`` observe ``write.before_bytes is
   None`` -- exactly the #4032 absent-authority shape WP02 now defers
   rather than applies. Keeping this fixture after WP02 would have silently
   flipped this NFR-002 oracle onto the SKIP path (``PreparedUpgradeRepairs.
   provisioning is None``, ``_finalizer_step_provision`` returns ``[]``
   without calling ``.apply()``) -- a regression this net exists to catch,
   not commit. FR-006/NFR-003 require this oracle to keep exercising the
   provisioning **apply** path.
2. Independently of authority state, the module-level ``_run_upgrade``
   helper here calls the undecorated ``upgrade()`` function directly, never
   through ``CliRunner``/Click -- every ``typer.Option(...)`` default is a
   live, always-truthy ``OptionInfo`` instance until Click resolves it, so
   an un-set ``plan_json`` always entered the unconditional ``if plan_json:
   raise typer.Exit(...)`` branch (``upgrade.py``) before this test's
   migration/commit flow ever ran -- confirmed pre-existing on the mission's
   pre-WP01 base commit (``804a6d7ece``) too, so it is orthogonal to the
   authority-presence fix and would have persisted even under the old
   fixture. ``_run_upgrade`` now pins ``plan_json=False`` explicitly.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from mission_runtime import CommitTarget

import specify_cli.cli.commands.upgrade as upgrade_cmd
from charter.activation.compiler import prepare_mission_type_activations
from specify_cli.core.commit_guard import GuardCapability
from specify_cli.upgrade import autocommit
from specify_cli.upgrade.migrations.base import MigrationResult
from specify_cli.upgrade.runner import UpgradeResult

from tests.upgrade._fixtures import build_initialized_project

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# Deliberately more than one path so set-equality (vs. subset) is a
# meaningful assertion below. Re-derived for the T013 real-init-ed fixture:
# both paths are genuinely written by a real `spec-kitty init`-ed project's
# upgrade run (the metadata version stamp, and -- since this net degrades
# `mission_type_activations` back out below to force a real apply -- the
# provisioning authority itself), unlike the old config-absent scaffold's
# arbitrary `.claude/commands/spec-kitty.tasks.md` literal.
EXPECTED_CHURN_PATHS = {
    ".kittify/metadata.yaml",
    ".kittify/config.yaml",
}


def _setup_upgrade_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A REAL ``spec-kitty init``-ed project (T013 -- config authority
    present), degraded to strip the ``mission_type_activations`` key that
    fresh ``init`` already seeds.

    This net's whole point is to prove the provisioning **apply** path (not
    merely a green run on an init-ed project, which a skip-path run could
    also produce with different churn -- WP03 T013 reviewer guidance): a
    project with the key already present would make
    ``_PreparedMissionTypeActivations.apply()`` a same-bytes no-op rewrite,
    which is not an affirmative witness. Stripping the key here reproduces
    the real-world PR #3246 scenario ``_provision_missing_mission_type_
    activations``'s own docstring describes (a project whose authority
    predates that provisioner) so ``apply()`` performs a genuine content
    change the test can observe.
    """
    project_path = build_initialized_project(tmp_path, monkeypatch)
    config_path = project_path / ".kittify" / "config.yaml"
    descriptor_before = prepare_mission_type_activations(project_path)
    assert descriptor_before.write.before_bytes is not None, "sanity: this must be a present-authority descriptor"
    config_text = config_path.read_text(encoding="utf-8")
    stripped_lines = []
    skipping = False
    for line in config_text.splitlines(keepends=True):
        if line.startswith("mission_type_activations:"):
            skipping = True
            continue
        if skipping and line.startswith(("-", " ")):
            continue
        skipping = False
        stripped_lines.append(line)
    config_path.write_text("".join(stripped_lines), encoding="utf-8")

    # Real `init` stamps the CURRENT CLI version into metadata.yaml; this
    # net's mocked `MigrationRegistry.get_applicable`/`MigrationRunner.upgrade`
    # (below) simulate an upgrade FROM "1.0.0a1" regardless of real metadata
    # content (`outcome.result.from_version`/`to_version` -- the commit
    # message's inputs -- are sourced from that mocked `UpgradeResult`, not a
    # metadata re-read), but the REAL, unmocked downgrade guard
    # (`validate_upgrade_target`) DOES read the real on-disk version before
    # migrations run at all -- so it must agree with the scenario's premise
    # or every real-init-ed project (already on the current, newer CLI
    # version) would look like a downgrade against this net's "3.2.0a4"
    # target.
    metadata_path = project_path / ".kittify" / "metadata.yaml"
    metadata_text = metadata_path.read_text(encoding="utf-8")
    metadata_path.write_text(
        re.sub(r"(?m)^(\s*version:\s*).*$", r"\g<1>'1.0.0a1'", metadata_text, count=1),
        encoding="utf-8",
    )
    return project_path


def _run_upgrade(**kwargs: object) -> None:
    """Drive the real `upgrade()` entry point (mirrors the sibling harness).

    WP03 (#4032, recorded out-of-map edit): ``upgrade()``'s ``typer.Option``
    defaults are live ``OptionInfo`` instances (always truthy) until Click
    resolves them -- calling the undecorated function directly without an
    explicit ``plan_json`` always entered the unconditional ``if plan_json:``
    branch and crashed via its own unconditional ``raise typer.Exit(...)``
    before this test's flow ever ran. Confirmed pre-existing on the
    mission's pre-WP01 base commit too (see module docstring point 2) --
    orthogonal to the T013 fixture re-pin, fixed here regardless.
    """
    kwargs.setdefault("agent_check", False)
    kwargs.setdefault("agent_choice", None)
    kwargs.setdefault("agent_latest", None)
    kwargs.setdefault("plan_json", False)
    upgrade_cmd.upgrade(**kwargs)


def test_default_migrations_pending_commit_behavior_characterization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """NFR-002 golden: DEFAULT auto_commit path, migrations pending.

    See module docstring for the full oracle rationale and the observable
    list (a)-(e). This is the char-net's single scenario: WP03/WP04 must
    keep it green across the finalizer refactor.
    """
    project_path = _setup_upgrade_project(tmp_path / "proj", monkeypatch)
    config_path = project_path / ".kittify" / "config.yaml"
    config_bytes_before = config_path.read_bytes()
    monkeypatch.setattr(Path, "cwd", lambda: project_path)

    # --- git_status_paths: call #1 is the pre-migration baseline (clean),
    # call #2 is the post-upgrade snapshot the commit seam diffs against.
    status_calls = {"count": 0}

    def _fake_status(_repo_path: Path) -> set[str]:
        status_calls["count"] += 1
        if status_calls["count"] == 1:
            return set()
        return set(EXPECTED_CHURN_PATHS)

    monkeypatch.setattr(autocommit, "git_status_paths", _fake_status)

    # --- branch detection inside commit_touched_checkout: succeed with a
    # fixed branch name (NOT the CalledProcessError fallback path — that is
    # contract C7 / FR-013's own scenario, not this default-path net).
    monkeypatch.setattr(subprocess, "check_output", lambda *_a, **_kw: "main\n")

    # --- spy on the two commit-seam boundaries named in the WP prompt. Each
    # captured field is its own typed list (rather than a dict[str, object])
    # so downstream assertions get real static types, not `object`.
    safe_commit_messages: list[str] = []
    safe_commit_paths: list[tuple[Path, ...]] = []
    safe_commit_targets: list[CommitTarget] = []
    safe_commit_capabilities: list[GuardCapability] = []

    def _spy_safe_commit(
        *,
        repo_root: Path,
        worktree_root: Path,
        destination_ref: str | None = None,
        target: CommitTarget | None = None,
        message: str,
        paths: tuple[Path, ...],
        capability: GuardCapability = GuardCapability.STANDARD,
    ) -> object:
        del repo_root, worktree_root, destination_ref  # unused by the assertions below
        safe_commit_messages.append(message)
        safe_commit_paths.append(paths)
        if target is not None:
            safe_commit_targets.append(target)
        safe_commit_capabilities.append(capability)
        return MagicMock(name="CommitResult")

    monkeypatch.setattr(autocommit, "safe_commit", _spy_safe_commit)

    original_commit_touched_checkout: Callable[[Path, set[str] | None, str, str], tuple[bool, list[str], str | None]] = autocommit.commit_touched_checkout
    commit_touched_checkout_from_versions: list[str] = []
    commit_touched_checkout_to_versions: list[str] = []

    def _spy_commit_touched_checkout(
        checkout: Path,
        baseline_paths: set[str] | None,
        from_version: str,
        to_version: str,
    ) -> tuple[bool, list[str], str | None]:
        commit_touched_checkout_from_versions.append(from_version)
        commit_touched_checkout_to_versions.append(to_version)
        return original_commit_touched_checkout(checkout, baseline_paths, from_version, to_version)

    monkeypatch.setattr(autocommit, "commit_touched_checkout", _spy_commit_touched_checkout)

    # --- a single successful, no-manual-review migration (the default path).
    fake_migration = MagicMock(
        migration_id="3.2.0a4_safe_globalize_commands",
        description="Safely remove lingering per-project spec-kitty command files",
        target_version="3.2.0a4",
    )
    monkeypatch.setattr(
        "specify_cli.upgrade.registry.MigrationRegistry.get_applicable",
        lambda *_args, **_kwargs: [fake_migration],
    )
    monkeypatch.setattr(
        "specify_cli.upgrade.runner.MigrationRunner.upgrade",
        lambda self, *args, **kwargs: UpgradeResult(
            success=True,
            from_version="1.0.0a1",
            to_version="3.2.0a4",
            migrations_applied=["3.2.0a4_safe_globalize_commands"],
            migration_results={"3.2.0a4_safe_globalize_commands": MigrationResult(success=True)},
        ),
    )

    _run_upgrade(
        dry_run=False,
        force=True,
        target="3.2.0a4",
        json_output=True,
        verbose=False,
        no_worktrees=True,
        cli=False,
        project=False,
    )

    data = json.loads(capsys.readouterr().out.strip())

    # Outcome-level sanity: this scenario has no mission-type-activation
    # errors and no surface-drift failure, so the json-branch `success`
    # variable and `_display_upgrade_results`'s raw `result.success` check
    # agree here — the #3392 divergence is simply not in play on this path.
    assert data["status"] == "success"
    assert data["success"] is True
    assert data["warnings"] == []

    # (a) a commit is created
    assert data["auto_committed"] is True
    assert len(safe_commit_messages) >= 1

    # (b) exactly one commit
    assert len(safe_commit_messages) == 1, "NFR-002(b): expected exactly one commit"
    [commit_message] = safe_commit_messages
    [commit_paths] = safe_commit_paths
    [commit_target] = safe_commit_targets
    [commit_capability] = safe_commit_capabilities

    # (c) the commit-message format/text (fully test-controlled inputs, so
    # an exact-match assertion is appropriate — not an env-derived value).
    assert commit_message == "chore: apply spec-kitty upgrade changes (1.0.0a1 -> 3.2.0a4)"

    # (d) the SET of churn paths committed — set-equality, not subset.
    committed_paths = {str(p) for p in commit_paths}
    assert committed_paths == EXPECTED_CHURN_PATHS
    assert set(data["auto_commit_paths"]) == EXPECTED_CHURN_PATHS

    # Structural (not byte-exact) check on the commit target/capability: the
    # ref is asserted as the fixed branch name we injected (structure), and
    # the capability is the fixed enum member the seam always uses for
    # upgrade bookkeeping — not environment-derived, so exact-match is fine.
    assert commit_target.ref == "main"
    assert commit_capability is GuardCapability.UPGRADE_BOOKKEEPING

    # (e) worktree commit behavior: the main-checkout commit is performed
    # through the SAME shared seam (`autocommit.commit_touched_checkout`)
    # that `runner._upgrade_worktrees` calls per-worktree post-refactor
    # (contract C4). This is a call-level pin on the seam being used, not an
    # execution of an actual worktree upgrade (out of scope here; see C5).
    assert len(commit_touched_checkout_from_versions) == 1
    assert commit_touched_checkout_from_versions[0] == "1.0.0a1"
    assert commit_touched_checkout_to_versions[0] == "3.2.0a4"

    # T013 -- affirmative apply-path witness (not green-by-accident): a
    # skip-path run (config-absent, `PreparedUpgradeRepairs.provisioning is
    # None`) could ALSO reach `data["success"] is True` with a different
    # churn set, so green alone does not prove the apply path fired. Prove
    # the provisioning authority was genuinely WRITTEN TO, not merely
    # planned: the degraded `mission_type_activations` key this fixture
    # stripped is back, with the canonical default set, and the file's
    # bytes actually changed on disk.
    config_bytes_after = config_path.read_bytes()
    assert config_bytes_after != config_bytes_before, "T013: no observable apply-effect -- config.yaml is byte-identical to the degraded pre-run state"
    descriptor_after = prepare_mission_type_activations(project_path)
    assert descriptor_after.write.before_bytes is not None
    assert descriptor_after.reason == "key_present", "the provisioning apply() call must have (re)written the key"
    assert descriptor_after.mission_type_activations, "the (re)written key must carry the seeded default values, not an empty list"
