---
work_package_id: WP03
title: Mission-review mode contract, validator, and existing-matrix remediation
dependencies:
- WP01
- WP02
- WP07
requirement_refs:
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-023
- FR-028
- FR-029
- FR-030
- FR-031
- FR-032
- FR-033
- FR-034
planning_base_branch: fix/3.2.x-review-merge-gate-hardening
merge_target_branch: fix/3.2.x-review-merge-gate-hardening
branch_strategy: Planning artifacts for this mission were generated on fix/3.2.x-review-merge-gate-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/3.2.x-review-merge-gate-hardening unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
- T021
- T022
- T023
agent: "claude:opus:reviewer:reviewer"
shell_pid: "522217"
history:
- at: '2026-05-12'
  actor: planner
  event: created
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/review/_mode.py
execution_mode: code_change
mission_id: 01KRC57CNW5JCVBRV8RAQ2ARXZ
mission_slug: review-merge-gate-hardening-3-2-x-01KRC57C
owned_files:
- src/specify_cli/cli/commands/review/_mode.py
- src/specify_cli/cli/commands/review/_issue_matrix.py
- src/specify_cli/cli/commands/review/_diagnostics.py
- src/specify_cli/cli/commands/review/ERROR_CODES.md
- kitty-specs/stability-and-hygiene-hardening-2026-04-01KQ4ARB/issue-matrix.md
- kitty-specs/charter-golden-path-e2e-tranche-1-01KQ806X/issue-matrix.md
- kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/issue-matrix.md
- kitty-specs/release-3-2-0a6-tranche-2-01KQ9MKP/issue-matrix.md
- kitty-specs/stable-320-p1-release-confidence-01KQTPZC/issue-matrix.md
- kitty-specs/stable-320-release-blocker-cleanup-01KQW4DF/issue-matrix.md
- .kittify/glossaries/spec_kitty_core.yaml
- tests/specify_cli/cli/commands/review/test_mode_resolution.py
- tests/specify_cli/cli/commands/review/test_issue_matrix_validator.py
- tests/specify_cli/cli/commands/review/test_existing_matrix_remediation.py
- tests/specify_cli/cli/commands/review/test_diagnostic_codes_documented.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else below, load the assigned agent profile so your behavior, boundaries, and governance scope match the role:

```
/ad-hoc-profile-load implementer-ivan
```

The profile establishes your identity (Implementer Ivan), primary focus (writing and verifying production-grade code), and avoidance boundary (no architectural redesign; no scope expansion beyond what this WP authorizes). If the profile load fails, stop and surface the error — do not improvise a role.

## Objective

Add explicit `--mode {lightweight|post-merge}` resolution with `meta.json.baseline_merge_commit` auto-detect default; enforce the audit-derived `issue-matrix.md` schema with closed-set named-optional columns and verdict allow-list; record Gate 1–4 results in the report frontmatter; remediate the 6 existing `issue-matrix.md` files on `main`. Author the corresponding `ERROR_CODES.md` sibling and glossary entries.

