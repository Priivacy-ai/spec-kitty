---
work_package_id: WP13
title: Subtask completion event-sourced; markdown checkboxes removed
dependencies:
- WP11
requirement_refs:
- FR-016
planning_base_branch: feat/runtime-state-corpus-cutover
merge_target_branch: feat/runtime-state-corpus-cutover
branch_strategy: Planning artifacts for this mission were generated on feat/runtime-state-corpus-cutover. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/runtime-state-corpus-cutover unless the human explicitly redirects the landing branch.
subtasks:
- T051
- T052
- T053
- T054
agent: "claude"
shell_pid: "802169"
shell_pid_created_at: "1784583308.14"
history:
- timestamp: '2026-07-20T08:39:02Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/subtask_rows.py
create_intent:
- tests/specify_cli/core/test_subtask_rows_snapshot.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/core/subtask_rows.py
- tests/specify_cli/core/test_subtask_rows_snapshot.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP13 – Subtask completion event-sourced; markdown checkboxes removed

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the **`python-pedro`** agent profile (role: `implementer`) **before doing any work**, and behave according to its guidance for the whole WP. This WP has a **behaviour-sensitive** core (the lane-transition guard blocks lane transitions on incomplete subtasks) plus a **large but shallow** doctrine/template surface. Hold an implementer's rigour: prove every reroute with a real block/unblock regression (ATDD-first, C-011), and treat the "edit SOURCE templates, never agent copies" rule as non-negotiable.

## Objective

Make the reduced event-log snapshot's **`subtasks` slot** the **sole** authority for subtask completion, and **remove** the `- [ ] T###` markdown checkboxes that are the incoherent proxy the WP view must stop reading. Concretely:

