---
work_package_id: WP11
title: Canonical WP-view reconstruction reader (4 gates -> 1)
dependencies:
- WP10
requirement_refs:
- FR-012
planning_base_branch: feat/runtime-state-corpus-cutover
merge_target_branch: feat/runtime-state-corpus-cutover
branch_strategy: Planning artifacts for this mission were generated on feat/runtime-state-corpus-cutover. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/runtime-state-corpus-cutover unless the human explicitly redirects the landing branch.
subtasks:
- T043
- T044
- T045
- T046
agent: "claude"
shell_pid: "722501"
shell_pid_created_at: "1784578367.44"
history:
- timestamp: '2026-07-20T08:39:02Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/wp_view.py
create_intent:
- src/specify_cli/status/wp_view.py
- tests/specify_cli/status/test_reconstruct_wp_view.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/status/wp_view.py
- tests/specify_cli/status/test_reconstruct_wp_view.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: Canonical WP-view reconstruction reader (4 gates -> 1)

## ⚡ Do This First: Load Agent Profile

Before touching any code, load the **`python-pedro`** agent profile and adopt it for the whole
work package:

```bash
spec-kitty charter context --action implement
```

`python-pedro` is the Python-specialist implementer profile — TDD/ATDD-first, type-safe, idiomatic
Python 3.11+, complexity-aware, zero-suppression. Everything below is written to that discipline:
tests land in the same WP as the code, `ruff` + `mypy` stay clean with **no** new
`# noqa` / `# type: ignore` / per-file ignores, and every new branch/helper gets a focused test.

This WP is a **MERGE-UNIT with WP10** (resolved-binding slots + historical provenance correction). Do not treat it
as independently landable — see **Branch Strategy** below.

## Objective

Create **one** canonical WP-view reconstruction reader —
`src/specify_cli/status/wp_view.py::reconstruct_wp_view(feature_dir, wp_id)` — that assembles a work
package's **resolved final-state** from the reduced snapshot (lane, agent, assignee, subtasks,
review, and the resolved `role`/`agent_profile`(+`agent_profile_version`)/`model`/`provider`) AND
surfaces the **authored/recommended** assignment from frontmatter as a **distinct** group, then
route all **FOUR** hand-rolled snapshot gates onto it so the dashboard, the `agent tasks status`
board, and `WorkPackage` can never disagree (SC-007). This is IC-07 of the mission.

The reader replaces four independently hand-rolled gates:
1. `src/specify_cli/dashboard/scanner.py::_process_wp_file`
2. `src/specify_cli/cli/commands/agent/tasks_status_cmd.py` (the `agent tasks status` board)
3. `src/specify_cli/task_utils/support.py::WorkPackage`
4. the snapshot accessor `wp_snapshot_state` (the shared read seam every gate must resolve through)

The single load-bearing rule (C-008 / INV-7): **authored intent and resolved actual are NEVER
conflated** — a WP with no resolved-binding slots shows the authored recommendation plus an *empty*
resolved group, **never** the authored value masquerading as the resolved actual.

## Context & grounding

- **Plan IC-07** (`plan.md`, "IC-07 — Canonical WP-view reconstruction reader"): collapse the three
  (now four) hand-rolled snapshot-authority gates into ONE reader that reconstructs resolved
  final-state from the event log/snapshot for all dynamic fields, and surfaces the authored
  recommendation distinctly. **Scope the reader to identity/runtime fields ONLY** (adversarial
  finding): the dashboard also produces presentation fields (`title` regex'd from the prompt body,
  `prompt_markdown`, `prompt_path`) that are NOT in the reader's contract — keep those consumer-side
  or the reroute reads as a regression.
- **FR-012** (`spec.md`): the hand-rolled gates — `dashboard/scanner.py`, `tasks_status_cmd.py`
  (the `agent tasks status` board), and `task_utils/support.py::WorkPackage` — collapse into **one**
  canonical reader that reconstructs resolved final-state for all dynamic fields (lane, agent,
  assignee, subtasks, review, resolved `role`/`agent_profile`/`model`), while surfacing the authored
  recommendation from frontmatter **distinctly labeled**. No reader hand-rolls its own gate afterward.
- **C-008** (`spec.md`): authored intent and resolved actual are surfaced as **distinct** values; no
  consumer treats the authored value as "what ran" or the resolved value as "what was intended".
