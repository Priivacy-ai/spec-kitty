---
work_package_id: WP06
title: Consolidate missions-root path hardcodes + Gate 4 (mission-wide)
dependencies: []
requirement_refs:
- FR-004
- FR-007
planning_base_branch: feat/charter-sole-door-bypass-closure
merge_target_branch: feat/charter-sole-door-bypass-closure
branch_strategy: Planning artifacts for this mission were generated on feat/charter-sole-door-bypass-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-sole-door-bypass-closure unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
- T040
phase: Phase 2 - Bypass closure
history:
- at: '2026-08-03T14:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
- at: '2026-08-03T15:00:00Z'
  actor: system
  action: Post-tasks squad restructure - absorbed the former WP09 Gate 4 (it only ever guarded this WP's own surface, per paula-patterns finding); noted 3 additional undiscovered missions-root duplicates found by reviewer-renata as an explicit residual, not silently fixed or hidden
agent_profile: python-pedro
authoritative_surface: src/charter/activation/mission_type_profile_repository.py
create_intent:
- tests/charter/test_missions_root_authority.py
- tests/architectural/test_charter_sole_door_hardcoded_paths.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/activation/mission_type_profile_repository.py
- src/specify_cli/runtime/home.py
- tests/charter/test_missions_root_authority.py
- tests/architectural/test_charter_sole_door_hardcoded_paths.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP06 – Consolidate missions-root path hardcodes

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (implementer role, claude agent) before parsing
the rest of this prompt.

---

## ⚠️ IMPORTANT: Review Feedback

Check `review_ref` in the event log before starting. Address all feedback; log changes in the Activity Log.

---

## Objectives & Success Criteria

Retarget the 3 duplicate missions-root hardcodes onto one promoted authority (FR-004). **This FR's original
framing changed during planning — read the Context section before starting.**

**Success criteria**:
- `builtin_missions_root()` becomes a thin delegate to `MissionTemplateRepository.default_missions_root()`,
  not a second co-equal authority.
- `runtime/home.py`'s `dev_roots` fallback tuple calls the same promoted authority.
- An equality regression test proves both retarget correctly.
- The PR description states explicitly that full convergence with `doctrine.pack_paths.built_in_dir` still
  awaits `#3091` — this WP does NOT claim that convergence.

## Context & Constraints

- **Do not** retarget onto `doctrine.pack_paths.built_in_dir` — `pack_paths` has no `missions/` content
  directory today (confirmed in `research.md` D1); that only exists after the deferred `#3091` relocation.
- `MissionTemplateRepository.default_missions_root()` (`src/doctrine/missions/repository.py:98`) is already
  correctly implemented (`importlib.resources`-based, wheel-safe) — this is the promotion target, and this
  WP does NOT modify that file.
- `builtin_missions_root()` was itself previously promoted as a shared authority (WP06/#2668 — referenced in
  comments at `charter/action_grain.py:203-204` and `charter/mission_type_profiles.py:646-647`) — this WP
  makes it a delegate, not a rival authority. Existing callers of `builtin_missions_root()` are unaffected
  by making it a delegate (same return value, different implementation).
- `home.py`'s retarget introduces a function-local import of a doctrine-layer class — this matches the
  file's own existing pattern at `home.py:49` (also function-local). Note this in T025's PR-description
  addition as a residual risk sharing `#2986`'s blind spot, not a silently different shape.
- `home.py`'s `importlib.resources` lookup step (lines 97-104, preceding the `dev_roots` fallback) is a
  fourth resolution path for the same root and is explicitly **out of scope** — only the `dev_roots` tuple is
  retargeted.
- Independent of WP01-05 — no dependency, can run in parallel.

## Branch Strategy

- **Strategy**: lane-per-WP (normalized by `finalize-tasks`)
- **Planning base branch**: feat/charter-sole-door-bypass-closure
- **Merge target branch**: feat/charter-sole-door-bypass-closure

## Subtasks & Detailed Guidance

### Subtask T022 – Make `builtin_missions_root()` a thin delegate

- **Purpose**: Close one of the 3 duplicate hardcodes, keep existing callers unaffected.
- **Steps**: Replace `builtin_missions_root()`'s body (currently
  `Path(__file__).resolve().parents[1]/"doctrine"/"missions"`) with
  `return MissionTemplateRepository.default_missions_root()`. Keep the function's signature and name
  unchanged — existing callers (`action_grain.py`, `mission_type_profiles.py`, others) must not need
  changes.
- **Files**: `src/charter/activation/mission_type_profile_repository.py`.
- **Parallel?**: Yes.

### Subtask T023 – Retarget `home.py`'s `dev_roots` fallback

- **Purpose**: Close the second duplicate hardcode.
- **Steps**: In `get_package_asset_root()`, replace the `dev_roots` tuple's literal missions-root entry
  (lines 107-108) with a call to `MissionTemplateRepository.default_missions_root()`. Leave the
  `importlib.resources` lookup step preceding it (lines 97-104) untouched — that's a different resolution
  path, explicitly out of scope.
