---
work_package_id: WP09
title: '#2074 test_mid8_direct_routing fixture re-pin to production-shaped meta.json (Lane B)'
dependencies:
- WP00
requirement_refs:
- FR-008
tracker_refs:
- '#2074'
planning_base_branch: feat/gate-read-surface-completion
merge_target_branch: feat/gate-read-surface-completion
branch_strategy: Planning artifacts for this mission were generated on feat/gate-read-surface-completion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/gate-read-surface-completion unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
phase: Phase 2 - Lock-the-fix (Lane B, parallel)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "4000092"
history:
- at: '2026-06-24T08:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/test_mid8_direct_routing.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/specify_cli/test_mid8_direct_routing.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP09 – #2074 test_mid8_direct_routing fixture re-pin (Lane B)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on
`authoritative_surface: tests/specify_cli/test_mid8_direct_routing.py`.

---

## Objective

Fix the stale `tests/specify_cli/test_mid8_direct_routing.py::test_mission_type_read_mid8_truncates_then_declines`.
Its fixture writes `full.json` / `explicit.json` / `bare.json`, but `_read_mission_mid8`
(`mission_type.py:632`) reads `<dir>/meta.json` via `load_meta` and **ignores the filename**
→ returns `""`. The test is **RED only because the fixture drifted** — the `resolve_mid8`
product code is correct. Re-pin the fixture to write a **production-shaped `meta.json`** (via
the canonical mission factory, per the #2074 CT3 direction) so the test actually exercises the
`resolve_mid8` routing parity it claims to guard.

This is the mid8-read sibling of WP07/WP08's "lock the fix" theme — a test remediation, not a
product change.

## Context & Constraints

Ground truth — read before editing:
- [spec.md](../spec.md) FR-008; the failing-test remediation framework (the TEST drifted →
  remediate the assertion/fixture, do NOT change the correct product code).
- [plan.md](../plan.md) IC-10.
- [data-model.md](../data-model.md) Lane B table (#2074 row).

Live-verified:
- `_read_mission_mid8` at `src/specify_cli/cli/commands/mission_type.py:632`; reads
  `meta = load_meta(meta_path.parent, ...)` at `:633` — it reads `<dir>/meta.json`, NOT the
  arbitrary filenames the fixture writes.
- The stale test at `tests/specify_cli/test_mid8_direct_routing.py:108`
  (`test_mission_type_read_mid8_truncates_then_declines`); fixture writes `full.json`
  (`:111`), `explicit.json` (`:115`), `bare.json` (`:119`) — none named `meta.json`, so
  `_read_mission_mid8` reads nothing and returns `""`.

**Diagnosis (failing-test remediation framework)**: the fixture is stale (writes wrong
filenames). The product (`resolve_mid8` / `_read_mission_mid8`) is correct. Remediation = fix
the FIXTURE to write `meta.json` in each scenario dir, so the test exercises the real routing
(full ULID → truncate to mid8; explicit mid8 → accept; bare slug → decline).

**Negative scope**: do NOT change `mission_type.py` / `resolve_mid8` (the product is correct).
Do NOT delete the test — re-pin it (it guards real routing parity).

## Branch Strategy

- **Strategy**: `parallel-lane` (Lane B — independent of Lane A)
- **Planning base branch**: `feat/gate-read-surface-completion`
- **Merge target branch**: `feat/gate-read-surface-completion`

> WP09 OWNS `tests/specify_cli/test_mid8_direct_routing.py` exclusively. `execution_mode` is
> `code_change` (test re-pin), per the mission tasking note.

## Subtasks & Detailed Guidance

### Subtask T029 – Re-pin the fixture to production-shaped meta.json

- **Purpose**: Make the test exercise the real `_read_mission_mid8` → `load_meta` path.
- **Files**: `tests/specify_cli/test_mid8_direct_routing.py`
  (`test_mission_type_read_mid8_truncates_then_declines`, `:108-121`).
- **Steps**:
  1. For each of the three scenarios (full ULID / explicit mid8 / bare slug), write a
     **`meta.json`** into a per-scenario directory (so `_read_mission_mid8` reads it), NOT
     `full.json`/`explicit.json`/`bare.json`. Use the canonical mission factory (per #2074 CT3)
     to produce a production-shaped meta.json — real 26-char ULID `mission_id`, full meta shape
     (`mission_slug`, `target_branch`, `topology`, etc.), not a hand-built 2-key dict.
  2. Scenario A (full): `mission_id` = a real 26-char ULID → assert `_read_mission_mid8`
     returns the truncated 8-char `mid8` (e.g. ULID `01KVW9B0XFXPKTBE77QT3KRSW8` → `01kvw9b0`).
  3. Scenario B (explicit mid8): a meta.json whose identity yields the explicit mid8 → assert
     it is accepted/returned as-is.
  4. Scenario C (bare slug, no resolvable identity): assert `_read_mission_mid8` **declines**
     (returns `""` / the documented decline) — the truncate-then-decline contract.
- **Notes**: Locate the canonical mission/meta factory used elsewhere in the suite (the
  write-side mission used a canonical factory for meta.json). REUSE it — do not hand-roll.

### Subtask T030 – Prove the re-pin exercises the real routing (green for the right reason)

- **Purpose**: Confirm the test is no longer green/red for the WRONG reason (filename drift),
  but exercises the actual `load_meta` → `resolve_mid8` parity.
- **Files**: `tests/specify_cli/test_mid8_direct_routing.py`.
- **Steps**:
  1. Run the re-pinned test — it must PASS by genuinely reading `meta.json` (assert the mid8
     values, not just non-empty).
  2. Sanity proof (record in log): with the OLD fixture (wrong filenames), `_read_mission_mid8`
     returns `""` for all three (test was RED for fixture drift, not product breakage). With the
     re-pinned `meta.json` fixture, the routing parity is exercised. This confirms the diagnosis
     (test drifted, product correct).
  3. Confirm NO product code (`mission_type.py`) was touched.

## Test Strategy

- `pytest tests/specify_cli/test_mid8_direct_routing.py::test_mission_type_read_mid8_truncates_then_declines -q`.
- `ruff check tests/specify_cli/test_mid8_direct_routing.py` + `mypy` — zero issues, no suppressions.

## Definition of Done

- [ ] Fixture re-pinned to write production-shaped `meta.json` (canonical factory, real ULID)
  in each scenario dir.
- [ ] Test exercises the real `_read_mission_mid8` → `load_meta` → `resolve_mid8` routing
  (full → mid8 truncate; explicit → accept; bare → decline).
- [ ] Test GREEN for the right reason (asserts mid8 values, reads `meta.json`).
- [ ] NO product code changed (`mission_type.py` / `resolve_mid8` untouched).
- [ ] #2074 instance fixed within the mission matrix (broader factory work stays with #2074).
- [ ] ruff + mypy clean; no suppressions.

## Risks & Mitigations

- **Hand-built meta dict masking real behavior**: Mitigation: canonical factory, full meta shape.
- **Re-pinning to green without exercising routing**: Mitigation: assert the actual mid8 values
  per scenario (T030).
- **Accidentally "fixing" the product**: Mitigation: the product is correct — only the fixture
  changes (failing-test remediation framework).

## Review Guidance

- Confirm only the FIXTURE changed (filenames → `meta.json`); `mission_type.py` is untouched.
- Confirm the fixture uses the canonical factory with a real 26-char ULID, not a 2-key dict.
- Confirm the assertions check the real mid8 values per scenario (not just non-empty / truthy).

## Activity Log

- 2026-06-24T08:00:00Z – system – Prompt created.
- 2026-06-24T15:13:49Z – claude:opus:python-pedro:implementer – shell_pid=3974435 – Assigned agent via action command
- 2026-06-24T15:19:45Z – user – shell_pid=3974435 – Claimed for implementation
- 2026-06-24T15:19:49Z – user – shell_pid=3974435 – Implementation in progress
- 2026-06-24T15:20:46Z – user – shell_pid=3974435 – Moved to claimed
- 2026-06-24T15:20:48Z – user – shell_pid=3974435 – Moved to in_progress
- 2026-06-24T15:21:08Z – claude:opus:python-pedro:implementer – shell_pid=3974435 – Re-pinned test_mission_type_read_mid8_truncates_then_declines: fixture now writes production-shaped meta.json per scenario dir (full/explicit/bare). All 19 tests GREEN, ruff+mypy clean, no product code changed (#2074 CT3).
- 2026-06-24T15:22:50Z – claude:opus:python-pedro:implementer – shell_pid=3974435 – Lane-j code committed a4bd6c643; status move from main (flat-mission divergence)
- 2026-06-24T15:22:51Z – claude:opus:reviewer-renata:reviewer – shell_pid=4000092 – Started review via action command
- 2026-06-24T15:25:34Z – user – shell_pid=4000092 – Review passed: fixture re-pinned to production-shaped meta.json per scenario dir (real load_meta->resolve_mid8 path). Scenario A full ULID->mid8 truncate, B explicit mid8 verbatim, C bare slug declines ''. Product (mission_type.py/resolve_mid8) UNTOUCHED. Old-fixture drift confirmed empirically (full.json->''). 19/19 pass, ruff+mypy clean.