- **Research D-14** (`research.md`, campsite census): `dashboard/scanner.py::_process_wp_file` is
  **cx ~13 → >15** on the IC-04/IC-07 reroute → **tidy-first** extract a `_wp_runtime_view` helper
  backed by the reconstruction reader in the SAME WP (do not inline the reroute into the already-hot
  function).
- **Data-model INV-7 / INV-8** (`data-model.md`): INV-7 — every WP-view consumer surfaces authored
  recommendation and resolved actual as distinct values; the reconstruction reader is the single
  assembly point. INV-8 — after multiple pick-ups the reconstructed resolved identity equals the
  most recent transition's actual, with 0 bytes written to `tasks/WP##.md`.
- **Contract "Reconstruction reader (IC-07)"** (`contracts/resolved-binding.md`): the reader returns
  two distinct identity groups —

  | Group | Source | Fields |
  |-------|--------|--------|
  | `resolved` (actual) | snapshot (event-sourced) | lane, agent, assignee, subtasks, review, resolved role/profile(+version)/model/provider |
  | `authored` (recommended) | frontmatter (static) | authored role/agent_profile/model, owned_files, dependencies, requirement_refs, … |

  Contract: all consumers call this reader; none hand-rolls a snapshot gate afterward (SC-007).
  Tolerate-absent: absent resolved slots → `authored` populated, `resolved` empty; never the authored
  value returned in the `resolved` group (INV-7). subtasks authority = the snapshot `subtasks` slot,
  not `tasks.md` checkbox counting.

### Code you are re-routing (verified against the tree)

- `wp_snapshot_state(feature_dir, wp_id)` — `src/specify_cli/status/reducer.py:333` — the shared
  `read_event_stream → reduce → work_packages.get(wp_id)` seam; returns the per-WP runtime dict or
  `None`. Runtime slots today: `shell_pid`, `agent`, `assignee`, `tracker_refs`, `subtasks`,
  `review`. **WP10 adds** the resolved-binding slots (`role`, `agent_profile`,
  `agent_profile_version`, `model`, `provider`). Your reader reads all of these THROUGH this accessor.
- `dashboard/scanner.py::_process_wp_file` (~:864): reads `agent` (`wp_meta_dict.agent`, :937),
  `assignee` (`wp_meta_dict.assignee`, :978), `agent_profile`/`role`/`model` (frontmatter attrs,
  :976-977), and subtask completion via **checkbox counting** (`count_wp_section_subtask_rows` /
  `count_subtask_rows`, :954-965). It ALSO produces `title` (regex on `# Work Package Prompt:` at
  :899), `prompt_markdown` (:980) and `prompt_path` (:981) — **presentation fields, keep consumer-side**.
- `tasks_status_cmd.py`: reads `agent_profile` via `extract_scalar(front, "agent_profile")` (:289)
  and feeds the human-in-charge sentinel `_get_hic_marker(wp.get("agent_profile"), …)` (:378 and
  the render legs); `agent`/`shell_pid` come through `_st_gated_runtime_fields` (:280).
- `task_utils/support.py::WorkPackage` (~:364): has `assignee`/`agent`/`shell_pid`/`lane` properties
  but **no `role`/`agent_profile`/`model` property today** — this is the third copy of the gate.
- **`prompt_builder.py:170` reads authored `agent_profile` for governance rendering** — that is
  **authored intent** (correctly frontmatter). **Do NOT reroute it.** It is not one of the four gates.

## Subtasks

### T043 — Create `status/wp_view.py::reconstruct_wp_view(feature_dir, wp_id)` (two distinct groups)

Create `src/specify_cli/status/wp_view.py` with a single public reader:

```python
def reconstruct_wp_view(feature_dir: Path, wp_id: str) -> WPView: ...
```

- Return a typed result (a frozen dataclass or a typed mapping) with **two clearly separated
  groups**:
  - `resolved` — snapshot-sourced (via `wp_snapshot_state`): `lane`, `agent`, `assignee`,
    `subtasks`, `review`, and the resolved `role`, `agent_profile`, `agent_profile_version`,
    `model`, `provider`.
  - `authored` — frontmatter-sourced (via the WP frontmatter parse): authored `role`,
    `agent_profile`, `model` (and pass-through static fields the consumers need, e.g.
    `owned_files`/`dependencies`/`requirement_refs` if a consumer reads them).