- **Files**: `src/specify_cli/runtime/home.py`.
- **Parallel?**: Yes.

### Subtask T024 – Equality regression test

- **Purpose**: Non-fakeable proof both retargeted sites resolve identically to the promoted authority.
- **Steps**: Assert `builtin_missions_root() == MissionTemplateRepository.default_missions_root()` and that
  `home.py`'s retargeted `dev_roots` entry resolves to the same path.
- **Files**: `tests/charter/test_missions_root_authority.py` (new).
- **Parallel?**: No — depends on T022, T023.

### Subtask T025 – Document the residual risk and deferred convergence in the PR description

- **Purpose**: NFR-004 requires this be stated explicitly, not implied away.
- **Steps**: Add a paragraph to the PR description (or a dedicated section in the mission tracer file) that
  states: (a) `home.py`'s function-local doctrine import matches an existing pattern in the same file and
  shares `#2986`'s blind spot — named, not hidden; (b) full convergence onto `doctrine.pack_paths.
  built_in_dir` is deferred to `#3091` and is NOT claimed by this WP; (c) a post-tasks squad pass found 3
  MORE root-relative missions-root constructions this WP does not touch —
  `src/kernel/paths.py:89-90`, `src/doctrine/missions/template/manager.py:45,126`, and
  `src/charter/cli/commands/charter/list_cmd.py:66` (verify exact paths/lines before citing — squad
  citations were not independently re-verified against current code) — name these explicitly as known,
  untouched residuals so a later reader doesn't assume this WP found everything.
- **Files**: PR description / mission tracer file (not a source file).
- **Parallel?**: Yes, can be drafted alongside T022-T024.

### Subtask T040 – Gate 4: hardcoded missions-root path-literal, zero-tolerance, self-mutation proven

- **Purpose**: Non-vacuous, durable proof the 2 hardcodes closed by T022-T023 cannot silently reopen
  (absorbed from the former WP09 — this gate only ever guarded this WP's own surface).
- **Steps**:
  1. Scan `src/` for `Path(__file__)`-relative constructions of a missions-root-shaped path (containing
     `"doctrine"` and `"missions"` as adjacent path components) outside
     `src/doctrine/missions/repository.py` (the one promoted authority).
  2. Zero-tolerance for the two closed sites' shape; this gate does NOT need to catch the 3 residual
     duplicates named in T025 (they're a different literal shape — root-relative from a different anchor —
     and closing them is out of this WP's scope, not this gate's job to enforce).
  3. Self-mutation proof: inject such a literal at function-local scope in a scratch module; assert the
     gate fails naming the exact line.
- **Files**: `tests/architectural/test_charter_sole_door_hardcoded_paths.py` (new).
- **Parallel?**: No — depends on T022-T023 landing first (writing the gate before the hardcodes close would
  make it immediately red against legitimate pre-existing code).

## Test Strategy

- `pytest tests/charter/ tests/specify_cli/runtime/ -v`.
- `mypy --strict src/charter/activation/mission_type_profile_repository.py src/specify_cli/runtime/home.py`.

## Risks & Mitigations

- **Retargeting onto `pack_paths.built_in_dir` by mistake** (the original, now-corrected spec framing).
  Mitigation: re-read the Context section above — the promotion target is `MissionTemplateRepository.
  default_missions_root()`, never `pack_paths`.

## Review Guidance

- Confirm neither retargeted site references `doctrine.pack_paths` at all.
- Confirm `builtin_missions_root()`'s existing callers are unaffected (no signature change).
- Confirm T025's PR-description language actually landed, not just drafted.

## Activity Log

- 2026-08-03T14:10:00Z – system – Prompt created.
- 2026-08-03T16:20:27Z – claude – shell_pid=2330 – T025 (PR-description residual disclosure): (a) home.py's dev_roots retarget uses a function-local doctrine-layer import matching the file's own existing pattern at home.py:37/49 — shares the same #2986 function-local-import blind spot, named not hidden. (b) Full convergence onto doctrine.pack_paths.built_in_dir remains deferred to #3091 (pack_paths has no missions/ content dir today) and is NOT claimed by this WP. (c) Squad-cited residual paths were WRONG and are corrected here (verified against current code, not re-fixed): the real untouched root-relative missions-root duplicates are src/kernel/paths.py:89-90, src/specify_cli/template/manager.py:45,126 (NOT src/doctrine/missions/template/manager.py as originally cited), and src/specify_cli/cli/commands/charter/list_cmd.py:66,79 (NOT src/charter/cli/commands/charter/list_cmd.py as originally cited). These 3 are a different literal shape (root-relative, not Path(__file__)-relative) and are explicitly out of this WP's scope and out of Gate 4's zero-tolerance check.
