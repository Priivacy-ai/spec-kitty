"""WP02 — fail-closed dead-symbol hash-refresh helper + non-fakeable regression.

Mission ``frozen-baseline-toll-reduction-01M0A42D`` (FR-001/FR-002/NFR-001,
Contract A). Tests ``_refresh_dead_symbol_hashes.py``:

* T005 pure-core signature + never-append invariant.
* T006 the helper's still-dead set equals the gate's for a known corpus.
* T007 fail-closed match — each Contract-A branch (refresh / dangling /
  ambiguous / unrecoverable) + collision-tier preservation.
* T008 the real (WP01-normalized) tree refreshes rather than refuses.
* T009 THE non-fakeable NFR-001/SC-006 regression: one run over a constructed
  corpus proving positive control (a), collision non-admit (b), candidate-set
  narrowing (c), all four branches (d), and a differential against a
  bare-name-only stub that passes (a) but fails (b)/(c).
* T010 AC3 edges — stale vs dangling, collision-tier tier preserved.
"""

from __future__ import annotations

import ast

import pytest

from tests.architectural._refresh_dead_symbol_hashes import (
    AllowlistEntry,
    DeadLocation,
    Outcome,
    RefreshDecision,
    compute_still_dead,
    decide,
    parse_allowlist_entries,
    plan_refresh,
    refresh,
)
from tests.architectural._symbol_key import (
    CorpusModule,
    SymbolKey,
    classify_collisions,
)
from tests.architectural.test_no_dead_symbols import (
    _compute_dangling,
    _compute_offenders,
    _compute_stale,
    _submodule_index,
)

pytestmark = [pytest.mark.architectural]

_OLD_HASH = "0" * 64


# ---------------------------------------------------------------------------
# Synthetic-corpus builders
# ---------------------------------------------------------------------------


def _module(source: str, pkg: str = "synthetic") -> CorpusModule:
    return CorpusModule(tree=ast.parse(source), source=source, containing_pkg=pkg)


def _one_symbol(name: str, body: str) -> str:
    """A module declaring a single ``__all__`` symbol bound to *body*.

    ``body`` is inserted verbatim as the assignment RHS. Callers pass distinct
    numeric literals when they need distinct ``body_hash`` values —
    ``code_tokens_by_line`` normalizes *string* literal content (so two
    different string bodies hash identically and would spuriously collide), but
    numeric tokens survive normalization (cf. the fan-out ``Shared = 1`` /
    ``Shared = 2`` gate test).
    """
    return f'{name} = {body}\n__all__ = ["{name}"]\n'


def _entry(
    bare_name: str,
    *,
    tier: str = "content",
    kwarg_module_path: str | None = None,
    provenance_module: str | None = None,
    body_hash: str = _OLD_HASH,
) -> AllowlistEntry:
    """A positional-free :class:`AllowlistEntry` for direct ``decide`` tests."""
    return AllowlistEntry(
        bare_name=bare_name,
        body_hash=body_hash,
        tier=tier,
        kwarg_module_path=kwarg_module_path,
        provenance_module=provenance_module,
        lineno=1,
        hash_row=1,
        hash_col_start=0,
        hash_col_end=0,
    )


def _allowlist_from_source(source: str) -> frozenset[SymbolKey]:
    """Reconstruct the ``SymbolKey`` frozenset from a rewritten allow-list source."""
    keys: set[SymbolKey] = set()
    for entry in parse_allowlist_entries(source):
        if entry.is_content_tier:
            keys.add(SymbolKey(entry.bare_name, entry.body_hash))
        else:
            keys.add(SymbolKey(entry.bare_name, entry.body_hash, module_path=entry.kwarg_module_path))
    return frozenset(keys)


def _offenders(
    source: str,
    corpus: dict[str, CorpusModule],
    decls: dict[str, frozenset[str]],
    per_symbol: dict[str, set[str]],
    star: set[str],
) -> list[str]:
    """Run the production gate with the allow-list parsed from *source*."""
    allow = _allowlist_from_source(source)
    collision_index = classify_collisions(corpus)
    return _compute_offenders(decls, per_symbol, star, allow, corpus, collision_index)


