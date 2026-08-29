---
work_package_id: WP01
title: Reader + precedence merge + seam wiring [ANCHOR]
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-007
- FR-008
- NFR-001
- NFR-002
- NFR-003
- C-001
- C-004
- C-005
- C-006
- C-007
- C-008
- C-010
- C-011
planning_base_branch: fix/accept-path-convention-override
merge_target_branch: fix/accept-path-convention-override
branch_strategy: Planning artifacts for this mission were generated on fix/accept-path-convention-override. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/accept-path-convention-override unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/
create_intent:
- src/specify_cli/config/path_conventions.py
- tests/specify_cli/config/test_path_conventions_reader.py
- docs/adr/3.x/2026-08-28-1-project-path-convention-override-precedes-doctrine.md
execution_mode: code_change
owned_files:
- src/specify_cli/config/path_conventions.py
- src/specify_cli/mission.py
- src/specify_cli/validators/paths.py
- src/specify_cli/acceptance/summary_core.py
- docs/adr/3.x/2026-08-28-*-project-path-convention-override-precedes-doctrine.md
- tests/specify_cli/config/**
- tests/agent/test_validators_unit.py
- tests/cross_cutting/misc/test_acceptance_support.py
- tests/architectural/test_no_dead_symbols.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:
`/ad-hoc-profile-load implementer-ivan` (or `spec-kitty agent profile show implementer-ivan`).
Apply its initialization, boundaries, and directives, then proceed.

## Objective

Deliver the project-level `path_conventions` override end-to-end so a repo whose real source root is not
`src/` (Django `apps/`, Go `internal/`) is honestly accepted — **without** changing the blocking policy
the honesty mission (#3783) established. This WP unifies the config reader with its wiring (a reader
reviewed alone trips the dead-symbol gate: its only `src/` caller is in this same WP).

**Read first**: `spec.md` (FR/NFR/C), `contracts/config-schema.md`, `contracts/precedence-contract.md`,
`data-model.md`. They are authoritative; this prompt is the execution sketch.

## Branch Strategy

Planning/base branch: `fix/accept-path-convention-override`. Final merge target:
`fix/accept-path-convention-override` (→ PR to upstream/main later). Execution worktree is allocated per
the computed lane from `lanes.json` — enter it via `spec-kitty agent action implement WP01 --agent claude`.

## Guidance per subtask

### T001 — Extract `VALID_PATH_KEYS` (C-005)
`valid_path_keys` is currently a function-local literal inside `MissionConfig.model_post_init`
(`src/specify_cli/mission.py:~183`, under `# pragma: no cover`). Hoist it to a module constant
`VALID_PATH_KEYS: frozenset[str] = frozenset({"workspace","tests","deliverables","documentation","data"})`
and reference it from `model_post_init`. `mission.py` declares no `__all__`, so this does not enter a
dead-symbol surface. No behavior change; existing `MissionConfig` tests stay green.

### T002 — Typed reader `config/path_conventions.py` (FR-001/007/008, C-004/010/011)
New leaf module. `load_project_path_conventions(repo_root: Path) -> dict[str, str]`:
- Read **only** the `project.path_conventions` subkey of `.kittify/config.yaml` — NOT the whole
  `project:` block (it carries `uuid/slug/node_id/build_id`; do not reject them — C-011).
- Plumbing modeled on `charter_runtime/preflight/config.py` (YAML(typ="safe"), path resolution), but
  the fail-closed validation is **authored, not inherited** — that template is lenient.
- Validation (remap-only, repo-layout only):
  - key ∉ `VALID_PATH_KEYS` → **reject** (typo) with an actionable message (FR-007a).
  - key == `deliverables` (or any key whose value would collide with a mission artifact token) →
    **warn/ignore** — excluded from the vocabulary (C-010). Keep this simple: exclude `deliverables`
    by name; document why in the ADR.
  - section present-but-not-a-mapping, or a non-string/null value → **raise** a typed, actionable error
    naming the offending key (FR-008).
  - absent key ⇒ `{}`. Whole-`config.yaml` unreadable/corrupt ⇒ **lenient** `{}` (match co-resident
    readers — scope fail-closed to the section shape, not the file).
- One config read, no per-key filesystem read (NFR-002). mypy --strict clean (narrow the YAML result
  through `isinstance` before returning `dict[str,str]`).

### T003 — Reader tests (red-first)
`tests/specify_cli/config/test_path_conventions_reader.py`. Cover: absent→{}; valid subset returned;
typo key→raises/reject; `deliverables` present→ignored+warn; section non-mapping→raises; non-string
value→raises; whole-file-corrupt→{} (lenient). Use frozenset/dict-equality assertions, not `len()==N`
(new dir → golden-count guard). **Two named-failure-mode cases the constraints exist for:**
- **C-011:** a full `project:` block carrying the real identity fields (`uuid`/`slug`/`node_id`/`build_id`)
  **alongside** `path_conventions` ⇒ reader returns only the override and does NOT raise (proves it reads
  the subkey, not the whole block with `extra=forbid`).
- **NFR-002:** patch/spy the YAML load (and `load_project_path_conventions`) and assert it is invoked
  **exactly once** across a full accept run — one config read, no per-key filesystem re-read.

### T004 — Merge at `paths.py:199` (FR-002, C-008, NFR-003)
In `validate_mission_paths`, add keyword-only param `path_overrides: dict[str, str] | None = None`.
Merge at **line 199**, on `declared`, **before** the `required_paths` comprehension and the artifact-token
check — remap-only: `for key in declared: if key in overrides: declared[key] = overrides[key]`. Do NOT
iterate the union (never add a key the mission didn't declare). Keep it a single pre-loop expression /
tiny helper `_resolve_required_paths(...)` so C901 stays ≤15 (baseline 12/15 — measure with
`ruff check --select C901`). Do NOT add a branch inside the per-key loop.

### T005 — Wire the seam (summary_core.py)
In `evaluate_path_conventions` (the single production caller of `validate_mission_paths`, ~:187 —
`repo_root` already in scope), call `load_project_path_conventions(repo_root)` and pass it as
`path_overrides`. No new plumbing up the chain.

### T006 — Behavior tests + regression (FR-003, NFR-001, SC-002, SC-006)
- `tests/agent/test_validators_unit.py`: `_MissionStub({workspace:src/})` + `apps/` tmp_path + override
  `{workspace:apps/}` ⇒ resolves `apps/`, no `src/` violation. SC-006: override `apps/` + `apps/` absent
  ⇒ still blocks under strict.
- `tests/cross_cutting/misc/test_acceptance_support.py`: add `test_no_override_still_blocks_strict`
  beside `test_lenient_downgrades_path_conventions_to_warning` (:767) — pins the **exact**
  `path_violations` payload + the full `format_errors()` string (both honest levers named). Add an
  `apps/` end-to-end accept via the `feature_repo` fixture.
- **SC-007 (accept boundary):** a malformed `path_conventions` section ⇒ the **accept run** fails closed
  with the actionable message and **no traceback** (verify the reader's raise is caught/rendered at the
  seam, not propagated as an uncaught stack trace) — not just that the reader raises in isolation.
- **C-009 (checkable):** do NOT delete or weaken any existing #3783 assertion. The two that MUST survive
  verbatim: the exact `path_violations` payload and the full two-lever `format_errors()` string
  (`accept --lenient` + adopt-the-convention). Additive coverage only.

### T007 — ADR + arch-gate re-pin (C-006, C-007)
- ADR `docs/adr/3.x/2026-08-28-1-project-path-convention-override-precedes-doctrine.md`: precedence order,
  non-reversal of #3783, the value↔artifact-token coupling and why `deliverables` is excluded (C-010),
  and #2744 auto-detection as the deliberate next step.
- Refresh the dead-symbol allowlist / shard / golden-count pins if the new symbol or a
  `PathValidationResult`/signature change trips them (`_refresh_dead_symbol_hashes`, as #3783 did).

## Definition of Done
- All T001-T007 tests green; `ruff` + `mypy --strict` clean; `validate_mission_paths` C901 ≤15
  (measured with `ruff check --select C901`, not assumed).
- **`apps/` accepts with an untouched tree**: assert clean `git status` (no `src/`/`apps/` fabricated),
  `--lenient` NOT passed, strict mode. SC-006 (declared-but-absent still blocks) green.
- NFR-002 (one config read) and C-011 (identity fields not rejected) each pinned by a T003 test.
- No `mission.yaml` doctrine edit (C-002). ADR committed (C-006). Arch-gate pins refreshed only if
  `PathValidationResult`/signature body changed (C-007).
- `#3783` suite green AND its exact `path_violations` payload + full `format_errors()` string unchanged
  (C-009). `pytest tests/architectural/test_no_legacy_terminology.py` green (touched acceptance prose).

## Reviewer guidance
Verify: merge is at line 199 pre-loop (not a loop branch); `deliverables` is excluded and remap-only holds
(no new required path); fail-closed is section-scoped (file-corrupt stays lenient); reader reads the subkey
only; no #3783 assertion weakened (C-009); complexity measured, not assumed.
