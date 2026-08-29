# Issue matrix — charter-preflight-remediation-01KYG9WK

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2831 | Charter preflight emits a remediation that cannot clear the check it is attached to (P0); charter presence resolved inconsistently across surfaces | in-mission | WP01 `2446a0bcd` lands the effectiveness mechanism RED (4 failed / 8 passed, failing exactly the four `charter sync` states) as NFR-002 red-first evidence; WP02 corrects the remediation and turns it green; WP04 converges the presence resolvers. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

**Note on `in-mission`**: this verdict passes per-WP `approved` so a dependency chain is not blocked
on its own downstream WPs, but it is **rejected on `done`**. It must be resolved to `fixed` before
the mission merges — see WP02 (the P0 correction) and WP06 (the regression envelope).
