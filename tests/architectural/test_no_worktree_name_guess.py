"""Literal-ban ratchet: worktree/branch name-guessing forbidden outside the seam.

This is the **filesystem twin** of the branch-identity seam — the 4th ratchet
assertion guarding the recurring wrong-compose regression class
(#1860 / #1949 / #1978 / #1899). The single canonical naming seam,
``src/specify_cli/lanes/branch_naming.py``, composes AND parses every mission /
lane / worktree / coordination directory name keyed on the declared
``(slug, mission_id)`` (FR-001 / FR-005). Any other module that hand-rolls a
worktree-dir, mission-branch, or mid8-dedup name reintroduces the defect: a
mid8-era mission whose on-disk worktree is ``<slug>-<mid8>-lane-x`` is mis-named
``<slug>-lane-x`` by a bare ``f"{slug}-{lane}"`` guess, so the path never
resolves (the #1899 class).

The ratchet scans every ``*.py`` under ``src/specify_cli/`` and ``src/runtime/``
for THREE forbidden idioms (the squad showed the first two alone miss the actual
recurrence shape):

1. **worktree-dir name-guess** — a ``.worktrees/`` path composed via an
   interpolated f-string, INCLUDING the assign-then-join indirection
   (``name = f"{slug}-{lane}"`` then ``... / ".worktrees" / name``). Caught by
   walking ``/``-division chains where one operand is a ``.worktrees`` literal /
   ``WORKTREES_DIR*`` name and another is an interpolated f-string (directly, or
   via a local name bound earlier in the function to such an f-string).
2. **branch name-guess** — a literal ``f"kitty/mission-{…}"`` (interpolated)
   not produced by the seam.
3. **inline mid8 re-dedup / bare mission-dir compose** — the
   ``…endswith(f"-{mid8}")…`` / ``endswith(suffix)`` compose idiom and the bare
   ``f"{slug}-{mid8}"`` mission-dir composition — the #1860/#1949 recurrence
   shape that carries NO ``.worktrees/`` literal (this is what would catch the
   historical ``tasks.py:844`` / ``_create.py:157`` sites).

Allow-list: exactly the seam module ``lanes/branch_naming.py`` (the sole legal
home of these idioms) plus a SMALL number of narrowly-justified, individually
commented carve-outs for genuinely-benign uses that are NOT a name compose
(e.g. a ``git branch --list`` glob, or a string fed straight back into the seam
PARSER). Each carve-out is a drift-proof ``(enclosing_qualname, token_line)``
composite key — inserting a blank or comment line above a pinned site does NOT
flip the ratchet RED (FR-008 / WP06 re-key).

Design-P REFERENCE implementation (do NOT convert)
--------------------------------------------------
This module is the canonical **reference implementation** of the *Design-P
content-pinned gate-key* pattern, named as such by the refactor-stable doctrine
(the ``testing-principles`` styleguide) and mission
``refactor-stable-gate-substrate-01KWK3FY``. Design-P freezes a tool-derived
``(enclosing_qualname, token)`` comparand (see ``_ALLOWED_SITES_FILES`` above)
and scans live source for set membership, so a gate key is pinned to CONTENT,
never to a raw line number. The pattern's two proof legs live here as the
template every other converted gate mirrors:

* ``test_name_compose_offenders_match_pinned_baseline`` — the staleness guard: a
  frozen allow-list entry with no live offender (or an extra unjustified entry)
  drifts the pinned baseline count and trips RED.
* ``test_composite_key_survives_line_drift`` — the drift theater: shifting a
  pinned site down by blank/comment lines leaves its composite key unchanged, so
  the ratchet stays GREEN on pure line drift.

**These key semantics MUST NOT be converted to seed-derivation** (the
``_RAW_JOIN_SITES`` load-time-seed style). Seed-derivation is content-FOLLOWING:
a fixed line seed still breaks on drift and a content edit is invisible — it
fails both halves of NFR-001 and would REGRESS this file's content-detection.
The mission's research D1 proves this empirically; FR-005's earlier
"convert Family E" plan was CANCELLED for exactly this reason. This file is the
destination pattern, not a conversion target.

WP09 / Issue #1899 / FR-001 / FR-005 / FR-009.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import TypeGuard

import pytest

from tests.architectural._ratchet_keys import composite_key

pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCAN_ROOTS = (
    _REPO_ROOT / "src" / "specify_cli",
    _REPO_ROOT / "src" / "runtime",
)

# The single canonical naming seam. It is the ONLY module permitted to compose
# worktree-dir / mission-branch / mid8-dedup names by literal/f-string — every
# other module must route through its public API
# (worktree_path / worktree_dir_name / mission_branch_name_required /
# coord_* / mission_dir_name).
_SEAM_REL = "src/specify_cli/lanes/branch_naming.py"

# Marker for the ``.worktrees`` directory literal (matches the bare name and a
# ``.worktrees/...`` leading-segment literal).
_WORKTREES_NAME = ".worktrees"

# Idiom 3 keys on the **mid8 disambiguator** specifically — the token the
# #1860/#1949 recurrence class drops or double-appends. A generic ``f"{a}-{b}"``
# or ``endswith(suffix)`` for path/glob matching is NOT the recurrence shape and
# must NOT be flagged (it would drown the real signal in false positives). The
# detector therefore requires the interpolation/suffix to reference ``mid8``.
_MID8_TOKEN_RE = re.compile(r"\bmid8\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Narrow, individually-justified allow-list (NOT broad carve-outs).
# Each entry is a drift-proof ``(enclosing_qualname, token_line)`` composite
# key (FR-008 / WP06).  Inserting a blank or comment line above a pinned site
# leaves the key unchanged; only a semantic edit (rename the function or change
# the guarded line) produces a new key.
# ---------------------------------------------------------------------------

# Stale-detection map: composite_key → relative file path (used ONLY by
# ``test_allow_list_entries_are_real_and_benign`` to verify the key is still
# live in the expected file; not used for the ratchet lookup itself).
_ALLOWED_SITES_FILES: dict[tuple[str, str], str] = {
    # ── recovery.py: a ``git branch --list`` GLOB pattern, not a compose ──
    # ``f"kitty/mission-{mission_slug}*"`` (trailing ``*``) is passed to
    # ``git branch --list`` to ENUMERATE existing branches; it never names a
    # branch to create. Benign UX/listing glob.
    ("_list_mission_branches", "pattern ="): "src/specify_cli/lanes/recovery.py",
    # ── vcs/detection.py: string fed straight back into the seam PARSER ──
    # ``parse_mission_slug_from_branch(f"kitty/mission-{worktree_name}")``
    # round-trips a worktree dir name THROUGH the canonical seam parser to
    # decode it — it decodes, it does not name/create a branch.
    (
        "_get_locked_vcs_from_feature",
        "parsed = parse_mission_slug_from_branch ( )",
    ): "src/specify_cli/core/vcs/detection.py",
    # ── lifecycle_sync.py: error-report placeholder, NOT a worktree lookup ──
    # ``repo_root / WORKTREES_DIRNAME / f"{mission_slug}-unknown"`` lives in
    # the ``CorruptLanesError`` branch — a human-readable diagnostic placeholder;
    # the path is reported, not opened.  Benign: not a name-guess of a real worktree.
    (
        "sync_lane_after_coordination_commit",
        "lane_worktree_path = repo_root / WORKTREES_DIRNAME / ,",
    ): "src/specify_cli/lanes/lifecycle_sync.py",
    # NOTE: the previously-allow-listed pre-existing ``<slug>-<mid8>`` composes
    # (``mission_creation.py:321`` / ``worktree.py:367`` / ``worktree.py:370``)
    # have been ROUTED through ``mission_dir_name()`` / ``resolve_mid8()`` (the
    # #2000 follow-up landed). The detector now flags ZERO offenders at those
    # sites, so the carve-outs were dropped (a stale exemption is a
    # false-negative window). The
    # ``test_name_compose_offenders_match_pinned_baseline`` cross-check below
    # pins the offender count so a re-grown stale allow-list entry is caught.
    # ── surface_resolver.py: _coord_mid8 fail-closed raise payload (idiom 1) ──
    # post-merge addition (coord-primary-partition-lock-01KWZ46V, squash-merged
    # 007528ddf): ``coord_candidate = repo_root / ".worktrees" /
    # f"{mission_slug}-coord" / KITTY_SPECS_DIR / mission_slug`` composes a
    # ``.worktrees``-shaped Path ONLY to populate the ``StatusReadPathNotFound``
    # diagnostic ``raise`` payload — the same site already dispositioned DIAG
    # (no FS sink) in ``test_single_mission_surface_resolver.py`` /
    # ``surface_resolution_audit/inventory.md`` /
    # ``untrusted_path_audit/inventory.md``. It replaced a
    # ``CoordinationWorkspace.worktree_path(...)`` seam call (#2091, invariant
    # M-1: that seam now REQUIRES a non-empty mid8 and would raise a DIFFERENT
    # exception before this more specific fail-closed one could raise) — no git
    # worktree is ever created/looked up from this value; it is raised
    # immediately.
    ("_coord_mid8", "coord_candidate = repo_root"): (
        "src/specify_cli/coordination/surface_resolver.py"
    ),
    # ── workspace.py: CoordinationWorkspaceIdentityUnresolved diagnostic (idiom 2) ──
    # post-merge addition (coord-primary-partition-lock-01KWZ46V, same commit):
    # the exception's message is a human-readable string that names the
    # malformed-shape placeholder ``'kitty/mission-<slug>-'`` (angle brackets,
    # not an f-string field) and separately interpolates the real
    # ``mission_slug`` elsewhere in the same sentence ("for mission
    # {mission_slug!r}"). The idiom-2 literal-text check does not distinguish
    # "field interpolated inside the kitty/mission- segment" from "field
    # interpolated anywhere in the concatenated string", so it flags this
    # prose. No branch/worktree/dir name is ever composed or used from this
    # string — it is raised as a StructuredError message and never parsed back
    # into a ref (same finding already carved out in
    # ``test_topology_resolution_boundary.py::_ALLOWLISTED_LEGACY_COMPOSE_SITES``).
    (
        "CoordinationWorkspaceIdentityUnresolved.__init__",
        "",
    ): "src/specify_cli/coordination/workspace.py",
}

_ALLOWED_SITES: frozenset[tuple[str, str]] = frozenset(_ALLOWED_SITES_FILES)

# Pinned count of name-COMPOSE offenders the detector currently flags across the
# scan roots (excluding the seam), pinned as a committed literal so the
# allow-list cannot rot undetected. Mirrors the short-id ratchet's
# ``_SHORTID_BASELINE_RAW_MATCHES``: a stale allow-list entry (one that no longer
# points at a live offender) or an extra unjustified entry would drift this
# count and trip the cross-check. Composition (verified at this baseline land):
#   recovery.py:135                    (branch-list glob — benign carve-out)
#   vcs/detection.py:161               (seam-parser round-trip — benign carve-out)
#   lifecycle_sync.py:135              (corrupt-lanes diagnostic placeholder — benign)
#   surface_resolver.py:499            (post-merge coord-primary-partition-lock
#                                        01KWZ46V — _coord_mid8 DIAG raise payload,
#                                        benign carve-out)
#   workspace.py:123                   (post-merge coord-primary-partition-lock
#                                        01KWZ46V — CoordinationWorkspaceIdentityUnresolved
#                                        diagnostic message, benign carve-out)
# => 5 raw offenders, all accounted for by the allow-list => 0 un-accounted.
_NAME_COMPOSE_BASELINE_RAW_MATCHES = 5

# Helper text appended to every failure so the offender knows the fix.
_SEAM_GUIDANCE = (
    "Route the compose through the canonical naming seam "
    f"(`{_SEAM_REL}`): use worktree_path()/worktree_dir_name() for worktree "
    "dirs, mission_branch_name_required()/coord_branch_name() for branches, and "
    "mission_dir_name()/coord_mission_dir_name() for mission dirs. Do NOT "
    "hand-roll a `.worktrees/` f-string, a `kitty/mission-{...}` literal, or an "
    "inline `endswith(f\"-{mid8}\")` dedup outside the seam."
)


def _rel(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def _iter_source_files() -> list[Path]:
    files: list[Path] = []
    for root in _SCAN_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            files.append(path)
    return files


def _is_interpolated_fstring(node: ast.AST) -> TypeGuard[ast.JoinedStr]:
    """True for an f-string carrying at least one ``{...}`` interpolation."""
    return isinstance(node, ast.JoinedStr) and any(
        isinstance(value, ast.FormattedValue) for value in node.values
    )


def _is_worktrees_literal(node: ast.AST) -> bool:
    """True for a ``.worktrees`` / ``.worktrees/...`` string literal."""
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and (node.value == _WORKTREES_NAME or node.value.startswith(_WORKTREES_NAME + "/"))
    )


def _is_worktrees_name(node: ast.AST) -> bool:
    """True for a ``WORKTREES_DIR`` / ``WORKTREES_DIRNAME`` style identifier."""
    return isinstance(node, ast.Name) and "WORKTREES" in node.id.upper()


def _flatten_div_operands(node: ast.BinOp) -> list[ast.expr]:
    """Flatten a left-assoc ``a / b / c`` Div chain into its leaf operands."""
    operands: list[ast.expr] = []
    stack: list[ast.expr] = [node]
    while stack:
        current = stack.pop()
        if isinstance(current, ast.BinOp) and isinstance(current.op, ast.Div):
            stack.append(current.left)
            stack.append(current.right)
        else:
            operands.append(current)
    return operands


def _collect_fstring_bound_names(tree: ast.AST) -> set[str]:
    """Names bound to an interpolated f-string (assign-then-join indirection).

    ``name = f"{slug}-{lane}"`` followed by ``... / ".worktrees" / name`` must
    still be caught, so a join operand that is a local ``Name`` bound to an
    interpolated f-string counts as the f-string for idiom 1.
    """
    bound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _is_interpolated_fstring(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bound.add(target.id)
        elif (
            isinstance(node, ast.AnnAssign)
            and node.value is not None
            and _is_interpolated_fstring(node.value)
            and isinstance(node.target, ast.Name)
        ):
            bound.add(node.target.id)
    return bound


def _collect_mid8_suffix_names(tree: ast.AST) -> set[str]:
    """Names bound to a mid8-referencing f-string suffix (``suffix = f"-{mid8}"``).

    The endswith-dedup idiom 3 has an assign-then-test variant: a local (commonly
    ``suffix``) is bound to an interpolated f-string that resolves the mid8, then
    tested with ``X.endswith(suffix)``. Track exactly those names so the test can
    flag the dedup without flagging generic ``endswith(suffix)`` glob/path checks.
    """
    bound: set[str] = set()
    for node in ast.walk(tree):
        value: ast.expr | None = None
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            value, targets = node.value, list(node.targets)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            value, targets = node.value, [node.target]
        if value is None or not _is_interpolated_fstring(value):
            continue
        if not _references_mid8(value):
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                bound.add(target.id)
    return bound


def _operand_is_interpolated(node: ast.expr, fstring_names: set[str]) -> bool:
    """True if a join operand is an interpolated f-string (direct or via a name)."""
    if _is_interpolated_fstring(node):
        return True
    return isinstance(node, ast.Name) and node.id in fstring_names


def _fstring_literal_text(node: ast.JoinedStr) -> str:
    """Concatenated literal (non-interpolated) text of an f-string."""
    return "".join(
        str(value.value)
        for value in node.values
        if isinstance(value, ast.Constant)
    )


def _references_mid8(node: ast.AST) -> bool:
    """True when an expression references the ``mid8`` disambiguator.

    Matches both a ``mid8(...)`` call and a name/attribute carrying ``mid8``
    (e.g. ``mid8_value``, ``meta.mid8``). Keyed on ``mid8`` specifically so the
    detector targets the recurrence token, not arbitrary string composition.
    """
    return bool(_MID8_TOKEN_RE.search(ast.unparse(node)))


def _is_bare_mid8_dir_compose(node: ast.JoinedStr) -> bool:
    """True for a bare ``f"{slug}-{mid8}"`` mission-dir compose (idiom 3).

    Recurrence shape with NO ``.worktrees/`` literal: exactly two interpolations
    joined by a single ``-`` and nothing else, where the SECOND interpolation
    resolves the ``mid8`` disambiguator. This is the #1860/#1949 shape that
    historically surfaced at ``tasks.py:844`` / ``_create.py:157`` — the canonical
    ``<human-slug>-<mid8>`` mission/worktree dir name that must be produced by the
    seam's ``mission_dir_name()`` / ``worktree_dir_name()`` instead.
    """
    interpolations = [v for v in node.values if isinstance(v, ast.FormattedValue)]
    if len(interpolations) != 2:
        return False
    if _fstring_literal_text(node) != "-":
        return False
    # The disambiguator is the trailing token; require it to reference mid8.
    return _references_mid8(interpolations[1].value)


def _scan_file(path: Path) -> dict[int, str]:
    """Return ``{lineno: idiom-label}`` for every forbidden idiom in ``path``."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return {}

    fstring_names = _collect_fstring_bound_names(tree)
    mid8_suffix_names = _collect_mid8_suffix_names(tree)
    violations: dict[int, str] = {}

    for node in ast.walk(tree):
        # Idiom 1 — worktree-dir name-guess: a ``/`` join chain mixing a
        # ``.worktrees`` literal/name with an interpolated f-string (direct or
        # via an assign-then-join local name).
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            operands = _flatten_div_operands(node)
            has_worktrees = any(
                _is_worktrees_literal(op) or _is_worktrees_name(op) for op in operands
            )
            has_fstring = any(
                _operand_is_interpolated(op, fstring_names) for op in operands
            )
            if has_worktrees and has_fstring:
                violations[node.lineno] = "worktree-dir name-guess (idiom 1)"
            continue

        # Idiom 3 — inline mid8 re-dedup: ``X.endswith(f"-{mid8}")`` /
        # ``X.endswith(suffix)`` (with ``suffix = f"-{mid8}"``) used to gate a
        # manual ``<slug>-<mid8>`` mission-dir compose. Keyed on mid8 so a
        # generic ``endswith(suffix)`` glob/path test is NOT flagged.
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "endswith"
            and node.args
        ):
            arg = node.args[0]
            if _is_interpolated_fstring(arg) and _references_mid8(arg):
                # ``endswith(f"-{mid8}")`` — the canonical dedup shape.
                violations[node.lineno] = "inline mid8 re-dedup endswith (idiom 3)"
            elif isinstance(arg, ast.Name) and arg.id in mid8_suffix_names:
                # ``endswith(suffix)`` where ``suffix = f"...{mid8}"`` — the
                # assign-then-test variant of the same dedup.
                violations[node.lineno] = "inline mid8 re-dedup endswith (idiom 3)"
            continue

        if _is_interpolated_fstring(node):
            literal_text = _fstring_literal_text(node)
            # Idiom 2 — branch name-guess: a ``kitty/mission-{...}`` f-string.
            if "kitty/mission-" in literal_text:
                violations[node.lineno] = "branch name-guess kitty/mission- (idiom 2)"
            # Idiom 3 (no-.worktrees variant) — bare ``f"{slug}-{mid8}"`` dir.
            elif _is_bare_mid8_dir_compose(node):
                violations[node.lineno] = "bare slug-mid8 mission-dir compose (idiom 3)"

    return violations


