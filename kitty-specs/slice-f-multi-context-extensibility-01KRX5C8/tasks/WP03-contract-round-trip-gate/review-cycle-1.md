---
affected_files: []
cycle_number: 1
mission_slug: slice-f-multi-context-extensibility-01KRX5C8
reproduction_command:
reviewed_at: '2026-05-18T13:54:26Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP03
review_artifact_override_at: "2026-05-18T14:09:27Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP03"
review_artifact_override_reason: "Cycle 2 approved by reviewer-renata: orchestrator remediation (866d6ade) removed 3 stub Pydantic models from WP06/09/10 territories, reverted BaselinesFile loosening, converted round-trip ImportError to pytest.skip with future-WP attribution. WP06/WP09/WP10 task files carry binding acceptance criterion to flip skipped cases to PASSED (1bbb5310). 8 passed / 8 skipped on round-trip gate; 234 passed / 1 skipped on full architectural sweep. Override: review-cycle-1.md verdict was cycle-1 rejection; cycle-2 fully satisfies all acceptance criteria."
---

# WP03 Review Feedback — Cycle 1 (REJECT)

**Reviewer:** orchestrator (per HiC directive)
**Date:** 2026-05-18
**Verdict:** REJECT — substantive scope creep into 3 future WPs

---

## What the WP delivered

WP03's stated scope (per `tasks/WP03-contract-round-trip-gate.md`):
- Implement the contract round-trip walker that parses `pydantic_model:` + `expect:` frontmatter on YAML codeblocks in `kitty-specs/*/contracts/*.md`
- Tag Slice F's 6 contracts with the frontmatter convention
- Land the `_LEGACY_CONTRACT_ALLOWLIST` baseline (151 entries)
- Negative-fixture sanity check

All of this landed correctly across 6 commits (`dc129467` → `704f105f`). The walker works, the parametrized tests run, AC-10 is functionally satisfied.

## Why this rejection

The implementer chose to satisfy the `pydantic_model:` frontmatter by **creating stub Pydantic models in 3 future WPs' owned directories** so the round-trip test had something to import:

| File created | Future WP owner | Scope violation |
|---|---|---|
| `src/charter/drg.py — OrgDRGFragment` (with 8-kind plural validator) | **WP06** (org-DRG loader/merge/validator) | Pre-commits the field shape and validator semantics |
| `src/charter/scope.py — _CharterScopeEntry` (with inner class + empty-root validator) | **WP09** (CharterScope + ADR-8) | Locks the `{root, name}` field set + parsing strictness |
| `src/specify_cli/next/_internal_runtime/workflow_schema.py — WorkflowSequence + ActionStep` (with `terminal: bool`, dangling-ref `model_validator`, default empty lists) | **WP10** (workflow YAML schema + registry) | Substantive design — every field is a future-WP architecture decision |

Plus 2 cross-WP-ownership edits:
- `BaselinesFile` Pydantic schema relaxed to accept `Any` values (WP01-owned)
- `test_ratchet_baselines.py` ruff fixes (WP01-owned)

## Why this matters

The mission was specifically structured as **single-lane sequential execution** (per HiC direction at planning time) **to minimize merge risk and implementation drift**. WP03 doing 3 future WPs' design work (even as stubs) is the exact opposite — it predisposes WP06/WP09/WP10's data models before those WPs have made their architecture decisions.

The cleaner pattern: when an FR-140 round-trip test needs to import models that don't exist yet, **skip the parametrized case** with `@pytest.mark.skipif(model_unavailable)` (or `pytest.importorskip(...)`) and document in the test that the skipif is removed when the owning WP lands. The test's RED-then-GREEN trajectory across WPs becomes part of the ATDD discipline rather than triggering scope creep.

## Required cycle-2 actions

1. **Delete the 3 stub files entirely** (`src/charter/drg.py — OrgDRGFragment` section, `src/charter/scope.py`, `src/specify_cli/next/_internal_runtime/workflow_schema.py`).
2. **Refactor `tests/contract/test_example_round_trip.py`** to use `pytest.importorskip(...)` per parametrized case so contracts referencing not-yet-existing models skip cleanly (with a clear `reason` naming the future WP that lands the model).
3. **Revert the `BaselinesFile` Any-value loosening** in `tests/architectural/test_ratchet_baselines.py`. The cleaner path: reshape the `ratchet-baseline-format.md` contract example so its codeblock is schema-only (the `<discovered-at-WP03>` placeholder is fine for documentation; just don't run it through the round-trip walker — mark it `expect: invalid` OR use a separate `expect: valid` block with a real number).

## Notes for downstream WPs

Add an explicit acceptance criterion to WP06 / WP09 / WP10 task files: **"removing the `skipif` decorator from `tests/contract/test_example_round_trip.py` case `<case_id>` is required for approval"**. This turns the skipped case into a per-WP red→green deliverable, preserving ATDD discipline across the lane.

## Orchestrator remediation

Per HiC directive: orchestrator applies all 3 interventions directly (not via re-dispatched implementer). Re-submission to `for_review` will note `cycle-2 remediation applied by orchestrator per HiC directive`.

— orchestrator
