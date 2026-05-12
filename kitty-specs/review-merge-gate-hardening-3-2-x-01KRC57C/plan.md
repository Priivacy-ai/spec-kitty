# Implementation Plan: Review/Merge Gate Hardening (3.2.x)

**Branch**: `fix/3.2.x-review-merge-gate-hardening` | **Date**: 2026-05-12 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/home/stijn/Documents/_code/SDD/fork/spec-kitty/kitty-specs/review-merge-gate-hardening-3-2-x-01KRC57C/spec.md`
**Mission**: `review-merge-gate-hardening-3-2-x-01KRC57C` (`mission_id=01KRC57CNW5JCVBRV8RAQ2ARXZ`)

## Summary

Eight WPs close the residual 3.2.x P1 release blockers in the **release-gate apparatus** (mission-review enforcement, merge idempotency, status-read worktree resolution, parallel-test fixture safety) plus a narrowed slice of the encoding chokepoint work, a hygiene refactor of `review.py`, and a migration flow for legacy charter content.

Technical approach (one line per WP):

- **WP01 #987**: replace `uv run pytest …` with `uv run python -m pytest …` everywhere it's a release gate; add preflight assertion that the project `.venv` has `pytest` installed.
- **WP02 #986**: add a file-lock around the `.pytest_cache/spec-kitty-test-venv` fixture creation; alternative considered (per-worker cache dir) rejected because it inflates CI cache traffic.
- **WP03 #985**: introduce `--mode {lightweight|post-merge}` with auto-detect default from `meta.json.baseline_merge_commit`; enforce the audit-derived `issue-matrix.md` schema; record Gate 1–4 with command/exit-code/result; remediate the 6 existing matrices on `main` with auto-normalize-or-fail-loud.
- **WP04 #983**: short-circuit mission-number assignment when `meta.json.mission_number` already equals the computed value; persist `mission_number_baked: true` on the merge-state so `--resume` skips the step; cover with a regression simulating partial-merge resume.
- **WP05 #984**: audit `_ensure_target_branch_checked_out`, `get_main_repo_root`, and sibling resolvers; route read-only status commands through current-worktree resolution; fail loudly when the command intentionally does not support detached worktrees.
- **WP06 #644 (narrowed)**: new `src/charter/_io.py :: load_charter_file()` applied to three ingest boundaries (`interview.py`, `sync.py`, `compiler.py`); `charset-normalizer` promoted to direct dep `>=3.4,<4`; hard-fail on ambiguous encoding with `--unsafe` bypass; dual-storage `.encoding-provenance.jsonl` (per-mission preferred; centralized for non-mission-scoped content).
- **WP07 (refactor)**: mechanical split of `src/specify_cli/cli/commands/review.py` into a package (`commands/review/__init__.py` + `_lane_gate.py`, `_dead_code.py`, `_ble001_audit.py`, `_report.py`, `_diagnostics.py`, `_issue_matrix.py`); preserves `review_mission()` import path; behavioral neutrality enforced by NFR-005.
- **WP08 (migration)**: `spec-kitty migrate charter-encoding` scans every existing mission's charter content, detects non-UTF-8 encodings, normalizes-with-provenance or fails-loud per file; idempotent (NFR-006); produces JSON-stable summary report.

## Technical Context

**Language/Version**: Python 3.11+ (project requirement; matches `pyproject.toml`)
**Primary Dependencies**: typer (CLI), rich (output), ruamel.yaml (frontmatter), pytest (testing), `charset-normalizer >= 3.4, < 4` (promoted from transitive via `requests` to direct as part of WP06)
**Storage**: Filesystem only (YAML frontmatter, JSONL event logs, JSON merge-state, Markdown reports). No DB introduction.
**Testing**: pytest 8+ via `uv run python -m pytest` (hermetic invocation per WP01); fixtures via conftest with file-locked shared venv per WP02; cross-surface fixture harness alignment per #992 Phase 0.
**Target Platform**: Linux + macOS + Windows (Windows charter-encoding case is the original #644 repro).
**Project Type**: Single-project Python CLI with auxiliary packaged subsystems (charter, dashboard, sync, status, merge).
**Performance Goals**: WP06 chokepoint adds ≤ 5 ms per charter-file ingest in the common UTF-8 fast path; WP02 venv-lock adds ≤ 2 s p99 to parallel gate startup.
**Constraints**:
- WP06 chokepoint must touch ≤ 5 modules (NFR-004).
- WP07 must be behaviorally neutral (NFR-005).
- WP08 must be idempotent (NFR-006).
- All new diagnostic codes are JSON-stable (NFR-001) and documented in `ERROR_CODES.md` siblings (NFR-008).
- The validator vocabulary (mandatory + named-optional + verdict allow-list) is encoded once as a typed object (NFR-007).
**Scale/Scope**: 8 WPs, 34 FRs, 8 NFRs, 15 acceptance scenarios, touches 11+ existing files across `src/specify_cli/cli/commands/review.py`, `src/specify_cli/merge/`, `src/specify_cli/status/`, `src/charter/`, conftest, and test fixtures.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter source: `.kittify/charter/charter.md` (loaded via `spec-kitty charter context --action plan --json`).

| Charter section | Compliance |
|-----------------|-----------|
| **Languages and Frameworks** (charter: Python) | ✅ Python 3.11+ across all WPs. |
| **Testing Requirements** (charter: pytest with hermetic invocation) | ✅ WP01 enforces hermetic invocation; WP02 hardens the shared fixture; existing pytest stack reused. |
| **Architecture: Shared Package Boundaries** (charter: events/tracker are external deps consumed via public imports; runtime is CLI-internal) | ✅ No WP modifies the shared-package boundary; charter encoding work is internal to `src/charter/`. |
| **Architecture: Branch and Release Strategy** (charter: 3.x branch, semver) | ✅ Mission branch `fix/3.2.x-review-merge-gate-hardening` targets `main`; landing closes residual 3.2.x P1 tranche. |
| **Quality Gates** (charter: contract + architectural + integration; no `--no-verify`) | ✅ WP01/WP02/WP03 specifically harden these gates; no hook bypass. |
| **Documentation Standards** (charter: docs live close to code) | ✅ Per-subsystem `ERROR_CODES.md` siblings (FR-033, NFR-008). |
| **Ownership Boundaries for Mutating Flows** (charter: explicit transitions; no implicit lifecycle inference) | ✅ WP03's mode resolution makes the lifecycle phase explicit via `--mode` or `baseline_merge_commit`. WP04's idempotency contract makes the merge-number lifecycle explicit. |
| **Branch-Intent Terminology Governance** (charter: canonical glossary) | ✅ FR-034 requires glossary entries for every new canonical term (scope item #10). |
| **User Customization Preservation** (charter: do not silently overwrite operator content) | ✅ WP03's existing-matrix remediation writes a one-line provenance note inside the file when normalizing; structural drift surfaces a diagnostic, never silent rewrite (FR-032). |

**No charter violations**. No Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```
kitty-specs/review-merge-gate-hardening-3-2-x-01KRC57C/
├── plan.md                  # This file
├── spec.md                  # Feature spec (already committed)
├── research.md              # Phase 0 output
├── data-model.md            # Phase 1 output
├── contracts/               # Phase 1 output
│   ├── review-mode-resolution.md
│   ├── issue-matrix-schema.md
│   ├── merge-state-idempotency.md
│   ├── status-read-worktree-resolution.md
│   ├── charter-io-chokepoint.md
│   └── encoding-provenance-schema.md
├── quickstart.md            # Phase 1 output
├── decisions/               # Decision moments (already exist)
│   ├── DM-01KRDW3BSDPKG1NF9Z2YGN5DP2.md   # planning strategy
│   ├── DM-01KRDW5BDACZD48BYMJTY7XB0X.md   # issue-matrix validator
│   ├── DM-01KRDWC8AWKGD9TCW40BRYRXE1.md   # charset-normalizer promotion
│   ├── DM-01KRDWDVRCRYKHFXNKAKZRPAEK.md   # diagnostic-code registry
│   └── index.json
└── tasks/                   # Phase 2 output (NOT in this command)
```

### Source Code (repository root)

```
src/specify_cli/cli/commands/
└── review/                              # WP07 split (was review.py)
    ├── __init__.py                      # public review_mission() entry, preserves imports
    ├── _lane_gate.py                    # Gate 1: WP lane check
    ├── _dead_code.py                    # Gate 2: dead-code scan
    ├── _ble001_audit.py                 # Gate 3: BLE001 audit
    ├── _report.py                       # Gate 4: report writer
    ├── _diagnostics.py                  # MissionReviewDiagnostic(StrEnum)
    ├── _issue_matrix.py                 # validator + remediator (WP03)
    ├── _mode.py                         # mode resolution + --mode flag (WP03)
    └── ERROR_CODES.md                   # FR-033 sibling doc

