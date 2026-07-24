"""Architectural ratchet: raw ``kitty-specs/`` enumeration in ``src/`` (WP04/FR-007).

FR-006 / FR-007 / #2173 Phase 2: the ``MissionResolver`` port
(``mission_runtime.mission_resolver_port.MissionResolver``, adapters in
``specify_cli.context.mission_resolver``) is the **single sanctioned trunk**
for handle -> mission resolution (see
``docs/adr/3.x/2026-07-08-1-mission-resolver-port.md``, D-06/D-08). Without a
structural gate, "one walk" is a reviewer-memory convention: nothing stops a
future caller from reaching for ``Path.iterdir()`` on ``kitty-specs/``
directly the next time it needs a quick mission listing -- "walker #7"
reappears, exactly as the Phase 1 ADR (``2026-06-26-1``) predicted for its own
boundary.

This module is the enumeration analogue of
``test_protection_resolver_call_sites.py`` (which fences a *decision*
function; this fences a *directory walk*), extended with two guarantees that
file does not need:

* **G-3** -- the scan derives its scope from ``src/`` wholesale
  (``_SRC_ROOT.rglob("*.py")``), never a hardcoded subdirectory list, so a new
  package cannot silently fall outside the gate's reach.
* **A free-function-caller ceiling** -- because the dominant read path is the
  *free function* ``resolve_mission`` (D-08), not only an assembler-injected
  port, a raw-walker ban alone would not stop ``resolve_mission`` callers from
  silently multiplying. A companion assertion counts bare-name
  ``resolve_mission(...)`` call sites and fails if a new one appears without a
  deliberate, reviewed ceiling bump.

Detection strategy (G-1)
------------------------
The guard AST-walks every ``*.py`` file under ``src/`` and flags any
``ast.Call`` whose callee is an attribute access with ``attr`` in
``{"iterdir", "glob", "scandir"}`` **and** whose receiver is "tainted" --
either an identifier assigned (anywhere in the file; this is a deliberately
coarse, file-wide, flow-insensitive approximation -- see "Known limitation"
below) from an expression that references the ``KITTY_SPECS_DIR`` constant or
the literal string ``"kitty-specs"``, or a bare name/parameter drawn from a
small, curated vocabulary of names this codebase already uses by convention
for the ``kitty-specs/`` root (``specs_dir``, ``mission_specs_dir``,
``mission_specs``, ``specs_root``, ``kitty_specs_dir``, ``kitty_specs``,
``wt_specs``, ``root_specs``, ``scan_specs``, ``main_specs``, ``scan_root``).

Known limitation (documented, not hidden): this is a static, name-based
approximation -- not full dataflow/call-graph analysis. A walker that threads
the specs directory through an unconventional name with no local
``KITTY_SPECS_DIR`` reference could in principle evade detection. This is the
same class of tradeoff ``test_protection_resolver_call_sites.py`` already
accepts (bare-name-call matching, not full alias resolution): the allowlist and
the name vocabulary are both human-reviewed, deliberately-extended surfaces.

G-2: matching (and the allowlist below) is keyed on **module paths and
identifier tokens**, never line numbers -- line numbers drift on every
unrelated edit in the same file and rot the gate silently.

Allowlist (FR-007 -- seeded from a live census, not the mission's planning
estimate)
---------------------------------------------------------------------------
The mission's planning notes estimated "~16" pre-existing walkers. A live
census grep run at WP04 implementation time found the **actual** count is
different in both directions: some planning-time entries do not walk
``kitty-specs/`` at all (they walk ``.kittify/missions/`` -- a different scan
root entirely, so a scan-root-keyed gate never matches them regardless of
whether they are listed); others were missing from the estimate. The
allowlist below reflects the verified census, with a one-line rationale per
entry. See ``docs/adr/3.x/2026-07-08-1-mission-resolver-port.md`` for the full
decision record.

WP04 / FR-006 / FR-007 / #2173.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"

# ---------------------------------------------------------------------------
# The sanctioned resolver module (FR-007) -- not part of the "legacy walker"
# allowlist below: this is the destination the other 19 files are being
# strangled towards, not a carve-out being tolerated.
# ---------------------------------------------------------------------------
_SANCTIONED_RESOLVER_MODULE = "src/specify_cli/context/mission_resolver.py"

# ---------------------------------------------------------------------------
# G-1 allowlist -- legacy runtime walkers being strangled (non-migration).
# Each entry is a *file*, never a line number (G-2). Extending this list is a
# deliberate policy decision: document the ONE flow the new entry authorises.
# ---------------------------------------------------------------------------
_LEGACY_WALKER_ALLOWLIST: frozenset[str] = frozenset(
    {
        # C-001: identity-audit exists to find the *mission_id-less* missions
        # the resolver's fail-closed contract silently skips during indexing.
        # Routing it through the resolver would blind the audit to the exact
        # defect class it audits for.
        "src/specify_cli/status/identity_audit.py",
        # C-002: caller-supplied (possibly non-primary) scan root + a
        # mission_number aggregation performed under the active merge lock --
        # does not fit the resolver's repo_root-bound construction.
        "src/specify_cli/merge/ordering.py",
        # C-003: best-effort swallow-and-degrade error-listing helper for CLI
        # error messages. The resolver's fail-closed-loud contract would turn
        # a friendly "did you mean" hint into a hard crash.
        "src/specify_cli/core/paths.py",
        # Advisory in-flight-WP scan for a charter step-removal warning --
        # best-effort UX warning, not an identity-resolution decision.
        "src/specify_cli/charter_activate.py",
        # `spec-kitty materialize` candidate-mission listing/selection UI.
        "src/specify_cli/cli/commands/materialize.py",
        # `spec-kitty doctor` coordination health-check enumeration across
        # every mission.
        "src/specify_cli/cli/commands/_coordination_doctor.py",
        # `spec-kitty doctor identity` topology enumeration -- distinct file
        # from status/identity_audit.py (both are legitimate walkers).
        "src/specify_cli/cli/commands/_identity_audit.py",
        # Feature/mission drift remediation candidate listing.
        "src/specify_cli/cli/commands/agent/mission_feature_resolution.py",
        # Lane sparse-checkout policy derivation scan (per-mission meta.json
        # glob to build the managed-lane policy set).
        "src/specify_cli/git/sparse_checkout.py",
        # Changelog generation walks every mission directory since a tag.
        "src/specify_cli/release/changelog.py",
        # Slug-prefix glob fallback used by the ambiguity/mid8 resolution
        # helper -- distinct from the threaded canonicalizer call
        # (`resolve_mission(..., resolver=resolver)`) in the same file.
        "src/specify_cli/missions/_read_path_resolver.py",
        # `get_all_features()` branch/dir discovery for legacy feature-branch
        # bookkeeping.
        "src/specify_cli/manifest.py",
        # Dashboard scan across worktrees + root kitty-specs (coord-vs-primary
        # topology classification, not identity resolution).
        "src/specify_cli/dashboard/scanner.py",
        # Audit engine's default `_scan_missions` walk (`scan_root` defaults
        # to `repo_root / KITTY_SPECS_DIR` at its assembler).
        "src/specify_cli/audit/engine.py",
        # `spec-kitty validate-tasks --all` scan (primary + worktree copies).
        "src/specify_cli/cli/commands/validate_tasks.py",
        # `spec-kitty validate-encoding --all` scan.
        "src/specify_cli/cli/commands/validate_encoding.py",
        # Fallback "list available missions" UX when no mission is active/given.
        "src/specify_cli/cli/commands/mission_type.py",
        # Charter corpus scan (`kitty-specs/*/charter/*.{yaml,md,txt}`) --
        # a different artifact kind than mission identity.
        "src/specify_cli/cli/commands/migrate/charter_encoding.py",
        # FR-014 one-time provenance backfill migration (lifecycle-gate-
        # execution-context WP05): walks the WHOLE acceptance-matrix corpus
        # across every mission under kitty-specs/ (a corpus-wide schema
        # backfill), not a single-mission identity resolution -- and per
        # C-004, migration-time code must not depend on the runtime
        # resolver's post-migration assumptions. Same rationale/sibling file
        # as charter_encoding.py in this directory.
        "src/specify_cli/cli/commands/migrate/backfill_provenance.py",
        # Partial-match handle-to-dir fallback scan (pre-dates the resolver;
        # a candidate for folding in a later #2173 phase, not this one).
        "src/specify_cli/retrospective/generator.py",
    }
)

# Migration-only walkers (C-004): migration-time code must not depend on the
# runtime resolver (a migration may run against a repo state the resolver's
# assumptions do not hold for yet, e.g. pre-mission_id or pre-topology
# metadata). Keyed on *directory prefix* tokens, not per-file, since C-004 is a
# blanket policy for the whole migration surface, present and future.
_MIGRATION_WALKER_DIR_PREFIXES: tuple[str, ...] = (
    "src/specify_cli/upgrade/migrations/",
    "src/specify_cli/migration/",
)

# ---------------------------------------------------------------------------
# Detection: enumeration call + taint heuristic
# ---------------------------------------------------------------------------

_ENUMERATION_METHODS: frozenset[str] = frozenset({"iterdir", "glob", "scandir"})

_SPECS_NAME_VOCABULARY: frozenset[str] = frozenset(
    {
        "specs_dir",
        "mission_specs_dir",
        "mission_specs",
        "specs_root",
        "kitty_specs_dir",
        "kitty_specs",
        "wt_specs",
        "root_specs",
        "scan_specs",
        "main_specs",
        "scan_root",
    }
)

_KITTY_SPECS_CONST_NAME = "KITTY_SPECS_DIR"
_KITTY_SPECS_LITERAL = "kitty-specs"


def _rel(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def _is_allowlisted(rel: str) -> bool:
    if rel == _SANCTIONED_RESOLVER_MODULE:
        return True
    if rel in _LEGACY_WALKER_ALLOWLIST:
        return True
    return any(rel.startswith(prefix) for prefix in _MIGRATION_WALKER_DIR_PREFIXES)


def _references_kitty_specs(node: ast.AST) -> bool:
    """Return True if any sub-node of *node* names the specs constant/literal."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and sub.id == _KITTY_SPECS_CONST_NAME:
            return True
        if isinstance(sub, ast.Constant) and sub.value == _KITTY_SPECS_LITERAL:
            return True
    return False


