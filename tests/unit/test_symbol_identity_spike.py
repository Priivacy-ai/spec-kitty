"""WP06 (IC-WS2-SPIKE) — relocation-proof symbol-identity design spike.

Prototypes and proves (or disproves) two candidate dead-symbol allow-list
keys against real T004 same-name fixtures from ``test_no_dead_symbols.py``,
runs a body-hash stability probe, and records the WP06 carve/continue
decision. See ``tests/architectural/_symbol_identity.py`` for the candidate
implementations and full design rationale; this module is the SPIKE PROOF,
not the gate — ``test_no_dead_symbols.py``'s 343-entry allow-list is
UNTOUCHED by WP06.

CARVE / CONTINUE RECOMMENDATION (T028)
=======================================

**Recommendation: CARVE to standalone #2546.**

Reasoning, evidence-based against the C-004 tripwire ("carve if the key
needs >2 implementation WPs, OR the body-hash proves unstable"):

1. **The body-hash itself is STABLE (T027).** Reusing
   ``anchoring.code_tokens_by_line`` for token normalization, the body-hash is
   provably unaffected by the NFR-001 motion battery (blank-line insertion,
   comment insertion, whitespace reformatting) and by the documented
   3.11<->3.12 f-string re-tokenization (PEP 701) — see
   ``test_code_tokens_by_line_strips_fstring_interpolation_content`` below,
   which exercises the exact same substrate property the existing
   ``composite_key`` ratchets already depend on. This half of the tripwire is
   NOT what forces the carve.

2. **The key design needs a second, structurally-different tier (T026),
   pushing "design" alone past a single WP.** A pure content key —
   ``(bare_name, body_hash)``, CANDIDATE A / :func:`relocation_only_identity`
   — is proven (below) to COLLIDE for the real
   ``doctrine.directives::ArtifactKind`` / ``doctrine.procedures::ArtifactKind``
   / ``doctrine.tactics::ArtifactKind`` fixture trio: all three re-export
   sites contain the byte-identical statement
   ``from doctrine.artifact_kinds import ArtifactKind``, so their local
   definition-site text cannot distinguish them by content alone. Sanctioning
   any one of the three under CANDIDATE A silently sanctions all three —
   reproducing the exact T004 re-blinding bare-name-alone was banned to
   prevent, via a different route. Restoring correctness requires CANDIDATE B
   / :func:`hybrid_identity` (adds a module-path tiebreak) — but that
   surrenders genuine cross-file relocation tolerance for precisely this
   fan-out subset, which is also FR-008's explicitly-named exemption category
   ("docstring/``__all__``-only re-export decomposition shims"). A real
   design would need BOTH tiers plus a rule for *when* to escalate from A to
   B — that is design work beyond a key-swap, before any migration starts.

3. **A third structural shape exists that neither candidate can even locate.**
   ``specify_cli.runtime::ResolutionResult`` / ``ResolutionTier`` are exposed
   via a lazy ``__getattr__`` facade dict (``_EXPORT_MODULES``), not an
   AST-visible name binding at all — :func:`definition_span` correctly
   returns ``None`` for it (proven below). A real implementation needs a
   THIRD detector path (dict-literal-value resolution) on top of the two
   already required by finding 2.

4. **WP-count arithmetic hits the tripwire.** Design (points 2+3, a two-tier
   key plus a facade-dict detector — already more than "prototype a key")
   is WP1; the 343-entry bulk migration (untouched by this WP, per the
   isolation rule) is WP2; FR-008's auto-derived exempt-category / module
   detectors (registry migrations, re-export shims, Typer sub-apps) are WP3.
   That is 3 implementation WPs for the *minimum* correct design — at the
   C-004 threshold's boundary, and the fan-out/facade findings above show the
   real count is likely to grow past 3 once edge cases (multi-target
   ``ImportFrom``, conditional/``TYPE_CHECKING``-guarded re-exports,
   decorator-carrying class bodies) are handled for all ~343 entries.

**Net**: the tripwire's "unstable body-hash" branch is NOT hit, but the
"key needs >2 implementation WPs" branch IS — CARVE, ship WS1+WS3 now, seed
#2546 with this spike's findings (candidate A/B split, the facade-dict gap,
and the concrete fan-out fixtures below as its regression corpus).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.contracts.anchoring import code_tokens_by_line
from tests.architectural._symbol_identity import (
    body_hash_for_definition,
    hybrid_identity,
    relocation_only_identity,
)

pytestmark = [pytest.mark.unit]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"

RECOMMENDATION = "CARVE"
RECOMMENDATION_REASON = (
    "key needs >2 implementation WPs (two-tier candidate + facade-dict "
    "detector, before the 343-entry migration and FR-008 category work); "
    "body-hash itself is stable under the T027 motion battery + f-string probe"
)

# ---------------------------------------------------------------------------
# T026 — real T004 same-name fixture files (module::Name allow-list STRINGS
# in test_no_dead_symbols.py, not importable classes; read as source text).
# ---------------------------------------------------------------------------

_ARTIFACT_KIND_DIRECTIVES = _SRC_ROOT / "doctrine" / "directives" / "__init__.py"
_ARTIFACT_KIND_PROCEDURES = _SRC_ROOT / "doctrine" / "procedures" / "__init__.py"
_ARTIFACT_KIND_TACTICS = _SRC_ROOT / "doctrine" / "tactics" / "__init__.py"

_GATE_DECISION_BRANCH_STRATEGY = (
    _SRC_ROOT / "specify_cli" / "cli" / "commands" / "_branch_strategy_gate.py"
)
_GATE_DECISION_RECEIVERS = _SRC_ROOT / "specify_cli" / "delivery" / "receivers.py"

_RESOLUTION_RESULT_RESOLVER = _SRC_ROOT / "specify_cli" / "runtime" / "resolver.py"
_RESOLUTION_RESULT_RUNTIME_FACADE = _SRC_ROOT / "specify_cli" / "runtime" / "__init__.py"


def _read(path: Path) -> str:
    assert path.is_file(), f"T026 fixture file missing: {path}"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# T025 — prototype the key: pure-move and distinct-symbol properties
# (synthetic sources, isolated from real-fixture noise).
# ---------------------------------------------------------------------------

_MODULE_A_SRC = '''"""Module A docstring."""

from __future__ import annotations


class Widget:
    """A widget."""

    value: int
'''

_MODULE_B_SRC = '''"""Module B docstring -- a completely different file the symbol relocated to."""

import os  # unrelated import picked up along the way, irrelevant to the body


class Widget:
    """A widget."""

    value: int
'''

_MODULE_C_SRC = '''"""Module C docstring."""

class Widget:
    """A DIFFERENT widget entirely -- distinct field."""

    other_field: str
'''


def test_pure_move_same_name_and_body_new_module_yields_same_key() -> None:
    """T025: a symbol whose definition moves file-to-file (same name + body)
    keeps an identical CANDIDATE A key even though the surrounding module
    content (docstring, imports, blank-line layout) differs -- the
    module-path-free design is relocation-tolerant by construction."""
    ident_a = relocation_only_identity(_MODULE_A_SRC, "Widget")
    ident_b = relocation_only_identity(_MODULE_B_SRC, "Widget")
    assert ident_a is not None
    assert ident_b is not None
    assert ident_a.as_key() == ident_b.as_key()


def test_two_distinct_same_named_symbols_get_distinct_keys() -> None:
    """T025: same bare name, genuinely different body -> distinct keys."""
    ident_a = relocation_only_identity(_MODULE_A_SRC, "Widget")
    ident_c = relocation_only_identity(_MODULE_C_SRC, "Widget")
    assert ident_a is not None
    assert ident_c is not None
    assert ident_a.as_key() != ident_c.as_key()


def test_candidate_a_is_not_bare_name_alone() -> None:
    """T025: CANDIDATE A always carries a body disambiguator alongside the
    bare name -- it is never a bare-name-alone key, even though (per T026
    below) that disambiguator is not always sufficient."""
    ident = relocation_only_identity(_MODULE_A_SRC, "Widget")
    assert ident is not None
    assert ident.bare_name == "Widget"
    assert ident.body_hash  # non-empty content disambiguator present


# ---------------------------------------------------------------------------
# T026 — the load-bearing T004 no-false-negative proof, against real fixtures.
# ---------------------------------------------------------------------------


def test_candidate_a_distinguishes_the_two_real_gate_decision_siblings() -> None:
    """Positive control: specify_cli.cli.commands._branch_strategy_gate::GateDecision
    and specify_cli.delivery.receivers::GateDecision are independently-defined
    dataclasses with different fields -- CANDIDATE A (pure body-hash, no
    module component) already distinguishes them correctly."""
    branch_gate_src = _read(_GATE_DECISION_BRANCH_STRATEGY)
    receivers_src = _read(_GATE_DECISION_RECEIVERS)

    branch_gate_id = relocation_only_identity(branch_gate_src, "GateDecision")
    receivers_id = relocation_only_identity(receivers_src, "GateDecision")

    assert branch_gate_id is not None
    assert receivers_id is not None
    assert branch_gate_id.as_key() != receivers_id.as_key()


def test_candidate_a_collides_on_the_real_artifact_kind_reexport_fanout() -> None:
    """THE load-bearing negative finding: doctrine.directives::ArtifactKind,
    doctrine.procedures::ArtifactKind, and doctrine.tactics::ArtifactKind are
    three real T004 fixtures that all contain the byte-identical re-export
    statement ``from doctrine.artifact_kinds import ArtifactKind``. CANDIDATE
    A cannot distinguish them by content alone -- proving a pure body-hash
    key is insufficient for real re-export fan-out."""
    directives_id = relocation_only_identity(_read(_ARTIFACT_KIND_DIRECTIVES), "ArtifactKind")
    procedures_id = relocation_only_identity(_read(_ARTIFACT_KIND_PROCEDURES), "ArtifactKind")
    tactics_id = relocation_only_identity(_read(_ARTIFACT_KIND_TACTICS), "ArtifactKind")

    assert directives_id is not None
    assert procedures_id is not None
    assert tactics_id is not None
    assert directives_id.as_key() == procedures_id.as_key() == tactics_id.as_key()


def test_t004_reblinding_is_reproduced_by_candidate_a_on_artifact_kind() -> None:
    """Negative control expressed as an allow-list simulation: because
    CANDIDATE A collapses the ArtifactKind trio to one shared key (previous
    test), sanctioning *any one* of the three re-export sites makes the
    allow-list treat ALL THREE as sanctioned -- the exact bare-name-alone
    re-blinding T004 exists to catch, reproduced via CANDIDATE A."""
    directives_id = relocation_only_identity(_read(_ARTIFACT_KIND_DIRECTIVES), "ArtifactKind")
    procedures_id = relocation_only_identity(_read(_ARTIFACT_KIND_PROCEDURES), "ArtifactKind")
    tactics_id = relocation_only_identity(_read(_ARTIFACT_KIND_TACTICS), "ArtifactKind")
    assert directives_id and procedures_id and tactics_id

    # Only `directives` is sanctioned; `procedures` is meant to be a
    # genuinely dead sibling that should still be CAUGHT (not in the
    # allow-list).
    allowlist = frozenset({directives_id.as_key()})

    # RE-BLINDING: because all three share one key under CANDIDATE A, the
    # unsanctioned `procedures` entry is incorrectly treated as allowed.
    assert procedures_id.as_key() in allowlist
    assert tactics_id.as_key() in allowlist


def test_hybrid_candidate_b_distinguishes_the_artifact_kind_fanout() -> None:
    """CANDIDATE B (module-path tiebreak) restores correctness for the same
    fixture trio CANDIDATE A collapses."""
    directives_id = hybrid_identity(
        _read(_ARTIFACT_KIND_DIRECTIVES), "doctrine.directives", "ArtifactKind"
    )
    procedures_id = hybrid_identity(
        _read(_ARTIFACT_KIND_PROCEDURES), "doctrine.procedures", "ArtifactKind"
    )
    tactics_id = hybrid_identity(_read(_ARTIFACT_KIND_TACTICS), "doctrine.tactics", "ArtifactKind")

    assert directives_id is not None
    assert procedures_id is not None
    assert tactics_id is not None
    keys = {directives_id.as_key(), procedures_id.as_key(), tactics_id.as_key()}
    assert len(keys) == 3  # all three distinct


def test_t004_no_reblinding_proof_with_hybrid_key() -> None:
    """THE load-bearing T004 no-false-negative proof (T026): using CANDIDATE
    B against the real ArtifactKind trio, marking one sibling dead while
    another is sanctioned means the dead one is STILL CAUGHT -- no
    re-blinding."""
    directives_id = hybrid_identity(
        _read(_ARTIFACT_KIND_DIRECTIVES), "doctrine.directives", "ArtifactKind"
    )
    procedures_id = hybrid_identity(
        _read(_ARTIFACT_KIND_PROCEDURES), "doctrine.procedures", "ArtifactKind"
    )
    tactics_id = hybrid_identity(_read(_ARTIFACT_KIND_TACTICS), "doctrine.tactics", "ArtifactKind")
    assert directives_id and procedures_id and tactics_id

    # `directives` and `tactics` are sanctioned siblings; `procedures` is the
    # genuinely dead one that must still be caught.
    allowlist = frozenset({directives_id.as_key(), tactics_id.as_key()})

    assert directives_id.as_key() in allowlist
    assert tactics_id.as_key() in allowlist
    assert procedures_id.as_key() not in allowlist  # <-- still caught, no re-blinding


def test_resolver_import_alias_resolution_result_is_locatable() -> None:
    """specify_cli.runtime.resolver::ResolutionResult is a plain
    ``from charter.resolution import ResolutionResult, ResolutionTier``
    import-alias re-export -- both candidate keys can locate and hash it."""
    resolver_src = _read(_RESOLUTION_RESULT_RESOLVER)
    ident = relocation_only_identity(resolver_src, "ResolutionResult")
    assert ident is not None


def test_facade_dict_resolution_result_export_is_not_locatable() -> None:
    """A third real structural finding (T026): specify_cli.runtime::ResolutionResult
    is exposed only via a lazy ``__getattr__`` facade dict
    (``_EXPORT_MODULES = {"ResolutionResult": _RESOLVER_MODULE, ...}``) --
    the bound name is a dict KEY STRING, not an AST-visible module-level
    binding. Neither candidate key can even locate a definition span for it
    today; a real implementation needs a third, dict-literal-aware detector.
    This is evidence for the WP-count carve reasoning above, not a bug in
    ``definition_span``."""
    runtime_facade_src = _read(_RESOLUTION_RESULT_RUNTIME_FACADE)
    ident = relocation_only_identity(runtime_facade_src, "ResolutionResult")
    assert ident is None


# ---------------------------------------------------------------------------
# T027 — body-hash stability probe: motion battery + interpreter probe.
# ---------------------------------------------------------------------------

_BASE_SAMPLE_SRC = '''class Sample:
    """Doc."""

    field_one: int
    field_two: str
'''


def test_body_hash_stable_under_blank_line_insertion() -> None:
    mutated = '''class Sample:
    """Doc."""


    field_one: int

    field_two: str
'''
    assert body_hash_for_definition(_BASE_SAMPLE_SRC, "Sample") == body_hash_for_definition(
        mutated, "Sample"
    )


def test_body_hash_stable_under_comment_insertion() -> None:
    mutated = '''class Sample:
    """Doc."""

    field_one: int
    # a comment describing field_two, added later
    field_two: str
'''
    assert body_hash_for_definition(_BASE_SAMPLE_SRC, "Sample") == body_hash_for_definition(
        mutated, "Sample"
    )


def test_body_hash_stable_under_whitespace_reformatting() -> None:
    mutated = '''class Sample:
    """Doc."""

    field_one   :    int
    field_two:str
'''
    assert body_hash_for_definition(_BASE_SAMPLE_SRC, "Sample") == body_hash_for_definition(
        mutated, "Sample"
    )


def test_body_hash_changes_on_genuine_field_edit() -> None:
    """Negative control: NFR-002 bite must survive -- a real semantic change
    (field type edit) must change the hash, or the design would silently
    stop catching genuine offenders."""
    mutated = '''class Sample:
    """Doc."""

    field_one: int
    field_two: bool
'''
    assert body_hash_for_definition(_BASE_SAMPLE_SRC, "Sample") != body_hash_for_definition(
        mutated, "Sample"
    )


_FSTRING_SRC = '''class Sample:
    def render(self) -> str:
        value = 42
        return f"prefix {value} suffix"
'''


def test_code_tokens_by_line_strips_fstring_interpolation_content() -> None:
    """T027 (b): the body-hash primitive reuses
    ``anchoring.code_tokens_by_line``'s documented 3.11<->3.12 interpreter
    independence (T025) rather than forking a second normalizer. On 3.11 an
    f-string is a single STRING token (dropped whole); on 3.12+ PEP 701
    re-tokenizes it into FSTRING_START/MIDDLE/END plus the interpolation's
    ordinary tokens, which ``code_tokens_by_line`` explicitly drops too (see
    its docstring), so the token-line is identical on both. This proves the
    substrate property this spike leans on, on whichever interpreter runs
    it."""
    tokens = code_tokens_by_line(_FSTRING_SRC)
    return_line = next(v for v in tokens.values() if v.startswith("return"))
    assert return_line == "return"  # neither "value" nor "prefix"/"suffix" leaked


def test_body_hash_unaffected_by_fstring_interpolation_content_change() -> None:
    """Corollary: since the f-string interior is fully stripped, changing
    *only* the interpolated expression (leaving the surrounding real-code
    ``value = 42`` assignment untouched) is invisible to the body-hash --
    reusing the same interpreter-independence guarantee ``composite_key``
    already relies on elsewhere in this mission (WS1)."""
    reinterpolated = _FSTRING_SRC.replace(
        'f"prefix {value} suffix"', 'f"totally different wording {value + 1} here"'
    )
    assert reinterpolated != _FSTRING_SRC  # sanity: the mutation actually changed something
    assert body_hash_for_definition(_FSTRING_SRC, "Sample") == body_hash_for_definition(
        reinterpolated, "Sample"
    )


# ---------------------------------------------------------------------------
# T028 — carve/continue checkpoint, made a live (not just prose) assertion.
# ---------------------------------------------------------------------------


def test_carve_continue_recommendation_is_recorded() -> None:
    """T028: the recommendation is CARVE (see module docstring for the full
    evidence-based reasoning) -- kept as a live assertion, not just prose, so
    a future edit to this module has to consciously touch the verdict."""
    assert RECOMMENDATION == "CARVE"
    assert "2546" in __doc__  # the seeded standalone-mission tracker ref
    assert RECOMMENDATION_REASON  # non-empty, carried alongside the constant