# ---------------------------------------------------------------------------
# T005 — pure core signature + never-append invariant
# ---------------------------------------------------------------------------


def test_refresh_returns_source_and_never_appends() -> None:
    """``refresh`` rewrites in place and never adds an entry for a new dead symbol."""
    corpus = {
        "synthetic.mod_a": _module(_one_symbol("Foo", "1")),
        "synthetic.mod_b": _module(_one_symbol("Bar", "2")),
    }
    decls = {
        "synthetic.mod_a": frozenset({"Foo"}),
        "synthetic.mod_b": frozenset({"Bar"}),
    }
    source = (
        "_CATEGORY_TEST = frozenset(\n"
        "    {\n"
        "        # synthetic.mod_a::Foo\n"
        f'        SymbolKey("Foo", "{_OLD_HASH}"),\n'
        "    }\n"
        ")\n"
    )

    rewritten = refresh(corpus, decls, {}, source)

    before = parse_allowlist_entries(source)
    after = parse_allowlist_entries(rewritten)
    assert len(after) == len(before) == 1, "refresh must never append or drop an entry"  # golden-count: cardinality-is-contract
    assert {e.bare_name for e in after} == {"Foo"}, "the new dead symbol 'Bar' must never be admitted"
    assert "Bar" not in rewritten
    assert rewritten.count("SymbolKey(") == source.count("SymbolKey(")


# ---------------------------------------------------------------------------
# T006 — still-dead authority equals the gate's
# ---------------------------------------------------------------------------


def test_compute_still_dead_equals_gate_offenders() -> None:
    """The helper's still-dead set is the gate's ``_compute_offenders`` set."""
    corpus = {
        "synthetic.dead_1": _module(_one_symbol("Alpha", "1")),
        "synthetic.dead_2": _module(_one_symbol("Beta", "2")),
        "synthetic.live": _module(_one_symbol("Gamma", "3")),
    }
    decls = {
        "synthetic.dead_1": frozenset({"Alpha"}),
        "synthetic.dead_2": frozenset({"Beta"}),
        "synthetic.live": frozenset({"Gamma"}),
    }
    per_symbol = {"synthetic.live": {"Gamma"}}  # Gamma has a caller -> live

    still_dead = compute_still_dead(corpus, decls, per_symbol, set())
    collision_index = classify_collisions(corpus)
    offenders = _compute_offenders(decls, per_symbol, set(), frozenset(), corpus, collision_index)

    assert {f"{d.module_path}::{d.bare_name}" for d in still_dead} == set(offenders)
    assert "synthetic.live::Gamma" not in {f"{d.module_path}::{d.bare_name}" for d in still_dead}


# ---------------------------------------------------------------------------
# T007 — fail-closed match, each Contract-A branch
# ---------------------------------------------------------------------------


def test_decide_refresh_on_exactly_one_candidate() -> None:
    still_dead = [DeadLocation("synthetic.m1", "Foo", "newhash")]
    decision = decide(_entry("Foo", provenance_module="synthetic.m1"), still_dead)
    assert decision.outcome == Outcome.REFRESH
    assert decision.new_hash == "newhash"
    assert decision.narrowed == ("synthetic.m1",)


def test_decide_dangling_on_zero_candidates() -> None:
    decision = decide(_entry("Foo", provenance_module="synthetic.m1"), [])
    assert decision.outcome == Outcome.DANGLING
    assert decision.new_hash is None


def test_decide_ambiguous_on_two_candidates_without_module_path() -> None:
    still_dead = [
        DeadLocation("synthetic.m1", "Foo", "h1"),
        DeadLocation("synthetic.m2", "Foo", "h2"),
    ]
    decision = decide(_entry("Foo", provenance_module=None), still_dead)
    assert decision.outcome == Outcome.AMBIGUOUS
    assert decision.new_hash is None
    assert len(decision.bare_matches) == 2  # golden-count: cardinality-is-contract


def test_decide_unrecoverable_refuses_even_with_single_candidate() -> None:
    """A content-tier entry with unrecoverable provenance NEVER falls back to a
    bare-name-only match — the silent-admit vector (NFR-001)."""
    still_dead = [DeadLocation("synthetic.m1", "Foo", "h1")]
    decision = decide(_entry("Foo", provenance_module=None), still_dead)
    assert decision.outcome == Outcome.UNRECOVERABLE
    assert decision.new_hash is None