def _tainted_names_in_file(tree: ast.AST) -> set[str]:
    """Return the set of identifiers this file treats as "the specs dir".

    Deliberately file-wide and flow-insensitive (not scoped per-function): a
    name assigned from a ``KITTY_SPECS_DIR``-referencing expression in one
    function and reused (by the same name) as a parameter in a sibling
    function within the same file -- e.g. ``audit/engine.py``'s ``scan_root``,
    assembled in one function and consumed by ``_scan_missions`` -- is still
    caught. This over-approximates conservatively (a new, unrelated variable
    that happens to share a tainted name in the same file would also be
    flagged) in exchange for not missing genuine same-file threading; the
    tradeoff is documented in the module docstring.
    """
    tainted: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            all_args = (
                list(node.args.posonlyargs)
                + list(node.args.args)
                + list(node.args.kwonlyargs)
            )
            for arg in all_args:
                if arg.arg in _SPECS_NAME_VOCABULARY:
                    tainted.add(arg.arg)
        elif isinstance(node, ast.Assign):
            if _references_kitty_specs(node.value):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        tainted.add(target.id)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            if _references_kitty_specs(node.value) and isinstance(
                node.target, ast.Name
            ):
                tainted.add(node.target.id)

    return tainted


def _find_raw_walker_calls(path: Path) -> list[tuple[int, str]]:
    """Return ``(lineno, method)`` for each flagged enumeration call in *path*."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    tainted = _tainted_names_in_file(tree)
    violations: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _ENUMERATION_METHODS
        ):
            continue
        receiver = node.func.value
        is_tainted_name = isinstance(receiver, ast.Name) and receiver.id in tainted
        is_direct_reference = _references_kitty_specs(receiver)
        if is_tainted_name or is_direct_reference:
            violations.append((node.lineno, node.func.attr))

    return violations


def _scan_tree_for_violations(src_root: Path) -> dict[str, list[tuple[int, str]]]:
    """Scan every ``*.py`` under *src_root*, filtering out allowlisted files.

    G-3: scope is derived from ``src_root.rglob("*.py")`` wholesale -- no
    hardcoded subdirectory list a new package could silently fall outside of.
    Assumes *src_root* is the repository's real ``src/`` tree (the allowlist
    is keyed on repo-relative ``src/...`` paths); the anti-mutant tests below
    call :func:`_find_raw_walker_calls` directly against a synthetic tree
    instead of going through this function, since a fabricated path can never
    match a real allowlist entry anyway.
    """
    violations: dict[str, list[tuple[int, str]]] = {}
    for py_file in sorted(src_root.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        rel = _rel(py_file)
        if _is_allowlisted(rel):
            continue
        hits = _find_raw_walker_calls(py_file)
        if hits:
            violations[rel] = hits
    return violations


# ---------------------------------------------------------------------------
# G-3: scope-derivation sanity check
# ---------------------------------------------------------------------------


def test_gate_scan_scope_reaches_known_walker_files() -> None:
    """The gate must not silently go blind to any part of ``src/``.

    Asserts the wholesale ``rglob("*.py")`` scan actually reaches a
    representative sample of files scattered across distinct subpackages --
    proving the scope is derived from ``src/`` itself, not a hardcoded,
    staleness-prone directory list.
    """
    scanned = {_rel(p) for p in _SRC_ROOT.rglob("*.py") if "__pycache__" not in p.parts}

    representative_sample = {
        _SANCTIONED_RESOLVER_MODULE,
        "src/specify_cli/status/identity_audit.py",
        "src/specify_cli/merge/ordering.py",
        "src/specify_cli/dashboard/scanner.py",
        "src/mission_runtime/mission_resolver_port.py",
    }
    missing = representative_sample - scanned
    assert not missing, (
        f"Gate scan scope did not reach: {sorted(missing)} -- "
        "the src/ walk may have silently narrowed (G-3 violation)."
    )
    # Sanity floor: the real src/ tree is large; a near-empty scan means the
    # scan root resolved to the wrong place entirely.
    assert len(scanned) > 200


# ---------------------------------------------------------------------------
# G-1/G-2: the main gate
# ---------------------------------------------------------------------------


def test_no_unsanctioned_raw_kitty_specs_enumeration_in_src() -> None:
    """All raw ``kitty-specs/`` enumeration in ``src/`` must be sanctioned.

    Passing means every raw ``iterdir()``/``glob()``/``scandir()`` call that
    this gate's taint heuristic attributes to the ``kitty-specs/`` directory
    lives in the sanctioned resolver module or an explicitly reviewed
    allowlist/migration-prefix entry above.

    To add a new sanctioned site: extend ``_LEGACY_WALKER_ALLOWLIST`` (or, for
    a migration-only walker, confirm it falls under one of the
    ``_MIGRATION_WALKER_DIR_PREFIXES``) and document the ONE flow the entry
    authorises.
    """
    violations = _scan_tree_for_violations(_SRC_ROOT)

    if violations:
        details = "\n".join(
            f"  {path}: {hits}" for path, hits in sorted(violations.items())
        )
        pytest.fail(
            "Found raw kitty-specs/ enumeration calls outside the FR-007 "
            "allowlist. Route through mission_runtime.MissionResolver / "
            "specify_cli.context.mission_resolver.resolve_mission instead, or "
            "-- for a genuinely distinct, non-identity-resolution walk -- "
            "extend _LEGACY_WALKER_ALLOWLIST with a one-line rationale.\n\n"
            f"Violations:\n{details}"
        )


# ---------------------------------------------------------------------------
# T020: anti-mutant proof -- the gate bites on a planted violation
# ---------------------------------------------------------------------------


def test_planted_raw_walker_is_detected_outside_allowlist(tmp_path: Path) -> None:
    """A synthetic, non-allowlisted raw walker must be flagged.

    Proves the detector actually "bites": a file that is unmistakably not in
    any allowlist/migration-prefix (it lives under a throwaway ``tmp_path``,
    not ``src/``) and that raw-enumerates a ``KITTY_SPECS_DIR``-derived path
    is caught by ``_find_raw_walker_calls`` -- the same function the real gate
    above calls -- and is *not* absorbed by ``_is_allowlisted`` (a relative
    path constructed under ``tmp_path`` can never match a real ``src/...``
    allowlist entry or migration prefix).
    """
    planted = tmp_path / "planted_walker.py"
    planted.write_text(
        "from specify_cli.core.constants import KITTY_SPECS_DIR\n"
        "\n"
        "def list_all_missions(repo_root):\n"
        "    specs_dir = repo_root / KITTY_SPECS_DIR\n"
        "    return list(specs_dir.iterdir())\n",
        encoding="utf-8",
    )

    hits = _find_raw_walker_calls(planted)
    assert hits == [(5, "iterdir")], (
        "Anti-mutant test failed to detect a planted raw iterdir() enumeration "
        f"of a KITTY_SPECS_DIR-derived path; got {hits!r}. The gate does not "
        "bite -- investigate the taint heuristic before trusting the green "
        "main gate above."
    )

    # And prove it would not be silently absorbed by the allowlist either: no
    # real src/... allowlist entry or migration prefix can match a path
    # rooted under an arbitrary tmp_path.
    fake_rel = f"src/{planted.name}"  # deliberately NOT a real allowlisted path
    assert not _is_allowlisted(fake_rel)


def test_planted_walker_using_conventional_parameter_name_is_detected(
    tmp_path: Path,
) -> None:
    """The parameter-name vocabulary tier also bites (covers threaded params).

    Mirrors the real ``charter_activate.py`` / ``audit/engine.py`` shape: the
    specs directory arrives as an already-resolved parameter (no local
    ``KITTY_SPECS_DIR`` reference in the function body), named by the
    established convention. This proves that tier of the heuristic -- not
    just the direct-reference tier exercised above -- also detects a planted
    violation.
    """
    planted = tmp_path / "planted_threaded_walker.py"
    planted.write_text(
        "def scan_inflight(removed_steps, mission_specs_dir):\n"
        "    for mission_dir in sorted(mission_specs_dir.iterdir()):\n"
        "        pass\n",
        encoding="utf-8",
    )

    hits = _find_raw_walker_calls(planted)
    assert hits == [(2, "iterdir")]


# ---------------------------------------------------------------------------
# Free-function-caller ceiling (D-08): resolve_mission callers must not
# silently multiply.
# ---------------------------------------------------------------------------

# The known count as of this mission (WP04): 8 pre-existing free-function
# callers (audit/engine.py, selector_resolution.py, retrospect.py,
# agent_retrospect.py, mission_type.py, runtime/show_origin.py,
# acceptance/__init__.py) + 1 threaded canonicalizer call
# (missions/_read_path_resolver.py). Bumping this ceiling is a deliberate,
# reviewed edit to this test file -- exactly like any other ratchet constant
# in this codebase (G-2: a count, never a line number).
_KNOWN_RESOLVE_MISSION_CALLER_CEILING = 9


def _find_bare_resolve_mission_calls(path: Path) -> list[int]:
    """Return line numbers of bare ``resolve_mission(...)`` call nodes.

    Mirrors ``test_protection_resolver_call_sites.py``'s detection shape:
    only bare-name calls (``ast.Name`` with ``id == "resolve_mission"``) are
    counted. The function *definition* (``def resolve_mission(...):``) is an
    ``ast.FunctionDef``, not an ``ast.Call``, and never trips this scanner.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "resolve_mission"
    ]


