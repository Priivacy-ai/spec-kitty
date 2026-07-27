---
affected_files: []
cycle_number: 3
mission_slug: common-docs-structural-move-01KW3SBK
reproduction_command:
reviewed_at: '2026-06-27T14:56:22Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP05
review_artifact_override_at: "2026-06-27T15:19:35Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP05"
review_artifact_override_reason: "Cycle-3 re-review APPROVED. review-cycle-3.md reopen's 4 required extensions all implemented (commit 4afe5040) and independently verified: (1) colon-outside-bold + (2) dash+bold dialects parse correctly; (3) status alias table — derivable qualifieds strip to MADR root, amended/partially-superseded→Superseded explicit+auditable+fail-closed (Ratified hard-errors), body verbatim (C-002); (4) Date-from-filename fallback (real header wins; no-date+no-filename hard-errors). Independent dry-run over 117 real ADRs: 0 hard-errors, 0 invariance fails (Accepted 93/Superseded 11/Proposed 13; 4 README non-ADRs correctly fail-closed). Raw-byte invariance + whitespace-only mutation test intact. 39 tests green, ruff clean, mypy clean."
---

**Issue**: Reopen — real-data execution (WP06) revealed the converter is incomplete vs the live 117 ADRs.

The cycle-2 approval validated 3 representative dialects + raw-byte invariance correctly, but the REAL 117 ADRs use 5 header dialects, not 3, plus non-MADR status values and Date edge cases. Required extensions (operator-approved):
1. Add parser for `**Status**: X` (colon OUTSIDE bold) — 26 real ADRs.
2. Add parser for `- **Status:** X` (dash+bold hybrid) — 1 ADR.
3. Add a reviewed status-normalization alias table: `Accepted (…)`→Accepted, `Proposed — …`→Proposed; the 2 ambiguous values `Amended — …superseded…` and `Partially superseded` → **Superseded** (operator-adjudicated). Mapping must be explicit/auditable, NOT silent; body prose preserved verbatim (C-002).
4. Add a Date-resolution rule: where the `**Date:**` header is broken/absent, derive from the filename date prefix (e.g. 2026-05-18-…); document the rule.

Keep raw-byte invariance + the whitespace-only mutation test. Extend `tests/docs/test_adr_converter.py` with fixtures for the 2 new dialects + the alias table + Date-derivation.
