# Tracer — design decisions

Mission: `mission-scaffold-tasks-lanes-defects-01M0NERD` (issue #3673)

Seeded at design. Record each binding decision with its rationale and its evidence.

---

## D1 — Scope is fail-loud / reject-only. NO new CLI surface. (Operator decision, binding)

Asked of the operator by the readiness probe, because CONTRIBUTING.md:377 requires prior
maintainer agreement for new commands and arguments ("Pull requests with large changes
that did not have a prior conversation and agreement will be closed."). Operator chose
the fail-loud option:

1. `specify`'s `meta.json` commit **raises** instead of silently swallowing the exception —
   the existing rollback machinery already handles this cleanly.
2. `execution_mode: code_change` combined with an explicit `owned_files: []` is **rejected
   as an authoring error**, not accepted as intent.
3. Lane computation **raises** instead of silently writing nothing, and
   `authoritative_surface` validation runs **regardless** of whether the manifest map is
   empty.

**Explicitly out of scope**: `spec-kitty migrate rebuild-meta`, a
`finalize-tasks --reinfer-ownership` flag, or any other new command or flag.

**Known, operator-accepted gap**: missions already broken today (with `meta.json` already
missing) get **no repair path** from this mission. Deferred to a later, separately-agreed
mission. The spec must state this gap explicitly rather than quietly growing CLI surface
back in to close it.

---

## D2 — FR-004's "remove the short-circuit" literal instruction, widened to a
non-vacuous fix (WP02 implementer judgment call, 2026-08-23)

**Context**: WP02's task file (T016) and plan.md both describe FR-004 as "remove/narrow
the `if not wp_manifests: return` short-circuit" in `_validate_ownership_manifests`. Traced
through the actual code before implementing (per this profile's directive to read
surrounding code, not assume): `_validate_ownership_via_mission`, `validate_glob_matches`,
and `validate_audit_coverage` all iterate `wp_manifests` (or values derived from it) only —
none reference `wp_frontmatters` for the `authoritative_surface` check itself.
`build_wp_manifests` (out of scope, not diffed) excludes any WP whose `execution_mode`/
`owned_files` are not BOTH truthy — so a WP with, e.g., `execution_mode: code_change` and
genuinely empty `owned_files` (post-FR-002, only reachable via an inference failure, not the
explicit-`[]` case FR-002 now rejects) never enters `wp_manifests` at all, regardless of
whether the short-circuit exists.

**Consequence traced**: literally deleting only the `if not wp_manifests: return` line
would leave the T014 rejection scenario (spec.md Acceptance Scenario 3 — "`wp_manifests`
empty AND a WP frontmatter carries a malformed `authoritative_surface`") **structurally
unreachable** — the malformed WP, being excluded from `wp_manifests`, would never be seen by
any of the three sub-checks, so a red-first test for it could never go green (and per this
mission's own governing precedent — the tasks-phase HALT on a test that could never go red
— that is exactly the trap to avoid, just on the implementation side instead of the test
side).

**Resolution, minimal and scoped**: added `_resolve_wp_manifests_for_validation`, which
re-derives any WP satisfying `build_wp_manifests`'s OWN inclusion predicate
(`execution_mode and owned_files` both truthy) directly from `wp_frontmatters` when it is
missing from the caller's `wp_manifests` view, before running the existing three checks
unchanged. This mirrors the predicate exactly, so it can never pull in a legitimately-exempt
`planning_artifact` WP with the FR-002 escape hatch's `owned_files: []` (verified by a
dedicated acceptance test, T014 step 2). `build_wp_manifests` itself is untouched, per the
WP's explicit "examined but NOT diffed" instruction. This stays inside
`_validate_ownership_manifests`'s own function body — no pipeline reordering, no new CLI
surface, no change to `_compute_and_write_lanes`'s frozen call site.

**Verified red-first**: reverted the production file to pre-mission `HEAD` and re-ran the
full WP02 test surface — every new/changed assertion, including this one, failed for the
expected reason (`DID NOT RAISE` for the rejection test) before the fix, and passed after.
Recorded here rather than silently picking a reading of "remove the short-circuit" that
would have produced an untestable — and therefore, per this mission's own standard,
unacceptable — fix.
