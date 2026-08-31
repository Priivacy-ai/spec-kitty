"""Fail-closed hash-refresh helper for the dead-symbol allow-list (WP02).

Mission: ``frozen-baseline-toll-reduction-01M0A42D``, WP02 (FR-001/FR-002/NFR-001);
extended by ``symbolkey-source-module-01M0B0SF`` WP02 (FR-002/FR-004/FR-007) to
read a content-tier entry's originating module from its backfilled
``source_module=`` keyword directly, rather than recovering it from the
allow-list's ``# module::Name`` comment (the comment text is kept for human
audit only -- SC-004 retires the machine comment-parser, not the comment).
Consumed by ``test_refresh_dead_symbol_hashes.py``; run as a script via
``python -m tests.architectural._refresh_dead_symbol_hashes`` to refresh the
live allow-list in ``test_no_dead_symbols.py`` in place.

.. warning::
   **Test-infra scaffolding, NOT a ``src/`` module.** ``_``-prefixed and
   non-collected by pytest, living under ``tests/architectural/`` exactly like
   ``_symbol_key.py``: a ``src/`` module imported only by tests would RED
   ``test_no_dead_modules`` (zero non-test callers). This module owns its own
   file (WP02) and imports — never edits — ``test_no_dead_symbols.py`` (WP01's
   file: the single hashing/deadness authority).

What this does (Contract A)
---------------------------
Recomputes ``body_hash`` for allow-list entries whose symbol is **still dead**,
so editing a dead symbol's body no longer forces a manual hash edit. It is
**structurally incapable of admitting a new dead symbol** because it iterates
*existing* entries only (never appends) and refreshes an entry **iff exactly one
still-dead candidate survives ``module_path`` narrowing** — otherwise it refuses
(fail-closed). Admitting a new dead symbol would require appending an entry,
which this module never does.

Single-source authorities (no re-implementation / split-brain)
--------------------------------------------------------------
* **Still-dead set** — :func:`test_no_dead_symbols._compute_offenders` with an
  **empty** allow-list returns the full currently-dead ``module::Name`` set via
  the production aggregate path.
* **New key / hash** — :func:`test_no_dead_symbols._resolve_final_key` (which
  threads ``resolve_symbol_key`` / ``key_tier`` / ``classify_collisions`` from
  ``_symbol_key.py``). ``classify_collisions`` has **no** deadness notion; the
  deadness signal comes only from ``_compute_offenders``.
* **source_module** — a content-tier ``SymbolKey`` is location-free
  (``module_path is None``); its originating module is read directly from the
  entry's backfilled ``source_module=`` keyword (#3552) — a **fail-closed
  hint only, never used for hashing**, and never re-derived by parsing the
  ``# module::Name`` comment.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from tests.architectural._symbol_key import (
    CorpusModule,
    classify_collisions,
)
from tests.architectural.test_no_dead_symbols import (
    _compute_offenders,
    _resolve_final_key,
)

__all__ = [
    "AllowlistEntry",
    "DeadLocation",
    "Outcome",
    "RefreshDecision",
    "compute_still_dead",
    "decide",
    "main",
    "parse_allowlist_entries",
    "plan_refresh",
    "refresh",
]


# ---------------------------------------------------------------------------
# Outcomes + data model
# ---------------------------------------------------------------------------


class Outcome:
    """The five Contract-A decision outcomes for one allow-list entry."""

    REFRESH = "refresh"
    """Exactly one still-dead candidate survives ``module_path`` narrowing."""
    DANGLING = "dangling"
    """Zero still-dead candidates at the entry's module (deleted/relocated)."""
    AMBIGUOUS = "ambiguous"
    """>=2 still-dead ``bare_name`` candidates the entry cannot disambiguate."""
    UNRECOVERABLE = "unrecoverable"
    """Content-tier entry carries no ``source_module`` (fail-closed backstop)."""
    NEEDS_MODULE_PATH = "needs_module_path"
    """A CONTENT-tier entry narrows to one candidate whose canonical key must be
    COLLISION-tier (its ``bare_name``/``body_hash`` collides live with another
    symbol, so :func:`key_tier` escalates). Rewriting the content-tier hash
    would be ineffective -- the gate's ``final_key in allowlist`` check compares
    the FULL ``SymbolKey`` tuple including ``module_path``, so a content-tier
    ``SymbolKey(name, hash)`` never equals a collision-tier
    ``SymbolKey(name, hash, module_path=...)`` -- leaving the gate RED for both
    colliding symbols. The operator must escalate this entry to the
    ``module_path=`` (collision) tier by hand; the helper refuses to guess
    which module (#3560 finding 1)."""


