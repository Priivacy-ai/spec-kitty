# Contract: Published-Page-Set Resolver

**Module**: `scripts/docs/_published_pages.py` (new)
**Concern**: IC-01
**Requirements**: FR-002, FR-003, FR-013, NFR-005

This module is the single authority for "which source pages are published". It exists because that question currently has two answers — `docs/docfx.json` and a hardcoded list in `tests/docs/test_docs_seo.py` — which silently diverged.

---

## Public surface

```python
def resolve_published_pages(
    *,
    docs_root: Path,
    docfx_config: Path | None = None,
) -> PublishedPageSet: ...
```

| Parameter | Meaning |
|---|---|
| `docs_root` | Directory containing the documentation tree |
| `docfx_config` | Path to `docfx.json`; defaults to `docs_root / "docfx.json"` |

**Returns** a `PublishedPageSet` (see `data-model.md`).

**Raises**

| Condition | Behaviour |
|---|---|
| `docfx.json` missing | `FileNotFoundError` — fail loud. A missing authority must never degrade to "assume everything" or "assume nothing". |
| `docfx.json` unparseable | `ValueError` naming the parse failure |
| Resolved set is empty | `ValueError` — violates I-01 |
| Resolved set below floor | `ValueError` naming observed and expected counts — violates I-02 |

**Fail-closed is mandatory.** Every error path raises. There is no path on which this function returns a degraded or partial set, because a silently-partial set is the defect under repair.

---

## Behavioural contract

### C-R1 — Reads the build's own globs

The `build.content[].files` patterns are read from `docfx.json` at call time. They are **not** duplicated into a module constant. A test asserts that adding a glob to `docfx.json` changes the resolved set, proving the read is live rather than shadowed.

### C-R2 — Honours `exclude`

`docfx.json` declares `"exclude": ["**/_*.md"]`. The resolver applies declared excludes; underscore-prefixed pages are not published and must not be gated.

### C-R3 — Explicit, reasoned exclusions

Additional exclusions beyond `docfx.json`'s own are enumerated with a reason each (I-04, I-05). At minimum:

| Pattern | Reason |
|---|---|
| `archive/**` | Immutable legacy snapshot; not rewritten for search (C-005) |
| `kitty-specs/**` | Generated mission-run pages; no human author for a description |

Any further exclusion requires a written reason in the same table. An exclusion without a reason is indistinguishable from an oversight.

### C-R4 — Non-vacuity floor

A committed floor constant guards against silent under-collection:

```python
MINIMUM_EXPECTED_PAGES: Final[int] = 500
```

Chosen below the measured 674 so ordinary page churn does not cause false failures, and far above the 16 the broken gate resolves, so the current defect would trip it immediately. Raising this constant is a deliberate act; lowering it requires justification.

> **Why a floor rather than an exact count**: the repository already retired a hardcoded exact ADR census count (`_EXPECTED_CENSUS`) on the grounds that it "guards little and merely fails on every legitimate add/remove — pure future friction." A floor captures the real invariant (the set must not collapse) without that friction.

### C-R5 — Glob-semantics fidelity

DocFX glob semantics are not Python `pathlib` semantics. DocFX's `context/**.md` matches recursively including the immediate directory; the naive `pathlib` translation `context/**/*.md` does **not** match `context/foo.md`.

**This is the single highest-risk detail in the mission.** Getting it wrong silently under-collects, which is the exact bug being fixed, wearing a new hat.

Mitigation is empirical, not analytical: a test asserts the resolved count is within a tolerance of the observed 674 and that specific known pages — `docs/api/slash-commands.md`, `docs/guides/install-spec-kitty.md`, `docs/adr/3.x/2026-07-08-1-mission-resolver-port.md` — are members. Reasoning about glob semantics is not accepted as proof; membership assertions are.

### C-R6 — Performance

O(n) in tree size, one filesystem walk, one read per file. Must leave headroom inside the 30-second gate budget (NFR-007) alongside the consuming checks.

---

## Test contract

| Test | Asserts |
|---|---|
| `test_resolves_from_docfx_not_a_constant` | Adding a glob to a temp `docfx.json` changes the result (C-R1) |
| `test_underscore_prefixed_pages_excluded` | `_draft.md` is absent (C-R2) |
| `test_every_exclusion_carries_a_reason` | All `Exclusion.reason` non-empty (I-05) |
| `test_empty_resolution_raises` | Empty set raises rather than returning (I-01) |
| `test_below_floor_raises` | Under-collection raises, naming both counts (I-02) |
| `test_missing_docfx_raises` | Absent config raises `FileNotFoundError` |
| `test_live_tree_membership` | The three known pages above are members (C-R5) |
| `test_live_tree_count_is_realistic` | Live count ≥ floor and within tolerance of 674 (C-R5) |
| `test_would_have_caught_the_original_regression` | A page set built from the retired pre-move globs fails the floor — the regression proof |

The last test is the one that matters. It encodes *this specific bug* so a future reorganisation cannot reproduce it silently.
