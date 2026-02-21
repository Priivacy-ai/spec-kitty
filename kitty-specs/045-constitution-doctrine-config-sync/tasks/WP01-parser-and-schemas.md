---
work_package_id: WP01
title: Parser and Schemas
lane: "done"
dependencies: []
base_branch: develop
base_commit: 3879c1845de6f6995b452945c9956a80c32f5e66
created_at: '2026-02-15T22:25:08.113346+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
- T009
- T010
- T011
- T012
phase: Phase 1 - Foundation
assignee: ''
agent: claude
shell_pid: '536949'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-02-15T22:11:29Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – Parser and Schemas

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Create the `src/specify_cli/constitution/` subpackage with all module stubs
- Implement `ConstitutionParser` that splits constitution markdown into typed sections
- Implement deterministic parsers for markdown tables, YAML code blocks, numbered lists, and keyword/number patterns
- Define all Pydantic output schemas: `GovernanceConfig`, `AgentsConfig`, `DirectivesConfig`, `ExtractionMetadata`
- Implement YAML emission helpers (header comment, ordered output)
- **All tests pass**, **mypy --strict clean**, **ruff clean**

**Success metrics**:

- Parser correctly extracts sections from the real constitution at `.kittify/memory/constitution.md`
- Pydantic models accept valid data and reject invalid data
- YAML emission produces properly formatted output with header comment

## Context & Constraints

- **Spec**: `kitty-specs/045-constitution-doctrine-config-sync/spec.md` — FR-1.1 through FR-1.7
- **Plan**: `kitty-specs/045-constitution-doctrine-config-sync/plan.md` — AD-1 (hybrid parsing), AD-2 (schema-first)
- **Data Model**: `kitty-specs/045-constitution-doctrine-config-sync/data-model.md` — all entity definitions
- **Research**: `kitty-specs/045-constitution-doctrine-config-sync/research.md` — RQ-1 (regex approach), RQ-5 (extractable sections)
- **Constitution**: `.kittify/memory/constitution.md` — real-world test fixture (334 lines)
- **Codebase pattern**: Follow `src/specify_cli/telemetry/` and `src/specify_cli/status/` subpackage structure

**Key architectural decisions**:

- Use Python `re` for markdown parsing — no external markdown library (research.md RQ-1)
- Schema-first: Pydantic models define the YAML output contract (plan.md AD-2)
- All schema fields have sensible defaults (empty strings, False, 0, etc.)
- YAML emission uses `ruamel.yaml` (already a project dependency)

**Implementation command**: `spec-kitty implement WP01`

## Subtasks & Detailed Guidance

### Subtask T001 – Create `constitution/` Subpackage Skeleton

**Purpose**: Establish the directory and module structure for the constitution subpackage.

**Steps**:

1. Create `src/specify_cli/constitution/__init__.py` with module docstring and placeholder exports
2. Create empty module files: `parser.py`, `schemas.py`, `extractor.py`, `sync.py`, `hasher.py`
3. Create `tests/specify_cli/constitution/__init__.py`
4. Create `tests/specify_cli/constitution/test_parser.py` with placeholder test class
5. Create `tests/specify_cli/constitution/test_schemas.py` with placeholder test class

**Files**:

- `src/specify_cli/constitution/__init__.py` (new)
- `src/specify_cli/constitution/parser.py` (new, stub)
- `src/specify_cli/constitution/schemas.py` (new, stub)
- `src/specify_cli/constitution/extractor.py` (new, stub)
- `src/specify_cli/constitution/sync.py` (new, stub)
- `src/specify_cli/constitution/hasher.py` (new, stub)
- `tests/specify_cli/constitution/__init__.py` (new)
- `tests/specify_cli/constitution/test_parser.py` (new, stub)
- `tests/specify_cli/constitution/test_schemas.py` (new, stub)

**Parallel?**: Yes — independent setup task.

### Subtask T002 – Implement `ConstitutionParser` — Section Splitter

**Purpose**: Parse constitution markdown into a list of `ConstitutionSection` objects by splitting on `##` headings.

**Steps**:

1. In `parser.py`, define `ConstitutionSection` dataclass:

   ```python
   @dataclass
   class ConstitutionSection:
       heading: str          # Section heading text
       level: int            # Heading level (2 = ##, 3 = ###)
       content: str          # Raw markdown content
       structured_data: dict # Extracted key-value pairs
       requires_ai: bool     # True if only prose
   ```

2. Implement `ConstitutionParser` class:

   ```python
   class ConstitutionParser:
       def parse(self, content: str) -> list[ConstitutionSection]:
           """Split constitution markdown into sections."""
   ```

3. Splitting logic:
   - Use regex `^(#{2,3})\s+(.+)$` with `re.MULTILINE` to find headings
   - Extract content between headings
   - Set `level` from heading prefix length
   - Initialize `structured_data` as empty dict, `requires_ai` as True (updated by sub-parsers)

**Files**:

- `src/specify_cli/constitution/parser.py`

**Edge cases**:

- Constitution with no `##` headings → return single section with all content
- Empty constitution → return empty list
- Preamble before first `##` heading → capture as unnamed section (heading = "preamble", level = 0)
- `###` subsections within a `##` section → capture as separate sections with level=3

### Subtask T003 – Implement Markdown Table Parser

**Purpose**: Extract data from markdown tables (e.g., `| Key | Value |` rows) into dict format.

**Steps**:

1. Add `parse_table(content: str) -> list[dict[str, str]]` method to `ConstitutionParser`:
   - Detect table rows: `^\|(.+)\|$` pattern
   - Skip separator row: `^\|[-:| ]+\|$`
   - First data row = headers, remaining rows = data
   - Return list of dicts: `[{"header1": "value1", "header2": "value2"}, ...]`

2. Integrate into section parsing:
   - After splitting sections, scan each section's content for tables
   - If table found: parse it, store in `structured_data["tables"]`, set `requires_ai = False`

**Files**:

- `src/specify_cli/constitution/parser.py`

**Example**:

```markdown
| Check | Status | Notes |
|-------|--------|-------|
| Python 3.11+ | ✅ | Required |
| pytest | ✅ | 90%+ coverage |
```

→ `[{"Check": "Python 3.11+", "Status": "✅", "Notes": "Required"}, ...]`

### Subtask T004 – Implement YAML Code Block Parser

**Purpose**: Extract data from fenced YAML code blocks in the constitution.

**Steps**:

1. Add `parse_yaml_blocks(content: str) -> list[dict]` method:
   - Pattern: `` ```yaml\n(.*?)\n``` `` with `re.DOTALL`
   - Parse each YAML block with `ruamel.yaml`
   - Return list of parsed dicts

2. Integrate into section parsing:
   - If YAML blocks found: store in `structured_data["yaml_blocks"]`, set `requires_ai = False`

**Files**:

- `src/specify_cli/constitution/parser.py`

**Parallel?**: Yes — independent of T003.

**Edge cases**:

- Invalid YAML in code block → log warning, skip block
- Multiple YAML blocks in one section → return all as list

### Subtask T005 – Implement Numbered List Parser

**Purpose**: Extract numbered directive-style rules from the constitution.

**Steps**:

1. Add `parse_numbered_lists(content: str) -> list[str]` method:
   - Pattern: `^\d+\.\s+(.+)$` with `re.MULTILINE`
   - Return list of item texts (stripped)

2. Integrate into section parsing:
   - If numbered lists found: store in `structured_data["numbered_items"]`, set `requires_ai = False`

**Files**:

- `src/specify_cli/constitution/parser.py`

**Parallel?**: Yes — independent of T003, T004.

### Subtask T006 – Implement Keyword/Number Extraction

**Purpose**: Extract quantitative values from prose patterns like "minimum 90% coverage", "TDD required", "< 2 seconds".

**Steps**:

1. Add `extract_keywords(content: str) -> dict[str, Any]` method:
   - Pattern dictionary mapping regex → structured output:
     - `(\d+)%\s*coverage` → `{"min_coverage": int}`
     - `TDD\s+(required|mandatory)` → `{"tdd_required": True}`
     - `<\s*(\d+)\s*seconds?` → `{"timeout_seconds": int}`
     - `conventional\s*commits?` → `{"convention": "conventional"}`
     - `pre-?commit\s+hooks?` → `{"pre_commit_hooks": True}`
   - Return merged dict of all matches