def test_no_worktree_or_branch_name_guess_outside_seam() -> None:
    """No worktree/branch/mid8 name-guess may live outside the canonical seam.

    Composing or de-duplicating a worktree-dir, mission-branch, or mission-dir
    name by hand anywhere other than ``lanes/branch_naming.py`` reintroduces the
    #1860/#1949/#1899 wrong-compose class. The seam is the sole legal home; a
    short, individually-justified allow-list carves out the provably-benign
    non-compose uses (a listing glob, a seam-parser round-trip).
    """
    offenders: list[str] = []

    for path in _iter_source_files():
        rel = _rel(path)
        if rel == _SEAM_REL:
            # The seam itself is where these idioms legally live.
            continue
        source = path.read_text(encoding="utf-8")
        for lineno, label in sorted(_scan_file(path).items()):
            key = composite_key(source, lineno)
            if key in _ALLOWED_SITES:
                continue
            offenders.append(f"  {rel}:{lineno}: {label}")

    if offenders:
        pytest.fail(
            "Forbidden worktree/branch name-guess found outside the canonical "
            "naming seam — this reintroduces the #1860/#1949/#1899 wrong-compose "
            "regression class.\n\n"
            "Offending sites:\n"
            + "\n".join(sorted(offenders))
            + "\n\n"
            + _SEAM_GUIDANCE
        )