def test_decide_collision_tier_preserves_module_path() -> None:
    still_dead = [
        DeadLocation("synthetic.dup_a", "Dup", "hnew"),
        DeadLocation("synthetic.dup_b", "Dup", "hnew"),
    ]
    entry = _entry("Dup", tier="collision", kwarg_module_path="synthetic.dup_a")
    decision = decide(entry, still_dead)
    assert decision.outcome == Outcome.REFRESH
    assert decision.new_hash == "hnew"
    assert decision.entry.kwarg_module_path == "synthetic.dup_a"  # tier preserved
    assert decision.narrowed == ("synthetic.dup_a",)


def test_decide_escalates_content_tier_entry_needing_collision_tier() -> None:
    """#3560 finding 1 — a CONTENT-tier entry narrows to exactly one still-dead
    candidate whose canonical key must be COLLISION-tier (``requires_module_path``),
    so ``decide`` must escalate rather than REFRESH: rewriting only the
    content-tier hash would leave the gate RED for both colliding symbols."""
    still_dead = [
        DeadLocation("synthetic.dup_a", "Dup", "hnew", requires_module_path=True),
        DeadLocation("synthetic.dup_b", "Dup", "hnew", requires_module_path=True),
    ]
    entry = _entry("Dup", provenance_module="synthetic.dup_a")  # content-tier, no module_path=
    decision = decide(entry, still_dead)
    assert decision.outcome == Outcome.NEEDS_MODULE_PATH
    assert decision.outcome != Outcome.REFRESH
    assert decision.new_hash is None
    assert decision.narrowed == ("synthetic.dup_a",)


# ---------------------------------------------------------------------------
# T008 — real (WP01-normalized) tree refreshes, never refuses on provenance
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_real_tree_refreshes_without_unrecoverable_provenance() -> None:
    """Over the live normalized tree the helper refreshes still-dead entries and
    NEVER hits the unrecoverable-provenance branch (WP01 normalization holds),
    and the rewrite is idempotent."""
    from tests.architectural.test_no_dead_symbols import (
        _THIS_SOURCE,
        _imports_by_target,
        _walk_modules,
    )

    decls, path_to_dotted, path_to_tree, corpus = _walk_modules()
    per_symbol, star = _imports_by_target(path_to_dotted, path_to_tree)
    source = _THIS_SOURCE.read_text(encoding="utf-8")

    decisions = plan_refresh(corpus, decls, per_symbol, source, star)
    outcomes = {d.outcome for d in decisions}
    assert Outcome.REFRESH in outcomes, "the live tree must have refreshable still-dead entries"
    unrecoverable = [d.entry.bare_name for d in decisions if d.outcome == Outcome.UNRECOVERABLE]
    assert not unrecoverable, f"WP01 normalization gap — unrecoverable provenance for: {unrecoverable}"

    once = refresh(corpus, decls, per_symbol, source, star)
    twice = refresh(corpus, decls, per_symbol, once, star)
    assert once == twice, "refresh must be idempotent over the real tree"


# ---------------------------------------------------------------------------
# T009 — THE non-fakeable NFR-001 / SC-006 regression
# ---------------------------------------------------------------------------


def _t009_corpus() -> tuple[dict[str, CorpusModule], dict[str, frozenset[str]]]:
    corpus = {
        "synthetic.mod_a": _module(_one_symbol("Foo", "11")),  # X, positive control
        "synthetic.mod_b": _module(_one_symbol("Foo", "22")),  # Y, collision non-admit
        "synthetic.mod_c": _module(_one_symbol("Amb", "33")),
        "synthetic.mod_d": _module(_one_symbol("Amb", "44")),
        "synthetic.mod_e": _module(_one_symbol("Solo", "55")),
    }
    decls = {
        "synthetic.mod_a": frozenset({"Foo"}),
        "synthetic.mod_b": frozenset({"Foo"}),
        "synthetic.mod_c": frozenset({"Amb"}),
        "synthetic.mod_d": frozenset({"Amb"}),
        "synthetic.mod_e": frozenset({"Solo"}),
    }
    return corpus, decls


