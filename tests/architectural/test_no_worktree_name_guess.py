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
PARSER). Each carve-out names a single ``file:line`` and carries its rationale.

WP09 / Issue #1899 / FR-001 / FR-005 / FR-009.
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
from typing import TypeGuard

import pytest

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
# Each entry is a ``file:line`` of a use that is provably NOT a name compose.
# ---------------------------------------------------------------------------
_ALLOWED_SITES: frozenset[str] = frozenset(
    {
        # ── recovery.py: a ``git branch --list`` GLOB pattern, not a compose ──
        # ``f"kitty/mission-{mission_slug}*"`` (trailing ``*``) is passed to
        # ``git branch --list`` to ENUMERATE existing branches; it never names a
        # branch to create. Benign UX/listing glob (the carve-out class the WP
        # explicitly permits).
        "src/specify_cli/lanes/recovery.py:135",
        # ── vcs/detection.py: string fed straight back into the seam PARSER ──
        # ``parse_mission_slug_from_branch(f"kitty/mission-{worktree_name}")``
        # round-trips a worktree dir name THROUGH the canonical seam parser to
        # decode it — it decodes, it does not name/create a branch. The seam
        # parser is the authority; this is a parse-caller, not a name-guess.
        "src/specify_cli/core/vcs/detection.py:161",
        # ── lifecycle_sync.py: error-report placeholder, NOT a worktree lookup ──
        # ``repo_root / WORKTREES_DIRNAME / f"{mission_slug}-unknown"`` lives in
        # the ``CorruptLanesError`` branch, paired with ``lane_id="unknown"`` /
        # ``lane_branch="unknown"``. The lanes manifest is corrupt, so there is no
        # real lane id to compose with — this synthesises a human-readable
        # placeholder for the raised ``LaneAutoRebaseSyncError`` diagnostic; it
        # never resolves an on-disk worktree (the path is reported, not opened).
        # Benign: not a name-guess of a real worktree.
        "src/specify_cli/lanes/lifecycle_sync.py:135",
        # NOTE: the previously-allow-listed pre-existing ``<slug>-<mid8>`` composes
        # (``mission_creation.py:321`` / ``worktree.py:367`` / ``worktree.py:370``)
        # have been ROUTED through ``mission_dir_name()`` / ``resolve_mid8()`` (the
        # #2000 follow-up landed). The detector now flags ZERO offenders at those
        # sites, so the carve-outs were dropped (a stale exemption is a
        # false-negative window). The
        # ``test_name_compose_offenders_match_pinned_baseline`` cross-check below
        # pins the offender count so a re-grown stale allow-list entry is caught.
    }
)

