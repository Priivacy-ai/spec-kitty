# Issue matrix — runtime-state-corpus-cutover-01KXZ0AX

One row per issue referenced in `spec.md`. All verdicts are terminal at mission closeout.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2816 | Runtime-state corpus cutover | fixed | WP01–WP13 deliver FR-001–FR-016; `acceptance-matrix.json` records the passing evidence. |
| #2684 | WP runtime-state eviction shipped as dual-write behind an off-by-default flag | fixed | WP01–WP07 wire and run the fail-closed corpus migration, make snapshot authority unconditional, delete the reader predicate and fallbacks, harden the invariant, and reduce inert fields. |
| #2093 | Resolved-binding record/reconstruct and single-authority invariant | deferred-with-followup | FR-008 and FR-012–FR-015 deliver this mission's record/reconstruct slice. The separately scoped frontmatter `lane`/legacy lane-mirror retirement is covered by the compatibility inventory and sunset-policy issue (Follow-up: #1059). |
| #2400 | WP-metadata authority sub-epic | deferred-with-followup | This mission completes the WP-metadata record slice; the parent epic remains open (Follow-up: #2400). |
| #2399 | Full fail-closed profile/model enforcement | deferred-with-followup | This mission records and reconstructs actual bindings; full enforcement remains out of scope (Follow-up: #2399). |
| #2647 | Canonical write target via `canonicalize_feature_dir` | verified-already-fixed | The shipped seam remains in use; cutover tests prove no repository-root event artifact is written. |
| #2815 | Repository-root event-write class | verified-already-fixed | The dogfood corpus guard and cutover tests assert that `status.events.jsonl` is never written at repository root. |
| #2817 | Predecessor dual-write and parity verification | verified-already-fixed | The mission invokes and extends the shipped backfill/verification library instead of re-deriving it. |
| #2819 | Event-log replay | deferred-with-followup | Replay remains downstream of this authority cutover (Follow-up: #2819). |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission`.
