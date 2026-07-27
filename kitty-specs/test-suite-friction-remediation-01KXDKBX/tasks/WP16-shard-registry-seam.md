---
work_package_id: WP16
title: Explicit shard-registry seam
dependencies:
- WP15
- WP11
requirement_refs:
- FR-011
- FR-016
- NFR-002
tracker_refs:
- '2621'
planning_base_branch: feat/test-suite-friction-remediation
merge_target_branch: feat/test-suite-friction-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-friction-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-friction-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T075
- T076
- T077
- T078
- T079
- T080
agent: "claude:sonnet:python-pedro:implementer"
history: []
agent_profile: python-pedro
authoritative_surface: tests/_shard_registry.py
create_intent:
- tests/_shard_registry.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/_shard_registry.py
- tests/_arch_shard_map.py
- tests/_next_shard_map.py
- tests/architectural/test_arch_shard_marker_completeness.py
- tests/conftest.py
role: implementer
tags: []
shell_pid: "3237943"
shell_pid_created_at: "1783958502.54"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-011 + Scenario 3,
[data-model.md](../data-model.md) E-07, [plan.md](../plan.md) §IC-10 + the "New-guard-file DoD" directive,
and the contract [contracts/shard-registry-seam.md](../contracts/shard-registry-seam.md). This WP is the
**sole owner** of `tests/conftest.py` (it co-tenants the quarantine-deselection block + the shard-marker
hook). New-guard-file DoD applies.

## Objective

Replace the import-side-effect assembly of `SHARD_GROUPS` with an idempotent, order-independent
`register(group)` / `all_groups()` seam plus an expected-group manifest, so the completeness guard fails
**diagnosably** ("group `<name>` not registered", never a bare `KeyError`) and an unmarked `tests/next`
universe fails loud.

## Context

- Today `tests/_next_shard_map.py` mutates `SHARD_GROUPS` at import time (a `# noqa: F401` import-for-side-
  effect), so a dropped import silently leaves `tests/next` unmarked and a missing group surfaces as a bare
  `KeyError`.
- Row owners (`arch`, `next`) must stay **separate** modules, each registering through the seam — do NOT
  collapse them into one module (contract anti-goals).

## Subtask guidance

- **T075 — the seam.** Create `tests/_shard_registry.py` exposing `register(group: ShardGroup)` (idempotent;
  rejects a duplicate key), `all_groups()`, and an **expected-group manifest** (the set of group names that
  MUST be registered).
- **T076 — refactor the row owners.** Change `tests/_arch_shard_map.py` and `tests/_next_shard_map.py` to
  call `register(...)` explicitly rather than mutating a shared dict at import; drop the `# noqa: F401`
  import-for-side-effect assembly mechanism. **WP16 now branches from WP11's tip (serial dependency), so
  WP11's `test_golden_count_ban.py` registration is already present in `tests/_arch_shard_map.py` under the
  old `SHARD_GROUPS`-dict idiom.** The `SHARD_GROUPS` dict→`register()` rewrite MUST carry that registration
  forward into the new `register(...)` seam — do not drop it. WP16 is the **sole owner and reconciler** of
  `tests/_arch_shard_map.py`; it absorbs WP11's upstream registration and re-expresses it through the seam.
- **T077 — diagnosable completeness guard.** Update
  `tests/architectural/test_arch_shard_marker_completeness.py` so a group named in the manifest but not
  registered fails with a diagnosable "group `<name>` not registered" message — never a bare `KeyError`.
- **T078 — conftest hook.** Update the shard-marker hook in `tests/conftest.py` to consume `all_groups()`;
  an unmarked `tests/next` test universe must fail loud (no silently-unmarked universe). Preserve the
  co-tenant quarantine-deselection block.
- **T079 — red-first regressions.** (a) Removing the `_next_shard_map` registration makes the guard emit the
  **diagnosable message** — assert on the message text, not just "raises". (b) An unmarked `tests/next`
  universe **fails**, not passes.
- **T080 — new-guard-file DoD + gates.** Register any new arch file in `tests/_arch_shard_map.py` (in-map —
  this WP owns it) and re-freeze both gate-coverage baselines (gc3b `--update-baseline`, gc2b
  `--freeze-baselines`); the residual must negate every `next_shard`/`arch_shard` marker. (If WP15 already
  scoped gc2b to orphans, the gc2b refreeze may be a no-op — keep it as fallback.) `ruff`/`mypy` clean;
  append tracer rows.

## Branch Strategy

Lane B, second in the serial chain. Branches from WP15's tip **and WP11's tip** (serial dependency — the
lane graph is now WP07→WP11→WP16→WP17). **Note:** because WP16 is serial downstream of WP11, WP11's
`test_golden_count_ban.py` registration is already present in `tests/_arch_shard_map.py` when WP16 starts —
WP16 carries it forward into the `register()` seam (T076), it is NOT a cross-lane append to reconcile. WP17
(downstream serial) appends its two new-guard registrations after WP16's seam exists. This WP owns the seam
and the file. **The gc3b `_gate_coverage_baseline.json` is a "last-writer regenerates" artifact, not a
textual merge — each WP that adds an arch guard regenerates it via `--update-baseline`; the terminus (WP17)
holds the authoritative final refreeze.**

## Definition of Done (non-fakeable — NFR-002)

- [ ] `tests/_shard_registry.py` exposes idempotent `register()` / `all_groups()` + an expected-group
      manifest; duplicate-key registration is rejected.
- [ ] `_arch_shard_map.py` + `_next_shard_map.py` register via the seam; the `# noqa: F401` side-effect
      assembly is gone; row owners stay separate.
- [ ] The completeness guard fails with a diagnosable "group `<name>` not registered" (asserted on the
      message), never a bare `KeyError`.
- [ ] A regression proves an unmarked `tests/next` universe fails loud.
- [ ] New-guard-file DoD satisfied: shard-registered + both baselines re-frozen; residual negates every
      `next_shard`/`arch_shard` marker.
- [ ] `ruff` + `mypy` clean; complexity ≤ 15.
- [ ] **Tracer (FR-016):** append a catalog row for the shard-marker completeness ratchet + friction log.

## Risks

- **Registration-order regressions** during the seam swap — keep `register()` idempotent + manifest-
  asserted.
- **Collapsing arch/next ownership** — keep the row-owner modules separate (contract anti-goal).

## Reviewer guidance

- Confirm the diagnosable message is asserted (not just "raises") and the unmarked-universe regression fails.
- Confirm the `# noqa: F401` side-effect import is gone and row owners remain separate.

## Activity Log

- 2026-07-13T16:02:31Z – claude:sonnet:python-pedro:implementer – shell_pid=3237943 – Assigned agent via action command
