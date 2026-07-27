---
affected_files: []
cycle_number: 4
mission_slug: tasks-py-degod-01KWF08S
reproduction_command:
reviewed_at: '2026-07-01T19:45:23Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP02
---

# WP02 Review — Cycle 3 — CHANGES REQUESTED

Reviewer: reviewer-renata. Verdict: **REJECT** — one blocking quality-gate defect
(NFR-003 / mypy-not-clean on the changed file). The cycle-2 FR-010 fix is correct
and is confirmed approve-quality — **do not touch it.** The block is a new
`# type: ignore` in this WP's own test file that both violates NFR-003 and makes
`mypy` on the changed file **fail**.

---

## ✅ CONFIRMED FIXED (do not re-touch) — FR-010 pin table (cycle-1 blocker)

Verified against live `src/specify_cli/cli/commands/agent/tasks.py`:

- **`move_task:1138`** — `_mt_feature_dir = resolve_feature_dir_for_mission(...)` is
  assigned **once** and **never reassigned**; the same value feeds
  `check_pre30_layout` (:1140), the authoritative event-log read
  `_read_transactional_wp_lane(feature_dir=_mt_feature_dir)` (:1149, STATUS
  partition), and `_persist_review_artifact_override_in_coord(coord_feature_dir=_mt_feature_dir)`
  (:1216). Correctly pinned to **`STATUS_STATE`** (coord-husk-preserving). ✅
- **`finalize_tasks:2373`** — guard var reassigned at :2453; **`list_dependents:3568`**
  — guard var reassigned at :3578. Both guard-only → **`WORK_PACKAGE_TASK`**. ✅
- **Hazard assertion** `test_fr010_move_task_status_read_must_stay_on_coord_husk`
  is falsifiable (not a tautology): `primary_read != coord_husk` and
  `status_read(STATUS_STATE) == coord_husk` genuinely encode the coord-topology
  non-equivalence and depend on the coord fixture having distinct dirs. The
  rationale text explicitly instructs WP06 **MUST NOT wholesale-repoint
  tasks.py:1138**. ✅

This part is approve-quality. Leave it exactly as-is.

---

## BLOCKING — Issue 1: new `# type: ignore[misc]` makes `mypy` FAIL (NFR-003)

`tests/specify_cli/cli/commands/agent/test_tasks_ports.py:258`
```python
ports.fs = FakeFsReader()  # type: ignore[misc]
```
This is a **new** suppression in WP02's own new file, so it falls under NFR-003
("0 new `# type: ignore`; prefer real fixes"). Worse than avoidable — it is
**wrong**: the project's mypy config is `strict = true`, which enables
`warn_unused_ignores`. Under that config mypy does **not** flag the assignment, so
the ignore is unused and mypy errors:

```
$ mypy tests/specify_cli/cli/commands/agent/test_tasks_ports.py
test_tasks_ports.py:258: error: Unused "type: ignore" comment  [unused-ignore]
```

The activity-log "ruff+mypy clean" claim is false for this file. (Cycle-1 review's
"zero new suppressions" was also an oversight — this predates cycle 2 but is still
WP02's work and is now the gating defect.)

### Required remediation (minimal, preserves the test)
**Delete the `# type: ignore[misc]` comment.** That is the whole fix. Verified:
- `mypy tests/.../test_tasks_ports.py` → `Success: no issues found`.
- `test_tasks_ports_is_frozen` still passes — `ports.fs = FakeFsReader()` still
  raises `FrozenInstanceError` at runtime.

Note for the record: the "switch to `dataclasses.replace`" idea does **not** apply
here — `dataclasses.replace(...)` and `object.__setattr__(...)` both **succeed
without raising**, which would defeat this test (it exists to prove immutability).
If a future toolchain config ever did flag the direct assignment, the correct
no-ignore form is `setattr(ports, "fs", FakeFsReader())` (routes through the frozen
`__setattr__` → raises; mypy does not flag dynamic `setattr`). But under the
current strict config, plain deletion is sufficient and correct.

---

## SECONDARY (fix in the same pass) — Issue 2: `# type: ignore[attr-defined]` lacks a real fix / rationale

`tests/specify_cli/cli/commands/agent/test_tasks_ports.py:286`
```python
for name, command in group.commands.items():  # type: ignore[attr-defined]
```
`get_command(app)` is typed to return `click.Command` (base), which has no
`.commands`; the ignore is genuinely needed today (mypy is not wrong). But NFR-003
still wants a real fix or an inline rationale. Prefer the real fix — narrow the
type, which also adds a runtime guard and drops the ignore:
```python
from click import Group
group = get_command(app)
assert isinstance(group, Group)  # multi-command Typer app => click.Group
for name, command in group.commands.items():
```
If you judge the ignore must stay, add a one-line inline rationale per NFR-003.

---

## Verification after remediation
- `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_ports.py -q` → 19 passed
- `mypy tests/specify_cli/cli/commands/agent/test_tasks_ports.py` → Success, no issues
- `ruff check` → clean
- No remaining `# type: ignore` / `# noqa` in either WP02-owned file.

Everything else (two-capability port, adapters, injection proof, stratification
invariants, C-001/C-002/C-005, the FR-010 fix above) remains approve-quality — the
only work this cycle is removing the two suppressions.
