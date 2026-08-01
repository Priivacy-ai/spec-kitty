---
affected_files: []
cycle_number: 1
mission_slug: doctrine-built-in-seam-consolidation-01KYW3TX
reproduction_command:
reviewed_at: '2026-07-31T17:28:26Z'
reviewer_agent: reviewer-renata
verdict: rejected
wp_id: WP01
---

# WP01 Review — REJECTED (reviewer-renata)

Mission: `doctrine-built-in-seam-consolidation-01KYW3TX` · WP01 · commit `c6e8737c4`

The implementation code (pack_paths authorities, artifact_kinds SSOT, 9 repo
defaults, 2 DRG root callers, new tests) is excellent and satisfies FR-001/
FR-001b/FR-002/FR-004/FR-005 and NFR-001/003/005. **The rejection is for a
single, concrete, verified regression: an INCOMPLETE campsite fix left a stale
reader that turns 3 previously-green tests red on this branch.** Fix that one
thing and this WP is approvable.

---

## DEFECT (blocking) — stale `resolve_pack_root` patch target — incomplete campsite fix

**File:** `tests/charter/test_context_parity.py:249`
(inside `TestBootstrapCorpusParity._render`, the `with (... patch(...) ...)` block)

**What's wrong:**
Line 249 does:
```python
patch(
    "doctrine.directives.repository.resolve_pack_root",
    return_value=doctrine_root,
),
```
WP01 changed `src/doctrine/directives/repository.py` to
`from doctrine.pack_paths import built_in_dir` and dropped the
`resolve_pack_root` import. `doctrine.directives.repository` therefore no longer
has a `resolve_pack_root` attribute. `unittest.mock.patch` (default
`create=False`) raises **AttributeError at patch entry**, so the whole `_render`
helper explodes before the assertion runs.

**Proof (run in the lane):**
`PWHEADLESS=1 uv run pytest tests/charter/test_context_parity.py -q`
```
AttributeError: <module 'doctrine.directives.repository' ...> does not have the
attribute 'resolve_pack_root'
FAILED tests/charter/test_context_parity.py::TestBootstrapCorpusParity::test_catalog_miss_marker
FAILED tests/charter/test_context_parity.py::TestBootstrapCorpusParity::test_token_budget_substitution_marker
FAILED tests/charter/test_context_parity.py::TestBootstrapCorpusParity::test_golden_byte_parity
3 failed, 4 passed
```

**This is a genuine WP01 regression (red-on-branch, green-on-base):**
`git show c6e8737c4^:src/doctrine/directives/repository.py | grep resolve_pack_root`
shows the base imported `resolve_pack_root` and joined `.../ "directives"`, so
the patch target existed and the tests were green before this commit. WP01
removed the symbol, so the patch now fails.

**Root cause:** This is exactly the reader-idiom regression class flagged in the
WP prompt / Step-5 audit. You correctly repointed ONE stale reader
(`tests/doctrine/test_loader_fail_closed.py`: `...loader.resolve_pack_root` →
`...loader.built_in_root`, a clean minimal campsite fix) but missed the
same-class break in `test_context_parity.py`. A full-tree audit finds exactly
these two; the second was not fixed.

**Required fix (minimal, behavior-preserving campsite edit — same justification
as the test_loader_fail_closed.py edit you already made):**
Repoint the patch to the relocated seam while preserving the fixture's intent
(decouple the directive catalog from the live `packs/built-in` canon by pointing
it at the empty `doctrine_root`). The directive repo now resolves via
`built_in_dir(ArtifactKind.DIRECTIVE)` → `resolve_pack_root("built-in") /
"directives"`, so patching `...repository.resolve_pack_root` is both stale AND
conceptually wrong (the join moved into `pack_paths`). Preferred repoint:
```python
patch(
    "doctrine.directives.repository.built_in_dir",
    return_value=doctrine_root / "directives",
),
```
(Alternatively patch `doctrine.pack_paths.resolve_pack_root`, but verify it does
not over-capture other resolutions in the same render.) Re-run
`tests/charter/test_context_parity.py` to green before re-submitting.

**Also re-run the full-tree stale-reader audit after fixing** to confirm no
third reader hides behind a multi-line `patch(...)` call (the single-line regex
in the first pass missed line 249 because the target string is on its own line;
audit by the raw target strings `doctrine.*repository.resolve_pack_root`,
`doctrine.drg.loader.resolve_pack_root`,
`doctrine.drg.migration.extractor.resolve_pack_root`).

---

## Everything else verified PASS (no action needed)

1. **Computed complement, not hand-listed (FR-005/NFR-005):** PASS. No literal
   `{...}` set in `pack_paths.py`; `built_in_dir` uses
   `if not kind.has_built_in_content_dir: raise`. New SSOT
   `_HAS_BUILT_IN_CONTENT_DIR` in `artifact_kinds.py` names exactly the 9
   content-dir kinds True / 3 carve-out (mission_step_contract, template,
   anti_pattern) False; covers all 12 members (no KeyError).
   `_NON_AUGMENTATION_ELIGIBLE_KINDS` is NOT reused. AST guard test present.
2. **`built_in_dir` reads `kind.plural`; named error; `built_in_root()` wraps
   `resolve_pack_root("built-in")`; both in `__all__`:** PASS.
3. **9 repo defaults + 2 DRG callers routed; no residual join outside
   pack_paths; DRG callers use `built_in_root()` (root):** PASS (grep clean).
4. **Positive tests assert through `resolve_pack_root(...)` not raw `.exists()`;
   3 complement kinds raise:** PASS.
5. **Reader-idiom audit:** FAIL — see DEFECT above.
6. **ruff + mypy:** PASS (ruff "All checks passed"; mypy "no issues").
7. **Import-cycle safety:** PASS (`artifact_kinds` is enum-only leaf).

## NOTE for the orchestrator (NOT a WP01 code defect)
`agent action review` entry is blocked by the FR-007/FR-008 bulk-edit
diff-compliance gate flagging WP01's owned src files as
`code_symbols → do_not_change`. Per the occurrence_map's OWN header (lines
8–13, 21), WP01's structural symbol changes are EXPLICITLY out of scope for the
path-rename gate ("those change symbols/signatures, not the path string, so the
path-heuristic gate does not apply"). This is a planning/tooling gap — the
occurrence_map should list WP01's structural src files as exceptions (or the gate
should not run against structural WPs) — not a fault in WP01's implementation.
