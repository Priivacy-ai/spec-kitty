# Orchestrator ruling — TASKS-FRESH-002

**Date**: 2026-08-25
**Finding**: TASKS-FRESH-002 (plan.md's WP4 Assertions text / revert-test summary table
rows are stale relative to the corrected tasks-phase WP files).

**Ruling**: `spec.md` and `plan.md` in this mission directory are COMPLETE, gated PASSED,
and already committed from prior mission phases. The phase-agent brief governing this
tasks-phase review run states explicitly: "Spec and plan phases are COMPLETE and
committed. Do NOT scaffold, do NOT re-author spec.md or plan.md. Anything that looks
wrong is a BLOCKED report, never a second scaffold." Editing plan.md is therefore **out
of scope** for this tasks-phase fix loop, regardless of how well-evidenced a staleness
finding against it is.

TASKS-FRESH-002's own remediation text offered two paths: (a) edit plan.md, or (b) add an
explicit note "so a reviewer diffing plan.md against the WP files understands it is a
deliberate, tracked correction, not an unflagged drift." Given the constraint above, **only
path (b) is acceptable**, and it is what the round-2 fix applied (provenance notes added to
`tasks/WP01-resolved-path-correctness.md`, `tasks/WP02-stop-double-reporting.md`, and
`tasks/WP04-red-first-tests.md`).

**This ruling REPLACES the acceptance bar for TASKS-FRESH-002.** A verifier checking this
finding must confirm the WP files carry a clear, discoverable deviation note explaining the
divergence from plan.md's literal text — NOT that plan.md itself was changed, and NOT that
any string match appears inside plan.md. A verifier applying the original "is plan.md
reconciled" bar will re-derive the same unresolved verdict on a question this ruling has
already answered; do not do that.

The round-3 fix (immediately following this ruling) makes the WP04 provenance note more
prominent/unambiguous so it is trivially discoverable by a reviewer diffing plan.md against
the WP file, without touching plan.md itself.
