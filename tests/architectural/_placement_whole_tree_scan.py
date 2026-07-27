"""Shared whole-tree ``src/`` scanner for the placement-enforcement gates (WP06).

FR-001 / IC-02 (coord-write-placement-closure-01KYCF83): the write-side
placement-enforcement gate in ``test_no_write_side_rederivation.py`` (and its
``target=CommitTarget(...)`` companion assertion in
``test_safe_commit_import_boundary.py``) retired the 17-module
``_CHECKOUT_GRAMMAR_MODULES`` allowlist in favour of scanning **every**
``.py`` module under ``src/`` — a module allowlist is exactly the kind of
blanket escape a future write surface could hide behind. This module is the
ONE walker + sanctioned-set accessor both gates (and WP07's read-placement
gate, IC-05) import, so there is a single canonical notion of "the whole-tree
scan scope", never a second fork of the walk logic.

Pure helper — carries **no** gate assertions of its own (no ``test_*``
functions, no ``pytest`` import) so it can be imported by any consumer,
including a plain module walk from outside the test-collection machinery.

Sanctioned-primitive exclusion set
-----------------------------------
``BOUNDARY_SANCTIONED_MODULES`` is the **existing** (relocated, not
duplicated) sanctioned-primitive collection: coord primitives / legacy
migration bookkeeping that are NEVER a mission-artifact write site awaiting a
placement-seam route — they ARE the sanctioned grammar (branch composition,
worktree resolution, seam internals, migration bookkeeping, generic
non-mission-artifact commit surfaces). Each entry is now a
``{rel_path: rationale}`` mapping (was a bare ``frozenset[str]`` before WP06)
so every exclusion carries an inline, enforceable justification — see
``test_no_write_side_rederivation.py``'s
``test_sanctioned_modules_carry_a_rationale`` meta-test.

``BOUNDARY_SANCTIONED_PREFIXES`` is RETAINED byte-for-byte from the
pre-widening scope (do not add a new dir-prefix entry — a new prefix is how
the retired module allowlist creeps back in inverted form; see
``test_checkout_grammar_boundary_excludes_sanctioned_modules``'s pinned-tuple
guard).
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"

#: Individually-justified sanctioned primitives, EXCLUDED from the whole-tree
#: placement-enforcement scan scope. Adding an entry here is a deliberate,
#: per-file scope decision (never a directory-prefix shortcut) and MUST carry
#: a non-empty rationale (T029 meta-test).
BOUNDARY_SANCTIONED_MODULES: dict[str, str] = {
    "src/specify_cli/lanes/branch_naming.py": (
        "Branch NAME composition primitive (mid8 resolution, branch string "
        "formatting) -- never constructs a CommitTarget/safe_commit call "
        "itself; a naming primitive, not a write surface."
    ),
    "src/specify_cli/coordination/workspace.py": (
        "CoordinationWorkspace worktree-path / branch-name composition "
        "primitive -- resolves paths and branch strings for the coordination "
        "workspace, not a MissionArtifactKind placement decision."
    ),
    "src/specify_cli/upgrade/autocommit.py": (
        "Upgrade-migration autocommit primitive -- deliberately commits "
        "migration bookkeeping onto whatever branch is CURRENTLY checked out "
        "(an upgrade runs in-place on the operator's checkout); not a "
        "mission-artifact placement decision."
    ),
    "src/specify_cli/invocation/executor.py": (
        "Invocation-record commit primitive -- commits onto the invocation's "
        "own recorded branch context, a lane-execution bookkeeping surface "
        "distinct from mission-artifact placement."
    ),
    "src/specify_cli/coordination/policy.py": (
        "GitChangeSet pre-flight validator (assert_allowed) -- re-wraps the "
        "CALLER-supplied, already-resolved change_set.destination_ref into "
        "the CommitTarget VO shape solely to invoke commit_guard.evaluate "
        "(the C-GUARD-1 blessed delegate per "
        "test_safe_commit_import_boundary.py); it makes no placement "
        "decision of its own."
    ),
    "src/specify_cli/cli/commands/safe_commit_cmd.py": (
        "Generic operator-file `spec-kitty safe-commit` CLI command -- both "
        "CommitTarget constructions (the `--to-branch` explicit override, "
        "and the deprecated HEAD-fallback pending v3.3 removal) fire ONLY "
        "when the file is NOT a classifiable mission artifact; a "
        "classifiable mission-artifact file is routed via "
        "_resolve_mission_aware_target (the placement seam) earlier in the "
        "same function and returns before reaching either site."
    ),
    "src/mission_runtime/write_target_degrade.py": (
        "Shared bootstrap-window degrade helper (placement-port-residuals-"
        "closure-01KYDEF0 WP04, FR-005): unifies the "
        "CommitTarget(ref=degrade_ref) construction formerly duplicated "
        "verbatim across decision_log.DecisionGitLog._resolve_default_target "
        "(fail-open) and bookkeeping_commit._resolve_bookkeeping_commit_target "
        "(fail-closed) into ONE helper, resolve_write_target_or_degrade. The "
        "degrade construction fires ONLY when the mission cannot be resolved "
        "via the placement port (no meta.json yet, or a caught "
        "ActionContextError/StatusReadPathNotFound/FileNotFoundError) -- an "
        "explicit existence gate degrading to the caller-SUPPLIED ref, never "
        "a checkout-HEAD re-derivation. This file is already excluded via the "
        "src/mission_runtime/ BOUNDARY_SANCTIONED_PREFIXES blanket; this "
        "per-file entry restores the individual, rationale-bearing "
        "accountability the four now-deleted ContentDescriptor entries used "
        "to carry for this exact construction (see "
        "test_no_write_side_rederivation.py's _CHECKOUT_GRAMMAR_ALLOW_LIST_SEED "
        "history) -- so test_sanctioned_modules_carry_a_rationale still "
        "polices it directly instead of it going unpoliced behind the "
        "package-wide prefix."
    ),
}

#: RETAINED byte-for-byte from the pre-widening scope (do not extend). A new
#: dir-prefix entry is forbidden by
#: ``test_checkout_grammar_boundary_excludes_sanctioned_modules``'s pinned
#: tuple guard -- use a per-file ``BOUNDARY_SANCTIONED_MODULES`` entry
#: instead.
#:
#: placement-port-residuals-closure-01KYDEF0 WP03 (FR-003/004, SC-002,
#: C-002): ``"src/specify_cli/migration/"`` was DROPPED from this tuple --
#: empirically the subtree has ZERO ``CommitTarget``/``safe_commit``
#: construction, so the prefix sanctioned nothing real; dropping it restores
#: "any module" scan precision. Keep this in LOCKSTEP with
#: ``test_no_write_side_rederivation.py``'s
#: ``_PINNED_BOUNDARY_SANCTIONED_PREFIXES`` (its meta-test hard-asserts
#: equality). Do not confuse with the separate, intentional ``migration/``
#: blanket in ``test_mission_resolver_walker_gate.py`` (C-004) -- a different
#: scan, untouched by this change.
BOUNDARY_SANCTIONED_PREFIXES: tuple[str, ...] = (
    "src/mission_runtime/",
    "src/specify_cli/upgrade/migrations/",
)


def iter_src_modules(*, src_root: Path = SRC_ROOT) -> list[Path]:
    """Every ``.py`` module under ``src_root``, sorted, skipping ``__pycache__``.

    The whole-tree walk (FR-001 / NFR-001): scans 100% of ``src/`` — no
    module allowlist. Sorted for deterministic iteration order (stable
    offender ordering across runs).
    """
    return sorted(p for p in src_root.rglob("*.py") if "__pycache__" not in p.parts)


def rel_path(path: Path, *, repo_root: Path = REPO_ROOT) -> str:
    """``path`` relative to ``repo_root``, POSIX-separated (the canonical
    identity every allow-list / sanctioned-module entry is keyed on)."""
    return path.relative_to(repo_root).as_posix()


def is_sanctioned(rel: str) -> bool:
    """``True`` iff the module at ``rel`` (a repo-root-relative POSIX path) is
    a sanctioned primitive excluded from the whole-tree scan scope.

    Checks the per-file ``BOUNDARY_SANCTIONED_MODULES`` set OR the retained
    ``BOUNDARY_SANCTIONED_PREFIXES`` — the ONLY two sanctioning mechanisms;
    there is no third.
    """
    if rel in BOUNDARY_SANCTIONED_MODULES:
        return True
    return rel.startswith(BOUNDARY_SANCTIONED_PREFIXES)


def scan_scope(*, src_root: Path = SRC_ROOT, repo_root: Path = REPO_ROOT) -> list[Path]:
    """Every ``src/`` module that is NOT sanctioned -- the actual gate scan scope."""
    return [
        module
        for module in iter_src_modules(src_root=src_root)
        if not is_sanctioned(rel_path(module, repo_root=repo_root))
    ]