_T009_SOURCE = (
    "_CATEGORY_TEST = frozenset(\n"
    "    {\n"
    "        # synthetic.mod_a::Foo\n"
    f'        SymbolKey("Foo", "{_OLD_HASH}"),\n'
    "        # synthetic.gone_mod::Gone\n"
    f'        SymbolKey("Gone", "{_OLD_HASH}"),\n'
    f'        SymbolKey("Amb", "{_OLD_HASH}"),\n'
    f'        SymbolKey("Solo", "{_OLD_HASH}"),\n'
    "    }\n"
    ")\n"
)


def _decide_barename_only(entry: AllowlistEntry, still_dead: list[DeadLocation]) -> RefreshDecision:
    """The UNSAFE differential stub — identical to ``decide`` EXCEPT it omits the
    ``module_path`` narrowing step: it matches by ``bare_name`` alone and
    refreshes to the first such candidate corpus-wide (the silent-admit vector).

    It still refreshes X (passes the positive control), so it is NOT a vacuous
    strawman; it fails specifically on (b) [admits a symbol the real helper
    refuses] and (c) [candidate set not narrowed to {X}].
    """
    bare_matches = tuple(sorted(loc.module_path for loc in still_dead if loc.bare_name == entry.bare_name))
    if not bare_matches:
        return RefreshDecision(entry, Outcome.DANGLING, bare_matches, (), None)
    chosen = bare_matches[0]
    new_hash = next(
        loc.new_hash for loc in still_dead if loc.bare_name == entry.bare_name and loc.module_path == chosen
    )
    return RefreshDecision(entry, Outcome.REFRESH, bare_matches, bare_matches, new_hash)


def _apply_stub(source: str, corpus: dict[str, CorpusModule], decls: dict[str, frozenset[str]]) -> str:
    from tests.architectural._refresh_dead_symbol_hashes import _apply

    still_dead = compute_still_dead(corpus, decls, {}, set())
    entries = parse_allowlist_entries(source)
    decisions = [_decide_barename_only(e, still_dead) for e in entries]
    return _apply(source, decisions)


def test_regression_positive_control_candidate_set_and_all_branches() -> None:
    """One run proving (a) positive control, (b) collision non-admit, (c)
    candidate-set narrowing, and (d) all four branches."""
    corpus, decls = _t009_corpus()
    still_dead = compute_still_dead(corpus, decls, {}, set())
    hash_x = next(d.new_hash for d in still_dead if d.module_path == "synthetic.mod_a" and d.bare_name == "Foo")

    decisions = plan_refresh(corpus, decls, {}, _T009_SOURCE)
    by_name = {d.entry.bare_name: d for d in decisions}
    real_rewritten = refresh(corpus, decls, {}, _T009_SOURCE)

    # (a) positive control — X (mod_a::Foo) IS refreshed to its new hash.
    foo = by_name["Foo"]
    assert foo.outcome == Outcome.REFRESH and foo.new_hash == hash_x
    assert hash_x in real_rewritten

    # (c) candidate-set assertion — >=2 bare_name matches narrowed to exactly {X}.
    assert foo.bare_matches == ("synthetic.mod_a", "synthetic.mod_b")
    assert len(foo.bare_matches) >= 2
    assert foo.narrowed == ("synthetic.mod_a",)

    # (b) collision non-admit — Y (mod_b::Foo) is NOT admitted; gate REDs on Y;
    # X is green.
    real_offenders = _offenders(real_rewritten, corpus, decls, {}, set())
    assert "synthetic.mod_b::Foo" in real_offenders
    assert "synthetic.mod_a::Foo" not in real_offenders

    # (d) all four Contract-A branches exercised in this run.
    assert by_name["Gone"].outcome == Outcome.DANGLING
    assert by_name["Amb"].outcome == Outcome.AMBIGUOUS
    assert by_name["Solo"].outcome == Outcome.UNRECOVERABLE
    assert {d.outcome for d in decisions} >= {
        Outcome.REFRESH,
        Outcome.DANGLING,
        Outcome.AMBIGUOUS,
        Outcome.UNRECOVERABLE,
    }


