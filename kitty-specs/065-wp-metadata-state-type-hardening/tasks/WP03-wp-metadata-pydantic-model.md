---
work_package_id: WP03
title: WPMetadata Pydantic Model (#410)
dependencies: [WP01]
requirement_refs:
- FR-005
- FR-006
- NFR-004
- C-003
- C-005
planning_base_branch: feature/metadata-state-type-hardening
merge_target_branch: feature/metadata-state-type-hardening
branch_strategy: Planning artifacts for this feature were generated on feature/metadata-state-type-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/metadata-state-type-hardening unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T013
phase: Phase 2 - Typed Domain Models
assignee: ''
agent: "opencode"
shell_pid: "152804"
history:
- at: '2026-04-06T05:37:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/status/wp_metadata.py
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/status/wp_metadata.py
- src/specify_cli/status/__init__.py
- tests/specify_cli/status/test_wp_metadata.py
task_type: implement
agent_profile: python-implementer
---

# Work Package Prompt: WP03 – WPMetadata Pydantic Model (#410)

## IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete.
- **Report progress**: As you address each feedback item, update the Activity Log.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- **Objective**: Create a `WPMetadata` Pydantic v2 model with typed fields for all known WP frontmatter keys, a `read_wp_frontmatter()` loader, and CI validation that all existing WP files pass validation.
- **SC-004**: A CI test validates all WP files in `kitty-specs/` against `WPMetadata.model_validate()` and passes with zero failures, without modifying any WP file.
- **NFR-004**: Round-trip safe — serializing back to YAML preserves field order and values.
- **C-003**: All active WP files pass validation without manual edits.
- **C-005**: No new runtime dependencies (Pydantic already present).

## Context & Constraints

- **Upstream issue**: #410 — WP frontmatter has no schema
- **Data model**: `kitty-specs/065-wp-metadata-state-type-hardening/data-model.md` (WPMetadata section)
- **Research**: `kitty-specs/065-wp-metadata-state-type-hardening/research.md` (Finding 5 — Field Inventory)
- **Plan**: `kitty-specs/065-wp-metadata-state-type-hardening/plan.md` (WP03 section)

**Key design decisions**:
- `frozen=True`: WPMetadata is a value object (entity-value-object-classification tactic)
- `extra="allow"`: Phase 1 — backward compatibility with unknown fields. Changed to `extra="forbid"` in WP04.
- `populate_by_name=True`: Accept both alias and field name

**Doctrine**:
- `tdd-red-green-refactor.tactic.yaml` — new model creation
- `acceptance-test-first.tactic.yaml`
- `refactoring-encapsulate-record.tactic.yaml` — replace raw dict access with typed model
- `refactoring-extract-first-order-concept.tactic.yaml` — WPMetadata is the hidden concept
- `entity-value-object-classification.tactic.yaml` — frozen, equality by attributes
- `refactoring-strangler-fig.tactic.yaml` — `extra="allow"` coexists with legacy

**Cross-cutting**:
- **Self Observation Protocol** (NFR-009): Write observation log at session end.
- **Quality Gate** (DIRECTIVE_030): Tests + type checks must pass before `for_review`.

## Branch Strategy

- **Implementation command**: `spec-kitty implement WP03 --base WP01`
- **Planning base branch**: `feature/metadata-state-type-hardening`
- **Merge target branch**: `feature/metadata-state-type-hardening`

## Subtasks & Detailed Guidance

### Subtask T009 – Create WPMetadata Pydantic model

- **Purpose**: Define the typed schema for WP frontmatter as a Pydantic v2 model.
- **Steps**:
  1. Create `src/specify_cli/status/wp_metadata.py`
  2. Implement `WPMetadata` exactly as specified in `data-model.md`:
     ```python
     from pydantic import BaseModel, ConfigDict, Field
     from typing import Any

     class WPMetadata(BaseModel):
         model_config = ConfigDict(
             frozen=True,
             extra="allow",
             populate_by_name=True,
         )

         # ── Required: identity ─────────────────────────────────
         work_package_id: str        # Pattern: r"^WP\d{2,}$"
         title: str                  # min_length=1

         # ── Required: dependency graph ─────────────────────────
         dependencies: list[str] = Field(default_factory=list)

         # ── Required: branch contract (optional at planning) ──
         base_branch: str | None = None
         base_commit: str | None = None   # Pattern: r"^[0-9a-f]{7,40}$"
         created_at: str | None = None    # ISO 8601

         # ── Optional: planning metadata ────────────────────────
         planning_base_branch: str | None = None
         merge_target_branch: str | None = None
         branch_strategy: str | None = None
         requirement_refs: list[str] = Field(default_factory=list)

         # ── Optional: execution context ────────────────────────
         execution_mode: str | None = None
         owned_files: list[str] = Field(default_factory=list)
         authoritative_surface: str | None = None

         # ── Optional: workflow metadata ────────────────────────
         subtasks: list[Any] = Field(default_factory=list)
         phase: str | None = None
         assignee: str | None = None
         agent: str | None = None
         shell_pid: int | None = None
         history: list[Any] = Field(default_factory=list)

         # ── Observed-in-practice fields ────────────────────────
         mission_id: str | None = None
         wp_code: str | None = None
         branch_strategy_override: str | None = None
     ```
  3. Note: `shell_pid` may arrive as a string from YAML; handle with a validator (see T011).
  4. Verify the import from Pydantic v2 works:
     ```bash
     python -c "from specify_cli.status.wp_metadata import WPMetadata; print('OK')"
     ```
- **Files**:
  - `src/specify_cli/status/wp_metadata.py` (NEW)
- **Validation**:
  - [ ] File created with all fields from data-model.md
  - [ ] Import succeeds

### Subtask T010 – Implement read_wp_frontmatter() loader

- **Purpose**: Provide a convenience function that wraps `FrontmatterManager` and returns a typed `WPMetadata` tuple.
- **Steps**:
  1. In `wp_metadata.py`, add:
     ```python
     from pathlib import Path
     from specify_cli.frontmatter import FrontmatterManager

     def read_wp_frontmatter(path: Path) -> tuple[WPMetadata, str]:
         """Load and validate WP frontmatter.
         
         Returns (WPMetadata, body_text).
         Raises pydantic.ValidationError on invalid data.
         """
         fm = FrontmatterManager()
         frontmatter_dict, body = fm.read(path)
         return WPMetadata.model_validate(frontmatter_dict), body
     ```
  2. Verify `FrontmatterManager.read()` returns `(dict, str)`:
     ```bash
     rg "def read\b" src/specify_cli/frontmatter.py
     ```
  3. Handle edge cases:
     - If `FrontmatterManager.read()` returns `None` for the dict, raise a clear error
     - If the frontmatter contains YAML types that Pydantic can't coerce, add pre-processing
  4. Test with an actual WP file:
     ```bash
     python -c "
     from pathlib import Path
     from specify_cli.status.wp_metadata import read_wp_frontmatter
     meta, body = read_wp_frontmatter(Path('kitty-specs/065-wp-metadata-state-type-hardening/tasks/WP01-validate-only-bootstrap-fix.md'))
     print(meta.work_package_id, meta.title)
     "
     ```
- **Files**:
  - `src/specify_cli/status/wp_metadata.py`
- **Validation**:
  - [ ] `read_wp_frontmatter()` returns `(WPMetadata, str)` for valid files
  - [ ] Raises `ValidationError` for malformed files

### Subtask T011 – Add field validators

- **Purpose**: Add Pydantic field validators for structured fields where data quality is critical.
- **Steps**:
  1. Add validators to `WPMetadata`:
     ```python
     from pydantic import field_validator
     import re

     @field_validator("work_package_id")
     @classmethod
     def validate_wp_id(cls, v: str) -> str:
         if not re.match(r"^WP\d{2,}$", v):
             raise ValueError(f"Invalid work_package_id: {v!r} (must match WP##)")
         return v

     @field_validator("base_commit")
     @classmethod
     def validate_base_commit(cls, v: str | None) -> str | None:
         if v is not None and not re.match(r"^[0-9a-f]{7,40}$", v):
             raise ValueError(f"Invalid base_commit: {v!r} (must be hex SHA)")
         return v

     @field_validator("title")
     @classmethod
     def validate_title(cls, v: str) -> str:
         if not v.strip():
             raise ValueError("title must not be empty")
         return v

     @field_validator("shell_pid", mode="before")
     @classmethod
     def coerce_shell_pid(cls, v: Any) -> int | None:
         if v is None or v == "":
             return None
         return int(v)
     ```
  2. The `shell_pid` coercion is critical: YAML frontmatter may store it as a string (e.g., `shell_pid: "18377"`).
  3. Run a quick check against a real WP file to ensure validators don't reject valid data:
     ```bash
     python -c "
     from pathlib import Path
     from specify_cli.status.wp_metadata import read_wp_frontmatter
     import glob
     for f in glob.glob('kitty-specs/*/tasks/WP*.md')[:5]:
         try:
             meta, _ = read_wp_frontmatter(Path(f))
             print(f'OK: {f} -> {meta.work_package_id}')
         except Exception as e:
             print(f'FAIL: {f} -> {e}')
     "
     ```
- **Files**:
  - `src/specify_cli/status/wp_metadata.py`
- **Validation**:
  - [ ] `work_package_id` validator rejects `"WP"`, `"wp01"`, `"WP1"` (too few digits)
  - [ ] `base_commit` validator rejects `"not-a-sha"`, accepts `"abc1234"`
  - [ ] `shell_pid` coercion handles string `"18377"` and empty string `""`
  - [ ] No validator breaks on real WP files

### Subtask T012 – Write WPMetadata unit tests

- **Purpose**: TDD red-green-refactor — comprehensive unit tests for the model.
- **Steps**:
  1. Create `tests/specify_cli/status/test_wp_metadata.py`
  2. Write tests covering:
     ```python
     class TestWPMetadata:
         def test_valid_minimal(self):
             """Minimal required fields produce a valid instance."""
             meta = WPMetadata(work_package_id="WP01", title="Setup")
             assert meta.work_package_id == "WP01"
             assert meta.dependencies == []

         def test_valid_full(self):
             """All fields populated."""
             ...

         def test_missing_required_field(self):
             """Missing work_package_id raises ValidationError."""
             with pytest.raises(ValidationError):
                 WPMetadata(title="No ID")

         def test_invalid_wp_id_pattern(self):
             """work_package_id must match WP## pattern."""
             with pytest.raises(ValidationError):
                 WPMetadata(work_package_id="WP1", title="Bad ID")

         def test_invalid_base_commit(self):
             """base_commit must be hex SHA."""
             with pytest.raises(ValidationError):
                 WPMetadata(work_package_id="WP01", title="T", base_commit="not-hex")

         def test_extra_fields_preserved(self):
             """Unknown fields preserved with extra='allow'."""
             meta = WPMetadata(work_package_id="WP01", title="T", custom_field="value")
             assert meta.model_extra["custom_field"] == "value"

         def test_frozen(self):
             """Model is immutable."""
             meta = WPMetadata(work_package_id="WP01", title="T")
             with pytest.raises(ValidationError):
                 meta.title = "Changed"

         def test_shell_pid_string_coercion(self):
             """shell_pid accepts string input from YAML."""
             meta = WPMetadata(work_package_id="WP01", title="T", shell_pid="18377")
             assert meta.shell_pid == 18377

         def test_shell_pid_empty_string(self):
             """Empty string shell_pid coerced to None."""
             meta = WPMetadata(work_package_id="WP01", title="T", shell_pid="")
             assert meta.shell_pid is None
     ```
  3. Run tests:
     ```bash
     pytest tests/specify_cli/status/test_wp_metadata.py -x -v
     ```
- **Files**:
  - `tests/specify_cli/status/test_wp_metadata.py` (NEW)
- **Parallel?**: Yes — can be written alongside T013.
- **Validation**:
  - [ ] All unit tests pass
  - [ ] Edge cases covered (empty, None, invalid, extra fields, frozen)

### Subtask T013 – Write CI validation test for kitty-specs/ WP files

- **Purpose**: Ensure all existing WP files validate without modification (C-003).
- **Steps**:
  1. In `tests/specify_cli/status/test_wp_metadata.py` (or a separate file), add a CI test:
     ```python
     import glob
     from pathlib import Path

     def test_all_kitty_specs_wp_files_validate():
         """All active WP files pass WPMetadata.model_validate()."""
         wp_files = glob.glob("kitty-specs/*/tasks/WP*.md")
         assert len(wp_files) > 0, "No WP files found — check working directory"
         
         failures = []
         for wp_file in wp_files:
             try:
                 meta, body = read_wp_frontmatter(Path(wp_file))
             except Exception as e:
                 failures.append(f"{wp_file}: {e}")
         
         assert not failures, f"WP files failed validation:\n" + "\n".join(failures)
     ```
  2. Run from repo root (cwd must contain `kitty-specs/`):
     ```bash
     pytest tests/specify_cli/status/test_wp_metadata.py -x -v -k "all_kitty_specs"
     ```
  3. If any files fail, investigate:
     - Missing required fields? → Make the field optional with a default
     - Unexpected types? → Add a pre-validator or coercion
     - Do NOT modify the WP files; adjust the model to accommodate them
  4. Export `WPMetadata` and `read_wp_frontmatter` from `status/__init__.py`:
     ```bash
     rg "from.*import" src/specify_cli/status/__init__.py
     ```
     Add: `from .wp_metadata import WPMetadata, read_wp_frontmatter`
- **Files**:
  - `tests/specify_cli/status/test_wp_metadata.py`
  - `src/specify_cli/status/__init__.py` (add exports)
- **Parallel?**: Yes — can be written alongside T012.
- **Validation**:
  - [ ] CI test passes against all existing WP files
  - [ ] No WP files required manual editing
  - [ ] Exports added to `__init__.py`

## Definition of Done

- [ ] `WPMetadata` model created with all fields from data-model.md (T009)
- [ ] `read_wp_frontmatter()` loader works (T010)
- [ ] Field validators enforce patterns (T011)
- [ ] Unit tests pass (T012)
- [ ] CI validation test passes against all kitty-specs/ WP files (T013)
- [ ] Exports in `status/__init__.py`
- [ ] Full test suite passes with zero regressions
- [ ] Type checks pass

## Risks & Mitigations

- **Risk**: Old WP files may have unexpected field values that break validators. **Mitigation**: CI test (T013) runs first; adjust model (make fields optional, add coercions) before tightening.
- **Risk**: `FrontmatterManager.read()` may return types Pydantic can't coerce. **Mitigation**: Add `mode="before"` validators for known problematic fields (e.g., `shell_pid`).

## Review Guidance

- Verify all fields from data-model.md are present in the model
- Check that `extra="allow"` is set (not `forbid` — that's WP04)
- Confirm the CI test runs against a meaningful number of WP files (not zero)
- Verify `read_wp_frontmatter()` wraps `FrontmatterManager` correctly

## Activity Log

- 2026-04-06T05:37:00Z – system – Prompt created.
- 2026-04-06T10:36:26Z – opencode – shell_pid=152804 – Started implementation via action command
- 2026-04-06T11:04:02Z – opencode – shell_pid=152804 – WPMetadata Pydantic v2 model + read_wp_frontmatter loader + field validators + 39 tests + CI validation 408/408 pass
- 2026-04-06T11:05:56Z – opencode – shell_pid=152804 – Started review via action command
- 2026-04-06T11:06:37Z – opencode – shell_pid=152804 – Review passed: All 22 fields from data-model.md present, validators correct (wp_id, title, base_commit, shell_pid/phase coercion), legacy normalization handles work_package_title and string deps, 39 tests comprehensive, CI validation 408/408, exports clean. Full suite 8634 passed.
