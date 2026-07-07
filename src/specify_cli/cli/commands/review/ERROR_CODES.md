# Mission-Review Error & Warning Codes

> **Source of truth**: `src/specify_cli/cli/commands/review/_diagnostics.py`
> (StrEnum class `MissionReviewDiagnostic`).
> This file is a hand-maintained mirror. Until #645's code-to-docs flow exists,
> the StrEnum members and this file's section count must match per NFR-008.

---

## MODE_MISMATCH

**Code**: `MISSION_REVIEW_MODE_MISMATCH`

**When it fires**: `--mode post-merge` was requested but `meta.json.baseline_merge_commit` is absent, meaning the mission has not been merged via `spec-kitty merge`.

**JSON stability**: this code string is stable across minor releases; consumers may match it as an opaque identifier.

**Remediation**:
1. Run `spec-kitty merge` to merge the mission and record the baseline commit, then retry `spec-kitty review --mode post-merge`.
2. Re-run with `--mode lightweight` to perform a consistency check without the full post-merge gate requirements.
3. For pre-083 missions already merged but lacking `baseline_merge_commit`, run `spec-kitty migrate backfill-identity` to backfill missing identity fields, which will also record the baseline merge commit if available.

**Body example**:

```text
MISSION_REVIEW_MODE_MISMATCH: --mode post-merge was requested but meta.json.baseline_merge_commit is absent.
```

---

## ISSUE_MATRIX_MISSING

**Code**: `MISSION_REVIEW_ISSUE_MATRIX_MISSING`

**When it fires**: The `issue-matrix.md` file is not present in the mission's `kitty-specs/<slug>/` directory when running in post-merge mode, or the file contains no Markdown table.

**JSON stability**: this code string is stable across minor releases; consumers may match it as an opaque identifier.

**Remediation**:
1. Create `kitty-specs/<slug>/issue-matrix.md` with mandatory columns `issue`, `verdict`, and `evidence_ref`.
2. Populate one row per GitHub issue in scope with a valid verdict from the allow-list: `fixed`, `verified-already-fixed`, `deferred-with-followup`, or `in-mission`.
3. If running a lightweight consistency check, use `--mode lightweight` to bypass the issue-matrix requirement.

**Body example**:

```text
MISSION_REVIEW_ISSUE_MATRIX_MISSING: issue-matrix.md is required in post-merge mode
```

---

## ISSUE_MATRIX_SCHEMA_DRIFT

**Code**: `MISSION_REVIEW_ISSUE_MATRIX_SCHEMA_DRIFT`

**When it fires**: An `issue-matrix.md` file uses column headers outside the canonical mandatory + named-optional vocabulary, or mandatory columns are missing or out of order.

**JSON stability**: this code string is stable across minor releases; consumers may match it as an opaque identifier.

**Remediation**:
1. Ensure mandatory columns are present in order: `issue`, `verdict`, `evidence_ref`.
2. Replace any unknown columns with named-optional columns from the canonical set: `title`, `scope`, `wp`, `fr`, `nfr`, `sc`, `repo`.
3. Apply canonical aliases: `theme` → `scope`, `wp_id` → `wp`, `fr(s)` → `fr`, `nfr(s)` → `nfr`, `evidence ref` → `evidence_ref`.

**Body example**:

```text
MISSION_REVIEW_ISSUE_MATRIX_SCHEMA_DRIFT: Unknown column(s) not in mandatory or named-optional vocabulary: Severity
```

---

## ISSUE_MATRIX_VERDICT_UNKNOWN

**Code**: `MISSION_REVIEW_ISSUE_MATRIX_VERDICT_UNKNOWN`

**When it fires**: A verdict cell value in `issue-matrix.md` is not in the closed-set allow-list (`fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission`).

**JSON stability**: this code string is stable across minor releases; consumers may match it as an opaque identifier.

**Remediation**:
1. Replace the unknown verdict with one of: `fixed`, `verified-already-fixed`, `deferred-with-followup`, or `in-mission`.
2. `deferred` (without `-with-followup`) is not valid; use `deferred-with-followup` and add a follow-up handle to `evidence_ref`.
3. `in-mission` declares the issue is being closed by a later WP in *this* mission. It is accepted at per-WP `approved`, but is rejected on the `done` transition (mission merge) — resolve it to a terminal verdict (`fixed` / `verified-already-fixed` / `deferred-with-followup`) before the mission lands.
4. Backtick-quoted verdicts (`` `fixed` ``) are accepted; the backticks are stripped during parsing.

**Body example**:

```text
MISSION_REVIEW_ISSUE_MATRIX_VERDICT_UNKNOWN: Row for issue '#123': verdict 'deferred' is not in the allowed set
```

---

## ISSUE_MATRIX_MULTI_TABLE

**Code**: `MISSION_REVIEW_ISSUE_MATRIX_MULTI_TABLE`

**When it fires**: `issue-matrix.md` contains more than one Markdown table at the top level. The schema requires exactly one table (additional prose sections are allowed).