def test_regression_fails_against_barename_only_stub_for_the_right_reason() -> None:
    """The differential: the bare-name-only stub passes (a) but fails (b)/(c).

    * (a) both real and stub refresh X (mod_a::Foo) — the stub is not vacuous.
    * (b) the stub ADMITS mod_e::Solo (refreshes the unrecoverable-provenance
      entry to a corpus-wide bare-name match) — a dead symbol the real helper
      leaves RED.
    * (c) the stub's candidate set for Foo is not narrowed to {X}.
    """
    corpus, decls = _t009_corpus()
    still_dead = compute_still_dead(corpus, decls, {}, set())
    hash_x = next(d.new_hash for d in still_dead if d.module_path == "synthetic.mod_a" and d.bare_name == "Foo")

    real_rewritten = refresh(corpus, decls, {}, _T009_SOURCE)
    stub_rewritten = _apply_stub(_T009_SOURCE, corpus, decls)

    # (a) BOTH refresh X — the stub is a fail-for-the-right-reason differential,
    # not a strawman that simply refuses everything.
    assert hash_x in real_rewritten
    assert hash_x in stub_rewritten
    assert "synthetic.mod_a::Foo" not in _offenders(stub_rewritten, corpus, decls, {}, set())

    # (b) the SAFETY difference: the real helper refuses mod_e::Solo (stays RED);
    # the stub silently admits it (goes GREEN). This is the non-admit teeth.
    real_offenders = _offenders(real_rewritten, corpus, decls, {}, set())
    stub_offenders = _offenders(stub_rewritten, corpus, decls, {}, set())
    assert "synthetic.mod_e::Solo" in real_offenders, "real helper must refuse the unrecoverable entry"
    assert "synthetic.mod_e::Solo" not in stub_offenders, "stub admits a dead symbol — the vector under test"

    # (c) the stub's candidate set is un-narrowed (differs only in the narrowing step).
    stub_foo = next(
        _decide_barename_only(e, still_dead) for e in parse_allowlist_entries(_T009_SOURCE) if e.bare_name == "Foo"
    )
    real_foo = next(d for d in plan_refresh(corpus, decls, {}, _T009_SOURCE) if d.entry.bare_name == "Foo")
    assert real_foo.narrowed == ("synthetic.mod_a",)
    assert stub_foo.narrowed != ("synthetic.mod_a",)
    assert set(stub_foo.narrowed) == {"synthetic.mod_a", "synthetic.mod_b"}


# ---------------------------------------------------------------------------
# T010 — AC3 edges: stale vs dangling, tier preserved
# ---------------------------------------------------------------------------


def test_ac3_gained_caller_body_unchanged_is_stale_not_refreshed() -> None:
    """Gained a caller, body unchanged -> gate REDs with STALE; not refreshed."""
    source_body = _one_symbol("Foo", "7")
    corpus = {"synthetic.mod_a": _module(source_body)}
    decls = {"synthetic.mod_a": frozenset({"Foo"})}
    per_symbol = {"synthetic.mod_a": {"Foo"}}  # Foo now has a caller
    collision_index = classify_collisions(corpus)
    # Allow-list still carries Foo at its CURRENT (unchanged) hash.
    from tests.architectural.test_no_dead_symbols import _resolve_final_key

    live_key = _resolve_final_key("Foo", "synthetic.mod_a", corpus["synthetic.mod_a"], corpus, collision_index)
    assert live_key is not None
    allowlist = frozenset({live_key})
    submodule_index = _submodule_index(per_symbol)

    stale = _compute_stale(decls, set(), corpus, collision_index, allowlist, per_symbol, submodule_index)
    assert "synthetic.mod_a::Foo" in stale

    # The helper does not refresh a symbol that gained a caller (0 still-dead).
    entry = _entry("Foo", provenance_module="synthetic.mod_a", body_hash=live_key.body_hash)
    decision = decide(entry, compute_still_dead(corpus, decls, per_symbol, set()))
    assert decision.outcome != Outcome.REFRESH