src/specify_cli/merge/
├── executor.py                          # WP04 idempotency edits
├── state.py                             # WP04 mission_number_baked flag

src/specify_cli/status/
└── lane_reader.py                       # WP05 worktree-aware resolution
(plus audit/edit of get_main_repo_root and _ensure_target_branch_checked_out wherever they live)

src/charter/
├── _io.py                               # WP06 chokepoint (new)
├── _diagnostics.py                      # CharterEncodingDiagnostic(StrEnum)
├── compiler.py                          # WP06 retrofit (ingest)
├── interview.py                         # WP06 retrofit (ingest)
├── sync.py                              # WP06 retrofit (ingest)
└── ERROR_CODES.md                       # FR-033 sibling doc

src/specify_cli/cli/commands/migrate/
└── charter_encoding.py                  # WP08 migration command (new file or new sub-command)

tests/
├── conftest.py                          # WP02 venv-fixture file lock
├── specify_cli/cli/commands/review/
│   ├── test_mode_resolution.py          # WP03
│   ├── test_issue_matrix_validator.py   # WP03 + FR-028 through FR-031
│   ├── test_existing_matrix_remediation.py  # WP03 / FR-032
│   └── test_diagnostic_codes_documented.py  # NFR-008
├── merge/
│   └── test_mission_number_idempotency.py  # WP04
├── status/
│   └── test_status_read_worktree_resolution.py  # WP05
├── charter/
│   ├── test_encoding_chokepoint.py      # WP06 / Scenario 7
│   ├── test_unsafe_bypass.py            # WP06 / Scenario 9
│   └── test_provenance_dual_storage.py  # WP06 / FR-022
└── migrate/
    └── test_charter_encoding_migration.py  # WP08