This WP fixes [#985](https://github.com/Priivacy-ai/spec-kitty/issues/985) and satisfies FR-005 through FR-009, FR-023, FR-028 through FR-034 in [`../spec.md`](../spec.md), plus NFR-007 and NFR-008.

Reference contracts:
- [`../contracts/review-mode-resolution.md`](../contracts/review-mode-resolution.md)
- [`../contracts/issue-matrix-schema.md`](../contracts/issue-matrix-schema.md)
- [`../data-model.md`](../data-model.md) §1

## Context

`spec-kitty review` today can pass with a one-line report even when post-merge mission-review doctrine requires `issue-matrix.md` + Gate 1–4 records. Operators get a green light that doesn't reflect the real release-gate contract. The fix has three concurrent layers:

1. **Mode contract**: distinguish "lightweight consistency check" from "post-merge release gate"; the mode is auto-detected from `meta.json.baseline_merge_commit` with explicit `--mode` override.
2. **Validator**: enforce the closed-set vocabulary derived from auditing 6 real `issue-matrix.md` files on `main` (see spec §"Existing-mission audit findings"). The validator is **strict** on mandatory + named-optional columns; rejects unknown columns; rejects multi-table layouts.
3. **Remediation**: auto-normalize trivial drift in the 6 existing matrices (capitalization, alias resolution) writing a one-line provenance note inside the file; surface structural drift via diagnostic for operator repair.

WP07 has already created the review/ package; WP01 has added the hermetic preflight. This WP fills the package with the contract-enforcement modules.

## Branch Strategy

- **Planning/base branch**: `fix/3.2.x-review-merge-gate-hardening`
- **Final merge target**: `main` (after PR review)
- **Execution worktree**: assigned by `spec-kitty implement WP03`. WP03 depends on WP01, WP02, WP07 — those must be merged into this branch first.

## Subtasks

### T017 [P] — `MissionReviewDiagnostic` StrEnum

**Purpose**: a single typed source of truth for all JSON-stable diagnostic codes emitted by `spec-kitty review`. The class docstring names the sibling `ERROR_CODES.md` so future readers of the code reach the doc.

**Steps**:

1. Create `src/specify_cli/cli/commands/review/_diagnostics.py`:
   ```python
   """Mission-review diagnostic codes.

   This is the single source of truth for JSON-stable diagnostic strings
   emitted by `spec-kitty review`. The cross-surface fixture harness
   (#992 Phase 0) and downstream dashboards consume these.

   See: src/specify_cli/cli/commands/review/ERROR_CODES.md
   (Hand-maintained mirror until the code-to-docs flow envisioned in
   GitHub #645 ships; cross-reference enforced by NFR-008 test.)
   """

   from enum import StrEnum


   class MissionReviewDiagnostic(StrEnum):
       MODE_MISMATCH = "MISSION_REVIEW_MODE_MISMATCH"
       ISSUE_MATRIX_MISSING = "MISSION_REVIEW_ISSUE_MATRIX_MISSING"
       ISSUE_MATRIX_SCHEMA_DRIFT = "MISSION_REVIEW_ISSUE_MATRIX_SCHEMA_DRIFT"
       ISSUE_MATRIX_VERDICT_UNKNOWN = "MISSION_REVIEW_ISSUE_MATRIX_VERDICT_UNKNOWN"
       ISSUE_MATRIX_MULTI_TABLE = "MISSION_REVIEW_ISSUE_MATRIX_MULTI_TABLE"
       ISSUE_MATRIX_EVIDENCE_REF_EMPTY = "MISSION_REVIEW_ISSUE_MATRIX_EVIDENCE_REF_EMPTY"
       ISSUE_MATRIX_DEFERRED_WITHOUT_HANDLE = "MISSION_REVIEW_ISSUE_MATRIX_DEFERRED_WITHOUT_HANDLE"
       GATE_RECORD_MISSING = "MISSION_REVIEW_GATE_RECORD_MISSING"
       MISSION_EXCEPTION_INVALID = "MISSION_REVIEW_MISSION_EXCEPTION_INVALID"
       TEST_EXTRA_MISSING = "MISSION_REVIEW_TEST_EXTRA_MISSING"
   ```

**Files**: `src/specify_cli/cli/commands/review/_diagnostics.py` (new)

**Validation**:
- [ ] mypy strict passes.
- [ ] Each member's string value is unique and matches its name (after the `MISSION_REVIEW_` prefix).

### T018 — Mode resolution + `--mode` flag

**Purpose**: implement the three-rule resolution order from `contracts/review-mode-resolution.md`. Mode mismatch (operator runs `--mode post-merge` against a pre-merge mission) hard-blocks with a remediation-rich diagnostic.

**Steps**:

1. Create `src/specify_cli/cli/commands/review/_mode.py`:
   ```python
   from enum import StrEnum
   from pathlib import Path
   import json


   class MissionReviewMode(StrEnum):
       LIGHTWEIGHT = "lightweight"
       POST_MERGE = "post-merge"


   def resolve_mode(
       feature_dir: Path,
       *,
       cli_flag: MissionReviewMode | None,
   ) -> tuple[MissionReviewMode, bool]:
       """Resolve the review mode per the contract.

       Returns (mode, auto_detected).
       Raises ModeMismatch when --mode post-merge is requested without baseline_merge_commit.
       """
       meta = json.loads((feature_dir / "meta.json").read_text())
       baseline = meta.get("baseline_merge_commit")
       if cli_flag is not None:
           if cli_flag is MissionReviewMode.POST_MERGE and baseline is None:
               raise ModeMismatch(MissionReviewDiagnostic.MODE_MISMATCH, ...)
           return cli_flag, False
       if baseline is not None:
           return MissionReviewMode.POST_MERGE, True
       return MissionReviewMode.LIGHTWEIGHT, True
   ```
2. Wire `--mode` into the typer/click CLI for `spec-kitty review` (located in `review/__init__.py` after WP07).
3. The diagnostic body for `MODE_MISMATCH` MUST contain three remediation options exactly as specified in FR-023 and `contracts/review-mode-resolution.md`.

**Files**: `src/specify_cli/cli/commands/review/_mode.py` (new), `review/__init__.py` (CLI wiring)

**Validation**:
- [ ] Auto-detect: pre-merge → lightweight; post-merge → post-merge.
- [ ] CLI override: `--mode lightweight` overrides auto-detect.
- [ ] Mode mismatch: pre-merge + `--mode post-merge` raises with the three-option remediation body.

### T019 — `issue-matrix.md` validator

**Purpose**: parse and validate any `issue-matrix.md` against the audit-derived schema. Closed mandatory + named-optional columns; verdict allow-list; single-table; body-cell rules.

**Steps**:

1. Create `src/specify_cli/cli/commands/review/_issue_matrix.py`:
   ```python
   from dataclasses import dataclass
   from enum import StrEnum
   from pathlib import Path


   MANDATORY_COLUMNS = ("issue", "verdict", "evidence_ref")
   NAMED_OPTIONAL_COLUMNS = ("title", "scope", "wp", "fr", "nfr", "sc", "repo")
   COLUMN_ALIASES = {
       "evidence ref": "evidence_ref",
       "wp_id": "wp",
       "fr(s)": "fr",
       "nfr(s)": "nfr",
       "theme": "scope",
   }


   class IssueMatrixVerdict(StrEnum):
       FIXED = "fixed"
       VERIFIED_ALREADY_FIXED = "verified-already-fixed"
       DEFERRED_WITH_FOLLOWUP = "deferred-with-followup"


   @dataclass(frozen=True)
   class IssueMatrixRow:
       issue: str
       verdict: IssueMatrixVerdict
       evidence_ref: str
       title: str | None = None
       scope: str | None = None
       wp: str | None = None
       fr: str | None = None
       nfr: str | None = None
       sc: str | None = None
       repo: str | None = None


   def validate_matrix(path: Path) -> list[IssueMatrixRow]:
       """Validate per contracts/issue-matrix-schema.md; raise with a JSON-stable
       diagnostic code on any violation."""
       ...
   ```
2. Implementation rules (each ties to a diagnostic code):
   - Locate the Markdown table(s). If more than one table at the top level, raise `MULTI_TABLE`.
   - Parse the header row. Normalize: lowercase, strip whitespace, resolve aliases. If any column is not in `MANDATORY ∪ NAMED_OPTIONAL`, raise `SCHEMA_DRIFT` naming the unknown column.
   - Mandatory columns must appear in the order `issue, verdict, evidence_ref` (after normalization). Order violation → `SCHEMA_DRIFT`.
   - Parse each body row. Validate verdict cell against `IssueMatrixVerdict`; unknown → `VERDICT_UNKNOWN`.
   - `evidence_ref` must be non-empty → `EVIDENCE_REF_EMPTY`.
   - When `verdict == DEFERRED_WITH_FOLLOWUP`, `evidence_ref` must contain a follow-up handle (regex `#\d+` OR substring `Follow-up:`) → `DEFERRED_WITHOUT_HANDLE`.

**Files**: `src/specify_cli/cli/commands/review/_issue_matrix.py` (new)

**Validation**:
- [ ] Each diagnostic code is reachable via a synthetic input.
- [ ] All 6 existing matrices on `main` produce known diagnostics or pass after normalization (covered in T021).

### T020 — Extend `_report.py` for new frontmatter

**Purpose**: the report writer (WP07's `_report.py`) now records `mode`, `gates_recorded`, `issue_matrix_present`, `mission_exception_present` in YAML frontmatter, matching the `MissionReviewReport` dataclass in `data-model.md`.

**Steps**:

1. Import `MissionReviewMode` and `GateRecord` from `_mode.py` and add a new module-internal dataclass for the report shape per `data-model.md`.
2. Extend the existing report-writer function to accept the new fields. Backward-compat: existing tests that don't pass these fields default them to sensible values (`mode=LIGHTWEIGHT`, `gates_recorded=[]`, etc.). This is a behavioral neutrality concession to NFR-005's spirit, but the gate command path always passes the new fields.
3. The frontmatter ordering must be stable for diff readability: `verdict`, `mode`, `reviewed_at`, `findings`, `gates_recorded`, `issue_matrix_present`, `mission_exception_present`.

**Files**: `src/specify_cli/cli/commands/review/_report.py` (modify — owned by WP07 but extended here per sequential dependency)

**Note on cross-WP file modification**: this WP extends a file WP07 created. The owned_files in this WP's frontmatter declares the new files WP03 creates; WP07 owns `_report.py` for initial creation. The dependency relationship (WP03 depends on WP07) authorizes the extension. Coordinate via the merge target — WP07 must land first.

**Validation**:
- [ ] Generated report frontmatter contains all 7 fields in stable order.
- [ ] Pre-existing report-writer tests pass with default-argument extension.

### T021 — Remediate the 6 existing `issue-matrix.md` files

**Purpose**: bring the 6 existing matrices on `main` into compliance with the new validator. Auto-normalize trivial drift (capitalization, aliases) with a provenance note; surface structural drift (multi-table, unknown columns) for operator repair.

**Steps**:

1. For each of the 6 files listed in `owned_files`, run the validator (T019).
2. **Trivial drift** (auto-normalize, write provenance note):
   - Capitalization variants (`Issue` → `issue`, `Evidence ref` → `evidence_ref`)
   - Alias variants (`wp_id` → `wp`, `theme` → `scope`)
   - Action: rewrite the header row with normalized names; prepend the line `<!-- normalized 2026-05-NN: header case folded; aliases resolved by WP03 -->` to the file.
3. **Structural drift** (surface, do NOT auto-fix):
   - `charter-golden-path-e2e-tranche-1-01KQ806X/issue-matrix.md` has 3 separate tables — emit `MULTI_TABLE` diagnostic and instruct the operator to consolidate.
   - Any unknown columns (e.g., `Surface`, `Where surfaced in code` in the charter-golden-path mission) — emit `SCHEMA_DRIFT` listing the column.
4. For structural drift files, write a sibling `.remediation-note.md` next to the matrix explaining what needs to change and pointing at `ERROR_CODES.md` for the canonical contract.

**Files**: the 6 `kitty-specs/*/issue-matrix.md` listed in this WP's `owned_files`.

**Note on ownership**: these are existing artifacts not previously owned by any WP. Owning them in this WP's `owned_files` is correct because we are modifying them.

**Validation**:
- [ ] Files that had trivial drift now pass validation; provenance note in place.
- [ ] Files with structural drift have `.remediation-note.md` and emit the expected diagnostic when validated.

### T022 [P] — Author `ERROR_CODES.md`

**Purpose**: per-subsystem documentation of every diagnostic code (NFR-008). The doc lives at `src/specify_cli/cli/commands/review/ERROR_CODES.md`; the `MissionReviewDiagnostic` StrEnum docstring references it.

**Steps**:

1. Create `src/specify_cli/cli/commands/review/ERROR_CODES.md` using the layout in `data-model.md` §5.
2. One section per `MissionReviewDiagnostic` member. Each section has:
   - The code name as the section heading
   - "When it fires": one-sentence summary
   - "JSON stability": commitment statement
   - "Remediation": ordered list of operator actions
   - "Body example": exact text the operator sees on stderr
3. The doc header includes: `Source of truth: src/specify_cli/cli/commands/review/_diagnostics.py StrEnum MissionReviewDiagnostic.`

**Files**: `src/specify_cli/cli/commands/review/ERROR_CODES.md` (new)

**Validation**:
- [ ] One section per StrEnum member; section count == member count.
- [ ] Each section names the diagnostic body exactly as emitted by the code.
- [ ] Cross-reference test (separate test file): `test_diagnostic_codes_documented.py` asserts every StrEnum member has a section in the doc.

### T023 [P] — Glossary entries (WP03's own + delegated from WP06)

**Purpose**: add new canonical terms introduced by this mission to `.kittify/glossaries/spec_kitty_core.yaml`. Per FR-034, terms cannot ship without entries. WP03 owns the glossary file; entries from sibling WPs (WP06, WP07, WP08) are added here per delegation.

**Steps**:

1. Open `.kittify/glossaries/spec_kitty_core.yaml`.
2. Append the following entries. Exact `definition` text is in `data-model.md` §6; copy/adapt. Keep alphabetical order within the existing file's organization.

   **From WP03**:
   - `lightweight mode`
   - `post-merge mode`
   - `mode mismatch`
   - `issue-matrix schema drift`

   **From WP06** (delegated; WP06's PR description lists these as required):
   - `encoding chokepoint`
   - `encoding provenance`
   - `unsafe bypass`

   **From WP07** (delegated):
   - `review.py package`

   **From WP08** (delegated):
   - `charter-content migration`

3. Each entry uses the shape:
   ```yaml
     - surface: <term>
       definition: <text from data-model.md §6>
       confidence: 0.95
       status: active
   ```
4. Verify with the doctor:
   ```bash
   spec-kitty doctor 2>&1 | grep -i glossary
   ```
   (or equivalent) so an unknown term doesn't slip through.

**Files**: `.kittify/glossaries/spec_kitty_core.yaml`

**Validation**:
- [ ] Each term listed above has a YAML entry.
- [ ] `confidence >= 0.8`, `status: active` for every entry.
- [ ] Sibling WPs (WP06, WP07, WP08) have their delegation noted in their PR descriptions; no orphaned canonical terms.

## Definition of Done

- [ ] T017–T023 acceptance checks pass.
- [ ] FR-005 through FR-009, FR-023, FR-028 through FR-034 cited in commits.
- [ ] NFR-007 (single typed vocabulary) and NFR-008 (ERROR_CODES.md + cross-reference test) satisfied.
- [ ] Scenarios 3, 4, 8, 12, 13, 14, 15 in spec.md have passing regression tests.

## Risks and Reviewer Guidance

**Risk**: silent rewrite of existing matrices. T021 MUST write a provenance note before modifying content. Reviewer should diff each remediated file and verify the note appears.

**Risk**: validator vocabulary drift between `_issue_matrix.py` constants and `contracts/issue-matrix-schema.md`. Encode the vocabulary in code (NFR-007); the contract doc references the code, not vice versa.

**Reviewer focus**:
- T019 implementation: every diagnostic code reachable by at least one synthetic test.
- T021: which files were modified, what notes were added; structural drift surfaced not auto-fixed.
- T022 ERROR_CODES.md: every StrEnum member documented; test asserts cross-reference.

## Suggested implement command

```bash
spec-kitty agent action implement WP03 --agent claude --mission review-merge-gate-hardening-3-2-x-01KRC57C
```

## Activity Log

- 2026-05-12T13:40:51Z – claude:sonnet:implementer-ivan:implementer – shell_pid=514824 – Started implementation via action command
- 2026-05-12T13:52:37Z – claude:sonnet:implementer-ivan:implementer – shell_pid=514824 – WP03 ready: mode contract + validator + 6-matrix remediation + ERROR_CODES.md + glossary (incl. delegated entries from WP06/07/08) + 4 test files
- 2026-05-12T13:54:25Z – claude:opus:reviewer:reviewer – shell_pid=522217 – Started review via action command
- 2026-05-12T13:57:21Z – claude:opus:reviewer:reviewer – shell_pid=522217 – Review passed: T017-T023 satisfied; FR-005..009/FR-023/FR-028..034/NFR-007/NFR-008 covered; 9 glossary entries added (4 WP03 + 3 WP06 + 1 WP07 + 1 WP08); 6-matrix remediation: 2 auto-normalized + provenance, 3 multi-table/structural-drift with .remediation-note.md siblings, 1 already-conforming no-op; ERROR_CODES.md mirrors all 10 StrEnum codes; NFR-008 cross-ref test enforces; 80/80 review pkg tests + 129/129 broader tests pass.