def test_resolve_mission_free_function_callers_do_not_silently_multiply() -> None:
    """A new bare ``resolve_mission(...)`` call site must be a reviewed edit.

    D-08: the dominant read path reaches the ``kitty-specs/`` walk through the
    free function ``resolve_mission``, not only through an assembler-injected
    port. G-1's raw-enumeration ban alone would not stop a tenth caller from
    appearing silently, so this is a companion ceiling on the *call site
    count* -- deliberately a count, not a per-line ratchet (G-2).
    """
    callers: dict[str, list[int]] = {}
    for py_file in sorted(_SRC_ROOT.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        hits = _find_bare_resolve_mission_calls(py_file)
        if hits:
            callers[_rel(py_file)] = hits

    total = sum(len(lines) for lines in callers.values())

    assert total <= _KNOWN_RESOLVE_MISSION_CALLER_CEILING, (
        f"Found {total} bare resolve_mission(...) call sites, exceeding the "
        f"known ceiling of {_KNOWN_RESOLVE_MISSION_CALLER_CEILING}. A new "
        "caller must route through the existing trunk deliberately -- if "
        "this is a legitimate new caller, bump "
        "_KNOWN_RESOLVE_MISSION_CALLER_CEILING in this test as a reviewed "
        f"edit and record it in D-08.\n\nCall sites:\n{callers}"
    )
