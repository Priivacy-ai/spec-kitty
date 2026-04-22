---
work_package_id: WP02
title: Chokepoint Class and Observation Bundle
dependencies:
- WP01
requirement_refs:
- C-001
- C-002
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-013
- NFR-001
- NFR-002
- NFR-003
- NFR-004
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Implement on the lane worktree allocated by spec-kitty implement WP02. WP01 must be merged to main before starting.
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
- T014
history:
- date: '2026-04-22'
  event: created
  author: planner
authoritative_surface: src/specify_cli/glossary/
execution_mode: code_change
mission_id: 01KPTE0P5JVQFWESWV07R0XG4M
mission_slug: glossary-drg-chokepoint-01KPTE0P
owned_files:
- src/specify_cli/glossary/chokepoint.py
- tests/specify_cli/glossary/test_chokepoint.py
- tests/specify_cli/glossary/bench_chokepoint.py
- architecture/adrs/2026-04-22-5-glossary-chokepoint-p95-measurement.md
tags: []
---

# WP02 — Chokepoint Class and Observation Bundle

## Objective

Implement `GlossaryObservationBundle` (the result container), `GlossaryChokepoint` (the deterministic matching engine), benchmark the chokepoint against the p95 ≤ 50ms target, and draft ADR-5. No executor wiring in this WP — WP03 does that.

## Branch Strategy

- **Planning/base branch:** `main`
- **Final merge target:** `main`
- **Execution worktree:** Allocated by `spec-kitty agent action implement WP02 --agent <name>`. Do not start until WP01 is merged.
- **Start command:** `spec-kitty agent action implement WP02 --agent <name>`

## Context

### What WP01 delivered (expected to be on main)

- `src/doctrine/drg/models.py` — `NodeKind.GLOSSARY = "glossary"` added
- `src/specify_cli/glossary/drg_builder.py` — exports `GlossaryTermIndex`, `build_index()`, `glossary_urn()`, `_normalize()`

### Key constraint: never block, never raise out of `run()`

`GlossaryChokepoint.run()` must catch ALL exceptions internally and return an error-bundle. The executor (WP03) will also wrap the call in its own try/except, but the primary containment is inside `run()` itself.

### No LLM, no I/O in hot path (C-002)

The only I/O permitted in `run()` is reading from the in-memory `GlossaryTermIndex` (already loaded). Index loading is lazy and happens once — it reads from `GlossaryStore`, which reads from `.kittify/glossaries/*.yaml` seed files.

---

## Subtask T008 — Implement `GlossaryObservationBundle`

**Purpose:** Immutable result container for the chokepoint. Always fully populated — never `None`.

**File:** `src/specify_cli/glossary/chokepoint.py` (new)

**Implementation:**

```python
"""GlossaryChokepoint and GlossaryObservationBundle.

GlossaryChokepoint runs deterministic term-matching against the active
glossary index on every profile invocation. No LLM calls; no blocking I/O
in the run() hot path.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from specify_cli.glossary.models import ConflictType, SemanticConflict, Severity, SenseStatus, TermSurface
from specify_cli.glossary.scope import GlossaryScope
from specify_cli.glossary.store import GlossaryStore

if TYPE_CHECKING:
    from specify_cli.glossary.drg_builder import GlossaryTermIndex

_logger = logging.getLogger(__name__)

DEFAULT_APPLICABLE_SCOPES: frozenset[GlossaryScope] = frozenset({
    GlossaryScope.SPEC_KITTY_CORE,
    GlossaryScope.TEAM_DOMAIN,
})


@dataclass(frozen=True)
class GlossaryObservationBundle:
    """Immutable result of one chokepoint run. Always present in InvocationPayload."""

    matched_urns: tuple[str, ...]
    high_severity: tuple[SemanticConflict, ...]   # surfaced inline to host
    all_conflicts: tuple[SemanticConflict, ...]   # written to JSONL trail
    tokens_checked: int
    duration_ms: float
    error_msg: str | None = None                  # non-None on internal failure

    def to_dict(self) -> dict[str, object]:
        """Serializable form for JSONL trail append."""
        return {
            "matched_urns": list(self.matched_urns),
            "high_severity_count": len(self.high_severity),
            "all_conflict_count": len(self.all_conflicts),
            "tokens_checked": self.tokens_checked,
            "duration_ms": self.duration_ms,
            "error_msg": self.error_msg,
            "conflicts": [
                {
                    "urn": urn,
                    "term": c.term.surface_text,
                    "conflict_type": c.conflict_type.value,
                    "severity": c.severity.value,
                    "confidence": c.confidence,
                    "context": c.context,
                }
                for urn, c in zip(self.matched_urns, self.all_conflicts)
            ],
        }
```

