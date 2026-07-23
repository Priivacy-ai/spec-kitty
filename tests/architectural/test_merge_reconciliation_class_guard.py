"""WP05 — class-closing guards for #2709 (FR-008 / SC-005).

Two NON-VACUOUS architectural lints that close the "merge silently overwrites
target-newer canonical state" defect class *by construction*, covering BOTH loss
mechanisms — NOT a re-run of the WP01 outcome repro. Precedent for the AST /
per-registry lint home: ``tests/architectural/test_merge_pipeline_ratchets.py``.

* **T012 — no-blind-copy AST lint** over the ``merge/`` projection path. The
  FR-005 regression is ``merge/bookkeeping_projection.py`` blind-``write_bytes``-ing
  a *foreign* status/meta/trace source straight onto the *authoritative*
  target-surface artifact (event log / ``meta.json`` / ``traces/*.md``) instead of
  reconciling it (``_union_event_logs`` / rematerialize). The lint fires on that
  exact shape and stays silent on the fixed tree — including the deliberately
  *derived* ``status.json`` copy (line ``write_bytes(source_status_bytes)``), which
  is a rematerialized/degenerate view, not an authoritative both-sides-divergent
  artifact.

* **T013 — driver-registry-completeness lint** (the primary #2709 ``-X theirs``
  vector, blind to the projection lint). Two independent assertions:
    - **sync**: every driver DECLARED in the in-code registry
      (``specify_cli.lanes.merge._MERGE_DRIVERS``) is REGISTERED in root
      ``.gitattributes`` and vice-versa — catches *dropping* an existing
      ``.gitattributes`` driver line;
    - **completeness (non-tautology)**: every both-sides-divergent canonical
      ``kitty-specs/**`` artifact enumerated from the INDEPENDENT
      mission-artifact-kind registry (``mission_runtime.artifacts`` —
      ``MissionArtifactKind`` + ``_MISSION_FILE_KIND_BY_BASENAME`` /
      ``_COORD_RESIDUE_DIRS`` / ``kind_for_mission_file``), NOT enumerated from
      ``.gitattributes`` itself, carries a registered merge driver. Fail-closed: a
      *future* net-new canonical artifact re-inherits #2709 via ``-X theirs``
      unless it is a driver or is explicitly classified as non-divergent below.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

import specify_cli
from mission_runtime.artifacts import (
    _COORD_RESIDUE_DIRS,
    _MISSION_FILE_KIND_BY_BASENAME,
    MissionArtifactKind,
    kind_for_mission_file,
)
from specify_cli.cli.commands import init as _init_command
from specify_cli.lanes.merge import _MERGE_DRIVERS
from specify_cli.upgrade.migrations import (
    m_3_1_1_event_log_merge_driver as _event_log_migration,
)
from specify_cli.upgrade.migrations import (
    m_3_2_6_meta_traces_merge_drivers as _meta_traces_migration,
)

pytestmark = [pytest.mark.architectural]

SRC_ROOT = Path(specify_cli.__file__).resolve().parent
REPO_ROOT = SRC_ROOT.parents[1]
MERGE_DIR = SRC_ROOT / "merge"
GITATTRIBUTES = REPO_ROOT / ".gitattributes"

# Authoritative, both-sides-divergent artifact surfaces whose target copy must
# NEVER be blind-overwritten (append-only event log / field-merge ``meta.json`` /
# union ``traces``). A write-receiver variable naming any of these tokens is an
# authoritative-target write. The *derived* ``status.json`` snapshot deliberately
# carries none of these tokens, so its rematerialized/degenerate copy is exempt.
_AUTHORITATIVE_ARTIFACT_TOKENS: tuple[str, ...] = ("events", "meta", "trace")

# A write argument that is one of these is a raw *foreign* read passed straight
# through to the target (a blind copy), rather than a reconciled value.
_RAW_READ_CALLEES: frozenset[str] = frozenset(
    {"_read_optional_bytes", "read_bytes", "read_text"}
)


# ---------------------------------------------------------------------------
# T012 — no-blind-copy of a foreign source onto an authoritative target
# ---------------------------------------------------------------------------


def _merge_sources() -> list[Path]:
    return sorted(MERGE_DIR.rglob("*.py"))


def _receiver_name(node: ast.expr) -> str:
    """Best-effort name of a ``<receiver>.write_bytes(...)`` receiver expression."""
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _is_authoritative_target_write(call: ast.Call) -> bool:
    """True for ``<...events|meta|trace...>.write_bytes/​write_text(...)`` calls."""
    func = call.func
    if not (isinstance(func, ast.Attribute) and func.attr in {"write_bytes", "write_text"}):
        return False
    receiver = _receiver_name(func.value).lower()
    return any(token in receiver for token in _AUTHORITATIVE_ARTIFACT_TOKENS)


def _arg_is_raw_foreign_read(call: ast.Call) -> bool:
    """True when the write's first positional arg is a raw foreign-source read.

    A ``source_*`` bare name, an inline ``_read_optional_bytes(...)`` call, or an
    inline ``<path>.read_bytes()/​.read_text()`` call passed straight to the write
    is a blind copy. A reconciler call (``_union_event_logs(...)``,
    ``_rematerialize_status_snapshot(...)``, …) is NOT one of these, so reconciled
    writes are permitted.
    """
    if not call.args:
        return False
    arg = call.args[0]
    if isinstance(arg, ast.Name) and "source" in arg.id.lower():
        return True
    if isinstance(arg, ast.Call):
        callee = arg.func
        if isinstance(callee, ast.Name) and callee.id in _RAW_READ_CALLEES:
            return True
        if isinstance(callee, ast.Attribute) and callee.attr in _RAW_READ_CALLEES:
            return True
    return False


def test_no_blind_copy_of_foreign_source_onto_authoritative_target() -> None:
    """SC-005 (FR-005): the ``merge/`` projection path must never blind-copy a
    foreign status/meta/trace source onto the authoritative target artifact —
    it must reconcile (union / field-merge / rematerialize). RED on a synthetic
    ``trusted_target_events_path.write_bytes(source_events_bytes)`` reintroduction."""
    offenders: list[str] = []
    for source in _merge_sources():
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        offenders.extend(
            f"{source.relative_to(SRC_ROOT)}:{node.lineno}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and _is_authoritative_target_write(node)
            and _arg_is_raw_foreign_read(node)
        )
    assert not offenders, (
        "Blind copy of a foreign source onto an authoritative both-sides-divergent "
        "target artifact in merge/ (FR-005/#2709 regression) — reconcile via the "
        f"union/field-merge/rematerialize seam instead of write_bytes: {offenders}"
    )


# ---------------------------------------------------------------------------
# T013 — driver-registry completeness (the -X theirs / no-driver vector)
# ---------------------------------------------------------------------------


def _gitattributes_merge_drivers() -> dict[str, str]:
    """Map ``pattern -> driver-key`` for every ``merge=`` line in ``.gitattributes``."""
    drivers: dict[str, str] = {}
    for raw in GITATTRIBUTES.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 2:
            continue
        pattern = fields[0]
        for attribute in fields[1:]:
            if attribute.startswith("merge="):
                drivers[pattern] = attribute.split("=", 1)[1]
    return drivers


def test_declared_merge_drivers_are_registered_in_gitattributes() -> None:
    """T013 sync (catches self-mutation (a) — dropping a ``.gitattributes`` line):
    the in-code ``_MERGE_DRIVERS`` registry and root ``.gitattributes`` must agree
    on every custom Spec Kitty merge driver, in both directions (C-006)."""
    registered = _gitattributes_merge_drivers()
    declared = {driver.pattern: driver.config_key for driver in _MERGE_DRIVERS}

    unregistered = [
        f"{pattern} merge={key}"
        for pattern, key in declared.items()
        if registered.get(pattern) != key
    ]
    assert not unregistered, (
        "Merge driver declared in specify_cli.lanes.merge._MERGE_DRIVERS but not "
        f"registered in root .gitattributes (#2709 re-inheritance risk): {unregistered}"
    )

    orphaned = [
        f"{pattern} merge={key}"
        for pattern, key in registered.items()
        if key.startswith("spec-kitty-") and declared.get(pattern) != key
    ]
    assert not orphaned, (
        "Spec Kitty merge driver registered in .gitattributes with no matching "
        f"_MERGE_DRIVERS declaration (drift): {orphaned}"
    )


# Canonical artifacts the mission classifies as NOT both-sides-divergent, so a
# custom reconcile driver is intentionally absent (fail-closed default is: any
# canonical artifact NOT listed here MUST carry a driver). Sourced by writer
# topology / FR-008 loss analysis, NOT from .gitattributes:
#   * human-authored planning SOURCE (registry ``_PRIMARY_ARTIFACT_KINDS``) — the
#     target never independently edits these; ``-X theirs`` keeping the mission
#     copy is the intended #1732 behavior, so no reconcile is needed;
#   * derived / materialized views — regenerated from the event log, so a lost
#     copy is recoverable by re-reduction;
#   * single-writer coordination / terminal artifacts — no both-sides divergence.
_NON_DIVERGENT_CANONICAL_ARTIFACTS: frozenset[str] = frozenset(
    {
        # planning SOURCE
        "spec.md",
        "data-model.md",
        "research.md",
        "plan.md",
        "tasks.md",
        # derived / materialized views
        "status.json",
        "lanes.json",
        "acceptance-matrix.json",
        "snapshot-latest.json",
        # single-writer derived baseline (post-merge stale-assertion snapshot,
        # review/baseline.py) — classified WORK_PACKAGE_TASK (PRIMARY partition),
        # written by exactly one path, never both-sides-divergent bookkeeping.
        "baseline-tests.json",
        # single-writer coordination / terminal
        "issue-matrix.md",
        "analysis-report.md",
        "retrospective.yaml",
    }
)


def _canonical_artifact_file_globs() -> dict[str, MissionArtifactKind]:
    """``kitty-specs/**`` file-glob -> kind for every canonical FILE artifact.

    Sourced from the INDEPENDENT mission-artifact-kind registry path maps (NOT from
    ``.gitattributes``), so registering a NEW canonical artifact there trips the
    completeness lint below (non-tautology). Directory kinds (``tasks/``,
    ``checklists/`` — human-authored planning collections) are handled separately.
    """
    return {
        f"kitty-specs/**/{filename}": kind
        for filename, kind in _MISSION_FILE_KIND_BY_BASENAME.items()
    }