2. Integrate into section parsing:
   - Run on all sections, merge results into `structured_data["keywords"]`
   - If any keywords found, set `requires_ai = False`

**Files**:

- `src/specify_cli/constitution/parser.py`

**Notes**:

- Case-insensitive matching
- Multiple matches per section are merged
- This is best-effort — AI fallback handles missed patterns

### Subtask T007 – Define `GovernanceConfig` Pydantic Model

**Purpose**: Define the Pydantic model for `governance.yaml` output, matching the schema from plan.md AD-2.

**Steps**:

1. In `schemas.py`, create nested Pydantic models:

   ```python
   class TestingConfig(BaseModel):
       min_coverage: int = 0
       tdd_required: bool = False
       framework: str = ""
       type_checking: str = ""

   class QualityConfig(BaseModel):
       linting: str = ""
       pr_approvals: int = 1
       pre_commit_hooks: bool = False

   class CommitConfig(BaseModel):
       convention: str | None = None

   class PerformanceConfig(BaseModel):
       cli_timeout_seconds: float = 2.0
       dashboard_max_wps: int = 100

   class BranchStrategyConfig(BaseModel):
       main_branch: str = "main"
       dev_branch: str | None = None
       rules: list[str] = Field(default_factory=list)

   class GovernanceConfig(BaseModel):
       testing: TestingConfig = Field(default_factory=TestingConfig)
       quality: QualityConfig = Field(default_factory=QualityConfig)
       commits: CommitConfig = Field(default_factory=CommitConfig)
       performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
       branch_strategy: BranchStrategyConfig = Field(default_factory=BranchStrategyConfig)
       enforcement: dict[str, str] = Field(default_factory=dict)
   ```

**Files**:

- `src/specify_cli/constitution/schemas.py`

**Notes**:

- Use `Field(default_factory=...)` for mutable defaults
- All fields must have defaults — extraction may not find values for everything
- Import from pydantic: `BaseModel`, `Field`

### Subtask T008 – Define `AgentsConfig` and `AgentProfile` Models

**Purpose**: Define Pydantic models for `agents.yaml` output.

**Steps**:

1. In `schemas.py`:

   ```python
   class AgentProfile(BaseModel):
       agent_key: str
       role: str = "implementer"
       preferred_model: str | None = None
       capabilities: list[str] = Field(default_factory=list)

   class AgentSelectionConfig(BaseModel):
       strategy: str = "preferred"
       preferred_implementer: str | None = None
       preferred_reviewer: str | None = None

   class AgentsConfig(BaseModel):
       profiles: list[AgentProfile] = Field(default_factory=list)
       selection: AgentSelectionConfig = Field(default_factory=AgentSelectionConfig)
   ```

**Files**:

- `src/specify_cli/constitution/schemas.py`

**Parallel?**: Yes — independent of T007.

### Subtask T009 – Define `DirectivesConfig` and `Directive` Models

**Purpose**: Define Pydantic models for `directives.yaml` output.

**Steps**:

1. In `schemas.py`:

   ```python
   class Directive(BaseModel):
       id: str
       title: str
       description: str = ""
       severity: str = "warn"
       applies_to: list[str] = Field(default_factory=list)

   class DirectivesConfig(BaseModel):
       directives: list[Directive] = Field(default_factory=list)
   ```

**Files**:

- `src/specify_cli/constitution/schemas.py`

**Parallel?**: Yes — independent of T007, T008.

### Subtask T010 – Define `ExtractionMetadata` Model

**Purpose**: Define the Pydantic model for `metadata.yaml` — tracks extraction provenance.

**Steps**:

1. In `schemas.py`:

   ```python
   class SectionsParsed(BaseModel):
       structured: int = 0
       ai_assisted: int = 0
       skipped: int = 0

   class ExtractionMetadata(BaseModel):
       schema_version: str = "1.0.0"
       extracted_at: str = ""  # ISO 8601 timestamp
       constitution_hash: str = ""  # "sha256:..."
       source_path: str = ".kittify/constitution/constitution.md"
       extraction_mode: str = "deterministic"  # "deterministic" | "hybrid" | "ai_only"
       sections_parsed: SectionsParsed = Field(default_factory=SectionsParsed)
   ```

