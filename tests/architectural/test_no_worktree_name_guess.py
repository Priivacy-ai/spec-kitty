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
        "src/specify_cli/lanes/recovery.py:136",
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
        # ── mission_creation.py / worktree.py: pre-existing <slug>-<mid8> compose ──
        # Out-of-scope, pre-existing seam-duplicating composes that PRE-DATE this
        # mission and were never in its NFR-001 routing scope (absent from
        # spec.md/plan.md). The canonical seam (`branch_naming.py`) now exists, so
        # routing these through ``mission_dir_name()`` / ``worktree_dir_name()`` is
        # a clean follow-up — tracked separately by the orchestrator (a logged,
        # non-silent exemption, NOT a silent work-around). Allow-listed here so the
        # ratchet stays green for this mission while the follow-up is queued.
        "src/specify_cli/core/mission_creation.py:321",
        "src/specify_cli/core/worktree.py:367",
        "src/specify_cli/core/worktree.py:370",
    }
)

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