def test_both_sides_divergent_canonical_artifacts_carry_merge_driver() -> None:
    """T013 completeness (catches self-mutation (b) — a NEW canonical artifact with
    no driver): every both-sides-divergent canonical ``kitty-specs/**`` artifact in
    the mission-artifact-kind registry MUST carry a registered merge driver, else a
    future ``git merge --squash -X theirs`` silently re-inherits #2709. Fail-closed:
    a registry artifact not in ``_NON_DIVERGENT_CANONICAL_ARTIFACTS`` is required to
    have a driver."""
    registered_patterns = set(_gitattributes_merge_drivers())
    # Directory kinds are human-authored planning collections (WORK_PACKAGE_TASK,
    # CHECKLIST) — not both-sides-divergent bookkeeping.
    assert set(_COORD_RESIDUE_DIRS) == {"tasks", "checklists"}

    uncovered: list[str] = []
    for glob, kind in _canonical_artifact_file_globs().items():
        basename = glob.rsplit("/", 1)[-1]
        if basename in _NON_DIVERGENT_CANONICAL_ARTIFACTS:
            continue
        # Cross-check the INDEPENDENT public classifier recognizes this artifact.
        assert kind_for_mission_file(f"kitty-specs/some-mission/{basename}") is kind
        if glob not in registered_patterns:
            uncovered.append(f"{glob} ({kind.value})")
    assert not uncovered, (
        "Both-sides-divergent canonical artifact(s) with no registered merge driver "
        "in root .gitattributes — they re-inherit #2709 under `git merge --squash "
        "-X theirs`. Register a reconcile driver (C-006) or, if genuinely "
        "single-writer/derived/human-source, classify in "
        f"_NON_DIVERGENT_CANONICAL_ARTIFACTS: {uncovered}"
    )


