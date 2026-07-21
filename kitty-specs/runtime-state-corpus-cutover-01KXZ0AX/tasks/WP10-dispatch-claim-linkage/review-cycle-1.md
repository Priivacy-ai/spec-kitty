---
affected_files: []
cycle_number: 1
mission_slug: runtime-state-corpus-cutover-01KXZ0AX
reproduction_command: null
reviewed_at: '2026-07-20T14:55:00Z'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP10
---

# WP10 Review — APPROVED (IC-08 dispatch→claim linkage + emit + re-seed)

> Closeout correction (2026-07-21): the C-011 re-seed approval below was superseded by the accepted
> field-authority ADR. Authored recommendations may not be recorded as resolved actuals; the generated
> seed rows were removed by exact deterministic ID.

Code 1beb316b9 (lane-i) + re-seed data 21e18f9c2 (feat). Verified the load-bearing constraints.

- **C-007 / INV-6 enforced BY CONSTRUCTION (the crux):** `_resolve_dispatch_binding(model, profile, invocation_id, repo_root)` has **no frontmatter parameter** — a resolved binding structurally cannot be a frontmatter copy. `--invocation-id` reads the Op record (`profile_id`) authoritatively; returns `None` (no frontmatter fallback) when no dispatch context. New typed `ResolvedBinding` carrier threads command→seam→emit. Role is seam-fixed (implementer/reviewer = the actual role that ran).
- **Emit shape correct:** `emit_resolved_binding` records an `InnerStateChanged` **annotation** at BOTH claim seams (latest-wins regardless of lane); actor built via `_build_resolved_actor` helper. **NOSONAR on `emit_status_transition` NOT inflated** (count unchanged; param surface intact) — the transition actor stays `str` with a `TODO(WP12)` breadcrumb (WP12 widens it). A `None` binding is a genuine no-op (slots stay absent, never frontmatter-filled).
- **SC-011 explicit-absent — non-vacuous:** `RESOLVED_MODEL_ABSENT` sentinel survives JSONL round-trip, is distinct from a real model and an untouched slot, and overwrites a stale prior model under latest-wins (M1→sentinel). Removing the sentinel makes the test red.
- **C-011 new namespace proven:** `_seed_id(…,"resolved_binding") != …"claim"`; with the committed claim seeds on disk, the extended backfill returns `action="wrote"` (not "skip").
- **Re-seed (T041):** 185 missions / 1154 resolved-binding events on feat (21e18f9c2); **self-mission excluded** (0 files; our `status_phase: None`); `verify_backfill` unperturbed (resolved slots outside its eviction-parity set).
- **11 linkage tests + 300+ regression tests pass**; ruff+mypy clean, zero new suppressions; only the pre-existing `SYNC_DISABLE_ENV_VARS` base-red remains (not WP10). Out-of-map edits (emit.py/workflow_executor.py/tasks_move_task.py/backfill/kitty-specs) documented + sequential.
- Deviation (acceptable): `provider`/`agent_profile_version` stay `None` on the live path (no source yet) — vocabulary-supported, threadable later; the Op record has no model so `--model` carries it.

**Verdict: APPROVED.** The resolved-binding RECORD half is in place with C-007 structurally guaranteed; the re-seed lands in WP11's merge unit.