- **Tolerate-absent (INV-7):** when `wp_snapshot_state` returns `None` or a dict missing a
  resolved-binding slot, the corresponding `resolved` field is **empty/None** — NEVER fall back to
  the authored value inside the `resolved` group. `authored` is always populated from frontmatter;
  `resolved` degrades to empty. No crash when there is no event log yet.
- **Subtasks authority = the snapshot `subtasks` slot**, not `tasks.md` checkbox counting (WP13
  removes the checkboxes — the reader must not depend on them).
- **Scope: identity/runtime fields ONLY.** Do NOT compute `title` (regex), `prompt_markdown`, or
  `prompt_path` in the reader — those are presentation concerns owned by the dashboard consumer.
- Resolve the event log via the existing seam (`wp_snapshot_state` / `read_event_stream`), never
  `Path.cwd()`; the accessor already resolves the passed `feature_dir` (C-003 co-constraint).
- Keep the reader's cyclomatic complexity ≤ 15; split assembly into small private helpers
  (`_resolved_group`, `_authored_group`) with stable inputs/outputs so they can be tested directly.

### T044 — Tidy-first: extract `scanner._process_wp_file`'s runtime-view helper (cx 13 → ≤15)

- `_process_wp_file` is **cx ~13** today and the IC-04/IC-07 reroute pushes it **>15**. Per D-14,
  **extract first**: pull the runtime-identity assembly into a `_wp_runtime_view(...)` helper (in
  `scanner.py`) that delegates to `reconstruct_wp_view`, then have `_process_wp_file` merge the
  returned resolved/authored groups with the presentation fields it still owns.
- **Keep the presentation fields consumer-side.** `title` (the `# Work Package Prompt:` regex),
  `prompt_markdown`, and `prompt_path` STAY in `_process_wp_file` — the reader does not produce them.
  If they get swallowed into the reader the reroute regresses the dashboard.
- After the extraction, confirm `_process_wp_file` and the new helper are each **≤15** cyclomatic
  complexity (`ruff` `C901` / Sonar `S3776`). Do not leave `_process_wp_file` at 16+.

### T045 — Reroute all four gates onto the reader (no consumer hand-rolls a gate afterward)

- **Dashboard scanner** (`dashboard/scanner.py::_process_wp_file` via the T044 helper): resolved
  `agent`/`assignee`/`role`/`agent_profile`/`model` and `subtasks` come from `reconstruct_wp_view`'s
  `resolved` group (subtasks from the snapshot slot, **not** the checkbox counters); the authored
  recommendation is carried distinctly. `lane` continues to come from the event log (`get_wp_lane`,
  already event-sourced at :918) — route it through the reader's `resolved.lane`.
- **`agent tasks status` board** (`tasks_status_cmd.py`): replace the `extract_scalar(front,
  "agent_profile")` (:289) and `_st_gated_runtime_fields` runtime reads with the reader. `_get_hic_marker`
  must be fed the **authored** `agent_profile` where it means "human-in-charge design intent"; the
  **resolved** actual profile is a distinct field on the row — do not conflate them (C-008).
- **`WorkPackage`** (`task_utils/support.py`): back `agent`/`assignee` (and add `role`/`agent_profile`/
  `model` properties that did not exist) with the reader's `resolved` group; keep an `authored_*`
  accessor for the frontmatter recommendation. Preserve the per-instance memoization intent (one
  reduce per instance).
- **`wp_snapshot_state`** stays the single low-level accessor; every gate resolves runtime through
  the reader, and the reader through the accessor — no gate re-implements the
  `read_event_stream → reduce → get(wp_id)` idiom afterward (SC-007).
- **Do NOT touch `prompt_builder.py`** — its authored `agent_profile` read is authored intent.

### T046 — Tests (ATDD): parity, latest-actual, tolerate-absent

Create `tests/specify_cli/status/test_reconstruct_wp_view.py`:

- **SC-007 parity**: build one WP with seeded resolved slots, then assert the **three** consumers
  (dashboard scanner row, `agent tasks status` board row, `WorkPackage`) return the **same** resolved
  runtime state for that WP — because they share one reconstruction path.
