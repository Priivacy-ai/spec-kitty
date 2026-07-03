# Issue matrix — refactor-stable-gate-substrate-01KWK3FY

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2072 | CT1: Re-key file:line architectural ratchets to composite_key + drain deferred entries | in-mission | Partial delivery: FR-001..FR-003 convert the last raw-line family (10 entries) + FR-004 folds the inventory-comparison redesign (priti's scope comment); the drain-deferred-entries remainder stays open upstream (FR-009 comment names it). Follow-up: #2072. |
| #2310 | CT8: Encode refactor-stable test-invariant principle into testing doctrine styleguide | in-mission | FR-006 delivers the styleguide + DRG regeneration; closes with this mission. |
| #2311 | CT9: Un-quarantine the 15 stale Typer/click-skew tests | in-mission | FR-007/FR-008 deliver the un-quarantine + honest stay-behind reasons; closes with this mission. |
| #2071 | Epic: Tests as scaffold, not friction | deferred-with-followup | Parent epic — this mission lands three children (CT1 partial, CT8, CT9); remaining CT children (#2073–#2077) stay open. Follow-up: #2071. |
| #2306 | test_untrusted_path_containment inventory off-by-one | verified-already-fixed | Fixed by the degod mission (this branch's base); FR-004 closes the failure CLASS by construction (line-insensitive comparison). |
| #2308 | (PR) Wave 2 tasks.py degod | verified-already-fixed | The base this mission builds on (C-002); rebase discipline recorded. |
| #2034 | CI marker-gate divergence | deferred-with-followup | Reference only: the quarantine set originates from its Wave-0 orphan binding; CT9 shrinks the set 31→16. Follow-up: #2034. |
| #2309 | Daemon-reaper kill-gate contract divergence | deferred-with-followup | Reference only: the 10 reaper quarantines stay (sync domain). Follow-up: #2309. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (must reach a terminal verdict before mission `done`).