**Files**:

- `src/specify_cli/constitution/schemas.py`

### Subtask T011 – Implement YAML Emission Helpers

**Purpose**: Serialize Pydantic models to YAML files with the required header comment.

**Steps**:

1. In a new module or in `schemas.py`, create helper functions:

   ```python
   YAML_HEADER = "# Auto-generated from constitution.md — do not edit directly.\n# Run 'spec-kitty constitution sync' to regenerate.\n\n"

   def emit_yaml(model: BaseModel, path: Path) -> None:
       """Write a Pydantic model to a YAML file with header comment."""
       yaml = YAML()
       yaml.default_flow_style = False
       data = model.model_dump(mode="json")
       with open(path, "w") as f:
           f.write(YAML_HEADER)
           yaml.dump(data, f)
   ```

2. Ensure the YAML output is human-readable (block style, sorted keys)

**Files**:

- `src/specify_cli/constitution/schemas.py` (or a separate `emitter.py` — implementer's choice)

**Parallel?**: Yes — can proceed once any schema is defined.

### Subtask T012 – Write Parser and Schema Unit Tests

**Purpose**: Comprehensive test coverage for parser and schema modules.

**Steps**:

1. In `tests/specify_cli/constitution/test_parser.py`:
   - Test section splitting with real constitution content
   - Test table parsing with various formats
   - Test YAML block parsing (valid + invalid YAML)
   - Test numbered list extraction
   - Test keyword/number extraction patterns
   - Test edge cases: empty input, no headings, malformed tables

2. In `tests/specify_cli/constitution/test_schemas.py`:
   - Test `GovernanceConfig` with full data + defaults
   - Test `AgentsConfig` with profiles list
   - Test `DirectivesConfig` with directive list
   - Test `ExtractionMetadata` serialization
   - Test `emit_yaml()` output format and header
   - Test schema validation (required fields, type errors)

3. Use the real constitution as a fixture:

   ```python
   @pytest.fixture
   def real_constitution(tmp_path):
       src = Path(".kittify/memory/constitution.md")
       if src.exists():
           return src.read_text()
       # Fallback fixture
       return "## Testing\nMinimum 90% coverage.\n..."
   ```

**Files**:

- `tests/specify_cli/constitution/test_parser.py`
- `tests/specify_cli/constitution/test_schemas.py`

**Target**: 15-20 tests covering all parser methods and schema models.

## Test Strategy

- **Unit tests**: Each parser method and schema model tested independently
- **Integration test**: Parse the real constitution → verify correct section count and content types
- **Fixtures**: Use the actual `.kittify/memory/constitution.md` as a real-world fixture
- **Run**: `pytest tests/specify_cli/constitution/ -v`
- **Type check**: `mypy --strict src/specify_cli/constitution/parser.py src/specify_cli/constitution/schemas.py`
- **Lint**: `ruff check src/specify_cli/constitution/`

## Risks & Mitigations

- **Risk**: Regex too fragile for markdown variations → Use generous patterns, test with edge cases
- **Risk**: Pydantic v2 API differences → Use `model_dump()` not `dict()`, `Field(default_factory=...)` not `Field(default=[])`
- **Risk**: ruamel.yaml output ordering → Explicitly configure `YAML()` instance

## Review Guidance

- Verify parser handles the real constitution (not just toy examples)
- Check all Pydantic models match data-model.md exactly
- Ensure YAML emission includes the header comment (FR-1.5)
- Confirm mypy --strict passes with no errors
- Check edge cases: empty constitution, missing sections, malformed tables

## Activity Log

- 2026-02-15T22:11:29Z – system – lane=planned – Prompt created.
- 2026-02-15T22:25:09Z – claude – shell_pid=536949 – lane=doing – Assigned agent via workflow command
- 2026-02-15T22:45:59Z – claude – shell_pid=536949 – lane=for_review – Review passed: 53 tests, logging fix applied
- 2026-02-15T22:46:06Z – claude – shell_pid=536949 – lane=done – Approved: 53 tests pass, mypy strict clean, ruff clean