# Pinned count of name-COMPOSE offenders the detector currently flags across the
# scan roots (excluding the seam), pinned as a committed literal so the
# allow-list cannot rot undetected. Mirrors the short-id ratchet's
# ``_SHORTID_BASELINE_RAW_MATCHES``: a stale allow-list entry (one that no longer
# points at a live offender) or an extra unjustified entry would drift this
# count and trip the cross-check. Composition (verified at this baseline land):
#   recovery.py:135            (branch-list glob — benign carve-out)
#   vcs/detection.py:161       (seam-parser round-trip — benign carve-out)
#   lifecycle_sync.py:135      (corrupt-lanes diagnostic placeholder — benign)
# => 3 raw offenders, all accounted for by the allow-list => 0 un-accounted.
_NAME_COMPOSE_BASELINE_RAW_MATCHES = 3

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
        for lineno, label in sorted(_scan_file(path).items()):
            site = f"{rel}:{lineno}"
            if site in _ALLOWED_SITES:
                continue
            offenders.append(f"  {site}: {label}")

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
    """Every allow-list entry must still point at a live, scannable line.

    Guards against the allow-list silently rotting (a carved-out site moves or is
    removed, leaving a stale exemption that could mask a future regression at the
    same path:line).
    """
    stale: list[str] = []
    for site in sorted(_ALLOWED_SITES):
        rel, _, lineno_text = site.rpartition(":")
        abs_path = _REPO_ROOT / rel
        if not abs_path.is_file():
            stale.append(f"{site} (file missing)")
            continue
        line_count = len(abs_path.read_text(encoding="utf-8").splitlines())
        if int(lineno_text) > line_count:
            stale.append(f"{site} (line {lineno_text} > {line_count} lines)")
    assert stale == [], (
        "Stale allow-list entries (the carved-out line no longer exists — "
        "re-verify the site and update or drop the exemption):\n  "
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
    raw_offenders: list[str] = []
    for path in _iter_source_files():
        rel = _rel(path)
        if rel == _SEAM_REL:
            continue  # the seam is the legal home of these idioms
        for lineno in sorted(_scan_file(path)):
            raw_offenders.append(f"{rel}:{lineno}")

    assert len(raw_offenders) == _NAME_COMPOSE_BASELINE_RAW_MATCHES, (
        "Pinned name-compose baseline drifted. Expected "
        f"{_NAME_COMPOSE_BASELINE_RAW_MATCHES} raw name-compose offenders across "
        f"the scan roots, found {len(raw_offenders)}:\n  "
        + "\n  ".join(sorted(raw_offenders))
        + "\n\nIf a NEW offender appeared, route it through the canonical seam. "
        "If an allow-listed offender was legitimately removed (routed through "
        "the seam), drop its allow-list entry AND update "
        "_NAME_COMPOSE_BASELINE_RAW_MATCHES (and the composition comment)."
    )

    unaccounted = [site for site in raw_offenders if site not in _ALLOWED_SITES]
    assert unaccounted == [], (
        "Name-compose offenders not covered by the allow-list (each is a REAL "
        "name-guess outside the seam — route it through the canonical seam, do "
        "NOT add an allow-list entry without a justification proving it is not a "
        "compose):\n  " + "\n  ".join(sorted(unaccounted))
    )

    # Inverse guard: every allow-list entry must STILL be a live offender, so a
    # stale exemption (the renata GAP) cannot survive. Combined with the count
    # assertion above this makes the allow-list exactly the offender set.
    stale_exemptions = sorted(set(_ALLOWED_SITES) - set(raw_offenders))
    assert stale_exemptions == [], (
        "Stale name-compose allow-list entries (the line is no longer an "
        "offender the detector flags — the site was routed through the seam; "
        "drop the exemption to close the false-negative window):\n  "
        + "\n  ".join(stale_exemptions)
    )


# ---------------------------------------------------------------------------
# NFR-001 diff-scan (T038a): the naming-seam consolidation must NOT bleed into
# the status reducer/store internals or the task_utils internals.
# ---------------------------------------------------------------------------

# Mission planning base — the branch all WPs target. The diff base is the
# merge-base of HEAD with this branch (falling back to the integration branch),
# so the scan captures the WHOLE mission's diff regardless of which lane runs it.
_MISSION_PLANNING_BRANCH = "mission/mission-identity-seam-and-1908-panel"
_MISSION_INTEGRATION_BRANCH = (
    "kitty/mission-mission-identity-seam-and-1908-panel-01KV6510"
)

# The ONLY ``status/`` file the consolidation is permitted to touch (it carries a
# single mid8 parse-caller routed by WP10; explicitly carved out by NFR-001).
_STATUS_ALLOWED = "src/specify_cli/status/aggregate.py"
_STATUS_PREFIX = "src/specify_cli/status/"
_TASK_UTILS_PREFIX = "src/specify_cli/task_utils/"


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def _resolve_mission_base() -> str | None:
    """Merge-base of HEAD with the mission branch, or ``None`` if unavailable."""
    for branch in (_MISSION_PLANNING_BRANCH, _MISSION_INTEGRATION_BRANCH):
        result = _git("merge-base", "HEAD", branch)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    return None


def test_nfr001_consolidation_does_not_bleed_into_status_or_task_utils() -> None:
    """NFR-001: zero ``status/`` hunks (except ``aggregate.py``) / zero ``task_utils/``.

    The naming-seam consolidation is intentionally cross-cutting across the
    branch/worktree call sites, but it must NOT touch the status reducer/store
    internals or the task_utils internals. A diff of the whole mission against its
    planning base must show no hunks under ``status/`` (other than the explicitly
    carved-out ``aggregate.py`` mid8 parse-caller) and none under ``task_utils/``.
    """
    base = _resolve_mission_base()
    if base is None:
        pytest.skip(
            "mission base branch not available in this checkout; "
            "NFR-001 diff-scan requires the mission/integration branch ref."
        )

    diff = _git("diff", "--name-only", f"{base}..HEAD")
    assert diff.returncode == 0, f"git diff failed: {diff.stderr.strip()}"

    changed = [line.strip() for line in diff.stdout.splitlines() if line.strip()]
    violations = [
        path
        for path in changed
        if (path.startswith(_STATUS_PREFIX) and path != _STATUS_ALLOWED)
        or path.startswith(_TASK_UTILS_PREFIX)
    ]

    assert violations == [], (
        "NFR-001 violated — the naming-seam consolidation bled into forbidden "
        "internals. Only `status/aggregate.py` may change under `status/`, and "
        "`task_utils/` must be untouched.\n  "
        + "\n  ".join(sorted(violations))
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
_SHORTID_NAMED_EXCLUSIONS: frozenset[str] = frozenset(
    {
        "src/specify_cli/invocation/executor.py:469",
    }
)

# Narrow, individually-justified short-id allow-list (file:line). The
# mission-identity CONSUMER class is otherwise EMPTY after WP03/WP04/WP05
# routed every site; only this deliberate diagnostic-tolerance fallback remains.
_SHORTID_ALLOWED_SITES: frozenset[str] = frozenset(
    {
        # ── doctor.py: diagnostic short-id TOLERANCE, not a missed route ──
        # ``short = resolve_mid8(slug, mission_id=mission_id) or mission_id[:8]``.
        # WP03 routed the derivation through the failover-aware ``resolve_mid8``;
        # the ``or mission_id[:8]`` tail is a CONSCIOUS fallback that keeps the
        # doctor diagnostic emitting a display short-id even when resolve_mid8
        # declines to ``""`` (e.g. a malformed/short mission_id). It is the
        # ``or`` RHS of an already-routed call — a tolerance branch, NOT a
        # consumer that bypassed the seam. Two emit sites, identical idiom.
        "src/specify_cli/cli/commands/doctor.py:3074",
        "src/specify_cli/cli/commands/doctor.py:3166",
    }
)

# Pre-mission baseline of mission-identity ``[:8]`` slices across ``src/`` (the
# raw count BEFORE home/allow-list filtering), pinned as a committed literal so
# "the consumer class is empty" is an OBJECTIVE, diff-checkable claim rather
# than a re-derivation of the live tree. Composition (verified at WP02 land):
#   branch_naming.py:146/199/415  (3, HOME)
#   mission_runtime/context.py:99/112  (2, HOME)
#   cli/commands/doctor.py:3074/3166  (2, allow-listed tolerance)
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
        for lineno, label in sorted(_scan_shortid_file(path).items()):
            site = f"{rel}:{lineno}"
            if site in _SHORTID_NAMED_EXCLUSIONS or site in _SHORTID_ALLOWED_SITES:
                continue
            offenders.append(f"  {site}: {label}")
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
    raw_matches: list[str] = []
    for path in _iter_shortid_source_files():
        rel = _rel(path)
        for lineno, label in sorted(_scan_shortid_file(path).items()):
            if "short-id slice" not in label:
                continue  # count slices only for the baseline, not _mid8 calls
            raw_matches.append(f"{rel}:{lineno}")

    assert len(raw_matches) == _SHORTID_BASELINE_RAW_MATCHES, (
        "Pinned short-id baseline drifted. Expected "
        f"{_SHORTID_BASELINE_RAW_MATCHES} raw mission-identity `[:8]` slices "
        f"across src/, found {len(raw_matches)}:\n  "
        + "\n  ".join(sorted(raw_matches))
        + "\n\nIf a NEW slice appeared, it is almost certainly a missed route — "
        "route it through `resolve_mid8`. If a home/allow-listed slice was "
        "legitimately removed, update _SHORTID_BASELINE_RAW_MATCHES (and the "
        "composition comment) to match."
    )

    # Every raw match must be accounted for by a home, a named exclusion, or the
    # allow-list — leaving an EMPTY un-accounted consumer set.
    unaccounted = [
        site
        for site in raw_matches
        if site.rsplit(":", 1)[0] not in _SHORTID_HOME_FILES
        and site not in _SHORTID_NAMED_EXCLUSIONS
        and site not in _SHORTID_ALLOWED_SITES
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
    """Every short-id allow-list / named-exclusion entry points at a live line.

    Mirrors ``test_allow_list_entries_are_real_and_benign`` for the short-id
    carve-outs: a stale exemption that outlives its line could silently mask a
    future regression at the same path:line.
    """
    stale: list[str] = []
    for site in sorted(_SHORTID_ALLOWED_SITES | _SHORTID_NAMED_EXCLUSIONS):
        rel, _, lineno_text = site.rpartition(":")
        abs_path = _REPO_ROOT / rel
        if not abs_path.is_file():
            stale.append(f"{site} (file missing)")
            continue
        line_count = len(abs_path.read_text(encoding="utf-8").splitlines())
        if int(lineno_text) > line_count:
            stale.append(f"{site} (line {lineno_text} > {line_count} lines)")
    assert stale == [], (
        "Stale short-id allow-list / named-exclusion entries (the carved-out "
        "line no longer exists — re-verify the site and update or drop it):\n  "
        + "\n  ".join(stale)
    )
