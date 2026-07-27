---
work_package_id: WP05
title: record-analysis self-bookkeeping allowlist + in-mission meta-reader sweep
dependencies:
- WP02
- WP03
- WP04
requirement_refs:
- FR-003
- FR-005
tracker_refs:
- '#2102'
- '#2100'
planning_base_branch: feat/gate-read-surface-completion
merge_target_branch: feat/gate-read-surface-completion
branch_strategy: Planning artifacts for this mission were generated on feat/gate-read-surface-completion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/gate-read-surface-completion unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
phase: Phase 1 - Gate-read spine (Lane A)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "4118521"
history:
- at: '2026-06-24T08:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/artifacts.py
create_intent:
- tests/mission_runtime/test_self_bookkeeping_allowlist.py
- tests/specify_cli/test_meta_reader_sweep.py
execution_mode: code_change
model: ''
owned_files:
- src/mission_runtime/artifacts.py
- tests/mission_runtime/test_self_bookkeeping_allowlist.py
- tests/specify_cli/test_meta_reader_sweep.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – record-analysis self-bookkeeping allowlist + in-mission meta-reader sweep

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on
`authoritative_surface: src/mission_runtime/artifacts.py`.

---

## Objective

Two concerns:
1. **Self-bookkeeping allowlist (FR-003, #2102)**: spec-kitty's own bookkeeping files
   (`meta.json`, `.kittify/encoding-provenance/global.jsonl`) currently classify
   `kind=None` → not allowlisted → the record-analysis dirty-tree preflight **falsely
   blocks**. Add a **self-bookkeeping allowlist**, kept **SEPARATE** from the coord-residue
   partition (so "stale primary spec.md = real dirt" still holds).
2. **In-mission meta-reader sweep (FR-005, #2100, in-mission scope only)**: route the
   residual inline `json.loads(meta…read_text())` reads in the **modules this mission
   touched** (mission.py / tasks.py / acceptance) through the canonical `load_meta` adapter.
   The full ~62-site backlog beyond touched modules stays **deferred** (Out of Scope).

## Context & Constraints

Ground truth — read before editing:
- [spec.md](../spec.md) FR-003 (allowlist, distinct from partition), FR-005 (sweep,
  in-mission only); Scenario 3; Out of Scope (62-site backlog deferred).
- [plan.md](../plan.md) IC-05 (allowlist), IC-06 (sweep).
- [data-model.md](../data-model.md) "Self-bookkeeping allowlist" table.
- [contracts/gate-read-seam.md](../contracts/gate-read-seam.md) G-5 (allowlist DISJOINT from
  coord-residue partition; stale primary spec.md remains non-allowlisted).
- [research.md](../research.md) Decision 4 (FR-003 is an allowlist concern, NOT a seam-read —
  the one place the spec was conceptually mis-grouped).

Live-verified:
- `_COORD_RESIDUE_FILENAMES` at `artifacts.py:113` (maps residue filenames → kind);
  `_COORD_RESIDUE_DIRS` follows. The self-bookkeeping allowlist goes **adjacent** but is a
  DISTINCT set — NOT folded into the coord-residue partition.
- `ANALYSIS_REPORT` is a COORD-partition kind (`artifacts.py:109`) — record-analysis is NOT a
  planning-seam read; this is purely an allowlist gap.

**The invariant (G-5, debbie's hazard)**: a stale **primary** `spec.md` is still "real dirt"
(NOT allowlisted). The self-bookkeeping allowlist must contain ONLY spec-kitty's own
metadata (`meta.json`, provenance jsonl), not planning artifacts. Conflating the two sets is
the failure mode to avoid.

**Shared `record_analysis` (mission.py) + touched modules**: WP05 depends on WP02/WP03/WP04
so the meta-reader sweep edits land AFTER those WPs have re-pointed their reads (the "touched
set" is defined by WP02-04 — IC-06 depends-on IC-02..05). The allowlist itself lives in
`artifacts.py` (WP05-owned exclusively). The sweep's edits into mission.py/tasks.py/acceptance
are well-justified out-of-map edits, serialized last in the lane.

**Negative scope**: do NOT extend the sweep beyond the touched modules (the 62-site backlog
is deferred — C / Out of Scope). Do NOT fold the allowlist into the coord-residue partition.

## Branch Strategy

- **Strategy**: `shared-lane` (Lane A; `artifacts.py` exclusive + serialized sweep edits)
- **Planning base branch**: `feat/gate-read-surface-completion`
- **Merge target branch**: `feat/gate-read-surface-completion`

> WP05 OWNS `artifacts.py`. It depends on WP02/WP03/WP04 so the in-mission meta-sweep edits
> the already-re-pointed touched modules (out-of-map, serialized last). This also serializes
> the shared `record_analysis` function (WP04 collapse first, WP05 allowlist after).

## Subtasks & Detailed Guidance

### Subtask T018 – Add the self-bookkeeping allowlist (DISTINCT set)

- **Purpose**: Allowlist `meta.json` + provenance jsonl so the dirty-tree preflight stops
  falsely blocking (FR-003).
- **Files**: `src/mission_runtime/artifacts.py` (adjacent to `_COORD_RESIDUE_FILENAMES`, `:113`).
- **Steps**:
  1. Add a module-level frozenset/dict, e.g.:
     ```python
     _SELF_BOOKKEEPING_FILENAMES: frozenset[str] = frozenset(
         {
             "meta.json",
             "global.jsonl",  # .kittify/encoding-provenance/global.jsonl
         }
     )
     ```
     with a comment citing FR-003 / data-model.md / G-5 stating this set is DISJOINT from
     the coord-residue partition and contains ONLY spec-kitty's own metadata.
  2. If the provenance path needs path-suffix matching (`.kittify/encoding-provenance/global.jsonl`)
     rather than bare filename, model it precisely so an unrelated `global.jsonl` elsewhere is
     not over-allowlisted. Prefer matching the full relative suffix.
- **Notes**: Keep it SEPARATE from `_COORD_RESIDUE_FILENAMES` (do NOT add these keys there) —
  that set drives coord-residue classification, a different concern.

### Subtask T019 – Wire the allowlist into the dirty-tree preflight classification

- **Purpose**: The preflight must treat self-bookkeeping files as allowlisted (not dirt).
- **Files**: `src/mission_runtime/artifacts.py` (the classification function that today
  returns `kind=None` for these files) + the record-analysis dirty-tree preflight call site.
- **Steps**:
  1. Find the classifier that maps a working-tree path → kind/disposition (the one returning
     `kind=None` for `meta.json`). Add a branch: if the path matches
     `_SELF_BOOKKEEPING_FILENAMES`, classify as **self-bookkeeping (allowlisted)** — a NEW
     disposition distinct from coord-residue.
  2. Ensure the record-analysis dirty-tree preflight consults this disposition and does NOT
     block on a self-bookkeeping file. Trace from `record_analysis` (mission.py) to the
     preflight check.
  3. Preserve the invariant: a primary `spec.md` (planning kind, NOT in the allowlist)
     remains "real dirt" → still blocks.
- **Notes**: This is the WP04-coordination point in `record_analysis` — WP04 collapsed the
  read leg; WP05 wires the allowlist disposition. Serialize behind WP04 (dependency).

### Subtask T020 – In-mission meta-reader sweep (touched modules only)

- **Purpose**: Route residual inline `json.loads(meta…read_text())` reads in the touched
  modules through the canonical `load_meta` adapter (FR-005).
- **Files**: `src/specify_cli/cli/commands/agent/mission.py`,
  `src/specify_cli/cli/commands/agent/tasks.py`, `src/specify_cli/acceptance/__init__.py`
  (out-of-map sweep edits, serialized last).
- **Steps**:
  1. Grep the THREE touched modules for inline `json.loads(... "meta.json" ... .read_text())`
     patterns. For each, replace with `load_meta(<dir>, ...)` (the canonical adapter — confirm
     its import path; the write-side mission used `load_meta` from the canonical module).
  2. Do NOT extend beyond these three modules. If a sweep target is in an untouched module,
     leave it (deferred — Out of Scope) and note it for the #2100 follow-up.
  3. Keep behavior identical — `load_meta` is a drop-in for the inline read.
- **Notes**: This is the in-mission slice of #2100. The full ~62-site backlog is deferred;
  record the deferred sites in the activity log for the follow-up.

### Subtask T021 – Red-first tests: allowlist + sweep

- **Purpose**: Prove the allowlist stops the false block AND keeps stale-spec dirt blocking;
  prove the sweep routes through `load_meta`.
- **Files**: new `tests/mission_runtime/test_self_bookkeeping_allowlist.py` and
  `tests/specify_cli/test_meta_reader_sweep.py`.
- **Steps (red-first)**:
  1. Allowlist test: a working tree containing `meta.json` + `.kittify/encoding-provenance/global.jsonl`
     — assert record-analysis dirty-tree preflight does NOT block (drive the real preflight /
     `record_analysis` entry point). Assert a tree with a stale primary `spec.md` DOES still
     block (the invariant — G-5). Prove red: pre-fix the meta.json tree blocks (RED).
  2. Sweep test: contract-pin that the touched modules import/use `load_meta` for meta reads
     (assert zero inline `json.loads(...meta...read_text())` remains in the three modules via
     an AST/source scan). Prove red: pre-sweep the inline reads exist.
  3. Production-shaped meta.json fixtures (real ULID `mission_id`, full meta shape — use the
     canonical mission factory, NOT a hand-built dict).

## Test Strategy

- `pytest tests/mission_runtime/test_self_bookkeeping_allowlist.py tests/specify_cli/test_meta_reader_sweep.py -q`.
- Red-first evidence for both (the false-block RED; the inline-read-present RED).
- `ruff check src/mission_runtime/artifacts.py` + `mypy` — zero issues, no suppressions.

## Definition of Done

- [ ] `_SELF_BOOKKEEPING_FILENAMES` (or equivalent) added, DISJOINT from the coord-residue
  partition; precise path matching for the provenance jsonl.
- [ ] Dirty-tree preflight classifies self-bookkeeping files as allowlisted (new disposition);
  record-analysis no longer falsely blocks on `meta.json`/provenance.
- [ ] Invariant preserved: a stale primary `spec.md` remains non-allowlisted ("real dirt").
- [ ] In-mission meta-reader sweep: the three touched modules route meta reads through
  `load_meta`; deferred sites recorded for #2100 follow-up.
- [ ] Red-first allowlist + sweep tests green; proven RED pre-fix; production-shaped meta.json
  (canonical factory).
- [ ] ruff + mypy clean; sweep out-of-map edits recorded with rationale; WP04 coordination noted.

## Risks & Mitigations

- **Conflating allowlist with coord-residue partition (G-5 hazard)**: Mitigation: a SEPARATE
  set + a SEPARATE disposition; the stale-spec-is-dirt test pins the invariant.
- **Over-allowlisting `global.jsonl`**: Mitigation: match the full relative path suffix, not
  the bare filename.
- **Scope creep on the sweep**: Mitigation: strictly the three touched modules; deferred sites
  logged, not edited.
- **Shared `record_analysis`/touched modules**: Mitigation: depends-on WP02/WP03/WP04;
  serialized last.

## Review Guidance

- Confirm the allowlist is a DISTINCT set/disposition — NOT folded into `_COORD_RESIDUE_FILENAMES`.
- Confirm the stale-primary-`spec.md`-still-blocks invariant test exists and passes (G-5).
- Confirm the sweep touched ONLY the three in-mission modules; deferred sites are logged.
- Confirm meta.json fixtures are production-shaped via the canonical factory (not hand-built).

## Activity Log

- 2026-06-24T08:00:00Z – system – Prompt created.
- 2026-06-24T16:12:33Z – user – Lane allocator broken (divergent bases); implementing directly on feat (deps integrated 32eb6df89/fd4588c86)
- 2026-06-24T16:23:57Z – claude – WP05 code c8ee1bd9f on feat (direct, allocator bypassed); status from main
- 2026-06-24T16:23:58Z – claude:opus:reviewer-renata:reviewer – shell_pid=4118521 – Started review via action command
- 2026-06-24T16:28:05Z – user – shell_pid=4118521 – Review passed: FR-003 self-bookkeeping allowlist + FR-005 meta-reader guard. G-5 verified by reviewer: stale primary spec.md still blocks (test_preflight_still_blocks_on_stale_primary_spec dirties meta.json+global.jsonl AND spec.md, still raises Exit). FR-003 non-vacuity proven RED: reverting the preflight drop blocks on dirty meta.json+global.jsonl; restored byte-clean. Over-allowlist guard real (suffix-anchored, unrelated global.jsonl rejected). Allowlist DISJOINT from _COORD_RESIDUE sets; ANALYSIS_REPORT stays coord kind. FR-005 AST guard non-vacuity proven RED: injected rogue json.loads(meta_path.read_text()) into tasks.py flagged at line 4658; synthetic arms real; touched modules route through load_meta. ruff clean; mypy artifacts.py/__init__ clean; mission.py 3 [no-any-return] baseline confirmed pre-existing on parent commit (lines shifted +8). 12/12 tests pass.