def test_allow_list_entries_are_real_and_benign() -> None:
    """Every allow-list composite key must still be live in its expected file.

    Guards against the allow-list silently rotting (a carved-out qualname or
    token-line changes, leaving a stale exemption that could mask a future
    regression at the same site).  Each key in ``_ALLOWED_SITES_FILES`` is
    verified by re-scanning the mapped file and confirming the composite key
    appears at least once.
    """
    stale: list[str] = []
    for key, rel in sorted(_ALLOWED_SITES_FILES.items(), key=lambda kv: kv[1]):
        abs_path = _REPO_ROOT / rel
        if not abs_path.is_file():
            stale.append(f"{rel!r} key={key!r} (file missing)")
            continue
        source = abs_path.read_text(encoding="utf-8")
        # Re-scan the file and collect all composite keys it produces.
        live_keys = {
            composite_key(source, ln) for ln in _scan_file(abs_path)
        }
        if key not in live_keys:
            stale.append(
                f"{rel!r} key={key!r} (no longer a flagged site in the file — "
                "function renamed or code line changed; update or drop)"
            )
    assert stale == [], (
        "Stale allow-list entries (the composite key no longer matches a live "
        "offender in the expected file — re-verify and update or drop):\n  "
        + "\n  ".join(stale)
    )