# ---------------------------------------------------------------------------
# T013b — driver-registry parity across the fresh/upgraded-repo seed surfaces
#
# The driver spec is declared in FOUR places: the in-code ``_MERGE_DRIVERS``
# registry, root ``.gitattributes`` (bound bidirectionally above), the ``init``
# seed (fresh repos), and the upgrade migrations (existing repos). The
# ``.gitattributes`` binding alone does NOT protect a NEW driver added to the
# registry+``.gitattributes`` but forgotten in the init seed or a migration:
# fresh/upgraded repos then silently re-inherit #2709 for that artifact because
# their ``.gitattributes`` never gains the mapping. These two lints bind the
# remaining two surfaces to the registry (superset direction).
# ---------------------------------------------------------------------------

_MERGE_ATTRIBUTES_LINE = re.compile(r"^\S+ merge=\S+$")


def _registry_attribute_lines() -> set[str]:
    """``<pattern> merge=<key>`` line for every driver in the in-code registry."""
    return {driver.attributes_line for driver in _MERGE_DRIVERS}


def _init_seed_attribute_lines() -> set[str]:
    """Every gitattributes ``merge=`` line the ``init`` command seeds for new repos.

    Scanned from the init module namespace (any ``<pattern> merge=<key>`` string
    constant), NOT a hardcoded list — a NEW driver constant is picked up
    automatically, and a registry driver with NO init constant trips the lint.
    """
    return {
        value
        for value in vars(_init_command).values()
        if isinstance(value, str) and _MERGE_ATTRIBUTES_LINE.match(value)
    }


