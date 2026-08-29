# Tasks: Accept path-convention portability (#3016)

Mission: `accept-path-convention-override-01M14P41` · Branch: `fix/accept-path-convention-override`
Spec/plan/contracts are authoritative; these WPs reference them. ATDD red-first per `quickstart.md`.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Extract `VALID_PATH_KEYS` constant from `mission.py:183` (C-005) | WP01 | |
| T002 | New typed reader `config/path_conventions.py`: read `project.path_conventions` subkey, remap-only + exclude-deliverables validation, fail-closed section (FR-001/007/008, C-004/010/011) | WP01 | |
| T003 | Red-first reader tests: absent→{}, typo-key reject, deliverables/undeclared-key ignore, malformed-section→raise, corrupt-file→lenient {} | WP01 | |
| T004 | Merge override into `declared` at `paths.py:199` before comprehension + artifact check; add `path_overrides` param (FR-002, C-008, NFR-003) | WP01 | |
| T005 | Wire `evaluate_path_conventions` (summary_core.py) to load + pass the override (repo_root in scope) | WP01 | |
| T006 | Red-first + integration: `apps/` accepts clean; no-override regression pins exact `path_violations` + full `format_errors()`; SC-006 declared-but-absent still blocks (FR-003, NFR-001, SC-002, SC-006) | WP01 | |
| T007 | Author ADR (`docs/adr/3.x/…`) + refresh dead-symbol/shard/golden arch-gate pins (C-006, C-007) | WP01 | |
| T008 | Coverage: research/plan/documentation mission honors override at the seam (FR-004, US2-1) | WP02 | [P] |
| T009 | Coverage: Go `internal/` layout accepts (FR-005) | WP02 | [P] |
| T010 | Coverage: artifact-routed-key (`deliverables`) rejection + override×`path_prefix` composition (US1-4, US2-3) | WP02 | [P] |
| T011 | NFR-004b single-caller guard test OUTSIDE `tests/architectural/`, frozenset-equality (not `len()==N`) | WP02 | [P] |
| T012 | Reorder `_missing_artifacts` call-site: fetch `mission` first, `None` fallback (acceptance/__init__.py) | WP03 | |
| T013 | `_missing_artifacts` reads `mission.config.artifacts.optional` (token→file/dir); `contracts/` severity guard | WP03 | |
| T014 | Red-first tests (SC-004): config-derived optional incl `checklists/`; `contracts/` unchanged; `None` fallback; reads a real `mission.yaml` | WP03 | |

## WP01 — Reader + precedence merge + seam wiring [ANCHOR]  (T001-T007)

- **Goal**: deliver the project `path_conventions` override end-to-end: a project on `apps/` accepts
  honestly; no-override behavior is byte-for-byte preserved; the value↔artifact-token coupling is guarded.
- **Priority**: P1 (MVP). **Depends on**: none.
- **Independent test**: software-dev mission in an `apps/` repo with a declared override accepts with a
  clean tree and no `--lenient`; the same repo without the override still blocks.
- **Prompt**: `tasks/WP01-reader-precedence-merge.md` (~7 subtasks, est. ~460 lines).

## WP02 — All-four-types + Go coverage [TEST-ONLY]  (T008-T011)

- **Goal**: prove the by-construction breadth (all four mission types + Go) and lock the single-seam
  invariant. Strictly test-only — any seam fix routes back to WP01.
- **Priority**: P2. **Depends on**: WP01. Parallel with WP03.
- **Prompt**: `tasks/WP02-all-types-coverage.md` (~4 subtasks, est. ~230 lines).

## WP03 — #3785 optional-artifact SSOT fold [SEVERABLE, P3]  (T012-T014)

- **Goal**: `_missing_artifacts` reads the mission's declared `artifacts.optional` instead of the
  hardcoded (drifted) list; `contracts/` severity unchanged. Split-tripwire per C-003/C-009.
- **Priority**: P3. **Depends on**: WP01. Parallel with WP02 (different module).
- **Prompt**: `tasks/WP03-missing-artifacts-from-config.md` (~3 subtasks, est. ~200 lines).

## MVP
WP01 alone delivers the #3016 fix. WP02 is breadth coverage; WP03 is the severable #3785 fold.