def test_name_compose_offenders_match_pinned_baseline() -> None:
    """The name-compose offender count is objectively pinned and fully accounted.

    Mirrors ``test_shortid_consumer_class_is_empty_against_pinned_baseline`` for
    the name-COMPOSE detector (whose only prior hygiene check,
    ``test_allow_list_entries_are_real_and_benign``, verified merely that an
    allow-listed line *exists* — not that it is still an offender). A stale
    allow-list entry (one that no longer points at a live compose) leaves a
    silent false-negative window; this cross-check catches it two ways:

      1. the live raw offender count must equal the committed literal, and
      2. every raw offender must be accounted for by the allow-list (zero
         un-accounted), so an *extra* unjustified entry cannot hide either.
    """
    raw_offenders: list[tuple[str, str]] = []
    for path in _iter_source_files():
        rel = _rel(path)
        if rel == _SEAM_REL:
            continue  # the seam is the legal home of these idioms
        source = path.read_text(encoding="utf-8")
        for lineno in sorted(_scan_file(path)):
            raw_offenders.append(composite_key(source, lineno))

    assert len(raw_offenders) == _NAME_COMPOSE_BASELINE_RAW_MATCHES, (
        "Pinned name-compose baseline drifted. Expected "
        f"{_NAME_COMPOSE_BASELINE_RAW_MATCHES} raw name-compose offenders across "
        f"the scan roots, found {len(raw_offenders)}:\n  "
        + "\n  ".join(str(k) for k in sorted(raw_offenders))
        + "\n\nIf a NEW offender appeared, route it through the canonical seam. "
        "If an allow-listed offender was legitimately removed (routed through "
        "the seam), drop its allow-list entry AND update "
        "_NAME_COMPOSE_BASELINE_RAW_MATCHES (and the composition comment)."
    )

    unaccounted = [key for key in raw_offenders if key not in _ALLOWED_SITES]
    assert unaccounted == [], (
        "Name-compose offenders not covered by the allow-list (each is a REAL "
        "name-guess outside the seam — route it through the canonical seam, do "
        "NOT add an allow-list entry without a justification proving it is not a "
        "compose):\n  " + "\n  ".join(str(k) for k in sorted(unaccounted))
    )

    # Inverse guard: every allow-list entry must STILL be a live offender, so a
    # stale exemption (the renata GAP) cannot survive. Combined with the count
    # assertion above this makes the allow-list exactly the offender set.
    stale_exemptions = sorted(set(_ALLOWED_SITES) - set(raw_offenders))
    assert stale_exemptions == [], (
        "Stale name-compose allow-list entries (the composite key is no longer a "
        "live offender the detector flags — the site was routed through the seam; "
        "drop the exemption to close the false-negative window):\n  "
        + "\n  ".join(str(k) for k in stale_exemptions)
    )


# ===========================================================================
# WP02 (this mission) — AST short-id slice detector + failover-bypass rule.
#
# A SECOND ratchet, distinct from the name-COMPOSE idioms above: it forbids
# hand-derived mission ``mid8`` SHORT-IDs (``mission_id[:8]`` and friends)
# outside the single sanctioned derivation home. The recurring defect this
# guards (FR-004 / FR-010) is a consumer that re-slices the mission_id to a
# mid8 instead of routing through ``resolve_mid8`` — the failover-aware
# entrypoint that reconciles a stale slug tail against the declared identity.
# A bare ``mission_id[:8]`` skips that reconciliation and silently mis-routes
# a colliding-tail mission (the #1899 / #1978 class).
#
# ⚠️ HONESTY NOTE — scope and known limits (binding; do NOT overclaim):
#   * This is a **syntax-level tripwire**, not a completeness oracle. It is
#     defeated by helper indirection: ``def _short(x): return x[:8]`` then
#     ``_short(mission_id)`` carries no ``[:8]`` at the call site and escapes.
#     The real correctness guarantee for this mission is
#     verification-by-deletion: WP03/WP04/WP05 deleted every consumer slice and
#     the suite stayed green. This ratchet only stops a *future* regrowth of
#     the exact syntactic shape.
#   * AST cannot structurally distinguish ``mission_id`` from ``invocation_id``
#     or a content hash — detection rests on a NAME predicate (substring
#     ``mission_id`` / ``mid``). The predicate is deliberately a SUBSTRING/glob,
#     never exact-match, so ``str(raw_mission_id)[:8]`` and ``mission_id_meta``
#     (the original blind spots Paula found) cannot escape via a wrapper or a
#     suffix.
#   * It explicitly does **NOT** cover the deferred ``feature_dir.parent.parent``
#     repo-root-derivation class (~9 sites), which is owned by the read-path /
#     error-fidelity follow-on focus (#2007), not this mission.
# ===========================================================================

# The short-id detector scans ALL of ``src/`` (FR-004 / FR-010 routing is
# repo-wide), NOT just the ``specify_cli`` + ``runtime`` subset the name-COMPOSE
# detector above uses — because one of the sanctioned homes
# (``mission_runtime/context.py``) and potential consumers (``mission_runtime``,
# ``charter``, ``glossary``, ...) live outside that subset. Benign content-hash
# / state slices in those packages carry neither ``mission_id`` nor ``mid`` in
# the operand name, so the name predicate spares them.
_SHORTID_SCAN_ROOT = _REPO_ROOT / "src"