_CONTENT_TIER = "content"
_COLLISION_TIER = "collision"


@dataclass(frozen=True)
class AllowlistEntry:
    """One parsed ``SymbolKey(...)`` allow-list entry with rewrite coordinates.

    ``source_module`` is the entry's backfilled ``source_module=`` keyword
    (content-tier only, #3552); ``kwarg_module_path`` is the escalated
    collision-tier ``module_path=`` keyword. :attr:`module_path` unifies them
    into the single identity-minus-hash discriminator, or ``None`` when a
    content-tier entry carries no ``source_module`` (the silent-admit guard).
    """

    bare_name: str
    body_hash: str
    tier: str
    kwarg_module_path: str | None
    source_module: str | None
    lineno: int
    hash_row: int
    hash_col_start: int
    hash_col_end: int

    @property
    def is_content_tier(self) -> bool:
        return self.tier == _CONTENT_TIER

    @property
    def module_path(self) -> str | None:
        """Originating module, or ``None`` if absent.

        Collision-tier entries carry it explicitly (``module_path=`` keyword);
        content-tier entries carry it via their own ``source_module=`` keyword.
        """
        if self.tier == _COLLISION_TIER:
            return self.kwarg_module_path
        return self.source_module


@dataclass(frozen=True)
class DeadLocation:
    """One still-dead live ``__all__`` location + its freshly-resolved hash.

    ``requires_module_path`` mirrors whether :func:`test_no_dead_symbols.key_tier`
    escalated this location's FINAL key to the collision tier (``module_path``
    set) -- i.e. its ``bare_name``/``body_hash`` collide live with another
    ``__all__`` symbol. Defaults to ``False`` so existing positional-arg
    constructions (tests predating #3560 finding 1) keep working unchanged.
    """

    module_path: str
    bare_name: str
    new_hash: str
    requires_module_path: bool = False


@dataclass(frozen=True)
class RefreshDecision:
    """The decision for one entry, with the candidate sets for auditing.

    ``bare_matches`` are the still-dead modules sharing the entry's
    ``bare_name`` **before** narrowing; ``narrowed`` is what survives narrowing
    to the entry's ``module_path``. The regression asserts on both to prove the
    discrimination step executed (guards the F1 vacuity trap).
    """

    entry: AllowlistEntry
    outcome: str
    bare_matches: tuple[str, ...]
    narrowed: tuple[str, ...]
    new_hash: str | None


# ---------------------------------------------------------------------------
# Parsing — AST only; source_module is a first-class kwarg, not a comment
# ---------------------------------------------------------------------------


def _iter_symbolkey_calls(tree: ast.Module) -> list[ast.Call]:
    """Yield every ``SymbolKey(...)`` call inside a module-level ``_CATEGORY_*``
    frozenset assignment.

    Scoped exactly like ``test_no_dead_symbols``'s own content-tier call walk
    so synthetic ``SymbolKey(...)`` calls in *test bodies* are excluded — only
    the calls that aggregate into ``_SYMBOL_ALLOWLIST`` are rewritten.
    """
    calls: list[ast.Call] = []
    for stmt in tree.body:
        targets: list[ast.expr] = []
        if isinstance(stmt, ast.Assign):
            targets = list(stmt.targets)
        elif isinstance(stmt, ast.AnnAssign):
            targets = [stmt.target]
        else:
            continue
        if not any(isinstance(t, ast.Name) and t.id.startswith("_CATEGORY_") for t in targets):
            continue
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "SymbolKey":
                calls.append(node)
    return calls


