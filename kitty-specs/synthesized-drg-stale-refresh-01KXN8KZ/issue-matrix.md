# Issue matrix — synthesized-drg-stale-refresh-01KXN8KZ

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2681 | charter `synthesized_drg` stuck `stale` — no-op-stable manifest write never refreshes freshness signal (THE mission target) | fixed | Fixed across WP01–WP04; content-identity `bundle_content_hash` replaces the mtime comparison. Reader swap (WP03) is the terminal fix (mission closed WP04). Evidence: WP01 `759d24fa6` (manifest field + finalizer + shim + write-side helper), WP02 `d6bc124e7` (writer wiring across promote/resynthesize/apply_post_condition + schema bump), WP03 `fc679f573` (reader swap to content-identity comparison, terminal fix). |
| #1912 | no-op-stable manifest write (the regression *source*) | verified-already-fixed | Not a defect being fixed here — its no-op-stable behavior is PRESERVED and re-verified (C-001 / NFR-001 keep `test_no_op_stable_writes` green); not modified. |
| #1913 | PR #1913 for #1912 (regression source) | verified-already-fixed | Same as #1912 — behavior preserved & re-verified, not modified. |
| #1914 | umbrella: no-op-stable governed operations | deferred-with-followup | Follow-up: #1914 (existing umbrella — no NEW issue created). OUT OF SCOPE (different, broader defect class); this mission resolves one concrete instance; the umbrella remains open. |
| #2157 | implement-gate bounce (`synthesized_drg: MISSING`) | deferred-with-followup | Follow-up: #2157 (existing — no NEW issue created). OUT OF SCOPE — different terminal state (MISSING vs stale) + different root cause (preflight cascade ordering). |
| #2373 | `build_charter_context` no-op-stable render side-effect | deferred-with-followup | Follow-up: #2373 (existing — no NEW issue created). OUT OF SCOPE — different code surface (context render vs freshness computer), zero overlap (code-verified). |
| #2009 | BOM/CRLF manifest-hash fix (shipped 3.2.1) | verified-already-fixed | Explicitly NOT related — different mechanism (BOM/CRLF), already shipped; deliberately not conflated. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

**Vocabulary note (per post-tasks squad):** the four canonical verdicts have no exact value for "preserved regression-source" (#1912/#1913 → recorded as `verified-already-fixed`) or "out-of-scope different defect, existing issue, no new follow-up" (#1914/#2157/#2373 → recorded as `deferred-with-followup`, where the "followup" is the pre-existing open issue, NOT a newly-created one). Annotations above carry the precise meaning. #2681 flipped `in-mission` → `fixed` at WP04 mission close (WP03 landed the terminal reader swap).

**Mission close-out (WP04):** all 7 rows above now carry a terminal verdict (`fixed` / `verified-already-fixed` / `deferred-with-followup`) — none remain `in-mission` or `unknown`. #2009 (explicitly-not-related) and #1912/#1913 (preserved regression-source, C-001) have no exact match in the four-value vocabulary; they are recorded as `verified-already-fixed` with the precise meaning annotated in each row rather than shoehorned into a new value. **DIR-003 caveat:** the MOES-Media fork cannot assign the Human-in-Charge on upstream Priivacy-ai issue #2681 (cross-fork contributor model has no assignment rights on the upstream repo) — best-effort attempted per the contributor model; recorded here as a known limitation, not a mission blocker.
