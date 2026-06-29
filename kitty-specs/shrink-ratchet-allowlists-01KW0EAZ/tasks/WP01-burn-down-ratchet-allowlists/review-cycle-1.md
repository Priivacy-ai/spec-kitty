---
affected_files: []
cycle_number: 1
mission_slug: shrink-ratchet-allowlists-01KW0EAZ
reproduction_command:
reviewed_at: '2026-06-25T23:28:19Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP01
review_artifact_override_at: "2026-06-26T00:08:20Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP01"
review_artifact_override_reason: "Cycle-2 re-implementation supersedes cycle-1 rejection (parser fix deferred to #2158). Review passed: baselines category_a=9, category_b=276, legacy_contract=151, pure_shim=0, category_5=0 all match live frozenset sizes; category_4=9 untouched. MismatchType grandfather correct (case b: only deleted compat/_adapters/version_checker.py imported it; no other src/ caller). Parser (_extract_all_literal) and write_pipeline.py NOT in diff. test_no_dead_symbols.py NET REMOVAL (-13/+1). Clean net shrink; gates green. Filled issue-matrix verdicts (#2049 fixed; #2048/#2152/#2158 deferred-with-followup)."
---

> **⚠️ Superseded historical record (do not treat as current).** This is the cycle-1 review log. It was
> first overtaken by a re-scope (parser fix deferred) and then again by the **2026-06-29 refresh onto
> current `origin/main`**, where `harden-dead-symbol-gate` overtook FR-001/FR-002/FR-006. The numbers
> below (`category_a=9`, `category_b=284`/`276`/`286→392`, `category_4=9`, "MismatchType grandfather
> correct") reflect earlier states and are NOT the delivered reality. Delivered: FR-003 + FR-004 +
> accuracy sync; `MismatchType` **demoted not grandfathered**; `category_b` informational = **264**;
> `category_4` = **8**. See [spec.md](../../spec.md) for the authoritative account.

# WP01 rejected — re-scope: defer the FR-006 parser fix

**Decision (HiC):** the FR-006 `_extract_all_literal` parser fix has a 38× larger blast radius than planned (un-blinds 57 modules / 117 pre-existing dead symbols), which GREW `category_b_grandfathered_legacy` 286→392 — the opposite of this mission's burn-down purpose. The parser fix is **deferred to its own issue #2158**.

## Required re-implementation (CLEAN shrink, NO parser fix)
Reset the lane to its base, then deliver ONLY the clean removals — do NOT touch `_extract_all_literal` and do NOT modify `src/charter/synthesizer/write_pipeline.py`:

1. **FR-001**: remove `write_pipeline::StagedArtifact` + `::promote` from the slice-F deferred frozenset in `test_no_dead_symbols.py`. These are inert (the gate is still blind to write_pipeline without the parser fix), so removal is safe. Set `_baselines.yaml` `category_a_slice_f_deferred: 9` (live was 11 → −2 = 9). Confirm live size == 9.
2. **FR-002**: remove `charter.activate::charter_activate_app` + `charter.deactivate::charter_deactivate_app`. Set `category_b_grandfathered_legacy: 284`. Confirm live == 284. (Do NOT add any newly-surfaced symbols — without the parser fix none surface.)
3. **FR-004**: delete the 3 `compat/_adapters/*` files + clean all 4 surfaces; `pure_shim_files: 0`, `category_5_wp_in_flight_adapters: 0`. (This part of your prior work was correct.)
4. **FR-003**: remove the dangling `033-…/event-envelope.md` entry; `legacy_contract_allowlist: 151`. (Correct previously.)
5. **FR-005**: corrections already posted to #2049 (#issuecomment-4804994494) — no re-post needed; add a note that the parser fix moved to #2158.

## Net expected baselines
`category_a_slice_f_deferred: 9`, `category_b_grandfathered_legacy: 284`, `legacy_contract_allowlist: 151`, `pure_shim_files: 0`, `category_5_wp_in_flight_adapters: 0`, `category_4_backcompat_shims: 9` (untouched). `test_no_dead_symbols.py` net change should be SMALL (just the 4 removed entries + the adapter entries), NOT +169 lines.

Gate must be green; the only `src/` change is the 3 file deletions.
