# Issue matrix — mission-lifecycle-dispatch-drg-closeout-01KV0S99

One row per issue this mission addresses. `in-mission` = being driven to closure by this mission
(non-terminal; must reach `fixed` / `verified-already-fixed` / `deferred-with-followup` before mission `done`).

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1802 | Epic: Pre- and post-mission lifecycle support | fixed | FR-001/FR-002 delivered (WP02): `spec-kitty mission reopen` + `mission follow-up` over MissionReopened/FollowUpRecorded events + reopen-aware classification (WP01); pre-mission half shipped via #687/#1220; no residual (FR-003); SC-3 |
| #1804 | Epic: Ops execution layer (ask/advise/do) | fixed | FR-007 — blocking child #1810 delivered (WP03/WP04); ops layer + Op lifecycle substantially complete; SC-2 |
| #1810 | refactor: collapse do/ask/advise to dispatch | fixed | FR-004/FR-005/FR-006 — canonical `spec-kitty dispatch` over single mechanism + byte-identical retained aliases (WP03, NFR-001 parity tests) + canonical-skill/manifest propagation (WP04); SC-1 |
| #1863 | DRG extractor orphans: styleguide/toolguide references | fixed | FR-008/FR-009 — java-implementer (+4 same-class) stale refs repaired, 12 orphans wired, orphans 26→14, deterministic regen + count regression (WP05); 14 residual documented + follow-up filed as #1923 (C-003); SC-4 |
| #687 | Pre-mission brief ingestion (lineage of #1802) | verified-already-fixed | Pre-mission ingestion half of #1802 — already shipped + closed by prior work; lineage context for FR-001/FR-002 |
| #1220 | Pre-mission ticket-context ingestion (lineage of #1802) | verified-already-fixed | Pre-mission half of #1802 — already shipped + closed; lineage context for FR-001/FR-002 |
| #133 | name-vs-authority remediation (originating post-merge audit) | verified-already-fixed | Mission #133 merged as PR #1908; its post-merge audit surfaced these residuals — already landed, referenced for provenance only |
| #1010 | API-surface epic | deferred-with-followup | Out of scope per C-005; tracked in its own epic #1010 (not folded into this mission) |
| #1907 | dev-tooling: subagent worktrees on stale ancestors | deferred-with-followup | Out of scope per C-005; tracked in #1907 (separate dev-tooling ticket) |
| #1913 | no-op-stability remediation (shared kernel util + ratchet) | deferred-with-followup | Out of scope per C-005; tracked in its own PR/ticket #1913 |
| #1914 | umbrella: governed/gate ops must be no-op-stable | deferred-with-followup | Out of scope per C-005; umbrella tracked in #1914 |
| #1924 | merge gate ignores review_artifact_override | fixed | Closeout remediation (operator-chosen in-mission fix): `src/specify_cli/review/artifacts.py` honors a complete override (actor+reason) on rejected terminal artifacts, consistent with the approval gate; pinning tests in `tests/review/test_artifacts.py`. Unblocked this mission's merge. |
| #1916 | ensure_identity relocation | deferred-with-followup | Out of scope per C-005; tracked in #1916 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission`.

Notes:
- Rows #687/#1220/#133 are lineage/provenance context (already delivered) — `verified-already-fixed`.
- Rows #1010/#1907/#1913/#1914/#1916 are the **C-005 out-of-scope** list — explicitly NOT addressed here, deferred to their own tickets (the issue number is the follow-up handle).
- The four `in-mission` rows (#1802/#1804/#1810/#1863) resolve to terminal verdicts at the mission accept/merge gate.