- **SC-008 latest-actual + byte-stability**: drive a WP through implement-claim (profile **P1**/model
  **M1**) then review-claim (profile **P2**/model **M2**); assert the reconstructed view shows the
  **current actual** (P2/M2) from the event log (latest-wins) with the authored recommendation still
  readable and distinctly labeled, and assert **0 bytes** are written to `tasks/WP##.md` across both
  claims (byte-identical before/after).
- **Tolerate-absent (INV-7 / INV-8 coverage)**: a **never-reclaimed** WP (no resolved-binding
  events) → `authored` populated from frontmatter, `resolved` **empty** — no crash, and the authored
  value **never** appears in the `resolved` group (no masquerade, no split-brain re-introduction).
- **Presentation-fields-not-swallowed**: assert the dashboard row still carries `title`,
  `prompt_markdown`, `prompt_path` after the reroute (the reader did not eat them).
- Add focused unit tests directly on `_resolved_group` / `_authored_group` (and the scanner
  `_wp_runtime_view` helper) so the new branches are covered without relying only on broad
  integration paths (Sonar new-code coverage).

## Branch Strategy

**MERGE-UNIT with WP10.** WP10 adds the resolved-binding delta slots to `WPInnerStateDelta` /
`_RUNTIME_SLOTS` / `_apply_annotation_delta` AND re-seeds this repo's dogfood corpus under the
`_seed_id(…, "resolved_binding")` namespace (C-011). If **this** reader (WP11) reaches
`feat/runtime-state-corpus-cutover` before WP10's re-seed lands, the dogfood corpus shows **empty
resolved slots** for every mission — the tolerate-absent path degrades gracefully but the corpus is
under-populated. So:

- WP11 declares `dependencies: [WP10]` and **must merge in the same merge unit** as WP10.
- Planning artifacts were generated on `feat/runtime-state-corpus-cutover`; completed changes merge
  back into `feat/runtime-state-corpus-cutover` (never a direct push to `origin/main`; PR-bound;
  the operator publishes).
- Do not merge WP11 to local main independently — coordinate the WP10+WP11 merge as one unit.

## Test strategy

Run per-file with the mission's canonical incantation (bare `python` resolves a sibling checkout →
false greens; `--extra test` is required):

```bash
uv run --extra test python -m pytest -p no:cacheprovider tests/specify_cli/status/test_reconstruct_wp_view.py
```

Also exercise the rerouted consumers' own suites per-file (dashboard scanner, `agent tasks status`,
`WorkPackage`) to confirm no regression, and confirm complexity/lint gates:

```bash
ruff check src/specify_cli/status/wp_view.py src/specify_cli/dashboard/scanner.py
mypy src/specify_cli/status/wp_view.py
```