def _iter_shortid_source_files() -> list[Path]:
    """Every ``*.py`` under ``src/`` (the short-id detector's repo-wide scope)."""
    files: list[Path] = []
    if _SHORTID_SCAN_ROOT.exists():
        for path in sorted(_SHORTID_SCAN_ROOT.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            files.append(path)
    return files


# The two permanent sanctioned slice HOMES, skipped at FILE level (the
# ``_SEAM_REL`` home-skip pattern). ``mission_id[:8]`` is legitimate ONLY here:
#   * branch_naming.py — ``_mid8`` / ``resolve_mid8`` are THE single-derivation
#     primitive + its failover-aware public door.
#   * mission_runtime/context.py — ``IdentityFragment`` computes the mid8
#     "here and nowhere else" (its own docstring) and self-checks the invariant.
_SHORTID_HOME_FILES: frozenset[str] = frozenset(
    {
        "src/specify_cli/lanes/branch_naming.py",
        "src/mission_runtime/context.py",
    }
)

# The single canonical failover-aware short-id entrypoint every consumer must
# route through instead of re-slicing.
_SHORTID_SEAM = "resolve_mid8"

# Substring tokens (case-insensitive) that mark a sliced operand as the
# mission-identity shape. SUBSTRING, not exact-match — that is the whole point:
#   ``mission_id`` catches ``mission_id`` / ``raw_mission_id`` / ``mission_id_meta``
#                  / ``self.mission_id`` (attr) ;
#   ``mid``        catches ``mid`` / ``mid8`` / ``raw_mid`` / ``_mid8``.
# A pure ``invocation_id`` / content-hash operand contains NEITHER token, so it
# is not flagged (and ``invocation_id[:8]`` is additionally named-out below).
_MISSION_ID_NAME_TOKENS: tuple[str, ...] = ("mission_id", "mid")

# Named exclusion: a DIFFERENT identity domain that legitimately slices its own
# id. ``invocation/executor.py`` formats an invocation_id short-tag for a log
# line; it is not a mission mid8 and the name predicate already excludes it, but
# we pin it by name so the intent is explicit and self-documenting.
# Keyed as (enclosing_qualname, token_line) composite (FR-008 / WP06 re-key).
# ``invocation_id[:8]`` lives inside an f-string on Python 3.11 so the
# tokenize-based token_line strips the f-string body → ``"message ="``.
# The qualname ``ProfileInvocationExecutor._commit_op_record`` distinguishes it
# from any future ``message =`` line in a different method.
_SHORTID_NAMED_EXCLUSIONS: frozenset[tuple[str, str]] = frozenset(
    {
        # src/specify_cli/invocation/executor.py:469
        ("ProfileInvocationExecutor._commit_op_record", "message ="),
    }
)

# Stale-detection map for named exclusions: composite_key → relative file path.
_SHORTID_NAMED_EXCLUSIONS_FILES: dict[tuple[str, str], str] = {
    ("ProfileInvocationExecutor._commit_op_record", "message ="): (
        "src/specify_cli/invocation/executor.py"
    ),
}

# Narrow, individually-justified short-id allow-list (composite key).
# The mission-identity CONSUMER class is otherwise EMPTY after WP03/WP04/WP05
# routed every site; only this deliberate diagnostic-tolerance fallback remains.
# Keyed as (enclosing_qualname, token_line) composite (FR-008 / WP06 re-key).
# The two doctor.py sites are byte-identical in source but live in DIFFERENT
# functions — the composite key disambiguates them via the qualname component.
_SHORTID_ALLOWED_SITES: frozenset[tuple[str, str]] = frozenset(
    {
        # ── _coordination_doctor.py — diagnostic short-id TOLERANCE, not a missed route ──
        # ``short = resolve_mid8(slug, mission_id=mission_id) or mission_id[:8]``
        # inside ``_check_coordination_worktree_health`` (moved from doctor.py by #2059).
        # WP03 routed the derivation through the failover-aware ``resolve_mid8``;
        # the ``or mission_id[:8]`` tail is a CONSCIOUS fallback that keeps the
        # doctor diagnostic emitting a display short-id even when resolve_mid8
        # declines to ``""`` (e.g. a malformed/short mission_id). Tolerance branch.
        (
            "_check_coordination_worktree_health",
            "short = resolve_mid8 ( mission_slug , mission_id = mission_id ) or mission_id [ : 8 ]",
        ),
        # ── _coordination_doctor.py — same idiom, different function ──
        # Inside ``_check_lane_sparse_checkout_drift``.  Byte-identical source
        # line; distinct qualname makes the composite key unique (T025-distinct-keys).
        (
            "_check_lane_sparse_checkout_drift",
            "short = resolve_mid8 ( mission_slug , mission_id = mission_id ) or mission_id [ : 8 ]",
        ),
    }
)

# Stale-detection map for the short-id allow-list: composite_key → relative file path.
# #2059 moved both tolerance sites out of ``doctor.py`` into the ``_coordination_doctor``
# sibling (same functions, byte-identical lines); the composite keys are unchanged, only
# the home file moved.
_SHORTID_ALLOWED_SITES_FILES: dict[tuple[str, str], str] = {
    (
        "_check_coordination_worktree_health",
        "short = resolve_mid8 ( mission_slug , mission_id = mission_id ) or mission_id [ : 8 ]",
    ): "src/specify_cli/cli/commands/_coordination_doctor.py",
    (
        "_check_lane_sparse_checkout_drift",
        "short = resolve_mid8 ( mission_slug , mission_id = mission_id ) or mission_id [ : 8 ]",
    ): "src/specify_cli/cli/commands/_coordination_doctor.py",
}

# Pre-mission baseline of mission-identity ``[:8]`` slices across ``src/`` (the
# raw count BEFORE home/allow-list filtering), pinned as a committed literal so
# "the consumer class is empty" is an OBJECTIVE, diff-checkable claim rather
# than a re-derivation of the live tree. Composition (verified at WP02 land):
#   branch_naming.py:146/199/415  (3, HOME)
#   mission_runtime/context.py:99/112  (2, HOME)
#   cli/commands/_coordination_doctor.py  (2, allow-listed tolerance; moved from
#       doctor.py by #2059)
# => 7 raw matches; 5 in homes + 2 allow-listed => 0 un-accounted consumers.
_SHORTID_BASELINE_RAW_MATCHES = 7


def _unwrap_str_call(node: ast.expr) -> ast.expr:
    """Unwrap a single ``str(<expr>)`` call to its inner argument.

    ``str(raw_mission_id)[:8]`` slices the *call* node; the identity-bearing
    name is the call argument. Unwrapping lets the substring predicate see
    ``raw_mission_id`` instead of the opaque ``str(...)`` text — closing the
    string-wrapped blind spot (M1).
    """
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "str"
        and len(node.args) == 1
    ):
        return node.args[0]
    return node