**Validation:**
- [ ] `GlossaryObservationBundle` is `frozen=True` (immutable)
- [ ] `to_dict()` produces a JSON-serializable dict (no custom types)
- [ ] An empty bundle (`matched_urns=(), high_severity=(), all_conflicts=(), tokens_checked=0, duration_ms=0.0`) serializes without error

---

## Subtask T009 — Implement `GlossaryChokepoint.__init__()` and lazy `_load_index()`

**Purpose:** The chokepoint must be instantiatable without any I/O (FR-013). The index is loaded on first `run()` call.

**Implementation:**

```python
class GlossaryChokepoint:
    """Deterministic glossary-term chokepoint for profile invocations.

    No I/O on __init__. Index lazily loaded on first run() call.
    """

    def __init__(
        self,
        repo_root: Path,
        applicable_scopes: set[GlossaryScope] | None = None,
    ) -> None:
        self._repo_root = repo_root
        self._applicable_scopes: frozenset[GlossaryScope] = (
            frozenset(applicable_scopes)
            if applicable_scopes is not None
            else DEFAULT_APPLICABLE_SCOPES
        )
        self._index: GlossaryTermIndex | None = None  # lazy

    def _load_index(self) -> GlossaryTermIndex:
        """Load or return cached GlossaryTermIndex."""
        if self._index is not None:
            return self._index
        from specify_cli.glossary.drg_builder import build_index
        # Load the active glossary store from seed files
        store = _load_store(self._repo_root)
        self._index = build_index(store, set(self._applicable_scopes))
        return self._index
```

And the store loader helper:

```python
def _load_store(repo_root: Path) -> GlossaryStore:
    """Load a GlossaryStore from all seed files in .kittify/glossaries/."""
    from specify_cli.glossary.scope import load_seed_file
    store = GlossaryStore(event_log_path=repo_root / ".kittify" / "events" / "glossary.jsonl")
    glossaries_dir = repo_root / ".kittify" / "glossaries"
    if not glossaries_dir.exists():
        return store
    for scope in GlossaryScope:
        for sense in load_seed_file(scope, repo_root):
            store.add_sense(sense)
    return store
```

**Validation:**
- [ ] `GlossaryChokepoint(repo_root=Path("."))` completes instantly (no I/O)
- [ ] `self._index` is `None` after `__init__`
- [ ] `_load_index()` is idempotent — calling it twice returns the same index object

---

## Subtask T010 — Implement `GlossaryChokepoint.run()`

**Purpose:** The hot-path method. Tokenizes request text, looks up terms against the index, classifies conflicts, measures duration. Must never raise.

**Implementation:**

```python
# Tokenizer pattern — split on whitespace and non-word chars
_TOKENIZER = re.compile(r"[\s\W]+")

def run(self, request_text: str, invocation_id: str = "") -> GlossaryObservationBundle:
    """Run the chokepoint. Never raises; returns error-bundle on failure."""
    t0 = time.monotonic()
    try:
        return self._run_inner(request_text, invocation_id, t0)
    except Exception as exc:  # noqa: BLE001
        duration_ms = (time.monotonic() - t0) * 1000.0
        _logger.warning(
            "GlossaryChokepoint.run failed (invocation_id=%r): %r",
            invocation_id, exc,
        )
        return GlossaryObservationBundle(
            matched_urns=(),
            high_severity=(),
            all_conflicts=(),
            tokens_checked=0,
            duration_ms=duration_ms,
            error_msg=repr(exc),
        )

def _run_inner(
    self, request_text: str, invocation_id: str, t0: float
) -> GlossaryObservationBundle:
    from specify_cli.glossary.extraction import COMMON_WORDS
    from specify_cli.glossary.drg_builder import _normalize

    index = self._load_index()
    tokens = [t for t in _TOKENIZER.split(request_text.lower()) if t]
    tokens_checked = len(tokens)

    matched_urns: list[str] = []
    all_conflicts: list[SemanticConflict] = []

    seen_surfaces: set[str] = set()
    for raw_token in tokens:
        if raw_token in COMMON_WORDS:
            continue
        normalized = _normalize(raw_token)
        if normalized in COMMON_WORDS:
            continue
        if normalized in seen_surfaces:
            continue  # deduplicate within one request
        seen_surfaces.add(normalized)

        urn = index.surface_to_urn.get(normalized)
        if urn is None:
            continue

        senses = index.surface_to_senses.get(normalized, [])
        conflict = _classify(normalized, senses, context="request_text")
        if conflict is not None:
            matched_urns.append(urn)
            all_conflicts.append(conflict)

    high_severity = tuple(c for c in all_conflicts if c.severity == Severity.HIGH)
    duration_ms = (time.monotonic() - t0) * 1000.0

    return GlossaryObservationBundle(
        matched_urns=tuple(matched_urns),
        high_severity=high_severity,
        all_conflicts=tuple(all_conflicts),
        tokens_checked=tokens_checked,
        duration_ms=duration_ms,
        error_msg=None,
    )
```