**JSON stability**: this code string is stable across minor releases; consumers may match it as an opaque identifier.

**Remediation**:
1. Consolidate all issue rows into a single Markdown table.
2. Move summary aggregation (e.g., verdict counts) to a prose section below the table, not a second table.
3. If the file was authored with separate product-findings / workflow-papercuts / pre-existing-failures tables, merge them into one table with an optional `scope` column to distinguish categories.

**Body example**:

```text
MISSION_REVIEW_ISSUE_MATRIX_MULTI_TABLE: issue-matrix.md contains 3 Markdown tables; exactly one is allowed.
```

---

## ISSUE_MATRIX_EVIDENCE_REF_EMPTY

**Code**: `MISSION_REVIEW_ISSUE_MATRIX_EVIDENCE_REF_EMPTY`

**When it fires**: The `evidence_ref` cell for a row in `issue-matrix.md` is empty or whitespace-only.

**JSON stability**: this code string is stable across minor releases; consumers may match it as an opaque identifier.

**Remediation**:
1. Add a concrete evidence reference: a commit SHA, test path, PR link, or file:line reference that closes the issue.
2. For deferred issues, the evidence_ref must contain a follow-up issue handle (e.g., `Follow-up: #NNN` or a URL matching `#\d+`).
3. Do not use placeholder values such as `TBD` or `N/A`; these will also be flagged by `ISSUE_MATRIX_DEFERRED_WITHOUT_HANDLE`.

**Body example**:

```text
MISSION_REVIEW_ISSUE_MATRIX_EVIDENCE_REF_EMPTY: Row for issue '#456': evidence_ref is empty.
```

---

## ISSUE_MATRIX_DEFERRED_WITHOUT_HANDLE

**Code**: `MISSION_REVIEW_ISSUE_MATRIX_DEFERRED_WITHOUT_HANDLE`

**When it fires**: A row has verdict `deferred-with-followup` but the `evidence_ref` cell contains no follow-up handle (no `#NNN` reference and no `Follow-up:` substring).

**JSON stability**: this code string is stable across minor releases; consumers may match it as an opaque identifier.

**Remediation**:
1. Add a GitHub issue reference to `evidence_ref`, e.g. `Follow-up: #789` or `see https://github.com/.../issues/789`.
2. The handle must match regex `#\d+` or contain the substring `Follow-up:`.
3. A bare `deferred-with-followup` with no follow-up handle is a Gate 4 hard fail per the mission-review doctrine.

**Body example**:

```text
MISSION_REVIEW_ISSUE_MATRIX_DEFERRED_WITHOUT_HANDLE: Row for issue '#789': verdict is 'deferred-with-followup' but evidence_ref contains no follow-up handle; got: 'TBD'
```

---

## GATE_RECORD_MISSING

**Code**: `MISSION_REVIEW_GATE_RECORD_MISSING`

**When it fires**: A gate record expected in the `mission-review-report.md` frontmatter (`gates_recorded`) is absent or has an invalid structure.

**JSON stability**: this code string is stable across minor releases; consumers may match it as an opaque identifier.

**Remediation**:
1. Re-run `spec-kitty review` to regenerate the report with all gate records.
2. If the report was manually edited, restore the `gates_recorded` block to the structure: `id`, `name`, `command`, `exit_code`, `result`.
3. Valid gate ids are: `gate_1` (wp_lane_check), `gate_2` (dead_code_scan), `gate_3` (ble001_audit), `gate_4` (report_writer).

**Body example**:

```text
MISSION_REVIEW_GATE_RECORD_MISSING: Expected gate_2 (dead_code_scan) record not found in mission-review-report.md
```

---

## MISSION_EXCEPTION_INVALID

**Code**: `MISSION_REVIEW_MISSION_EXCEPTION_INVALID`

**When it fires**: A `mission-exception.md` file exists but does not conform to the required structure, or a post-merge review requires exception documentation that is absent.

**JSON stability**: this code string is stable across minor releases; consumers may match it as an opaque identifier.

**Remediation**:
1. Ensure `mission-exception.md` contains a clear description of the exception, its scope, and the approver.
2. For post-merge mode when exceptions occurred (e.g., SaaS endpoint unavailable during E2E), document them in `mission-exception.md` before running `spec-kitty review`.
3. If no exception is needed, do not create the file; its presence signals to reviewers that an exception was granted.

**Body example**:

```text
MISSION_REVIEW_MISSION_EXCEPTION_INVALID: mission-exception.md is present but missing required 'Approver:' field
```

---

## TEST_EXTRA_MISSING

**Code**: `MISSION_REVIEW_TEST_EXTRA_MISSING`

**When it fires**: `pytest` is not importable from the active Python interpreter. This prevents the dead-code scan and BLE001 audit from running.

**JSON stability**: this code string is stable across minor releases; consumers may match it as an opaque identifier.