def _str_arg(node: ast.expr | None) -> str | None:
    """Return the string value of a ``Constant`` string node, else ``None``."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _module_path_kwarg(call: ast.Call) -> str | None:
    """The ``module_path="..."`` keyword string, or ``None`` when absent."""
    for kw in call.keywords:
        if kw.arg == "module_path":
            return _str_arg(kw.value)
    return None


def _source_module_kwarg(call: ast.Call) -> str | None:
    """The ``source_module="..."`` keyword string, or ``None`` when absent.

    Mirrors :func:`_module_path_kwarg`. Content-tier entries carry their
    originating module here (backfilled, #3552) instead of it being recovered
    from the ``# module::Name`` comment.
    """
    for kw in call.keywords:
        if kw.arg == "source_module":
            return _str_arg(kw.value)
    return None


def parse_allowlist_entries(source: str) -> list[AllowlistEntry]:
    """Parse every allow-list ``SymbolKey(...)`` entry from *source*.

    AST gives the exact ``body_hash`` string-literal coordinates (for the
    in-place rewrite), the collision-tier ``module_path=`` keyword, and the
    content-tier ``source_module=`` keyword. Malformed entries (missing the
    two positional string args) are skipped.
    """
    tree = ast.parse(source)
    entries: list[AllowlistEntry] = []
    for call in _iter_symbolkey_calls(tree):
        if len(call.args) < 2:
            continue
        bare_name = _str_arg(call.args[0])
        hash_node = call.args[1]
        body_hash = _str_arg(hash_node)
        if bare_name is None or body_hash is None or not isinstance(hash_node, ast.Constant):
            continue
        kwarg_module_path = _module_path_kwarg(call)
        tier = _COLLISION_TIER if kwarg_module_path is not None else _CONTENT_TIER
        source_module = None if tier == _COLLISION_TIER else _source_module_kwarg(call)
        entries.append(
            AllowlistEntry(
                bare_name=bare_name,
                body_hash=body_hash,
                tier=tier,
                kwarg_module_path=kwarg_module_path,
                source_module=source_module,
                lineno=call.lineno,
                hash_row=hash_node.lineno,
                hash_col_start=hash_node.col_offset,
                hash_col_end=hash_node.end_col_offset if hash_node.end_col_offset is not None else hash_node.col_offset,
            )
        )
    return entries


# ---------------------------------------------------------------------------
# Still-dead authority + fail-closed decision
# ---------------------------------------------------------------------------


def compute_still_dead(
    corpus: Mapping[str, CorpusModule],
    decls: dict[str, frozenset[str]],
    per_symbol: dict[str, set[str]],
    star_targets: set[str],
) -> list[DeadLocation]:
    """The full currently-dead set with each location's freshly-resolved hash.

    Deadness authority is :func:`_compute_offenders` with an **empty**
    allow-list (the production aggregate path); each offender's new hash is
    :func:`_resolve_final_key`. An un-keyable offender (``None`` key) is dropped
    — an entry that finds no candidate refuses (fail-closed), never guesses.
    """
    collision_index = classify_collisions(corpus)
    offenders = _compute_offenders(decls, per_symbol, star_targets, frozenset(), corpus, collision_index)
    locations: list[DeadLocation] = []
    for qualified in offenders:
        module_path, _, bare_name = qualified.partition("::")
        final_key = _resolve_final_key(bare_name, module_path, corpus.get(module_path), corpus, collision_index)
        if final_key is None:
            continue
        locations.append(
            DeadLocation(
                module_path=module_path,
                bare_name=bare_name,
                new_hash=final_key.body_hash,
                requires_module_path=final_key.module_path is not None,
            )
        )
    return locations


def _location_for(still_dead: Sequence[DeadLocation], bare_name: str, module_path: str) -> DeadLocation | None:
    for location in still_dead:
        if location.bare_name == bare_name and location.module_path == module_path:
            return location
    return None


def decide(entry: AllowlistEntry, still_dead: Sequence[DeadLocation]) -> RefreshDecision:
    """Decide one entry's fate (Contract A) — refresh iff exactly one candidate.

    ``bare_matches`` = still-dead locations sharing the entry's ``bare_name``.
    The entry is refreshed **only** when its recovered ``module_path`` narrows
    that set to exactly one candidate; every other case fails closed. A
    content-tier entry with an unrecoverable ``module_path`` **always** refuses
    — it never falls back to a bare-name-only corpus-wide match (the
    silent-admit vector).

    A narrowed CONTENT-tier entry whose sole candidate needs COLLISION-tier
    keying (:attr:`DeadLocation.requires_module_path`) escalates to
    :attr:`Outcome.NEEDS_MODULE_PATH` instead of refreshing — rewriting only the
    hash of a content-tier ``SymbolKey`` would be structurally ineffective
    against a collision the gate can only exempt via a ``module_path=``-tagged
    key (#3560 finding 1). A COLLISION-tier entry (already carries
    ``module_path=``) that narrows cleanly is unaffected and still refreshes.
    """
    bare_matches = tuple(sorted(loc.module_path for loc in still_dead if loc.bare_name == entry.bare_name))
    entry_module = entry.module_path
    if entry_module is None:
        # Content-tier provenance unrecoverable -> fail closed, never bare-name-only.
        outcome = Outcome.AMBIGUOUS if len(bare_matches) >= 2 else Outcome.UNRECOVERABLE
        return RefreshDecision(entry, outcome, bare_matches, (), None)
    narrowed = tuple(module for module in bare_matches if module == entry_module)
    if len(narrowed) == 1:
        location = _location_for(still_dead, entry.bare_name, entry_module)
        if location is None:
            return RefreshDecision(entry, Outcome.DANGLING, bare_matches, narrowed, None)
        if entry.is_content_tier and location.requires_module_path:
            # Fail-closed escalation: never widen what gets refreshed by
            # rewriting a content-tier hash that cannot exempt the collision.
            return RefreshDecision(entry, Outcome.NEEDS_MODULE_PATH, bare_matches, narrowed, None)
        return RefreshDecision(entry, Outcome.REFRESH, bare_matches, narrowed, location.new_hash)
    if len(narrowed) >= 2:
        # Defensive: >=2 still-dead siblings in one module (unique __all__ names
        # make this rare) -> cannot disambiguate, refuse.
        return RefreshDecision(entry, Outcome.AMBIGUOUS, bare_matches, narrowed, None)
    # narrowed == 0: the symbol is gone from the entry's module (deleted/relocated).
    return RefreshDecision(entry, Outcome.DANGLING, bare_matches, narrowed, None)


# ---------------------------------------------------------------------------
# Plan + in-place rewrite
# ---------------------------------------------------------------------------


def plan_refresh(
    corpus: Mapping[str, CorpusModule],
    decls: dict[str, frozenset[str]],
    per_symbol: dict[str, set[str]],
    allowlist_source: str,
    star_targets: set[str] | None = None,
) -> list[RefreshDecision]:
    """The per-entry decisions for *allowlist_source* against the live corpus."""
    entries = parse_allowlist_entries(allowlist_source)
    still_dead = compute_still_dead(corpus, decls, per_symbol, star_targets or set())
    return [decide(entry, still_dead) for entry in entries]


def _guard_no_shared_hash_rows(decisions: Sequence[RefreshDecision]) -> None:
    """Refuse (loudly, before any rewrite) if >=2 REFRESH decisions target the
    same physical source row.

    ``_apply`` slices columns captured from the ORIGINAL line for each
    decision. If two REFRESH decisions land on the same ``hash_row``, the
    first rewrite shifts the line's content (a different-length hash changes
    column offsets), so the second decision's ``hash_col_start``/
    ``hash_col_end`` -- captured before either rewrite -- would slice the
    WRONG span of the already-mutated line, silently corrupting it. Contract A
    assumes one allow-list entry per physical line (#3560 finding 3); this
    guard makes that assumption fail-closed instead of silently violated.
    """
    seen_rows: dict[int, str] = {}
    for decision in decisions:
        if decision.outcome != Outcome.REFRESH or decision.new_hash is None:
            continue
        row = decision.entry.hash_row
        if row in seen_rows:
            raise ValueError(
                f"_apply: >=2 REFRESH decisions target the same source row {row} "
                f"({seen_rows[row]!r} and {decision.entry.bare_name!r}) -- rewriting "
                "both would corrupt column offsets captured from the original line; "
                "refusing (fail-closed, #3560 finding 3)"
            )
        seen_rows[row] = decision.entry.bare_name


def _apply(source: str, decisions: Sequence[RefreshDecision]) -> str:
    """Rewrite only the ``body_hash`` literals of REFRESH decisions, in place.

    Every other byte of *source* is preserved — no entry is added or removed
    (the never-append invariant is structural: only existing hash tokens are
    overwritten). Each allow-list entry is single-line with its own hash token,
    so column-slice replacement never collides -- :func:`_guard_no_shared_hash_rows`
    verifies that assumption before any mutation happens.
    """
    _guard_no_shared_hash_rows(decisions)
    lines = source.splitlines(keepends=True)
    for decision in decisions:
        if decision.outcome != Outcome.REFRESH or decision.new_hash is None:
            continue
        entry = decision.entry
        row_index = entry.hash_row - 1
        line = lines[row_index]
        original = line[entry.hash_col_start : entry.hash_col_end]
        quote = original[0]
        replacement = f"{quote}{decision.new_hash}{quote}"
        lines[row_index] = line[: entry.hash_col_start] + replacement + line[entry.hash_col_end :]
    return "".join(lines)


def refresh(
    corpus: Mapping[str, CorpusModule],
    decls: dict[str, frozenset[str]],
    per_symbol: dict[str, set[str]],
    allowlist_source: str,
    star_targets: set[str] | None = None,
) -> str:
    """Return *allowlist_source* with every still-dead entry's hash refreshed.

    Pure: the corpus is injected (no ``_SRC_ROOT`` closure), so the NFR-001
    regression can construct a synthetic tree. Existing entries are iterated;
    none is ever appended.
    """
    decisions = plan_refresh(corpus, decls, per_symbol, allowlist_source, star_targets)
    return _apply(allowlist_source, decisions)


# ---------------------------------------------------------------------------
# Script entrypoint — refresh the real allow-list in place
# ---------------------------------------------------------------------------


def main() -> int:
    """Refresh the live allow-list source (``test_no_dead_symbols.py``) in place.

    Prints every refusal (``bare_name`` + module) instead of guessing, then
    writes back the refreshed source. A refusal is not fatal: dangling/stale
    entries are left unchanged for the gate to red at their new key.
    """
    from tests.architectural.test_no_dead_symbols import (
        _THIS_SOURCE,
        _imports_by_target,
        _walk_modules,
    )

    decls, _all_literal_decls, path_to_dotted, path_to_tree, corpus = _walk_modules()
    per_symbol, star_targets = _imports_by_target(path_to_dotted, path_to_tree)
    source = _THIS_SOURCE.read_text(encoding="utf-8")
    decisions = plan_refresh(corpus, decls, per_symbol, source, star_targets)
    for decision in decisions:
        if decision.outcome != Outcome.REFRESH:
            print(f"REFUSE[{decision.outcome}] {decision.entry.bare_name} (module_path={decision.entry.module_path})")
    rewritten = _apply(source, decisions)
    _THIS_SOURCE.write_text(rewritten, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