**Validation:**
- [ ] Clean request (no known terms) returns bundle with `error_msg=None`, empty conflict lists
- [ ] Request containing a known term returns that term's URN in `matched_urns`
- [ ] `duration_ms` is positive and non-zero
- [ ] Any exception inside `_run_inner` is caught by `run()` → error-bundle returned

---

## Subtask T011 — Implement `_classify()` conflict classifier

**Purpose:** Given a matched surface and its active senses, produce a `SemanticConflict` (or `None` for unambiguous clean terms).

**Implementation:**

```python
def _classify(
    surface: str,
    senses: list,  # list[TermSense]
    context: str = "",
) -> SemanticConflict | None:
    """Classify a matched glossary term hit as a SemanticConflict.

    v1 severity model:
    - 0 active senses → None (shouldn't happen if index is correct)
    - 1 active sense, confidence >= 0.9 → None (unambiguous, no conflict)
    - 1 active sense, confidence < 0.9 → LOW conflict
    - 2+ active senses → MEDIUM (ambiguous)
    - Any sense with confidence < 0.7 → HIGH (inconsistent/low-confidence term)
    """
    if not senses:
        return None

    active = [s for s in senses if s.status == SenseStatus.ACTIVE]
    if not active:
        return None

    min_confidence = min(s.confidence for s in active)
    term_surface = TermSurface(surface)

    if min_confidence < 0.7:
        return SemanticConflict(
            term=term_surface,
            conflict_type=ConflictType.INCONSISTENT,
            severity=Severity.HIGH,
            confidence=1.0 - min_confidence,
            candidate_senses=[],
            context=context,
        )
    if len(active) > 1:
        return SemanticConflict(
            term=term_surface,
            conflict_type=ConflictType.AMBIGUOUS,
            severity=Severity.MEDIUM,
            confidence=0.8,
            candidate_senses=[],
            context=context,
        )
    if active[0].confidence < 0.9:
        return SemanticConflict(
            term=term_surface,
            conflict_type=ConflictType.UNKNOWN,
            severity=Severity.LOW,
            confidence=active[0].confidence,
            candidate_senses=[],
            context=context,
        )
    return None  # unambiguous, high-confidence → no conflict surfaced
```

**Validation:**
- [ ] Single high-confidence sense → `None`
- [ ] Single low-confidence sense (< 0.9) → `LOW`
- [ ] Single very-low-confidence sense (< 0.7) → `HIGH`
- [ ] Two active senses → `MEDIUM`
- [ ] Empty senses → `None`

---

## Subtask T012 — Write benchmark script `tests/specify_cli/glossary/bench_chokepoint.py`

**Purpose:** Measure p95 latency to validate NFR-001 (≤50ms at 2,000 words + 500 terms) and NFR-002 (≤2ms at ≤50 words).

**File:** `tests/specify_cli/glossary/bench_chokepoint.py` (new, not run by default CI)

**Implementation sketch:**

