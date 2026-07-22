---
work_package_id: WP05
title: Lane.UNINITIALIZED member + loader + FSM + display unification (#2675 core)
dependencies: []
requirement_refs:
- C-001
- FR-010
- NFR-003
- NFR-004
- NFR-005
tracker_refs: []
planning_base_branch: feat/landing-pass-campsite-followups
merge_target_branch: feat/landing-pass-campsite-followups
branch_strategy: Planning artifacts for this mission were generated on feat/landing-pass-campsite-followups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/landing-pass-campsite-followups unless the human explicitly redirects the landing branch.
subtasks:
- T040
- T041
- T042
- T043
- T044
- T045
- T046
phase: Phase 2 - Lane unification core
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3761962"
shell_pid_created_at: "1784159093.94"
history:
- at: '2026-07-15T22:32:40Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/
create_intent:
- tests/specify_cli/status/test_lane_uninitialized.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/status/models.py
- src/specify_cli/status/wp_state.py
- src/specify_cli/status/lane_reader.py
- src/specify_cli/status/reducer.py
- src/specify_cli/status/wp_metadata.py
- src/specify_cli/status/lifecycle.py
- src/specify_cli/status_lanes.py
- src/specify_cli/cli/commands/agent/tasks_status_view.py
- tests/specify_cli/status/test_lane_uninitialized.py
- tests/status/test_models.py
- tests/status/test_reducer.py
- tests/status/test_parity.py
- tests/status/test_transitions.py
- tests/specify_cli/status/test_in_review_display.py
- tests/specify_cli/status/test_progress.py
- tests/specify_cli/status/test_wp_metadata.py
- tests/specify_cli/cli/commands/agent/test_tasks_status_view.py
- tests/specify_cli/cli/commands/agent/test_tasks_status_cmd_seam.py
- tests/integration/test_dashboard_counters.py
- tests/test_dashboard/test_scanner.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Lane.UNINITIALIZED member + loader + FSM + display unification (#2675 core)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

This is a **core-domain** change to the status state model. Apply **tiered rigour**: the `status/` package is load-bearing runtime authority, so treat every edit here as high-rigour (RED-first, no suppression, canonical single-source, full type discipline).

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`,````bash`

---

## Objectives & Success Criteria

**Objective.** Introduce a NEW canonical `Lane.UNINITIALIZED = "uninitialized"` member cleanly, so that `get_wp_lane` returns a **pure `Lane`** (retiring the `Lane | str` union *at its source*), and so that the "which lanes are non-display" rule has **one authority** instead of four inline `is not Lane.GENESIS` checks.

This WP is the **FOUNDATION** for WP06, which updates the behavioral consumers (`worktree_topology`, `done_bookkeeping`, `workflow_executor`, `workspace/context`) that currently compare against the raw `"uninitialized"` string. Do NOT touch those consumers here — WP06 owns them.

This is part of **#2675**. The operator explicitly chose **FULL unification** (a first-class enum member plus a single non-display authority), **not** a pragmatic `coerce-to-Lane` shim at the boundary. Implement the full member; do not band-aid the union away with a local cast.

**Success criteria (all must hold):**

1. `Lane.UNINITIALIZED` exists on the `Lane` StrEnum with value `"uninitialized"` — so pre-existing `== "uninitialized"` equality still holds (StrEnum equality against its `.value`).
2. `Lane.UNINITIALIZED` is documented and behaves as a **non-display, non-transitionable read sentinel**, semantically **distinct** from `Lane.GENESIS` (see semantics below).
3. `import specify_cli.status.transitions` succeeds — the FSM import-time loop over `Lane` does not crash on the new member.
4. `get_wp_lane` returns `Lane.UNINITIALIZED` (a `Lane`, never a bare `str`) on the unseeded path; its annotation is `-> Lane`.
5. `get_all_wp_lanes` is annotated `-> dict[str, Lane]`.
6. Display summaries (lane count maps and display-lane lists) **EXCLUDE** `UNINITIALIZED` — no `"uninitialized": 0` regression appears in any summary.
7. The set of non-display lanes has ONE canonical home; the **five** filter sites (`reducer.py` ×2, `wp_metadata.py`, `tasks_status_view.py`, and the currently-unfiltered `lifecycle.py:119`) consume that authority instead of inlining `is not Lane.GENESIS` (or, for `lifecycle.py`, having no filter at all).
8. `mypy` is clean on the edited `status/` surface; no `# type: ignore`, no `# noqa`, no suppression added.

## Context & Constraints

**Governing docs** — load before editing:

- `.kittify/charter/charter.md` — governing principles (single canonical authority, DDD + tiered rigour, ATDD-first / RED-first).
- `kitty-specs/landing-pass-campsite-followups-01KXKWD7/plan.md` — see **IC-05**.
- `kitty-specs/landing-pass-campsite-followups-01KXKWD7/data-model.md` — see **LN-1**.
- `kitty-specs/landing-pass-campsite-followups-01KXKWD7/research-notes-csf-2670.md` — full trace of the union and the four filter sites.

**Binding constraints:**

- **C-005 (RED-first / ATDD).** Write the failing test FIRST (T040) through the real entry points before touching product code. The RED test must fail for the right reason (member absent / union returned) — capture that.
- **C-001 (charter fix-not-suppress).** Fix the code, never silence the checker. No blanket `# noqa` / `# type: ignore` / per-file ignore additions. Complexity ceiling 15; repeated literals → constants.
- **Tiered rigour (core domain).** `status/` is canonical runtime authority. Every branch/helper you add needs a focused test in THIS WP.
- **Canonical single-source.** The non-display-lane rule becomes ONE authority (T043). Do not leave a fifth inline copy of the check anywhere.

**Verified code facts (as of this mission's base):**

- `src/specify_cli/status/lane_reader.py`:
  - `LEGACY_UNINITIALIZED_SENTINEL: str = "uninitialized"` (~line 19). Documented as the shared sentinel; `status/aggregate.py` imports it. **Keep the symbol** — other modules (WP06/WP07 surfaces) import it.
  - `get_wp_lane(feature_dir, wp_id) -> Lane | str` (~line 50). Returns `LEGACY_UNINITIALIZED_SENTINEL` when the event log EXISTS but is EMPTY (~line 65) OR when the WP is ABSENT from the reduced snapshot (~line 69). Otherwise returns `Lane(wp_state.get("lane", Lane.GENESIS))` (~line 72).
  - `get_all_wp_lanes(feature_dir) -> dict[str, str]` (~line 75) — annotated `str` but ALREADY builds `Lane(...)` values (~line 93); WPs with no events are simply omitted from the dict.
- **CRITICAL SEMANTICS.** `"uninitialized"` (WP absent from snapshot / empty event log) is **DISTINCT** from `Lane.GENESIS = "genesis"` (a WP that IS seeded but sits on an unseeded lane). DO NOT reuse `GENESIS` for the uninitialized path — add a NEW member. The StrEnum value MUST stay `"uninitialized"` so the existing string-equality contract (`lane == "uninitialized"`) survives untouched for the WP06 consumers.
- `Lane` is a `StrEnum` in `src/specify_cli/status/models.py` (~lines 23–49). `GENESIS` is documented there as a non-display, non-transitionable lane.
- **FSM import hazard.** `src/specify_cli/status/transitions.py:44` runs `for lane in Lane: wp_state_for(lane)` **at import time**. `wp_state_for` (in `wp_state.py`) **raises** on any member that has no `_STATE_MAP` entry. Therefore the new member MUST be given a `_STATE_MAP` (and, if the factory path needs it, a `_FACTORY_ALIASES`) entry — otherwise `import specify_cli.status.transitions` crashes for the whole process.
- **Display filter sites** that currently exclude only `GENESIS` and must ALSO exclude `UNINITIALIZED`:
  - `reducer.py:134` — `{lane.value: 0 for lane in Lane if lane is not Lane.GENESIS}`
  - `reducer.py:166` — same idiom
  - `wp_metadata.py:385` — `[lane.value for lane in Lane if lane is not Lane.GENESIS]`
  - `tasks_status_view.py:163` — `for lane in Lane if lane is not Lane.GENESIS`
  - **`lifecycle.py:119` (FIFTH SITE — squad-found)** — `summary={lane.value: 0 for lane in Lane}` builds the summary with **NO genesis filter at all**; it already emits `"genesis": 0` today, and after the new member it will emit `"uninitialized": 0`, violating success criterion #6. This site must ALSO route through the new non-display authority (see T043). It is the reason criterion #6 is a real regression risk, not a hypothetical.
- **`CANONICAL_LANES` parity (squad-found).** `src/specify_cli/status_lanes.py:5-15` defines a hardcoded 9-tuple `CANONICAL_LANES` with **no** `"uninitialized"` (and no `"genesis"`). `tests/status/test_parity.py:812-822` asserts that every non-genesis `Lane` member is present in `CANONICAL_LANES`. Because `UNINITIALIZED` is non-display like `GENESIS`, it must be **EXEMPTED** from that parity assertion (mirror the existing genesis exemption), **NOT** added to `CANONICAL_LANES`. See T046.

**Sequencing within #2675.** This WP is purely additive at the domain layer: a new enum member, a factory-map entry, a single non-display authority, and a loader that now returns that member. It must land and be green **before** WP06, because WP06 migrates the behavioral consumers to compare against `Lane.UNINITIALIZED` (the enum) rather than the `"uninitialized"` string, and relies on `get_wp_lane` already returning a pure `Lane`. The StrEnum-value bridge (member value == `"uninitialized"` == `LEGACY_UNINITIALIZED_SENTINEL`) is what lets WP06's consumers keep passing during the interim — do not break that bridge here.

**Out of scope (WP06 owns these — do NOT edit here):**

- `worktree_topology`, `done_bookkeeping`, `workflow_executor`, `workspace/context`, and any other behavioral consumer that compares a lane against the raw `"uninitialized"` string.
- Deleting `LEGACY_UNINITIALIZED_SENTINEL` — WP06/WP07 still import it. Coordinate purely by keeping the constant's value equal to `Lane.UNINITIALIZED.value`.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

Implement in the listed order. T040 is RED and must be authored and observed failing before T041–T044.

### Subtask T040 (RED) – Failing test for the new member, pure-Lane loader, and FSM import-safety

- **Purpose**: Lock the three foundational contracts before touching product code, per C-005.
- **File (create)**: `tests/specify_cli/status/test_lane_uninitialized.py`
- **Steps**:
  1. Add a test asserting `Lane.UNINITIALIZED.value == "uninitialized"` and that `Lane.UNINITIALIZED == "uninitialized"` (StrEnum equality contract). This RED-fails today with `AttributeError` (member absent).
  2. Add a test that `Lane.UNINITIALIZED is not Lane.GENESIS` and that their values differ (`"uninitialized"` vs `"genesis"`) — pins the distinct-semantics requirement so a future refactor can't collapse them.
  3. Add a test for the **empty-event-log** path: create a feature dir with an event log file that exists but has zero events (mirror the fixture style already used in the `tests/specify_cli/status/` suite — seed via the same helpers/`store` API those tests use; do NOT hand-roll a raw file if a fixture exists). Assert `get_wp_lane(feature_dir, "WP01")` returns `Lane.UNINITIALIZED` and, critically, `isinstance(result, Lane)` is `True` (NOT a bare `str`).
  4. Add a test for the **WP-absent-from-snapshot** path: seed an event log that has events for some *other* WP but none for `"WPZZ"`; assert `get_wp_lane(feature_dir, "WPZZ")` returns `Lane.UNINITIALIZED` and `isinstance(result, Lane)`.
  5. Add an **import-safety** test: `import importlib; importlib.import_module("specify_cli.status.transitions")` (or a plain `import specify_cli.status.transitions`) succeeds without raising. This guards T042 — without the `_STATE_MAP` entry the module crashes at import.
  6. (Recommended) Add a **display-exclusion** assertion so T043 is covered by a behavioral test rather than only structural: after seeding a normal snapshot, assert that a reducer lane-count map (the `reduce`/materialize summary that feeds the board) does NOT contain the `"uninitialized"` key. Reuse whatever public reducer entry point the existing status tests use to obtain the count map; do not reach into private internals if a public path exists.
- **Parallel?**: No — this test file gates the rest of the WP.
- **Notes**: Use realistic, production-shaped WP ids (`WP01`, not `x`). Prefer the existing fixture/helpers in `tests/specify_cli/status/`; if none seed an empty-but-present event log, add a minimal local fixture but route writes through the `store` API, not raw file writes, so the test stays coupled to the real format. Run and CONFIRM it fails for the intended reasons before proceeding; record that in the Activity Log.

### Subtask T041 – Add `Lane.UNINITIALIZED` to the `Lane` StrEnum

- **Purpose**: Introduce the canonical member so the loader can return a real `Lane`.
- **File**: `src/specify_cli/status/models.py`
- **Steps**:
  1. Add `UNINITIALIZED = "uninitialized"` to the `Lane` StrEnum (~lines 23–49), placed alongside `GENESIS` so the "read sentinel / non-display" grouping reads clearly.
  2. Document it in the enum docstring / inline comment as a **NON-DISPLAY, NON-TRANSITIONABLE read sentinel**, returned when a WP is **absent from the snapshot** (no events yet) or the event log is **empty** — explicitly **distinct** from `GENESIS`, which means "seeded WP on an unseeded lane." State the invariant that `UNINITIALIZED` is never persisted to the event log and never appears in a display summary.
  3. Do NOT add it to any transition matrix or any list of user-selectable lanes.
- **Shape (illustrative — match the existing member style, do not copy verbatim):**

  ```python
  class Lane(StrEnum):
      GENESIS = "genesis"          # seeded WP on an unseeded lane (non-display)
      UNINITIALIZED = "uninitialized"  # WP absent from snapshot / empty log — read sentinel, never persisted, non-display, non-transitionable
      PLANNED = "planned"
      # ... unchanged ...
  ```

- **Parallel?**: No — precedes T042/T044.
- **Notes**: Keep StrEnum member values lowercase to match the existing convention. Do not renumber or reorder existing members' values.

### Subtask T042 – FSM import-safety: dedicated `UninitializedState` with EMPTY targets in `wp_state.py`

- **Purpose**: Prevent the import-time crash at `transitions.py:44`, which iterates `for lane in Lane` and calls `wp_state_for(lane)`; a member with no `_STATE_MAP` entry raises. Do this WITHOUT injecting any transition edges and WITHOUT making `UNINITIALIZED` transitionable.
- **File**: `src/specify_cli/status/wp_state.py`
- **Concrete structure (verified)**: `wp_state_for(lane)` (~line 648) does `lane_str = str(lane)` (a StrEnum stringifies to its `.value`, so `str(Lane.UNINITIALIZED) == "uninitialized"`), then `lane_str = _FACTORY_ALIASES.get(lane_str, lane_str)` (~line 643, currently only `{"doing": "in_progress"}`), then `cls = _STATE_MAP.get(lane_str)` (~line 629, keyed by string value, `"genesis": GenesisState` etc.), and **raises `ValueError(f"Unknown lane: {lane_str!r}")`** when `cls is None`. That raise is what would break `transitions.py:44`.
- **⚠️ DO NOT alias `uninitialized → genesis` (this guidance was UNSOUND and is now corrected).** `GenesisState.allowed_targets()` returns `{PLANNED, CANCELED}` (`wp_state.py:248`). `transitions.py:43-48` builds `ALLOWED_TRANSITIONS` from the **same** `for lane in Lane` import-time sweep, doing `edges.add((lane.value, target.value))` for each `target` in that lane's `allowed_targets()`. So aliasing `uninitialized → GenesisState` (or mapping `"uninitialized": GenesisState` directly) would inject the edges `("uninitialized","planned")` and `("uninitialized","canceled")` → `len(ALLOWED_TRANSITIONS)` jumps 29 → 31 → **`tests/status/test_transitions.py:44` (which asserts `== 29`) FAILS**, AND it makes `UNINITIALIZED` transitionable, directly violating the non-transitionable criterion (#2). Reusing GenesisState is therefore wrong on both counts.
- **CORRECT FIX — dedicated state class with empty targets**:
  1. Add a NEW `UninitializedState` class in `wp_state.py`, structured exactly like `GenesisState` (mirror its shape/base class), but whose `allowed_targets()` returns `frozenset()` — **EMPTY**. Empty targets add ZERO edges to `ALLOWED_TRANSITIONS`, so the count stays **29** (`test_transitions.py:44` stays green) AND `UNINITIALIZED` is genuinely non-transitionable (honors criterion #2 and `test_wp_state.py:161`, which pins the current edge/target invariants).
  2. Register it so `wp_state_for(Lane.UNINITIALIZED)` resolves to it: add `"uninitialized": UninitializedState` to `_STATE_MAP` (~line 629). If the factory path also routes through `_FACTORY_ALIASES` (~line 643), ensure the resolution reaches `UninitializedState` (no alias to `"genesis"` — that would re-introduce the edge bug). Without this registration, `transitions.py:44`'s import-time sweep crashes with `ValueError: Unknown lane: 'uninitialized'`.
  3. Add a one-line comment on the class explaining WHY its targets are empty (read sentinel, absent-from-snapshot / empty-log, never transitions out — it is not GENESIS) so a future reader does not "simplify" it back into GenesisState.
  4. Confirm `wp_state_for(Lane.UNINITIALIZED)` returns an `UninitializedState` instance without raising, and that `len(ALLOWED_TRANSITIONS)` is unchanged (still 29).
- **Parallel?**: No — must land with/after T041 and before importing `transitions` succeeds.
- **Notes**: This subtask is **load-bearing** on two axes: (a) skipping the registration makes `import specify_cli.status.transitions` crash at import time; (b) getting the state class wrong (non-empty targets) silently expands the transition matrix and breaks `test_transitions.py:44`. Guards: the T040 import-safety test AND the edge-count invariant. Do NOT add `UNINITIALIZED` to any explicit transition edge in `transitions.py` — it is non-transitionable; the empty-targets state is precisely what keeps it that way.

### Subtask T043 – Canonical non-display-lane authority + rewire the four filter sites

- **Purpose**: Unify the "which lanes are non-display" rule into ONE canonical source (charter single-canonical-authority), and ensure `UNINITIALIZED` is excluded from every display summary — no `"uninitialized": 0` regression.
- **Files**: `src/specify_cli/status/models.py` (define authority); `src/specify_cli/status/reducer.py` (lines ~134, ~166); `src/specify_cli/status/wp_metadata.py` (line ~385); `src/specify_cli/status/lifecycle.py` (line ~119 — **fifth site**); `src/specify_cli/cli/commands/agent/tasks_status_view.py` (line ~163).
- **Steps**:
  1. In `models.py`, introduce a single canonical authority next to the `Lane` enum. Prefer one of:
     - a module constant `NON_DISPLAY_LANES: frozenset[Lane] = frozenset({Lane.GENESIS, Lane.UNINITIALIZED})`, **or**
     - a helper `def is_display_lane(lane: Lane) -> bool: return lane not in NON_DISPLAY_LANES`.
     Pick ONE and use it everywhere; do not ship both a set and a helper that can drift. Whichever you choose, it is the sole definition of "non-display." Illustrative shape:

     ```python
     # models.py — the single source of truth for "which lanes never display"
     NON_DISPLAY_LANES: frozenset[Lane] = frozenset({Lane.GENESIS, Lane.UNINITIALIZED})

     # filter sites become:
     summary = {lane.value: 0 for lane in Lane if lane not in NON_DISPLAY_LANES}
     ```
  2. Rewrite `reducer.py:134` and `reducer.py:166` to build their `{lane.value: 0 ...}` maps by filtering with the new authority (e.g. `if lane not in NON_DISPLAY_LANES` or `if is_display_lane(lane)`) instead of the inline `if lane is not Lane.GENESIS`.
  3. Rewrite `wp_metadata.py:385`'s `[lane.value for lane in Lane if lane is not Lane.GENESIS]` to use the authority.
  4. Rewrite `tasks_status_view.py:163`'s `for lane in Lane if lane is not Lane.GENESIS` to use the authority.
  4b. **Rewrite `lifecycle.py:119` (fifth site).** It currently builds `summary={lane.value: 0 for lane in Lane}` with **NO** filter — so it already emits `"genesis": 0` and will emit `"uninitialized": 0` after T041. Add the non-display filter (`if lane not in NON_DISPLAY_LANES` / `if is_display_lane(lane)`) so BOTH `genesis` and `uninitialized` are excluded, satisfying criterion #6. If you determine this summary intentionally includes `genesis` for a downstream consumer, STOP and record the decision — but the default is to exclude both via the authority, and criterion #6 forbids a `"uninitialized"` key in any summary.
  5. Update the adjacent explanatory comments so they stay truthful: `reducer.py:121` and `reducer.py:164` currently say "Lane.GENESIS is excluded — it is a non-display lane"; extend that prose to name UNINITIALIZED too (both are excluded via the authority).
  6. Leave `wp_metadata.py:388` (`if canonical == Lane.GENESIS.value:`) as-is unless the review shows it also needs to treat UNINITIALIZED — it is a **value-equality guard**, not a display-loop filter, so it is out of this subtask's "four sites." If you determine it must also branch on UNINITIALIZED, do so explicitly and add a test; otherwise note the decision in the Activity Log.
  7. Grep the repo for any remaining `is not Lane.GENESIS` / `== Lane.GENESIS`-style inline display filters in these owned files and confirm none survive as a competing definition. (Consumers OUTSIDE the owned files are WP06's problem — do not edit them, but note them in the Activity Log if you spot a fifth site so WP06 can fold it.)
- **Parallel?**: No — depends on T041 (member) existing.
- **Notes**: If `tasks_status_view.py` or `wp_metadata.py` cannot import from `models.py` without a cycle, keep the authority in `models.py` (the enum's home) and import it — `models.py` is the lowest layer and should not import back. If a genuine import cycle appears, STOP and record it; do not paper over it with a duplicated local set (that would recreate the very drift this subtask removes).

### Subtask T044 – Loader returns pure `Lane`; retighten annotations

- **Purpose**: Retire the `Lane | str` union at its source so callers receive a `Lane` and mypy can enforce it.
- **File**: `src/specify_cli/status/lane_reader.py`
- **Steps**:
  1. Change both unseeded returns in `get_wp_lane` (the empty-event-log branch ~line 65 and the WP-absent branch ~line 69) to return `Lane.UNINITIALIZED` instead of `LEGACY_UNINITIALIZED_SENTINEL`.
  2. Change `get_wp_lane`'s return annotation from `Lane | str` to `-> Lane`. Update its docstring to say it returns `Lane.UNINITIALIZED` for the unseeded/absent case.
  3. Change `get_all_wp_lanes`'s annotation from `-> dict[str, str]` to `-> dict[str, Lane]` (its body already yields `Lane(...)` values; missing WPs remain omitted — the docstring note that callers treat missing keys as uninitialized stays accurate, but consider recommending `Lane.UNINITIALIZED` in the prose).
  4. **Keep** `LEGACY_UNINITIALIZED_SENTINEL` defined and exported. WP06/WP07 surfaces still import it. Preserve the invariant that `LEGACY_UNINITIALIZED_SENTINEL == Lane.UNINITIALIZED.value` — optionally re-express the constant as `LEGACY_UNINITIALIZED_SENTINEL: str = Lane.UNINITIALIZED.value` so the two can never drift, but do NOT remove the name.
  5. Do not change the `CanonicalStatusNotFoundError` raise path (absent event log) — that hard-fail is unchanged.
- **Parallel?**: No — final step; depends on T041 (member) and benefits from T042 (import safety) already in place.
- **Notes**: Because `Lane` is a StrEnum, returning `Lane.UNINITIALIZED` preserves `== "uninitialized"` for any consumer still doing string comparison, so WP06's consumers keep working until WP06 migrates them. That is the deliberate bridge — do not break it.

### Subtask T045 – Update pre-existing lane-roster tests broken by the new member (squad-found)

- **Purpose**: Adding an enum member ripples into every test that derives an "all non-genesis lanes" expectation or pins a hardcoded lane roster. These tests fail (or must extend their roster) the moment `Lane.UNINITIALIZED` exists. This subtask owns updating them so the suite goes green for the RIGHT reason (member legitimately present), not by weakening an assertion.
- **Files (verified touch-points — line numbers are as-of-base hints, not exact contracts)**:
  - `tests/status/test_models.py:62` — hardcoded 10-lane roster expectation → becomes 11 (extend the roster, or exclude `uninitialized` if the roster is meant to be "display lanes only" — verify intent).
  - `tests/status/test_models.py:279` — second lane-set assertion in the same file; re-check.
  - `tests/status/test_reducer.py:64` — reducer lane-count / roster expectation.
  - `tests/status/test_parity.py:569-575` — parity lane-set derivation (distinct from the `CANONICAL_LANES` block owned by T046).
  - `tests/status/test_transitions.py:44` — asserts `len(ALLOWED_TRANSITIONS) == 29`. **Kept green by T042's empty-targets `UninitializedState`** (zero new edges). This is a VERIFY, not an edit — if it went red, T042 was done wrong (do not "fix" it by bumping the number).
  - `tests/specify_cli/status/test_in_review_display.py:219` — display-lane expectation.
  - `tests/specify_cli/status/test_progress.py:87` — progress/roster expectation.
  - `tests/specify_cli/status/test_wp_metadata.py:210-211` — metadata display-lane list.
  - `tests/specify_cli/cli/commands/agent/test_tasks_status_view.py:96,307` — status-view lane roster (two sites).
  - `tests/specify_cli/cli/commands/agent/test_tasks_status_cmd_seam.py:79` — status command seam roster.
  - `tests/integration/test_dashboard_counters.py:29` — dashboard counter roster.
  - `tests/test_dashboard/test_scanner.py:1099` — scanner lane expectation.
- **Steps**:
  1. For each site, determine whether it is a **hard fail** (exact-set / exact-count assertion) or a **tolerant superset** (membership check that still passes). Update only the ones that actually break.
  2. Where the expectation is "all non-display lanes," add `uninitialized` to the exclusion set **mirroring the existing `genesis` exemption** — do not add it to a display roster.
  3. Where the expectation is a full roster of enum members, extend it to include `uninitialized` (e.g. 10 → 11).
  4. Re-run each touched test file and confirm green for the intended reason.
- **Parallel?**: No — depends on T041 (member) existing; run after T041–T044 so the product side is settled.
- **Notes**: Whether each is a hard fail or a tolerant superset **varies** — the implementer VERIFIES each and updates only those that break; do not blanket-edit. **Ownership-map leeway** applies for any test file not listed in `owned_files` — no other WP owns these lane-roster tests, so rationale-backed edits outside the owned set are acceptable; record any such edit in the Activity Log.

### Subtask T046 – Exempt `UNINITIALIZED` from `CANONICAL_LANES` parity (squad-found)

- **Purpose**: `tests/status/test_parity.py:812-822` asserts every non-genesis `Lane` member appears in `CANONICAL_LANES` (`src/specify_cli/status_lanes.py:5-15`, a hardcoded 9-tuple with neither `"genesis"` nor `"uninitialized"`). Because `UNINITIALIZED` is a non-display read sentinel like `GENESIS`, it must be **EXEMPTED** from that parity check — **NOT** added to `CANONICAL_LANES`.
- **Files**: `tests/status/test_parity.py` (the parity assertion at ~812-822); reference `src/specify_cli/status_lanes.py` (do NOT add `uninitialized` to the 9-tuple).
- **Steps**:
  1. Locate the parity loop that skips `Lane.GENESIS` when asserting membership in `CANONICAL_LANES`.
  2. Extend the exemption so `Lane.UNINITIALIZED` is skipped exactly like `Lane.GENESIS` (both are non-display / non-canonical for the display roster).
  3. Do **NOT** modify `status_lanes.py`'s `CANONICAL_LANES` tuple — it is the 9-lane DISPLAY roster and must not gain a sentinel. If you find yourself editing the tuple, stop: that is the wrong fix.
  4. Confirm `tests/status/test_parity.py` passes with the new member present and the tuple unchanged.
- **Parallel?**: No — depends on T041 (member) existing.
- **Notes**: This mirrors the existing genesis carve-out precisely. Adding `uninitialized` to `CANONICAL_LANES` would leak the sentinel into the display roster and reintroduce the very `"uninitialized": 0`-style regression T043 removes — reference `status_lanes.py:5-15` to confirm the tuple's shape before touching the test.

## Test Strategy

- **RED gate**: author `tests/specify_cli/status/test_lane_uninitialized.py` first; observe it fail with member-absent / union-returned reasons before implementing.
- **⚠️ WIDE GREEN GATE (squad-found — the narrow gate was a false-green trap).** The hardest breaks from this change live in `tests/status/` (edge-count invariant, `CANONICAL_LANES` parity, lane-roster expectations), which the old `tests/specify_cli/status/`-only gate did NOT run → the WP would go false-green locally then red on CI. The GREEN gate for this WP is ALL of the following, all passing:
  - `uv run pytest tests/specify_cli/status/test_lane_uninitialized.py -q` — all new tests pass.
  - `uv run pytest tests/status/ -q` — the FSM edge-count, parity, and lane-roster suites (where the hardest breaks land).
  - `uv run pytest tests/specify_cli/status/ -q` — no regression in the surrounding status suite.
  - `uv run pytest tests/specify_cli/cli/commands/agent/ -q` — status-view / command-seam lane rosters.
  - `uv run pytest tests/integration/test_dashboard_counters.py -q` — dashboard counter roster.
  - `uv run pytest tests/test_dashboard/test_scanner.py -q` — scanner lane expectations.
- **Type discipline**: `uv run mypy src/specify_cli/status/lane_reader.py src/specify_cli/status/models.py src/specify_cli/status/wp_state.py src/specify_cli/status/reducer.py src/specify_cli/status/wp_metadata.py src/specify_cli/status/lifecycle.py` — clean, zero errors/warnings, no new suppressions. (Run `uv run mypy` broadly if editing more surfaces.)
- **Import safety (explicit)**: `uv run python -c "import specify_cli.status.transitions"` exits 0.
- **Display exclusion (explicit)**: confirm no reducer / metadata / status-view summary contains a `"uninitialized"` key (covered by the T040 display-exclusion assertion; spot-check manually if unsure).
- **Lint**: `uv run ruff check src/specify_cli/status/ src/specify_cli/cli/commands/agent/tasks_status_view.py tests/specify_cli/status/test_lane_uninitialized.py`.
- **Data note**: use production-shaped WP ids and the `store` write API for fixtures — no placeholder-shaped ids, no raw file writes when a fixture/helper exists.

## Risks & Mitigations

- **Import crash (highest risk).** Omitting the `_STATE_MAP` entry (T042) makes `import specify_cli.status.transitions` crash at import, taking down large swaths of the CLI. Mitigation: the T040 import-safety test; run it early and keep it green.
- **Display regression.** Skipping or half-applying T043 leaks `"uninitialized": 0` into board/summary output. Mitigation: single authority + the T040 display-exclusion assertion; grep ALL FIVE sites (`reducer.py` ×2, `wp_metadata.py`, `tasks_status_view.py`, and the unfiltered `lifecycle.py:119`).
- **Transition-matrix expansion (squad-found, HIGH).** Aliasing `uninitialized → genesis` in the FSM (the original, now-corrected T042 guidance) injects `("uninitialized","planned")` + `("uninitialized","canceled")` edges → `len(ALLOWED_TRANSITIONS)` 29 → 31, breaking `test_transitions.py:44`, and makes `UNINITIALIZED` transitionable (violates criterion #2). Mitigation: the dedicated `UninitializedState` with EMPTY `allowed_targets()` (T042) — zero new edges, non-transitionable. Verify the edge count stays 29.
- **`CANONICAL_LANES` parity break (squad-found).** The new member trips `test_parity.py:812-822`. Mitigation: EXEMPT `UNINITIALIZED` in the parity test like `GENESIS` (T046) — never add it to the `status_lanes.py` 9-tuple.
- **Collapsing UNINITIALIZED into GENESIS.** Tempting because both are non-display, but they carry distinct meaning (absent-from-snapshot vs seeded-unseeded-lane). Mitigation: the T040 `is not Lane.GENESIS` + distinct-value test pins them apart. Do not reuse GENESIS.
- **Deleting a symbol WP06/WP07 consume.** Removing `LEGACY_UNINITIALIZED_SENTINEL` breaks imports in modules this WP does not own. Mitigation: keep the constant; tie its value to `Lane.UNINITIALIZED.value`.
- **Scope creep into WP06.** Editing `worktree_topology` / `done_bookkeeping` / `workflow_executor` / `workspace/context` here creates ownership overlap and merge conflict. Mitigation: those are explicitly out of scope; note any fifth display-filter site for WP06 rather than fixing it.
- **Import cycle when defining the authority.** If a filter-site module cannot import from `models.py` cleanly, do NOT duplicate the set locally. Mitigation: keep the authority in `models.py` (lowest layer); if a real cycle surfaces, stop and record it.
- **Sizing (squad-found).** This WP is **medium-sized, NOT mechanical** — a new `Lane` member ripples through the transition matrix (T042), `CANONICAL_LANES` parity (T046), a fifth unfiltered display site (T043/`lifecycle.py`), and **~12 lane-roster tests** (T045). Treat it as such: own every affected surface, or use rationale-backed ownership-map leeway (no other WP owns these lane-roster/parity tests). Do not under-scope it as "add one enum member."

## Review Guidance

Reviewer (`reviewer-renata`) — verify:

- `Lane.UNINITIALIZED` exists, value is `"uninitialized"`, documented as non-display / non-transitionable, and is **distinct** from `GENESIS` (not a reuse).
- FSM is import-safe: `import specify_cli.status.transitions` succeeds; `wp_state_for(Lane.UNINITIALIZED)` does not raise; a **dedicated `UninitializedState` with EMPTY `allowed_targets()`** is registered in `_STATE_MAP` (NOT an alias to `GenesisState`); `len(ALLOWED_TRANSITIONS)` is unchanged at 29 (`test_transitions.py:44` green); `UNINITIALIZED` is non-transitionable.
- The non-display authority is a **single** definition; all **five** owned filter sites (incl. `lifecycle.py:119`) consume it; no inline `is not Lane.GENESIS` display check survives in owned files; no `"uninitialized"` key leaks into any summary.
- `UNINITIALIZED` is EXEMPTED from `CANONICAL_LANES` parity (`test_parity.py`) like `GENESIS`, and was NOT added to the `status_lanes.py` 9-tuple (T046).
- The ~12 pre-existing lane-roster tests (T045) were updated for the RIGHT reason (member legitimately present / non-display exemption mirrored), not by weakening assertions; the WIDE green gate (incl. `tests/status/`, `tests/specify_cli/cli/commands/agent/`, dashboard counters, scanner) all pass.
- `get_wp_lane` returns a pure `Lane` (annotation `-> Lane`, both unseeded branches return `Lane.UNINITIALIZED`); `get_all_wp_lanes` is `-> dict[str, Lane]`.
- `LEGACY_UNINITIALIZED_SENTINEL` is retained and equals `Lane.UNINITIALIZED.value`; no out-of-scope consumers were edited.
- RED-first honored (T040 landed and observed failing first); mypy/ruff clean; no suppressions added; new branches/helpers carry focused tests in this WP.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Format**:

```
- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>
```

**Example (correct chronological order)**:

```
- 2026-01-12T10:00:00Z – system – Prompt created
- 2026-01-12T10:30:00Z – claude – Started implementation
- 2026-01-12T11:00:00Z – codex – Implementation complete, ready for review
- 2026-01-12T11:30:00Z – claude – Review passed, all tests passing  ← LATEST (at bottom)
```

**Common mistakes (DO NOT DO THIS)**:

- Adding new entry at the top (breaks chronological order)
- Using future timestamps (causes acceptance validation to fail)
- Inserting in middle instead of appending to end

**Why this matters**: The acceptance system reads the LAST activity log entry as the current state. If entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:

- 2026-07-15T22:32:40Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task <WPID> --to <status>` to change WP status.

### Optional Phase Subdirectories

For large features, organize prompts under `tasks/` to keep bundles grouped while maintaining lexical ordering.
- 2026-07-15T23:17:15Z – claude:sonnet:python-pedro:implementer – shell_pid=3622117 – Assigned agent via action command
- 2026-07-15T23:43:52Z – claude:sonnet:python-pedro:implementer – shell_pid=3622117 – T040-T044 marked done via mark-status. T045 (update ~12 lane-roster tests) and T046 (exempt UNINITIALIZED from CANONICAL_LANES parity) were fully implemented and verified green, but mark-status could not tag them: tasks.md's Subtask Index table for WP05 only lists T040-T044 (the squad-found T045/T046 additions in the WP prompt file were never back-synced to tasks.md's master table) -- upstream tracking gap, not a WP05 implementation gap.
- 2026-07-15T23:44:06Z – claude:sonnet:python-pedro:implementer – shell_pid=3622117 – Lane.UNINITIALIZED member + dedicated UninitializedState (empty allowed_targets, ALLOWED_TRANSITIONS stays 29) + NON_DISPLAY_LANES single authority routed through all 5 filter sites (reducer x2, wp_metadata, tasks_status_view, lifecycle) + get_wp_lane/get_all_wp_lanes retightened to pure Lane. RED-first (test_lane_uninitialized.py, 10 tests, observed AttributeError before T041). Wide gate green: tests/status + tests/specify_cli/status + tests/specify_cli/cli/commands/agent + dashboard_counters + scanner = 2614 passed. mypy/ruff clean, no suppressions. T045/T046 fully done but tasks.md outline table lacks their rows (upstream sync gap, logged in history).
- 2026-07-15T23:44:57Z – claude:opus:reviewer-renata:reviewer – shell_pid=3761962 – Started review via action command
- 2026-07-15T23:52:32Z – user – shell_pid=3761962 – Review passed: Lane.UNINITIALIZED landed as full unification (not a coerce shim). RED genuine (member absent at base -> AttributeError). UninitializedState.allowed_targets()=frozenset() -> ALLOWED_TRANSITIONS==29 held (test_transitions green). Registered in _STATE_MAP so 'import status.transitions' is safe. CANONICAL_LANES untouched; parity test exempts UNINITIALIZED mirroring GENESIS. All FIVE display-filter sites (reducer x2, wp_metadata, tasks_status_view, lifecycle fifth-site) route through single NON_DISPLAY_LANES authority; no inline 'is not Lane.GENESIS' display idiom remains; no 'uninitialized':0 leak. get_wp_lane -> pure Lane, get_all_wp_lanes -> dict[str,Lane]. Semantics distinct from GENESIS (tested). Green gate passes (10 apparent fails were reviewer's SPEC_KITTY_SYNC_MINIMAL_IMPORT env var, verified green without it). mypy: sole error is pre-existing progress.py to_dict no-any-return (confirmed identical at base, untouched by WP). ruff clean, no new suppressions. Leeway edits (progress.py weight, status/__init__ re-export) owned by no other WP and test-backed. Anti-pattern checklist all PASS.