.kittify/glossaries/
└── spec_kitty_core.yaml                 # FR-034 additions (new canonical terms)
```

**Structure Decision**: Single-project Python CLI. WP07 introduces a package directory at `src/specify_cli/cli/commands/review/` to replace the current single-file `review.py`. WP06 introduces a new internal package `src/charter/_io.py` co-located with existing charter modules. No new top-level packages; no new test top-level dirs (added sub-dirs under existing `tests/` are conventional).

## Phase Execution

### Phase 0 — Outline & Research

Research questions to consolidate in `research.md` (commissioned to subagent research; consolidated here when complete):

1. **R-1 (WP01)** — Survey of all places where `uv run pytest …` is documented as a release-gate command (mission templates, docs, agent skills, doctrine). What's the blast radius of changing all to `uv run python -m pytest`? Are there any agent integrations that expect the verb-form?
2. **R-2 (WP02)** — Compare file-lock vs per-worker-cache-dir for the pytest-venv fixture. Quantify cache size in CI (does per-worker double our cache traffic?). Measure pytest startup latency overhead from a stale-but-locked fixture.
3. **R-3 (WP03)** — Confirm `meta.json.baseline_merge_commit` is set unconditionally by every merge path (e.g., `--squash`, `--rebase`, `--merge` strategies all write it). If not, identify the omission and decide: fix the omission as part of WP03, or scope WP03's mode-detection rule to only work for the strategies that write the field.
4. **R-4 (WP03)** — Investigate whether `gates_recorded` (FR-007) is best stored as YAML frontmatter keys on `mission-review-report.md` or as a sibling `gate-records.jsonl`. Trade-off: frontmatter is single-file but limits gate count; JSONL scales but adds a second artifact.
5. **R-5 (WP04)** — Confirm the mission-number-assignment commit path: which function writes `mission_number` to `meta.json`, and how is it serialized? Is `meta.json` written atomically (temp + rename) or in-place? The idempotency check must read `meta.json` at the right moment in the merge state machine.
6. **R-6 (WP05)** — Inventory every call site of `get_main_repo_root()` in status-read code paths. Confirm which are read-only vs read-write — only read-only ones get the worktree-preferring resolution. Audit `_ensure_target_branch_checked_out` for the same.
7. **R-7 (WP06)** — Inspect `interview.py`, `sync.py`, `compiler.py` line numbers reported by the audit (~ `interview.py:283,398`, `sync.py:151`, `compiler.py:594`) to confirm the ingest-vs-re-read classification. Confirm none of the deferred sites (`context.py`, `hasher.py`, `language_scope.py`, `compact.py`, `neutrality/lint.py`) actually ingest from external sources — only re-read normalized files.
8. **R-8 (WP06)** — Pin the `charset-normalizer` API surface used: `from_bytes()` returns a `CharsetMatches` collection; we want the highest-confidence match's `encoding` attribute. Confirm the fallback when no candidate clears confidence ≥ 0.85.
9. **R-9 (WP08)** — Inventory existing mission directories for charter-content files (`kitty-specs/*/charter/*.{yaml,md,txt}` and any other patterns). Estimate corpus size. Plan a dry-run mode for the migration.
10. **R-10 (cross-cutting)** — Inspect existing `StrEnum` use in the codebase. Is `enum.StrEnum` (Python 3.11+) already used somewhere, or does the codebase still use `str, Enum` mix-in pattern? Use the existing pattern for consistency.

Each research question produces a `## R-N` section in `research.md` with: Decision, Rationale, Alternatives Considered.

### Phase 1 — Design & Contracts

**Prerequisites:** `research.md` complete.

Deliverables produced in this phase:

1. **`data-model.md`** — Defines:
   - `MissionReviewMode` enum (lightweight, post-merge)
   - `IssueMatrixRow` dataclass with canonical fields (issue, verdict, evidence_ref) + named-optional fields
   - `IssueMatrixVerdict` enum (fixed, verified-already-fixed, deferred-with-followup)
   - `MergeState` field additions (`mission_number_baked: bool`)
   - `CharterContent` dataclass (text, source_encoding, confidence, source_path, normalization_applied)
   - `EncodingProvenanceRecord` shape (event_id, at, file_path, source_encoding, confidence, normalization_applied, bypass_used, actor, mission_id)
   - `MissionReviewDiagnostic` and `CharterEncodingDiagnostic` StrEnum members
2. **`contracts/`** — One Markdown contract per cross-cutting interface:
   - `review-mode-resolution.md` — order: `--mode` flag → `baseline_merge_commit` present → `post-merge` else `lightweight`
   - `issue-matrix-schema.md` — mandatory + named-optional columns; verdict allow-list; single-table requirement; body-cell rules; aliases
   - `merge-state-idempotency.md` — pre/post condition contract for the mission-number step
   - `status-read-worktree-resolution.md` — when reads prefer current worktree; when they intentionally fail-loud
   - `charter-io-chokepoint.md` — `load_charter_file()` signature; detection order; bypass semantics
   - `encoding-provenance-schema.md` — record schema; routing rule (per-mission vs centralized); no-duplication invariant
3. **`quickstart.md`** — Operator-facing walk-through:
   - Running `spec-kitty review --mission <slug>` (lightweight default vs `--mode post-merge`)
   - Reading a `mission-review-report.md` and its YAML frontmatter
   - Authoring/maintaining `issue-matrix.md` against the new canonical contract
   - Resuming an interrupted `spec-kitty merge` (WP04 path)
   - Verifying a merged SHA from a detached worktree (WP05 happy path)
   - Running `spec-kitty migrate charter-encoding` (WP08)
   - Bypassing `CHARTER_ENCODING_AMBIGUOUS` with `--unsafe` (WP06 escape hatch)

## Complexity Tracking

*No Charter Check violations. Section intentionally empty.*

## Branch Contract (final reminder before /spec-kitty.tasks)

- **Current branch**: `fix/3.2.x-review-merge-gate-hardening`
- **Planning/base branch**: `fix/3.2.x-review-merge-gate-hardening`
- **Merge target**: `main` (after PR review; this branch IS the dedicated remediation branch)
- `branch_matches_target` per `setup-plan --json`: **true**

The next step is `/spec-kitty.tasks` (run only when ready to generate WPs). This `/spec-kitty.plan` command ends here.
