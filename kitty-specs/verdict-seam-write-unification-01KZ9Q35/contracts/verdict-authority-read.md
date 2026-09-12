# Contract — Verdict-Authority Read

**Owner**: `status/reducer.py::event_sourced_review_result` (+ `ReviewResultLookup`).
**Consumers** (all repointed here in IC-03): approval guard `resolve_review_verdict_facts`; merge gate
`find_rejected_review_artifact_conflicts`; dashboard `show_kanban_status`/`_get_wp_review_verdict`;
status-display review/verdict fields; fix-mode `has_prior_rejection` / `implement_try_render_fix_mode_prompt`.

## Signature (stable)

`event_sourced_review_result(feature_dir, wp_id) -> ReviewResultLookup`

`ReviewResultLookup` three-way:
- `slot_present=False` → **absent** (no verdict recorded)
- `slot_present=True, result=None` → **damaged**
- `slot_present=True, result=ReviewResult(verdict=…)` → **present**

## Guarantees

- **G1**: no consumer parses `review-cycle-N.md` frontmatter for a verdict. *(SC-002)*
- **G2**: safety-gate consumers (approval guard, merge gate) treat **absent** as "no approval" and
  **damaged** as fail-closed (never approve, never crash uncaught). *(SC-004)*
- **G3**: on a corrupt log (`StoreError → slot_present=False`), "absent" is read
  **direction-dependently**: the **approval guard** fails **closed** (absent = "no
  approval" ⇒ a WP that cannot be proven approved is refused, so it never reaches
  `approved` and never merges), while the **merge-rejection block gate** is
  **fail-open** on the same value (absent = "no block") — safe only because it is
  backstopped by that fail-closed approval guard, never a standalone gate. The
  end-to-end property (a corrupt log never lets a real rejection merge) holds via
  the approval guard, not the block gate.

## Verified by

`test_2093_authority_invariant.py` (derived ratchet, extended in IC-03) + the verdict-seam census +
a parametrized damaged-record test over every safety-gate consumer.