1. **Reroute the lane-transition guard** (whose blocking source is `core/subtask_rows.py`) and any remaining **dashboard** subtask-count reader onto the snapshot `subtasks` slot (via WP11's `reconstruct_wp_view` reader) — **preserving block/unblock semantics** (behaviour-sensitive).
2. **Remove the `- [ ] T###` checkboxes** from the tasks templates and this mission's own `tasks.md` — **only after** the backfill has already seeded historical completion from them (C-010).
3. **Update the SOURCE doctrine prompt templates** under `src/doctrine/missions/mission-steps/` (+ the tasks templates) so agents are directed to `spec-kitty agent tasks mark-status` instead of ticking checkboxes.

This is IC-10 (plan lines 441–465). It is the last step of the mission's headline reduction: after the cutover (WP04) made the snapshot authoritative for the #2684-evicted fields, subtask completion is the final field still read from a markdown proxy. FR-016 / SC-010.

## Context & grounding

- **Plan IC-10 (lines 441–465)** — the authority. Affected surfaces: the dashboard checkbox count (`dashboard/scanner.py:954-965`), the lane-transition guard (`core/subtask_rows.py` — `iter_wp_section_subtask_rows` / `count_wp_section_subtask_rows` are its blocking source), checkbox removal from `tasks.md`/WP templates, and the doctrine prompt templates (breadth risk — propagates to 13 agent dirs via `spec-kitty upgrade`; **never** hand-edit agent copies).
- **Spec FR-016 (line 245)** — subtask completion **solely** event-sourced (via `mark-status` → `InnerStateChanged.subtasks` → snapshot); `- [ ] T###` checkboxes **removed** from `tasks.md`/WP templates; reroute the lane-transition guard + dashboard off checkbox counting onto the snapshot `subtasks` slot; update the doctrine prompt templates to direct `mark-status`; remove checkboxes **only after** the backfill seeded from them (C-010).
- **Spec SC-010 (lines 336–339)** — **acceptance shape:** No `- [ ] T###` markdown checkbox remains in `tasks.md`/WP templates; subtask completion is read from the snapshot everywhere (dashboard + lane-transition guard); the guard **blocks/unblocks correctly off the snapshot**; agent prompt templates direct `mark-status`. Historical completion was seeded before any checkbox removal (C-010).
- **Spec C-010 (line 271)** — checkbox removal MUST be ordered **after** the backfill has seeded historical subtask completion from them (they are the legacy source `read_legacy_runtime` / `_subtasks_from_tasks_md` reads via `iter_wp_section_subtask_rows`). Removing them earlier strands historical completion (same class as C-001).
- **Spec NFR-003 (line 253)** — WP-file byte-stability: after cutover a runtime-state transition writes 0 bytes to `tasks/WP##.md`. Removing the checkboxes retires the last markdown proxy a runtime write could touch; a subtask completion mark must never write the WP file.
- **research D-13 (lines 214–227)** — the incoherence: today the dashboard counts live `tasks.md` checkboxes and the guard blocks on checkbox rows, while the snapshot slot is written only by `mark-status` (`tasks_mark_status.py:371`). So a raw checkbox edit without `mark-status` shows frozen progress — exactly the incoherence the operator wants removed. Ordering (C-010): backfill-then-remove. Breadth: the guard (behaviour-sensitive) + the doctrine templates across the mission-step families.
- **data-model — deleted/inert table (lines 56–58):** `- [ ] T###` checkboxes → **removed** (subtask completion snapshot-only via `mark-status`; removed only after backfill seeds from them, C-010); lane-transition guard checkbox parsing (`core/subtask_rows.py`) → **rerouted** to the snapshot `subtasks` slot; doctrine prompt templates instructing checkbox ticks → **updated** to direct `mark-status`.
- **⚠️ CLAUDE.md — Template Source Location (BINDING):** edit **SOURCE** templates under `src/doctrine/missions/mission-steps/` (+ `src/doctrine/missions/*/templates/`), **NEVER** the generated agent copies in `.claude/`, `.amazonq/`, `.augment/`, `.github/`, `.gemini/`, … They are regenerated from source by `spec-kitty upgrade`. A same-content edit in an agent dir is a **defect** the reviewer will reject.

### Where the guard and the checkbox readers live (verified against the tree)

`core/subtask_rows.py` is the single canonical definition of "what counts as a WP subtask row" (`_walk_wp_section`, the `UNCHECKED_SUBTASK_ROW` / `CHECKED_SUBTASK_ROW` patterns). Its consumers:

| Consumer | Call site | Role | WP13 action |
|----------|-----------|------|-------------|
| Lane-transition guard | `cli/commands/agent/tasks_shared.py::_check_unchecked_subtasks` (:428) → `iter_wp_section_subtask_rows` roster (:497) + `_legacy_unchecked_subtask_ids` fallback (:412/:520) | **blocks lane transitions on incomplete subtasks** | **Reroute** — roster off checkboxes, completion + roster off the snapshot slot; retire the `_legacy_unchecked_subtask_ids` checkbox fallback (post-seed, C-010) |
| Dashboard | `dashboard/scanner.py:954-965` (`count_wp_section_subtask_rows` / `count_subtask_rows`) | progress badge | **Finalize** — WP11's `reconstruct_wp_view` already reroutes subtasks onto the snapshot slot; delete any checkbox-count call that remains |
| Backfill (migration) | `migration/backfill_runtime_state.py:281` (`iter_wp_section_subtask_rows`) | **seeds** historical completion from legacy checkboxes | **KEEP** — this is the C-010 legacy source; existing/upgrading deployments still carry checkboxes to seed |
| Acceptance gate | `acceptance/gates_core.py:112` (`iter_unchecked_subtask_rows`) | gate check | **Leave as-is** unless the reroute strands it — coordinate, do not silently change gate semantics |
| Rollback writer | `tasks_move_task.py` (`uncheck_wp_section_subtask_rows`) | `move-task --to planned` unchecks rows | **Leave as-is** — WP05 owns `tasks_move_task.py`; do not touch |

**Post-WP04 note (verify before you start):** WP04 collapsed `emit.py::_infer_subtasks_complete` to an unconditional `_infer_subtasks_complete_from_snapshot`, so its `count_wp_section_subtask_rows` checkbox call is gone. WP04 also removed the `_phase1` flag branch in `_check_unchecked_subtasks`, so the guard **already** reads completion from `wp_snapshot_state(...)["subtasks"]` — but it **still** derives its **roster** from `iter_wp_section_subtask_rows` (checkbox rows) and **still** falls back to `_legacy_unchecked_subtask_ids` (checkbox rows) when the slot is silent. Those two remaining checkbox dependencies are what WP13 retires.

### The load-bearing behaviour trap (read this before touching the guard)

The guard returns `[]` (→ **never blocks**) when the roster is empty (`tasks_shared.py:498-499`). Today the roster comes from checkbox rows in `tasks.md`. **The instant you remove the checkboxes (T052), that roster becomes empty and the guard silently stops blocking every WP** — a severe correctness regression that no existing test would catch. The reroute (T051) MUST therefore change the **roster source** away from checkbox rows **before/with** the removal: the authored roster is the WP frontmatter `subtasks` list (static design intent — the guard's own docstring says "the roster … is always the authored … static design intent"), and completion is the snapshot `subtasks` slot. T054 exists specifically to prove the guard still blocks (incomplete) and unblocks (complete) off the snapshot after removal.

Concretely, `_check_unchecked_subtasks` today (post-WP04) reads:

```
roster = list(iter_wp_section_subtask_rows(content, wp_id))   # checkbox rows  ← retire
if not roster: return []
wp_state = wp_snapshot_state(feature_dir, wp_id)              # snapshot slot   ← keep
if wp_state is None or "subtasks" not in wp_state:
    return _legacy_unchecked_subtask_ids(content, wp_id)      # checkbox fallback ← delete (C-010)
subtasks = wp_state.get("subtasks") or {}
return [tid for tid, _ in roster if str(subtasks.get(tid, "")) != str(Lane.DONE)]
```

Target shape after WP13: the roster is the authored `subtasks` list (frontmatter / the snapshot's recorded keys), completion is the snapshot slot, and the `_legacy_unchecked_subtask_ids` checkbox fallback is gone. An absent snapshot for a WP that *has* an authored roster now **blocks** (fail-closed), matching the guard's pre-existing "unprovable completeness must block" intent (mirrors `emit._infer_subtasks_complete`'s fail-closed rule).

### Doctrine / template surface (enumerated — SOURCE only)

Every file below is a **SOURCE** artifact under `src/doctrine/`. None is in `owned_files`; each is a recorded out-of-map edit (see Risks). Do **not** touch the regenerated agent copies.

| SOURCE file | What it does today | WP13 change |
|-------------|--------------------|-------------|
| `missions/software-dev/templates/tasks-template.md` (:41–:146) | emits `- [ ] T001 …` example tracking rows | drop the checkbox glyph; rows become `T001 …` reference rows tracked by `mark-status` |
| `missions/documentation/templates/tasks-template.md` (:40–:142) | same | same |
| `missions/research/templates/tasks-template.md` (:37–:86) | same | same |
| `missions/mission-steps/software-dev/tasks/prompt.md` (:129–:147) | "Task Tracking Format" — "Use **checkbox format**"; `- [ ] T001` examples; "`mark-status` targets these per-WP checkbox rows" | flip the framing: `mark-status` records completion in the **event log**; there is no checkbox to tick |
| `missions/mission-steps/software-dev/tasks/prompt.md` (:179, :182, :511) | "Included subtasks (checkbox list …)"; "Preserve the checklist style so implementers can mark progress" | "Included subtasks (reference list …)"; drop "mark progress" checkbox framing → point at `mark-status` |
| `missions/mission-steps/software-dev/tasks-packages/prompt.md` (:145) | WP-prompt `## Definition of Done` generator ("verifiable checklist") | keep a verifiable DoD; subtask-completion evidence is `mark-status`, not a ticked box |
| `skills/spec-kitty-implement-review/SKILL.md` (:229) | already directs `spec-kitty agent tasks mark-status …` | verify consistency; strengthen only if the tasks-prompt wording shifted |

**Before → after example (any tasks-template row):**

```
- [ ] T012 [P] Create [Entity1] model in `src/models/[entity1].py`     ← before
T012 [P] Create [Entity1] model in `src/models/[entity1].py`           ← after (mark-status tracks completion)
```

## Subtasks

- [ ] **T051 [FR-016 / SC-010 / behaviour-sensitive] Reroute the lane-transition guard + dashboard subtask-count reader onto the snapshot `subtasks` slot.**
  - **Guard — the authoritative-surface edit in `core/subtask_rows.py`.** Add a snapshot-backed resolver (e.g. `unchecked_subtask_ids_from_snapshot(feature_dir, wp_id, roster)` returning the ids whose snapshot `subtasks` status is not `Lane.DONE`, and/or a `done/total` counterpart for the dashboard). This makes `core/subtask_rows.py` — not checkbox parsing — the guard's blocking source, honouring the plan's "reroute the guard onto the snapshot `subtasks` slot" framing while keeping the authoritative surface owned by this WP.
  - **Guard — the reroute in `tasks_shared.py::_check_unchecked_subtasks` (recorded out-of-map).** Numbered so the collapse is unambiguous:
    1. Take the **roster** from the authored `subtasks` list (WP frontmatter, static design intent) or the snapshot's recorded subtask keys — **not** `iter_wp_section_subtask_rows(content, wp_id)`.
    2. Resolve **completion** from `wp_snapshot_state(feature_dir, wp_id)["subtasks"]` via the new `core/subtask_rows.py` resolver.
    3. **Delete** the `_legacy_unchecked_subtask_ids(content, wp_id)` checkbox fallback (safe post-seed, C-010) and the now-dead `iter_wp_section_subtask_rows` import in that function.
    4. Rewrite the docstring: it currently narrates a flag ON/OFF checkbox-vs-snapshot story that no longer exists — describe the single snapshot path.
  - **Behaviour preservation is mandatory (SC-010):** the guard must still **block** a lane transition when a WP has incomplete subtasks and **unblock** when all are `done`, now reading the snapshot slot instead of checkbox bytes. `force=True` still only warns (returns the ids without raising). A WP with an empty authored roster is "nothing to block on" (unchanged). Do **not** fail open on an absent snapshot for a WP that *has* an authored roster — fail-closed (block) matches the guard's prior intent and `emit._infer_subtasks_complete`'s rule.
  - **Consider `_legacy_unchecked_subtask_ids` (:412):** once the guard stops calling it and no other runtime-authority caller remains, it is dead — delete it (campsite) rather than leaving an orphan checkbox reader that re-invites the split-brain. Confirm no live caller before removal.
  - **Dashboard (finalize).** WP11's `reconstruct_wp_view` already routes the dashboard's subtask read onto the snapshot slot (T045). Confirm; if the checkbox-count call at `dashboard/scanner.py:954-965` (`count_wp_section_subtask_rows` / `count_subtask_rows`) still remains, delete it here so the badge is snapshot-only, and drop the now-orphan imports (`:954-957`) + the stale comment (`:948-953`). Out-of-map (scanner is WP05/WP11's file) — record it (see Risks); gate on "only if it remains".
  - **KEEP the backfill's checkbox reader.** Do **not** remove `iter_wp_section_subtask_rows` / `count_subtask_rows` / `_walk_wp_section` / the row patterns from `core/subtask_rows.py`: `migration/backfill_runtime_state.py:281` still consumes them to seed legacy/upgrading corpora from their checkboxes (C-010), and `acceptance/gates_core.py` + `tasks_move_task.py` rollback still use them. Retire checkbox parsing only where it is the **runtime authority** (guard + dashboard), never the **migration seed** / gate / rollback paths. Update the module docstring's caller inventory (lines 1–30) to reflect that the guard now reads the snapshot, not these patterns.

- [ ] **T052 [FR-016 / C-010 / SC-010] Remove the `- [ ] T###` checkboxes AND redirect the SOURCE doctrine templates to `mark-status`.** Order gate: do this **only after** WP03's seed is on the merge unit's base (C-010 — the backfill has already read the checkboxes; removing them now strands nothing). Verify the seed first (a sampled done mission's snapshot `subtasks` slot is populated). Steps, one surface at a time:
  1. **This mission's `tasks.md`** (owned): remove any residual `- [ ] T###` canonical checkbox rows so SC-010 holds for the mission's own artifacts. **Keep** the pipe-table Subtask Index and the per-WP `**Subtasks**:` reference lists — they are reference surfaces (no leading `-`, not matched by `UNCHECKED_SUBTASK_ROW`), not tracking checkboxes.
  2. **`software-dev/templates/tasks-template.md`** (SOURCE, out-of-map): strip the `- [ ] ` glyph from the example rows at :41–:146; rows become `T001 …` reference rows tracked by `mark-status`.
  3. **`documentation/templates/tasks-template.md`** (SOURCE, out-of-map): same for :40–:142.
  4. **`research/templates/tasks-template.md`** (SOURCE, out-of-map): same for :37–:86.
  5. **`mission-steps/software-dev/tasks/prompt.md`** (SOURCE, out-of-map): rewrite the "Task Tracking Format" section (:129–:147) — replace "Use **checkbox format**" + the `- [ ] T001` examples + "`mark-status` targets these per-WP checkbox rows" with: *record completion via `spec-kitty agent tasks mark-status <T-ids> --status done`; the reduced event-log snapshot is the authority — there is no checkbox to tick.* Update the "Included subtasks (checkbox list …)" / "Preserve the checklist style so implementers can mark progress" wording (:179, :182, :511) to "reference list" + a pointer to `mark-status`.
  6. **`mission-steps/software-dev/tasks-packages/prompt.md`** (SOURCE, out-of-map): the WP-prompt `## Definition of Done` generator (:145) keeps a **verifiable** DoD, but its subtask-completion evidence is a `mark-status` record, not a ticked box.
  7. **`skills/spec-kitty-implement-review/SKILL.md`** (SOURCE): confirm :229 ("Mark subtasks done: `spec-kitty agent tasks mark-status …`") stays consistent; strengthen only if the tasks-prompt wording shifted.
  8. **Sweep for stragglers:** `grep -rn -E '^-\s*\[\s*\]\s*T[0-9]{3,}' src/doctrine/` returns nothing after the edits (SOURCE side clean).
  - **NEVER hand-edit generated agent copies** (`.claude/`, `.amazonq/`, `.augment/`, `.github/`, `.gemini/`, `.cursor/`, `.qwen/`, `.opencode/`, `.windsurf/`, `.kilocode/`, `.roo/`, `.kiro/`, `.agent/`, `.agents/skills/`). They regenerate from source via `spec-kitty upgrade`. A `- [ ] T` hit in an agent dir is expected drift closed by upgrade, **not** a WP13 edit target.

- [ ] **T053 [NFR-004 / terminology + docs-freshness] Guard the prose/template edits.** After the T052 prose/template changes, run (per-file, `uv run --extra test python -m pytest -p no:cacheprovider <FILE>`):
  - `tests/architectural/test_no_legacy_terminology.py` — the Terminology Canon guard (canonical `Mission` not `feature`, `status commit` not `ceremony`, …). ≈0.1 s; some repo-wide gates run **only** in CI's `integration-tests-core-misc` job, so run this locally before you consider the templates done.
  - `tests/docs/test_check_docs_freshness.py` and `tests/docs/test_check_cli_reference_freshness.py` — docs/CLI-reference freshness, since template/prose surfaces changed.
  - Fix any drift at the root (no suppression). If a freshness snapshot must be regenerated, do so via its sanctioned refresh path, not by editing the expected fixture by hand.

- [ ] **T054 [ATDD / SC-010 / C-010] Tests.** In `tests/specify_cli/core/test_subtask_rows_snapshot.py` (new, owned). Every case drives **real** snapshot state; the guard's read source is never mocked:
  1. **Guard blocks off the snapshot (SC-010):** *Given* a fixture WP with an authored `subtasks` roster and a snapshot slot marking **some** id not-`done`, **and no `- [ ] T###` checkbox rows in the fixture `tasks.md`**, *When* the rerouted guard runs with `force=False`, *Then* it returns the incomplete ids and blocks the transition (raises `typer.Exit`). Proves the block comes from the snapshot, not a checkbox.
  2. **Guard unblocks off the snapshot (SC-010):** the same WP with every roster id marked `done` in the snapshot slot → the guard returns `[]` and the transition proceeds. Reach the `done` state via `mark-status` / `emit_inner_state_changed(subtasks=…)`, not by writing a checkbox byte.
  3. **`force=True` still only warns:** an incomplete WP with `force=True` returns the ids without raising (no behaviour drift for the force path).
  4. **Empty roster is nothing-to-block-on:** a WP with no authored subtasks → guard returns `[]` (unchanged semantics).
  5. **Fail-closed on silent snapshot:** a WP that *has* an authored roster but whose snapshot slot is empty/absent → the guard **blocks** (does not fall open to "complete"). Proves the deleted checkbox fallback did not become a silent open.
  6. **Dashboard reads snapshot subtasks:** the scanned WP's `subtasks_done`/`subtasks_total` reflect the snapshot slot — assert they update after a `mark-status` and are **unchanged** by a raw checkbox edit (the D-13 incoherence is gone).
  7. **No checkbox remains (SC-010):** an in-test scan asserts **zero** `- [ ] T###` canonical rows (via `UNCHECKED_SUBTASK_ROW.match`) in the mission `tasks.md` and in each SOURCE tasks template you edited.
  8. **Seed-before-remove (C-010):** a regression proving the backfill still seeds subtask completion from checkboxes for a legacy fixture that *has* checkboxes (the migration reader `iter_wp_section_subtask_rows` is intact) — removal in canonical missions did not break the migration seed path.
  - Run each file with `uv run --extra test python -m pytest -p no:cacheprovider <FILE>` (bare `python` resolves a sibling checkout → false greens). Do **not** run the whole `tests/architectural/` directory (it hangs).

## Implementation sequence (recommended order)

The ordering is not cosmetic — T051 must land the roster/completion reroute **before** T052 removes the checkboxes, or the guard silently stops blocking (the behaviour trap). Recommended order:

1. **Verify the seed exists (C-010 gate).** Confirm WP03's backfill has committed seed events for this repo's corpus — sample a done mission and assert its snapshot `subtasks` slot is populated. Do not remove any checkbox until this holds.
2. **Add the snapshot-backed resolver to `core/subtask_rows.py`** (the authoritative surface) — pure addition, no consumer wired yet; unit-test it directly.
3. **Reroute the guard** (`tasks_shared.py::_check_unchecked_subtasks`) onto the resolver: roster from the authored `subtasks`, completion from the snapshot slot, delete the checkbox fallback. Land the T054 block/unblock regressions here — they must be green **before** any checkbox is removed.
4. **Finalize the dashboard** (`scanner.py`) — delete any residual checkbox-count call left after WP11.
5. **Remove the checkboxes** (T052) — this mission's `tasks.md` first, then the SOURCE templates, then the SOURCE prompt-template redirect to `mark-status`.
6. **Run the guards** (T053) — terminology + docs-freshness — after the prose/template edits.
7. **Full T054 pass** — including the no-checkbox-remains scan and the seed-before-remove regression.

If any step 2–4 pushes a touched function over complexity 15, extract a small named helper (with a focused test) rather than suppress.

## Branch Strategy

- **Strategy:** Planning artifacts were generated on `feat/runtime-state-corpus-cutover`; completed changes merge back into `feat/runtime-state-corpus-cutover`.
- **Planning base branch:** `feat/runtime-state-corpus-cutover`
- **Merge target branch:** `feat/runtime-state-corpus-cutover`
- **Formal dependency: WP11** — WP13 consumes WP11's `reconstruct_wp_view` reader (the snapshot `subtasks` slot is read through it). WP11's worktree must be merged first so the reader exists.
- **C-010 seed ordering — WP03 is the transitive predecessor that matters:** checkbox removal (T052) is safe **only after** WP03 (IC-01b) has run the backfill over this repo's `kitty-specs/` and committed the seed events — that is the step that reads the checkboxes into the event log. WP03 is upstream of WP11 on the dependency spine (`WP03 → WP04 → … → WP10 → WP11 → WP13`), so by the time WP13 branches from WP11's merged state the seeds are already committed. **Verify the seed is present** (a sampled done mission's snapshot `subtasks` slot is populated) before removing any checkbox — do not assume; C-010 is a data-loss constraint.
- Per project policy: `spec-kitty merge` targets **local main only**; never `git push origin main`. Publishing is the operator's explicit, separate step.

## Test strategy

- **Per-file only** — `uv run --extra test python -m pytest -p no:cacheprovider <FILE>`. **NEVER** run the whole `tests/architectural/` directory — it hangs. Exercise a single guard file with a timeout if needed.
- New coverage lands in `tests/specify_cli/core/test_subtask_rows_snapshot.py` (owned). The block/unblock proof must drive **real** snapshot state via `mark-status` / `emit_inner_state_changed`, and assert the **absence** of checkbox rows in the fixture — never mock the guard's read source (a mocked snapshot would make the "off the snapshot" claim vacuous; the reviewer will check this).
- After the T052 template/prose edits, run the **terminology guard** (`tests/architectural/test_no_legacy_terminology.py`) and **docs-freshness** (`tests/docs/test_check_docs_freshness.py`, `tests/docs/test_check_cli_reference_freshness.py`) — T053.
- The guard block/unblock regression must be **non-vacuous**: it must fail if the reroute fell back to reading checkboxes, and fail if the guard stopped blocking on an incomplete WP.
- **Fixtures must have no checkbox rows.** The guard-blocks/unblocks fixtures deliberately carry a `tasks.md` with the checkboxes already removed (or never present) — if a fixture still has `- [ ] T###` rows, a passing test proves nothing about the snapshot path. Assert the fixture's `tasks.md` yields zero rows from `UNCHECKED_SUBTASK_ROW` as a precondition of the block/unblock cases.
- **Seed-before-remove needs its own fixture with checkboxes present** — the C-010 regression is the mirror image: a *legacy* fixture that still has checkboxes, fed to the backfill, must seed the snapshot slot correctly. Keep the two fixture families distinct.
- **Do not add tests to `tests/architectural/`** — they must be run per-file and the directory hangs on a full run. All new coverage lands in the owned `tests/specify_cli/core/test_subtask_rows_snapshot.py`.
- **Pre-existing reds are not yours** — the phantom `SYNC_DISABLE_ENV_VARS` arch-adversarial red and the ADR-2026-07-17-1 known-P0s (#2736/#2772/#1834) are baseline; confirm on the merge-base before attributing any red to this diff.

## Definition of Done

**T051 — guard + dashboard reroute (FR-016 / SC-010):**
- [ ] `core/subtask_rows.py` carries the snapshot-backed resolver; it is the guard's blocking source (roster authored, completion from the snapshot `subtasks` slot).
- [ ] `tasks_shared.py::_check_unchecked_subtasks` no longer reads checkbox rows; the `_legacy_unchecked_subtask_ids` fallback is deleted (and the function removed if no live caller remains); its docstring describes the single snapshot path.
- [ ] **Block/unblock semantics preserved** — proven by the T054 real regressions (blocks incomplete, unblocks complete, `force` warns, empty roster no-ops, silent snapshot fail-closed).
- [ ] The dashboard subtask badge is snapshot-only (WP11's reader); any residual checkbox-count call + orphan imports in `scanner.py:948-965` deleted.
- [ ] The **backfill / gate / rollback** checkbox readers (`iter_wp_section_subtask_rows`, `count_subtask_rows`, `_walk_wp_section`, patterns) are **retained** (C-010); the module docstring's caller inventory is updated.

**T052 — checkbox removal + template redirect (FR-016 / C-010 / SC-010):**
- [ ] No `- [ ] T###` canonical checkbox remains in this mission's `tasks.md`.
- [ ] No `- [ ] T###` example/tracking row remains in the three SOURCE `tasks-template.md` files.
- [ ] The SOURCE doctrine prompt templates (`tasks/prompt.md`, `tasks-packages/prompt.md`) direct agents to `spec-kitty agent tasks mark-status`, not checkbox ticks.
- [ ] **Zero edits to generated agent copies** (`.claude/`, `.amazonq/`, `.augment/`, …) — SOURCE only.
- [ ] Removal landed **after** WP03's seed was committed (C-010); the seed was verified present first.

**T053 / T054 — guards + tests:**
- [ ] Terminology guard (`test_no_legacy_terminology.py`) + docs-freshness (`test_check_docs_freshness.py`, `test_check_cli_reference_freshness.py`) green after the prose/template edits (NFR-004).
- [ ] All eight T054 cases green with **real** snapshot state and **no** mocked read source.

**Cross-cutting:**
- [ ] **SC-010** honoured end-to-end: subtask completion read from the snapshot everywhere (dashboard + guard); guard blocks/unblocks off the snapshot; no `- [ ] T###` remains in `tasks.md`/templates; templates direct `mark-status`; historical completion seeded before removal.
- [ ] **NFR-003** honoured: a subtask completion mark writes 0 bytes to `tasks/WP##.md` (the checkbox proxy is gone — completion rides the event log only).
- [ ] `ruff` + `mypy` clean with **no** new `# noqa` / `# type: ignore` / per-file ignores (fix the code, do not suppress); every touched function stays at complexity **≤15**.
- [ ] No edits outside `owned_files` **except** the recorded out-of-map edits (Risks): `scanner.py` checkbox-count finalize, the `tasks_shared.py` guard reroute, and the SOURCE doctrine templates.

## Risks & out-of-map edits

- **OUT-OF-MAP: `src/specify_cli/dashboard/scanner.py`** (owned by WP05, further rerouted by WP11). WP11's `reconstruct_wp_view` already moves the subtask read onto the snapshot slot; WP13 only **finalizes** — delete the residual `count_wp_section_subtask_rows` / `count_subtask_rows` checkbox-count call (`:954-965`) if it survived WP11. Minimal, recorded, and gated by "only if it remains".
- **OUT-OF-MAP: `src/specify_cli/cli/commands/agent/tasks_shared.py`** (owned by WP04) — the guard function `_check_unchecked_subtasks` lives here. The reroute's authoritative surface is `core/subtask_rows.py` (the snapshot-backed resolver), but wiring the guard to it requires a **minimal** edit to `_check_unchecked_subtasks` (swap the roster source + delete the checkbox fallback). Record it; keep it to the completion/roster source only — do not refactor the surrounding function.
- **OUT-OF-MAP (large surface): the SOURCE doctrine templates under `src/doctrine/missions/mission-steps/**` and `src/doctrine/missions/*/templates/`.** Enumerated in T052. Edit **SOURCE only** — the 13 agent-dir copies regenerate via `spec-kitty upgrade`; a same-content edit in `.claude/`/`.amazonq/`/… is a defect. This is the plan's flagged breadth risk (IC-10); keep the edits mechanical (checkbox glyph → mark-status directive) and enumerate each file touched in the PR body.
- **C-010 data-loss trap (do not reorder):** removing checkboxes before WP03's seed is committed strands historical completion. Verify the seed is present (sampled snapshot `subtasks` slot populated) before any removal. Historical missions whose checkboxes are removed must already be seeded.
- **Behaviour trap (empty roster = guard never blocks):** removing checkboxes empties the guard's roster unless T051 first moves the roster source to the authored frontmatter `subtasks`. Never land T052 without T051; T054's block regression is the guard against a silent open.
- **Do NOT delete the migration checkbox reader.** `iter_wp_section_subtask_rows` stays — the backfill (`migration/backfill_runtime_state.py`) reads it to seed legacy/upgrading corpora (C-010). Retire checkbox parsing only in the runtime-authority path.
- **Do NOT touch `tasks_move_task.py`** (WP05's; `uncheck_wp_section_subtask_rows` rollback semantics) or the acceptance gate (`acceptance/gates_core.py`) beyond what the reroute strictly requires — coordinate rather than silently change gate/rollback behaviour.
- **`emit._infer_subtasks_complete` is already snapshot-only (post-WP04).** WP04 collapsed it to `_infer_subtasks_complete_from_snapshot`, so its `count_wp_section_subtask_rows` checkbox call is gone. Confirm this before assuming any remaining `emit.py` checkbox read is yours — if one survived WP04, flag it to WP04's owner rather than fixing it out-of-band here.
- **Roster source must be the authored `subtasks`, not a fresh checkbox parse.** The WP frontmatter already carries `subtasks: [T…]` (static design intent). Sourcing the roster from there — not from re-parsing `tasks.md` — is what makes checkbox removal safe. If the implementer instead keeps parsing `tasks.md` for the roster, the removal breaks the guard; the reviewer must confirm the roster no longer depends on checkbox rows.
- **Complexity:** the guard reroute + resolver are small; if `_check_unchecked_subtasks` drifts over cx 15, extract the snapshot resolution into the `core/subtask_rows.py` helper (where it belongs) rather than inline it.

## Reviewer guidance

- **Guard reroute preserves block/unblock (REAL regression):** confirm `tests/specify_cli/core/test_subtask_rows_snapshot.py` drives real snapshot state (via `mark-status`/`emit_inner_state_changed`) with **no checkbox rows in the fixture**, proves the guard blocks an incomplete WP and unblocks a complete one, and would fail if the reroute fell back to checkboxes or stopped blocking. Not mocked.
- **No checkbox remains (SC-010):** `grep -rn -E '^-\s*\[\s*\]\s*T[0-9]{3,}'` over this mission's `tasks.md` and the SOURCE tasks templates returns nothing; the doctrine prompt templates direct `spec-kitty agent tasks mark-status`.
- **SOURCE templates only — no agent-copy edits:** the diff touches `src/doctrine/…` exclusively for templates; **zero** changes under `.claude/`, `.amazonq/`, `.augment/`, `.github/`, `.gemini/`, `.cursor/`, `.qwen/`, `.opencode/`, `.windsurf/`, `.kilocode/`, `.roo/`, `.kiro/`, `.agent/`, or `.agents/skills/`. Any agent-dir edit is a reject.
- **Seed-before-remove (C-010):** the PR shows checkbox removal landed after WP03's seed commit; the seed-before-remove regression proves the migration reader still seeds legacy checkboxes.
- **Backfill reader intact:** `iter_wp_section_subtask_rows` is still imported/used by `migration/backfill_runtime_state.py`; only the guard + dashboard stopped reading checkboxes as runtime authority.
- **Guards green:** terminology guard + docs-freshness pass after the prose/template edits; `ruff` + `mypy` clean, no new suppressions, touched functions ≤15 complexity.
- **Dashboard is snapshot-only, no double-read:** the scanner does not both count checkboxes and read the snapshot — the checkbox count path is deleted, not left as a shadow. Confirm the progress badge reflects a `mark-status` change and ignores a raw checkbox edit (the D-13 incoherence is closed at the UI seam, per the UI proof discipline in CLAUDE.md).
- **Guard fixtures are honest:** the block/unblock fixtures carry a checkbox-free `tasks.md`; the seed-before-remove fixture carries checkboxes — the two families are not conflated, so neither test can pass for the wrong reason.
- **Retained readers verified live:** `iter_wp_section_subtask_rows` / `count_subtask_rows` still have real callers (backfill, gate, rollback); they were not left dead, and were not deleted. `_legacy_unchecked_subtask_ids`, by contrast, is gone if the guard was its only live caller.
- **Ordering evidence:** the PR narrative shows the C-010 sequence — seed committed (WP03) → guard rerouted (T051) → checkboxes removed (T052) — not the reverse. A diff that removes checkboxes without the roster reroute in the same unit is a reject.

## Activity Log

- 2026-07-20T20:34:25Z – claude – shell_pid=746586 – Assigned agent via action command
- 2026-07-20T21:31:52Z – claude – shell_pid=746586 – Ready for review — guard reroute + doctrine templates event-sourced (#2816 IC-10). Pre-review gate skipped: arch-dir scoped run timed out (300s); per-file evidence: owned+remediated test files green, ruff clean, mypy 68=68 base.
- 2026-07-20T21:35:21Z – claude – shell_pid=802169 – Started review via action command
- 2026-07-20T21:37:14Z – user – shell_pid=802169 – Approved: guard fail-closed off snapshot, 52 template checkboxes stripped, mypy clean; emit-door consistency + corpus strip = closeout items