The dashboard reroute has a live UI surface — do not assert dashboard behaviour from API/row shape
alone if a Playwright regression already covers the modal; extend the existing UI guard rather than
asserting from row dicts only (see the repo's UI-e2e policy).

## Definition of Done

- **FR-012**: one canonical `reconstruct_wp_view(feature_dir, wp_id)` exists in
  `src/specify_cli/status/wp_view.py`; the **four** gates (dashboard scanner, `agent tasks status`
  board, `WorkPackage`, and the shared `wp_snapshot_state` seam) all resolve runtime through it — no
  consumer hand-rolls a snapshot gate afterward.
- **C-008 / INV-7**: authored intent and resolved actual are surfaced as **distinct** groups and are
  **never** conflated; no consumer treats authored as "what ran".
- **SC-007**: dashboard, status board, and `WorkPackage` return the **same** resolved runtime state
  for the same WP (proven by a per-consumer parity test).
- **SC-008 / INV-8**: implement-claim(P1/M1) → review-claim(P2/M2) reconstructs the **current actual**
  (P2/M2, latest-wins) with **0 bytes** written to `tasks/WP##.md`; a never-reclaimed WP shows
  authored + empty resolved (no masquerade).
- **Tolerate-absent**: absent resolved slots degrade to empty `resolved` with `authored` intact;
  no crash on a WP with no event log.
- **Scope discipline**: reader covers identity/runtime fields ONLY; presentation fields
  (`title`/`prompt_markdown`/`prompt_path`) stay consumer-side and are not swallowed.
- **Quality**: `_process_wp_file` and the extracted helper are each **≤15** cyclomatic complexity;
  `ruff` + `mypy` clean with **no** new `# noqa` / `# type: ignore` / per-file ignores; every new
  branch/helper has a focused test in this WP.

## Risks & out-of-map edits

- **OUT-OF-MAP (sequential — owners ran earlier)**: this WP re-routes three files it does not own,
  onto the reader. This is safe because those owners land before WP11 in the merge sequence:
  - `src/specify_cli/dashboard/scanner.py` — owned by **WP05**; WP11 extracts `_wp_runtime_view` and
    reroutes `_process_wp_file` onto the reader.
  - `src/specify_cli/cli/commands/agent/tasks_status_cmd.py` — owned by **WP04**; WP11 reroutes the
    board's runtime reads onto the reader.
  - `src/specify_cli/task_utils/support.py` — owned by **WP04**; WP11 backs the `WorkPackage`
    runtime properties (and adds `role`/`agent_profile`/`model`) with the reader.
  Confirm the current state of these files at implementation time; if an owner's edit has shifted a
  line the notes above cite, re-locate the read rather than assuming the offset.
- **Subtly different per-gate fallbacks**: the three gates encode subtly different fallback behaviour
  (frontmatter-attr access vs `extract_scalar` vs `_st_gated_runtime_fields`; checkbox counting vs
  snapshot slot). **Unify carefully** — a naive merge silently picks one gate's fallback for all.
  The per-consumer parity test (T046) is the guard that catches divergence.
- **Presentation-field swallow**: the single most likely regression is pulling `title`/
  `prompt_markdown`/`prompt_path` into the reader — the dashboard then loses them. The reader's
  contract is identity/runtime only; the presentation-fields-not-swallowed test pins this.
- **Do NOT reroute `prompt_builder.py`** — authored intent belongs in frontmatter; rerouting it to
  the resolved actual would break governance rendering and violate C-008.
- **`status_phase` predicate is gone by WP11's point in the sequence** (IC-03) — the reader is
  unconditional against the snapshot; do not reintroduce a flag branch.

## Reviewer guidance

- Verify **one** reader (`reconstruct_wp_view`) backs **all four** consumers — grep that
  `wp_snapshot_state` is reached only through the reader in the rerouted gates, and that no consumer
  re-implements the `read_event_stream → reduce → get(wp_id)` idiom afterward (SC-007).
- Verify authored ≠ resolved is **never** conflated: the two groups are distinct on the return type;
  `_get_hic_marker` is fed the authored profile; the resolved actual is a separate field.
- Verify **tolerate-absent has no masquerade**: a WP with no resolved-binding slots yields empty
  `resolved` with `authored` intact — assert the authored value does NOT appear in the resolved
  group (this is the split-brain the mission exists to close).
- Verify **presentation fields are not swallowed**: `title`, `prompt_markdown`, `prompt_path` remain
  produced by the dashboard consumer, not the reader.
- Verify complexity: `_process_wp_file` and the extracted `_wp_runtime_view` helper are each ≤15;
  no new suppressions; new branches/helpers carry focused tests.
- Verify subtask authority is the snapshot `subtasks` slot, not `tasks.md` checkbox counting.

## Activity Log

- 2026-07-20T19:22:25Z – claude – shell_pid=517976 – Assigned agent via action command
- 2026-07-20T20:12:24Z – claude – shell_pid=517976 – Ready for review: canonical reconstruct_wp_view reader (4 gates -> 1). Pre-review gate hit the 300s scoped-run cap (env timeout, not a failure); per-file evidence GREEN: test_reconstruct_wp_view (17), test_2093 (6), test_tasks_compat_surface (295), test_dashboard + board seam + WP lifecycle (231), test_all_declarations_required + test_status_module_boundary + test_2093 (102), test_dashboard_wp_modal UI (1); ruff+mypy clean, cx<=15.
- 2026-07-20T20:12:51Z – claude – shell_pid=722501 – Started review via action command
- 2026-07-20T20:33:02Z – user – shell_pid=722501 – Approved: reconstruct_wp_view 4 gates->1, SC-007/008/tolerate-absent, mypy net-clean 68<=70, merges cleanly with Phase-1