def _operand_is_mission_identity(node: ast.expr) -> bool:
    """True if the sliced operand names the mission-identity shape.

    Substring (not exact) match on the unparsed operand text — after unwrapping
    a ``str(...)`` wrapper — against ``mission_id`` / ``mid``. Substring is
    deliberate: an exact-match predicate would let ``str(raw_mission_id)`` and
    ``mission_id_meta`` escape (the original recurrence blind spots).
    """
    text = ast.unparse(_unwrap_str_call(node)).lower()
    return any(token in text for token in _MISSION_ID_NAME_TOKENS)


def _is_eight_slice(node: ast.AST) -> bool:
    """True for a subscript slice ``X[:8]`` / ``X[0:8]`` (no step)."""
    if not isinstance(node, ast.Subscript):
        return False
    sl = node.slice
    if not isinstance(sl, ast.Slice) or sl.step is not None:
        return False
    lower_ok = sl.lower is None or (
        isinstance(sl.lower, ast.Constant) and sl.lower.value == 0
    )
    upper_ok = isinstance(sl.upper, ast.Constant) and sl.upper.value == 8
    return lower_ok and upper_ok


def _scan_shortid_file(path: Path) -> dict[int, str]:
    """Return ``{lineno: label}`` for forbidden short-id idioms in ``path``.

    Two idioms:
      * **slice** — a mission-identity ``[:8]`` slice (incl. ``str(<id>)[:8]``).
      * **bypass** — a bare ``_mid8(...)`` call to the now-private primitive
        (the failover-bypass rule, T019): consumers must call ``resolve_mid8``,
        not the unguarded private slice primitive.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return {}

    violations: dict[int, str] = {}
    for node in ast.walk(tree):
        if _is_eight_slice(node):
            assert isinstance(node, ast.Subscript)  # narrowed by _is_eight_slice
            if _operand_is_mission_identity(node.value):
                operand = ast.unparse(node.value)
                violations[node.lineno] = (
                    f"mission-identity short-id slice `{operand}[:8]` — route "
                    f"through `{_SHORTID_SEAM}` (failover-aware), do not re-slice"
                )
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_mid8"
        ):
            violations[node.lineno] = (
                "bare `_mid8(...)` call bypasses the failover entrypoint — "
                f"route through `{_SHORTID_SEAM}` instead of the private primitive"
            )
    return violations


def _iter_shortid_offenders() -> list[str]:
    """Collect ``file:line: label`` for every un-accounted short-id idiom."""
    offenders: list[str] = []
    for path in _iter_shortid_source_files():
        rel = _rel(path)
        if rel in _SHORTID_HOME_FILES:
            # Sanctioned derivation homes — skipped at file level.
            continue
        source = path.read_text(encoding="utf-8")
        for lineno, label in sorted(_scan_shortid_file(path).items()):
            key = composite_key(source, lineno)
            if key in _SHORTID_NAMED_EXCLUSIONS or key in _SHORTID_ALLOWED_SITES:
                continue
            offenders.append(f"  {rel}:{lineno}: {label}")
    return offenders


def test_no_mission_shortid_slice_or_failover_bypass_outside_seam() -> None:
    """No mission-identity ``mid8`` short-id may be hand-derived outside the seam.

    The mission-identity CONSUMER class must be EMPTY: every consumer routes its
    mid8 through ``resolve_mid8`` (FR-004 / FR-010). The two sanctioned
    derivation homes (``branch_naming.py``, ``mission_runtime/context.py``) are
    skipped at file level; ``invocation_id[:8]`` is a different identity domain
    excluded by name; the doctor diagnostic-tolerance ``or mission_id[:8]`` is a
    single justified allow-list entry. Anything else is a real missed route.
    """
    offenders = _iter_shortid_offenders()
    if offenders:
        pytest.fail(
            "Forbidden mission-identity short-id derivation found outside the "
            "sanctioned home — this reintroduces the colliding-tail mis-route "
            "class (#1899 / #1978). A bare `mission_id[:8]` (or `_mid8(...)`) "
            "skips the failover reconciliation in `resolve_mid8`.\n\n"
            "Offending sites (each is a REAL missed route — do NOT allow-list "
            "without a justification that proves it is not a consumer):\n"
            + "\n".join(sorted(offenders))
            + f"\n\nRoute the derivation through `{_SHORTID_SEAM}` "
            "(`src/specify_cli/lanes/branch_naming.py`)."
        )


def test_shortid_consumer_class_is_empty_against_pinned_baseline() -> None:
    """The un-accounted short-id consumer count is objectively zero.

    Pins the pre-mission raw match count as a committed literal and asserts the
    live tree's accounting (homes + named exclusions + allow-list) leaves zero
    un-accounted consumers, so "the consumer class is empty" is diff-checkable
    rather than a re-derivation of whatever the tree happens to contain.
    """
    raw_matches: list[tuple[str, tuple[str, str]]] = []
    for path in _iter_shortid_source_files():
        rel = _rel(path)
        source = path.read_text(encoding="utf-8")
        for lineno, label in sorted(_scan_shortid_file(path).items()):
            if "short-id slice" not in label:
                continue  # count slices only for the baseline, not _mid8 calls
            raw_matches.append((rel, composite_key(source, lineno)))

    assert len(raw_matches) == _SHORTID_BASELINE_RAW_MATCHES, (
        "Pinned short-id baseline drifted. Expected "
        f"{_SHORTID_BASELINE_RAW_MATCHES} raw mission-identity `[:8]` slices "
        f"across src/, found {len(raw_matches)}:\n  "
        + "\n  ".join(f"{r}: {k}" for r, k in sorted(raw_matches))
        + "\n\nIf a NEW slice appeared, it is almost certainly a missed route — "
        "route it through `resolve_mid8`. If a home/allow-listed slice was "
        "legitimately removed, update _SHORTID_BASELINE_RAW_MATCHES (and the "
        "composition comment) to match."
    )

    # Every raw match must be accounted for by a home, a named exclusion, or the
    # allow-list — leaving an EMPTY un-accounted consumer set.
    unaccounted = [
        f"{rel}: {key}"
        for rel, key in raw_matches
        if rel not in _SHORTID_HOME_FILES
        and key not in _SHORTID_NAMED_EXCLUSIONS
        and key not in _SHORTID_ALLOWED_SITES
    ]
    assert unaccounted == [], (
        "The mission-identity short-id CONSUMER class is not empty — these "
        "slices are neither in a sanctioned home nor justified in the "
        "allow-list:\n  " + "\n  ".join(sorted(unaccounted))
    )


def test_shortid_detector_self_test_flags_all_five_shapes() -> None:
    """The detector flags all 5 recurrence shapes and spares ``invocation_id``.

    Plants each shape Paula found into an in-memory module and asserts the
    scanner flags it; plants ``invocation_id[:8]`` (a different identity domain)
    and asserts it is NOT flagged. Guards the substring predicate against
    silently regressing to exact-match (which would let the wrapped/suffixed
    shapes escape).
    """
    flagged_source = (
        "mission_id[:8]\n"
        "str(raw_mission_id)[:8]\n"
        "mid[:8]\n"
        "raw_mid[:8]\n"
        "mission_id_meta[:8]\n"
    )
    not_flagged_source = "invocation_id[:8]\n"

    flagged_tree = ast.parse(flagged_source)
    flagged: list[str] = []
    for node in ast.walk(flagged_tree):
        if _is_eight_slice(node):
            assert isinstance(node, ast.Subscript)
            if _operand_is_mission_identity(node.value):
                flagged.append(ast.unparse(node.value))

    assert flagged == [
        "mission_id",
        "str(raw_mission_id)",
        "mid",
        "raw_mid",
        "mission_id_meta",
    ], f"detector missed a recurrence shape; flagged only: {flagged}"

    not_flagged_tree = ast.parse(not_flagged_source)
    for node in ast.walk(not_flagged_tree):
        if _is_eight_slice(node):
            assert isinstance(node, ast.Subscript)
            assert not _operand_is_mission_identity(node.value), (
                "invocation_id[:8] is a different identity domain and must NOT "
                "be flagged by the mission-identity short-id detector"
            )


def test_shortid_failover_bypass_self_test() -> None:
    """The failover-bypass rule flags a bare ``_mid8(...)`` call.

    The now-private ``_mid8`` primitive slices without the failover
    reconciliation; a consumer calling it directly bypasses ``resolve_mid8``.
    Plants such a call (outside any home) and asserts it is flagged.
    """
    bypass_source = "x = _mid8(mission_id)\n"
    tree = ast.parse(bypass_source)
    flagged = False
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_mid8"
        ):
            flagged = True
    assert flagged, "failover-bypass rule must flag a bare `_mid8(...)` call"


def test_shortid_allow_list_entries_are_real() -> None:
    """Every short-id allow-list / named-exclusion composite key is still live.

    Mirrors ``test_allow_list_entries_are_real_and_benign`` for the short-id
    carve-outs: a stale composite key (qualname renamed or code line changed)
    could silently mask a future regression at the same site.

    * **Allow-list entries** are verified against the scanner: the composite key
      must still appear in ``_scan_shortid_file`` output for the mapped file.
    * **Named-exclusion entries** (a DIFFERENT identity domain, not flagged by
      the scanner) are verified by scanning ALL composite keys in the mapped
      file; the entry's key must appear among them (proves the qualname + token
      line still exist, even though the scanner intentionally does not flag it).
    """
    from tests.architectural._ratchet_keys import composite_key as _ck

    stale: list[str] = []

    # --- allow-list entries (scanner-flagged sites) ---
    for key, rel in sorted(_SHORTID_ALLOWED_SITES_FILES.items(), key=lambda kv: kv[1]):
        abs_path = _REPO_ROOT / rel
        if not abs_path.is_file():
            stale.append(f"{rel!r} key={key!r} (file missing)")
            continue
        source = abs_path.read_text(encoding="utf-8")
        live_keys = {_ck(source, ln) for ln in _scan_shortid_file(abs_path)}
        if key not in live_keys:
            stale.append(
                f"{rel!r} key={key!r} (no longer a flagged site — "
                "function renamed or code line changed; update or drop)"
            )

    # --- named-exclusion entries (different identity domain, not scanner-flagged) ---
    for key, rel in sorted(
        _SHORTID_NAMED_EXCLUSIONS_FILES.items(), key=lambda kv: kv[1]
    ):
        abs_path = _REPO_ROOT / rel
        if not abs_path.is_file():
            stale.append(f"{rel!r} key={key!r} (file missing)")
            continue
        source = abs_path.read_text(encoding="utf-8")
        # Collect ALL composite keys in the file (not just scanner-flagged ones)
        # to verify the qualname + token line still exist.
        from tests.architectural._ratchet_keys import (
            code_tokens_by_line as _ctbl,
            enclosing_qualname as _eq,
        )
        all_keys = {
            (_eq(source, ln), tl)
            for ln, tl in _ctbl(source).items()
            if tl  # skip empty token lines
        }
        if key not in all_keys:
            stale.append(
                f"{rel!r} key={key!r} (qualname or token line no longer "
                "present in file — update or drop)"
            )

    assert stale == [], (
        "Stale short-id allow-list / named-exclusion entries (the composite key "
        "no longer matches a live site in the expected file — re-verify "
        "and update or drop):\n  " + "\n  ".join(stale)
    )


# ===========================================================================
# T025 — Drift-proof + non-vacuity executable tests (FR-008 / WP06)
#
# Three executable tests proving the re-keyed ratchet:
#   1. Survives a +1 line drift (blank/comment line inserted above a pin).
#   2. Flags a NEW offender in an allow-listed function (non-vacuity).
#   3. Produces DISTINCT keys for the two byte-identical doctor.py sites.
# ===========================================================================


def test_composite_key_survives_line_drift() -> None:
    """A +1 line drift leaves the composite key UNCHANGED (ratchet stays GREEN).

    Builds a minimal Python source with a flagged short-id slice inside a known
    function, records the composite key, inserts a blank line above the
    flagged line (shifting it from line N to line N+1), re-scans, and asserts
    the composite key is identical.  This proves the qualname + token-line
    anchoring survives pure line-number drift with zero semantic change.
    """
    from tests.architectural._ratchet_keys import composite_key as ck

    original_source = (
        "def _check_coord_health(mission_id: str) -> None:\n"
        "    from foo import resolve_mid8\n"
        "    short = resolve_mid8(mission_id) or mission_id[:8]\n"
        "    print(short)\n"
    )
    # Insert a blank comment line BEFORE the flagged line (line 3 → line 4).
    drifted_source = (
        "def _check_coord_health(mission_id: str) -> None:\n"
        "    from foo import resolve_mid8\n"
        "    # inserted comment — pure drift, no semantic change\n"
        "    short = resolve_mid8(mission_id) or mission_id[:8]\n"
        "    print(short)\n"
    )

    # Locate the short-id slice in the original source via the AST scanner.
    import ast as _ast

    def _find_slice_lineno(src: str) -> int:
        tree = _ast.parse(src)
        for node in _ast.walk(tree):
            if _is_eight_slice(node):
                assert isinstance(node, _ast.Subscript)
                if _operand_is_mission_identity(node.value):
                    return node.lineno
        raise AssertionError("no short-id slice found in fixture source")

    original_lineno = _find_slice_lineno(original_source)
    drifted_lineno = _find_slice_lineno(drifted_source)

    assert drifted_lineno == original_lineno + 1, (
        f"expected the drift to shift the line by 1 "
        f"(original={original_lineno}, drifted={drifted_lineno})"
    )

    original_key = ck(original_source, original_lineno)
    drifted_key = ck(drifted_source, drifted_lineno)

    assert original_key == drifted_key, (
        f"composite key changed after a +1 line drift — the ratchet is NOT "
        f"drift-proof.\n  original key : {original_key!r}\n  drifted key  : {drifted_key!r}"
    )


def test_new_offender_in_allowlisted_function_is_flagged_red() -> None:
    """A new offender INSIDE an allow-listed function is NOT matched (RED).

    Inserts an EXTRA ``mission_id[:8]`` slice at a DIFFERENT line inside the
    same function as an allow-listed entry.  The composite key for the new
    offender shares the qualname component but has a different token-line
    component, so it does NOT match the allow-listed key.  This proves the
    token-line component is load-bearing: the allow-list is not too loose.
    """
    from tests.architectural._ratchet_keys import composite_key as ck

    # Simulate a source whose allow-list key is the same qualname as doctor.py.
    # The allowed line: ``short = resolve_mid8(...) or mission_id[:8]``
    # The extra (forbidden) line: ``tag = mission_id[:8]``
    source_with_extra = (
        "def _check_coordination_worktree_health(mission_id: str) -> None:\n"
        "    from foo import resolve_mid8\n"
        "    short = resolve_mid8(mission_id) or mission_id[:8]\n"
        "    tag = mission_id[:8]  # NEW offender — not in the allow-list\n"
        "    print(short, tag)\n"
    )
    # The allow-listed key for the ORIGINAL site (line 3):
    # qualname = "_check_coordination_worktree_health"
    # token_line = "short = resolve_mid8 ( mission_id ) or mission_id [ : 8 ]"
    import ast as _ast

    allowed_lineno = 3  # ``short = resolve_mid8(...) or mission_id[:8]``
    extra_lineno = 4  # ``tag = mission_id[:8]``

    allowed_key = ck(source_with_extra, allowed_lineno)
    extra_key = ck(source_with_extra, extra_lineno)

    # Both share the same qualname; their token lines MUST differ.
    assert allowed_key[0] == extra_key[0], (
        "expected both lines to be inside the same function "
        f"(allowed qualname={allowed_key[0]!r}, extra qualname={extra_key[0]!r})"
    )
    assert allowed_key[1] != extra_key[1], (
        "token-line component must differ for the two offender lines — "
        "the allow-list would be vacuous if they matched.\n"
        f"  allowed token_line : {allowed_key[1]!r}\n"
        f"  extra   token_line : {extra_key[1]!r}"
    )

    # Simulate the ratchet lookup: the extra offender must NOT be exempted.
    allow_set: frozenset[tuple[str, str]] = frozenset({allowed_key})
    assert extra_key not in allow_set, (
        "the extra offender matched the allow-list key — the token-line "
        "component is not load-bearing (allow-list is too loose).\n"
        f"  extra key    : {extra_key!r}\n"
        f"  allowed key  : {allowed_key!r}"
    )

    # Verify the AST scanner actually flags the extra line (not just the allow-listed one).
    tree = _ast.parse(source_with_extra)
    flagged_linenos: list[int] = []
    for node in _ast.walk(tree):
        if _is_eight_slice(node):
            assert isinstance(node, _ast.Subscript)
            if _operand_is_mission_identity(node.value):
                flagged_linenos.append(node.lineno)
    assert extra_lineno in flagged_linenos, (
        f"the short-id scanner did not flag the extra offender at line {extra_lineno}; "
        f"flagged lines: {flagged_linenos}"
    )


def test_two_doctor_sites_produce_distinct_composite_keys() -> None:
    """The two byte-identical doctor tolerance sites produce DISTINCT composite keys.

    Both sites contain the same source line
    ``short = resolve_mid8(mission_slug, mission_id=mission_id) or mission_id[:8]``.
    A bare token-line key would collide, silently allowing one to cover the other.
    The qualname component distinguishes them: ``_check_coordination_worktree_health``
    vs ``_check_lane_sparse_checkout_drift``.  This test proves the two entries in
    ``_SHORTID_ALLOWED_SITES`` are genuinely distinct.

    #2059 decomposed ``doctor.py``: both functions (and their byte-identical
    tolerance lines) moved into the ``_coordination_doctor`` sibling. The composite
    keys are unchanged (qualname + token-line are byte-preserved); only the file the
    sites live in changed, so this test now scans the sibling.
    """
    from tests.architectural._ratchet_keys import composite_key_from_file

    doctor_path = _REPO_ROOT / "src/specify_cli/cli/commands/_coordination_doctor.py"
    if not doctor_path.exists():
        pytest.skip("_coordination_doctor.py not present in this checkout")

    # Locate the two byte-identical tolerance sites by source content rather than
    # by hardcoded line numbers — the literal-line pins drift whenever an edit
    # above them shifts the file (e.g. the #2059 god-module tag comment), turning
    # a pure line-shift into a spurious RED. The qualname-anchored composite key
    # is itself drift-proof; the test fixture must be too.
    site_marker = "short = resolve_mid8(mission_slug, mission_id=mission_id) or mission_id[:8]"
    doctor_lines = doctor_path.read_text(encoding="utf-8").splitlines()
    site_linenos = [
        idx for idx, line in enumerate(doctor_lines, start=1) if site_marker in line
    ]
    assert len(site_linenos) == 2, (
        "expected exactly two byte-identical `mission_id[:8]` tolerance sites in "
        f"_coordination_doctor.py, found {len(site_linenos)} at lines {site_linenos}"
    )

    key_3074 = composite_key_from_file(doctor_path, site_linenos[0])
    key_3166 = composite_key_from_file(doctor_path, site_linenos[1])

    # The token-line component must be EQUAL (byte-identical source lines).
    assert key_3074[1] == key_3166[1], (
        "expected the token-line component to be identical for the two "
        f"byte-identical source lines:\n  3074 token: {key_3074[1]!r}\n  3166 token: {key_3166[1]!r}"
    )

    # The qualname component must be DIFFERENT (different enclosing functions).
    assert key_3074[0] != key_3166[0], (
        "expected different qualnames for the two doctor.py sites but got the same — "
        "the composite key cannot disambiguate them:\n"
        f"  3074 qualname: {key_3074[0]!r}\n  3166 qualname: {key_3166[0]!r}"
    )

    # The overall composite keys must be DISTINCT.
    assert key_3074 != key_3166, (
        f"composite keys are identical — a colliding implementation would "
        f"allow one allow-list entry to cover both sites:\n"
        f"  3074 key: {key_3074!r}\n  3166 key: {key_3166!r}"
    )

    # Cross-check: both keys appear in _SHORTID_ALLOWED_SITES.
    assert key_3074 in _SHORTID_ALLOWED_SITES, (
        f"doctor.py:3074 composite key {key_3074!r} is missing from "
        "_SHORTID_ALLOWED_SITES — the allow-list and the live source are out of sync"
    )
    assert key_3166 in _SHORTID_ALLOWED_SITES, (
        f"doctor.py:3166 composite key {key_3166!r} is missing from "
        "_SHORTID_ALLOWED_SITES — the allow-list and the live source are out of sync"
    )