def test_ac3_gained_caller_plus_body_edit_is_dangling_not_stale() -> None:
    """Gained a caller AND body edited -> gate REDs with DANGLING, not STALE."""
    corpus = {"synthetic.mod_a": _module(_one_symbol("Foo", "8"))}
    decls = {"synthetic.mod_a": frozenset({"Foo"})}
    per_symbol = {"synthetic.mod_a": {"Foo"}}  # Foo has a caller
    collision_index = classify_collisions(corpus)
    # Allow-list carries Foo under a STALE (pre-edit) hash — no longer resolves.
    allowlist = frozenset({SymbolKey("Foo", _OLD_HASH)})
    submodule_index = _submodule_index(per_symbol)

    stale = _compute_stale(decls, set(), corpus, collision_index, allowlist, per_symbol, submodule_index)
    offenders = _compute_offenders(decls, per_symbol, set(), allowlist, corpus, collision_index)
    dangling = _compute_dangling(allowlist, decls, collision_index, offenders)

    assert "synthetic.mod_a::Foo" not in stale, "a body edit changes the key — the stale matcher cannot match"
    assert any("Foo" in d for d in dangling), "the orphaned pre-edit key must surface as dangling"


def test_ac3_collision_tier_refresh_preserves_module_path_in_source() -> None:
    """A collision-tier entry keeps its ``module_path=`` keyword after refresh."""
    body = 'Dup = "same-body"\n__all__ = ["Dup"]\n'
    corpus = {
        "synthetic.dup_a": _module(body),
        "synthetic.dup_b": _module(body),  # byte-identical -> live collision
    }
    decls = {
        "synthetic.dup_a": frozenset({"Dup"}),
        "synthetic.dup_b": frozenset({"Dup"}),
    }
    source = (
        "_CATEGORY_TEST = frozenset(\n"
        "    {\n"
        f'        SymbolKey("Dup", "{_OLD_HASH}", module_path="synthetic.dup_a"),\n'
        "    }\n"
        ")\n"
    )

    rewritten = refresh(corpus, decls, {}, source)
    entries = parse_allowlist_entries(rewritten)
    assert len(entries) == 1  # golden-count: cardinality-is-contract
    entry = entries[0]
    assert entry.kwarg_module_path == "synthetic.dup_a", "collision-tier module_path must be preserved"
    assert entry.body_hash != _OLD_HASH, "the collision-tier hash must be refreshed"
    assert 'module_path="synthetic.dup_a"' in rewritten


def test_content_tier_entry_needing_collision_tier_escalates_end_to_end() -> None:
    """#3560 finding 1, end-to-end: a CONTENT-tier allow-list entry (no
    ``module_path=`` kwarg) whose only still-dead candidate collides live with
    a sibling symbol must escalate via ``plan_refresh`` and must NOT be
    rewritten by ``refresh``/``_apply`` — an ineffective content-tier hash
    rewrite would leave the gate RED for both ``Dup`` symbols."""
    body = 'Dup = "same-body"\n__all__ = ["Dup"]\n'
    corpus = {
        "synthetic.dup_a": _module(body),
        "synthetic.dup_b": _module(body),  # byte-identical -> live collision
    }
    decls = {
        "synthetic.dup_a": frozenset({"Dup"}),
        "synthetic.dup_b": frozenset({"Dup"}),
    }
    source = (
        "_CATEGORY_TEST = frozenset(\n"
        "    {\n"
        "        # synthetic.dup_a::Dup\n"
        f'        SymbolKey("Dup", "{_OLD_HASH}"),\n'
        "    }\n"
        ")\n"
    )

    decisions = plan_refresh(corpus, decls, {}, source)
    assert len(decisions) == 1  # golden-count: cardinality-is-contract
    decision = decisions[0]
    assert decision.outcome == Outcome.NEEDS_MODULE_PATH, (
        "a content-tier entry whose target needs collision-tier keying must "
        "escalate, never REFRESH an ineffective content-tier hash"
    )
    assert decision.new_hash is None

    rewritten = refresh(corpus, decls, {}, source)
    assert rewritten == source, "_apply must not rewrite an escalation decision"
    assert 'SymbolKey("Dup", "' + _OLD_HASH + '")' in rewritten