**Remediation**:
1. Source/dev checkout: run `uv sync --extra test` to install the test extra in the current virtual environment.
2. uv tool install: run `uv tool install --force --with pytest <current-tool-source>` to repair the tool environment. For PyPI installs this is `spec-kitty-cli==<current-version>`; for local/source tool installs this preserves the uv receipt source path.
3. Verify with `python -c "import pytest; print(pytest.__version__)"` using the interpreter that runs `spec-kitty`.
4. If using a non-uv environment, install pytest directly into the interpreter that runs `spec-kitty`.

**Body example**:

```text
MISSION_REVIEW_TEST_EXTRA_MISSING: pytest is not importable from the active Python interpreter. Run `<remediation command>` to install pytest into that interpreter, then retry.
```

---

## LIGHTWEIGHT_REVIEW_MISSING_BASELINE

**Code**: `LIGHTWEIGHT_REVIEW_MISSING_BASELINE`

**When it fires**: `spec-kitty review --mode lightweight` is run against a modern mission (one whose `meta.json` has a populated `mission_id` — the ULID introduced by mission 083) whose `baseline_merge_commit` is still `null`. Without a baseline commit the dead-code scan cannot compute a diff, so the gate now fails-hard instead of silently passing. See issue [#989](https://github.com/Priivacy-ai/spec-kitty/issues/989).

**JSON stability**: this code string is stable across minor releases; consumers may match it as an opaque identifier.

**Remediation**:
1. Run `spec-kitty merge` to bake `baseline_merge_commit` into `meta.json`, then re-run `spec-kitty review --mode lightweight`.
2. Or, if the mission is already merged, run `spec-kitty review --mode post-merge` instead.

**Body example**:

```text
LIGHTWEIGHT_REVIEW_MISSING_BASELINE: dead-code scan cannot run without baseline_merge_commit on a modern mission. Run `spec-kitty merge` to bake one, or use `--mode post-merge` after merge.
```

---

## LEGACY_MISSION_DEAD_CODE_SKIP

**Code**: `LEGACY_MISSION_DEAD_CODE_SKIP`

**When it fires**: `spec-kitty review --mode lightweight` is run against a genuinely legacy mission (one whose `meta.json` has no `mission_id` field — i.e., predates the mission 083 canonical-identity migration) whose `baseline_merge_commit` is still `null`. The dead-code scan is skipped, but the verdict is tagged with this code so the skip is greppable and cannot be confused with a clean post-083 scan.

**JSON stability**: this code string is stable across minor releases; consumers may match it as an opaque identifier.

**Remediation**:
1. Run `spec-kitty migrate backfill-identity` to bring the legacy mission onto the canonical identity schema, then re-run review.
2. Or, accept the skipped scan as historical and continue.

**Body example**:

```text
LEGACY_MISSION_DEAD_CODE_SKIP: dead-code scan skipped on a pre-083 mission. Run `spec-kitty migrate backfill-identity` to bring the mission onto the canonical identity schema.
```

---

## ENV_SKEW

**Code**: `MISSION_REVIEW_ENV_SKEW`

**When it fires**: the active interpreter's installed `typer`/`click` versions diverge from the exact versions pinned in `uv.lock`. A local `.venv` built without `--frozen` can drift onto a newer `typer`/`click` than CI installs — including a `typer>=0.26` release that vendors `click` internally and stops re-exporting it — so local CLI-shard test runs can silently diverge from CI. This preflight is **warn-loud by default**: divergence prints a warning and `spec-kitty review` proceeds. Fail-closed is opt-in via the `SPEC_KITTY_ENV_SKEW_FAIL_CLOSED` environment variable (truthy: `1`/`true`/`yes`/`y`/`on`), in which case the command exits non-zero instead of proceeding — this is deliberately opt-in so a legitimately forward-compat dev loop (testing against a newer `typer`/`click` ahead of the repo's pin bump) is never bricked by default.

Unlike the other codes in this file, `MISSION_REVIEW_ENV_SKEW` is emitted by the standalone environment preflight in `_test_env_check.py` (module-level constant, not a `MissionReviewDiagnostic` StrEnum member) — it guards the local dev environment itself, not a mission's verdict findings.

**JSON stability**: this code string is stable across minor releases; consumers may match it as an opaque identifier.

**Remediation**:
1. Run `uv sync --frozen --all-extras` from the repository root to restore the exact `typer`/`click` versions pinned in `uv.lock`.
2. Re-run `spec-kitty review` (or your local test command) to confirm the warning clears.
3. If you are intentionally testing against a newer `typer`/`click` ahead of the repo's pin bump, the warning is informational only (default warn-loud mode) — no action is required unless `SPEC_KITTY_ENV_SKEW_FAIL_CLOSED` is set.

**Body example**:

```text
MISSION_REVIEW_ENV_SKEW: local typer/click versions diverge from uv.lock:
  - typer: locked=0.24.2, installed=0.26.0
Run `uv sync --frozen --all-extras` to restore parity with CI.
```