def _migration_seed_attribute_lines() -> set[str]:
    """Every gitattributes ``merge=`` line the upgrade migrations seed.

    The migration surface is split by version: the event-log driver ships in
    ``m_3_1_1`` (``_ATTRIBUTES_ENTRY``) and the meta/traces drivers in ``m_3_2_6``
    (``_DRIVERS``). Their UNION is the upgraded-repo seed surface.
    """
    lines = {_event_log_migration._ATTRIBUTES_ENTRY}
    lines.update(driver.attributes_entry for driver in _meta_traces_migration._DRIVERS)
    return lines


def test_init_seed_is_superset_of_registry_merge_drivers() -> None:
    """T013b (fresh repos): every driver in ``_MERGE_DRIVERS`` MUST also be seeded
    by ``init`` into ``.gitattributes`` — else a freshly ``init``-ed repo never
    activates the driver and re-inherits #2709 for that artifact. RED when a
    registry driver has no matching init constant."""
    missing = _registry_attribute_lines() - _init_seed_attribute_lines()
    assert not missing, (
        "Merge driver(s) declared in specify_cli.lanes.merge._MERGE_DRIVERS but NOT "
        "seeded by the init command (fresh repos re-inherit #2709 — no .gitattributes "
        f"mapping). Add the entry in specify_cli/cli/commands/init.py: {sorted(missing)}"
    )


def test_migration_seed_is_superset_of_registry_merge_drivers() -> None:
    """T013b (upgraded repos): every driver in ``_MERGE_DRIVERS`` MUST also be seeded
    by an upgrade migration (m_3_1_1 event-log ∪ m_3_2_6 meta/traces) — else an
    UPGRADED repo never activates the driver and re-inherits #2709 for that
    artifact. RED when a registry driver is in neither migration."""
    missing = _registry_attribute_lines() - _migration_seed_attribute_lines()
    assert not missing, (
        "Merge driver(s) declared in specify_cli.lanes.merge._MERGE_DRIVERS but NOT "
        "seeded by any upgrade migration (upgraded repos re-inherit #2709). Add the "
        f"driver to an m_*_meta_traces / event-log migration: {sorted(missing)}"
    )