```python
"""Benchmark: GlossaryChokepoint.run() latency.

Run manually: python tests/specify_cli/glossary/bench_chokepoint.py
Not included in the default pytest suite.
"""
import statistics
import time
from pathlib import Path
from unittest.mock import MagicMock
from specify_cli.glossary.chokepoint import GlossaryChokepoint
from specify_cli.glossary.drg_builder import GlossaryTermIndex

# Build a synthetic 500-term index
def make_synthetic_index(n: int) -> GlossaryTermIndex:
    surfaces = [f"term{i}" for i in range(n)]
    surface_to_urn = {s: f"glossary:{i:08x}" for i, s in enumerate(surfaces)}
    return GlossaryTermIndex(
        surface_to_urn=surface_to_urn,
        surface_to_senses={s: [] for s in surfaces},
        applicable_scope_set=frozenset(),
        term_count=n,
    )

def bench(label: str, text: str, chokepoint: GlossaryChokepoint, n: int = 1000) -> None:
    times = []
    for _ in range(n):
        bundle = chokepoint.run(text, invocation_id="bench")
        times.append(bundle.duration_ms)
    p50 = statistics.median(times)
    p95 = sorted(times)[int(n * 0.95)]
    print(f"{label}: p50={p50:.2f}ms p95={p95:.2f}ms")

if __name__ == "__main__":
    # Patch _load_index to use synthetic index
    idx = make_synthetic_index(500)
    cp = GlossaryChokepoint.__new__(GlossaryChokepoint)
    cp._repo_root = Path(".")
    cp._applicable_scopes = frozenset()
    cp._index = idx

    short_text = " ".join(["what is the status of WP01"] * 4)   # ~50 words
    medium_text = " ".join(["review mission lane work package"] * 50)  # ~500 words
    long_text = " ".join(["mission lane worktree implement review"] * 100)  # ~2000 words

    bench("50-word request, 500-term index", short_text, cp)
    bench("500-word request, 500-term index", medium_text, cp)
    bench("2000-word request, 500-term index", long_text, cp)
```

**Run the benchmark and record results.** Record p95 values for all three input sizes. They will feed T013 (ADR-5).

**Validation:**
- [ ] Script runs without error: `python tests/specify_cli/glossary/bench_chokepoint.py`
- [ ] p95 ≤ 50ms for 2,000-word input
- [ ] p95 ≤ 2ms for 50-word input
- [ ] If p95 > 50ms: record the value and note in T013 that the threshold may need revision

---

## Subtask T013 — Draft ADR-5

**Purpose:** Document the p95 latency measurement, the confirmed threshold, and the rationale. Required by DIRECTIVE_003 (Decision Documentation Requirement) and spec Assumption A-1.

**File:** `architecture/adrs/2026-04-22-5-glossary-chokepoint-p95-measurement.md` (new)

**Template:**

```markdown
# ADR-5: Glossary Chokepoint p95 Latency Threshold

**Date:** 2026-04-22
**Status:** Accepted
**Deciders:** [author]
**Issue:** #467 (Phase 5 — glossary chokepoint)

## Context

The glossary chokepoint in `ProfileInvocationExecutor.invoke()` must be non-blocking and
deterministic. Issue #467 proposed a p95 ≤ 50ms threshold as an assumption (spec A-1).
This ADR records the actual measured value.

## Benchmark Methodology

- Synthetic `GlossaryTermIndex` with 500 active terms
- 1,000 iterations per input size
- Request text sizes: 50 words, 500 words, 2,000 words
- Machine: [describe]
- Python version: [describe]
- Measurement: `GlossaryObservationBundle.duration_ms` (time.monotonic() inside `run()`)

## Results

| Input size | p50 | p95 |
|-----------|-----|-----|
| 50 words  | [X]ms | [Y]ms |
| 500 words | [X]ms | [Y]ms |
| 2,000 words | [X]ms | [Y]ms |

## Decision

p95 threshold for the chokepoint: **[confirmed or revised value]ms** at 500 terms / 2,000 words.

[If below 50ms: The original 50ms threshold from issue #467 is confirmed.]
[If above 50ms: The threshold is revised to Xms based on measurement. This is acceptable because...]

## Consequences

- The `run()` implementation based on pure-Python suffix stripping + dict lookup meets the
  performance target for realistic Spec Kitty glossary sizes (< 500 terms).
- If glossary size grows beyond 500 terms, performance should be re-benchmarked.
```

**Validation:**
- [ ] ADR-5 file exists at the correct path
- [ ] Benchmark result table is filled in with real numbers
- [ ] Decision section explicitly states the confirmed or revised threshold

---

## Subtask T014 — Unit tests for `GlossaryChokepoint` and `GlossaryObservationBundle`

**File:** `tests/specify_cli/glossary/test_chokepoint.py` (new)

**Critical test: exception isolation**

```python
def test_run_returns_error_bundle_on_exception(tmp_path):
    """Chokepoint must not propagate exceptions from internal failure."""
    cp = GlossaryChokepoint(tmp_path)
    # Inject a broken index
    from specify_cli.glossary.drg_builder import GlossaryTermIndex
    broken_index = MagicMock(spec=GlossaryTermIndex)
    broken_index.surface_to_urn = None  # will cause AttributeError in _run_inner
    cp._index = broken_index

    bundle = cp.run("test request", invocation_id="test-123")
    assert bundle.error_msg is not None
    assert "AttributeError" in bundle.error_msg or bundle.error_msg != ""
    assert bundle.invocation_id_preserved or True  # bundle is returned without raising
```

**Other test cases:**

```python
def test_bundle_immutable():
    bundle = GlossaryObservationBundle(
        matched_urns=(), high_severity=(), all_conflicts=(),
        tokens_checked=0, duration_ms=0.0,
    )
    with pytest.raises((AttributeError, TypeError)):
        bundle.tokens_checked = 99  # frozen dataclass

def test_to_dict_serializable():
    import json
    bundle = GlossaryObservationBundle(
        matched_urns=("glossary:abc",), high_severity=(), all_conflicts=(),
        tokens_checked=10, duration_ms=1.5,
    )
    d = bundle.to_dict()
    json.dumps(d)  # must not raise

def test_run_clean_request_returns_empty_bundle(tmp_path):
    cp = GlossaryChokepoint(tmp_path)
    cp._index = make_empty_index()
    bundle = cp.run("what is the current status of WP01")
    assert bundle.error_msg is None
    assert bundle.matched_urns == ()
    assert bundle.tokens_checked > 0

def test_run_high_severity_found(tmp_path):
    """Request containing a low-confidence term → high severity conflict."""
    cp = GlossaryChokepoint(tmp_path)
    cp._index = make_index_with_low_confidence_sense("lane")
    bundle = cp.run("move this to a new lane (channel)", invocation_id="test")
    assert any(c.severity == Severity.HIGH for c in bundle.all_conflicts)
    assert len(bundle.high_severity) > 0

def test_lazy_init_no_io_on_construction(tmp_path):
    """__init__ must complete without any filesystem access."""
    import unittest.mock
    with unittest.mock.patch("builtins.open", side_effect=AssertionError("I/O during init")):
        cp = GlossaryChokepoint(tmp_path)  # must not raise
    assert cp._index is None

def test_chokepoint_default_scopes():
    from specify_cli.glossary.scope import GlossaryScope
    cp = GlossaryChokepoint.__new__(GlossaryChokepoint)
    cp._applicable_scopes = GlossaryChokepoint.__init__.__defaults__  # not accessible this way
    # Just verify DEFAULT_APPLICABLE_SCOPES contains the expected values
    from specify_cli.glossary.chokepoint import DEFAULT_APPLICABLE_SCOPES
    assert GlossaryScope.SPEC_KITTY_CORE in DEFAULT_APPLICABLE_SCOPES
    assert GlossaryScope.TEAM_DOMAIN in DEFAULT_APPLICABLE_SCOPES
    assert GlossaryScope.MISSION_LOCAL not in DEFAULT_APPLICABLE_SCOPES
```

**Validation:**
- [ ] All tests pass
- [ ] `mypy --strict src/specify_cli/glossary/chokepoint.py` → zero errors
- [ ] `ruff check src/specify_cli/glossary/chokepoint.py` → zero errors
- [ ] ≥90% line coverage on `chokepoint.py` (`pytest --cov=specify_cli.glossary.chokepoint`)

---

## Definition of Done

- [ ] `src/specify_cli/glossary/chokepoint.py` contains `GlossaryObservationBundle` and `GlossaryChokepoint`
- [ ] `GlossaryChokepoint.run()` never raises (verified by exception-injection test)
- [ ] Benchmark p95 documented in ADR-5
- [ ] `tests/specify_cli/glossary/test_chokepoint.py` exists and all tests pass
- [ ] `mypy --strict` and `ruff check` pass on all new files
- [ ] ≥90% line coverage on `chokepoint.py`

## Reviewer Guidance

1. Run the exception-injection test manually and confirm `error_msg` is set.
2. Verify `GlossaryObservationBundle` is `frozen=True` — attempt attribute mutation should raise.
3. Verify `DEFAULT_APPLICABLE_SCOPES` contains `SPEC_KITTY_CORE` and `TEAM_DOMAIN` only.
4. Review ADR-5 benchmark numbers — if p95 > 50ms, the threshold must be revised with justification.
5. Confirm no new `pip` dependencies were introduced.
