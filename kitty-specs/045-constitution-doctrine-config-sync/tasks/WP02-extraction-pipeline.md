---
work_package_id: WP02
title: Extraction Pipeline
lane: "done"
dependencies: [WP01]
base_branch: develop
base_commit: 74212b4708320dfe76a0b529be45164b7b676d9c
created_at: '2026-02-15T22:46:18.262223+00:00'
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
phase: Phase 1 - Foundation
assignee: ''
agent: claude
shell_pid: '542720'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-02-15T22:11:29Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Extraction Pipeline

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

- Implement `Extractor` class that maps parsed constitution sections to validated Pydantic models
- Implement section-to-schema keyword mapping (heading → YAML field)
- Implement merge logic for data scattered across multiple sections
- Implement AI fallback interface (prompt template + subprocess stub)
- Implement YAML file writer that emits validated models to `.kittify/constitution/*.yaml`
- **All tests pass**, **mypy --strict clean**, **ruff clean**

**Success metrics**:

- Feed the real constitution through the extractor → verify governance.yaml has correct testing/quality values
- AI fallback prompt is well-structured and parseable
- Extraction is idempotent (FR-1.6)

## Context & Constraints

- **Spec**: `kitty-specs/045-constitution-doctrine-config-sync/spec.md` — FR-1.1 through FR-1.7
- **Plan**: `kitty-specs/045-constitution-doctrine-config-sync/plan.md` — AD-1 (hybrid parsing), AD-5 (AI fallback)
- **Data Model**: `kitty-specs/045-constitution-doctrine-config-sync/data-model.md` — state transitions diagram
- **Research**: `kitty-specs/045-constitution-doctrine-config-sync/research.md` — RQ-2 (AI fallback), RQ-5 (extractable sections)
- **Depends on WP01**: `ConstitutionParser`, `ConstitutionSection`, all Pydantic schemas, `emit_yaml()`

**Implementation command**: `spec-kitty implement WP02 --base WP01`

## Subtasks & Detailed Guidance

### Subtask T013 – Implement `Extractor` Class — Deterministic Pipeline

**Purpose**: Orchestrate the extraction from parsed sections to validated Pydantic models.

**Steps**:

1. Create `src/specify_cli/constitution/extractor.py`:

   ```python
   class Extractor:
       def __init__(self, parser: ConstitutionParser | None = None):
           self.parser = parser or ConstitutionParser()

       def extract(self, content: str) -> ExtractionResult:
           """Full extraction pipeline: parse → map → validate → return."""
           sections = self.parser.parse(content)
           governance = self._extract_governance(sections)
           agents = self._extract_agents(sections)
           directives = self._extract_directives(sections)
           metadata = self._build_metadata(content, sections)
           return ExtractionResult(
               governance=governance,
               agents=agents,
               directives=directives,
               metadata=metadata,
           )
   ```

2. Define `ExtractionResult` dataclass:

   ```python
   @dataclass
   class ExtractionResult:
       governance: GovernanceConfig
       agents: AgentsConfig
       directives: DirectivesConfig
       metadata: ExtractionMetadata
   ```

3. Implement `_extract_governance()`:
   - Iterate sections, look for governance-related headings
   - Merge `structured_data` from matching sections into `GovernanceConfig`
   - Use keyword extraction results to populate specific fields

**Files**:

- `src/specify_cli/constitution/extractor.py` (new)

### Subtask T014 – Implement Section-to-Schema Mapping

**Purpose**: Map constitution section headings to target schema fields using keyword matching.

**Steps**:

1. Define mapping dictionary:

   ```python
   SECTION_MAPPING: dict[str, tuple[str, str]] = {
       # keyword → (target_schema, target_field)
       "testing": ("governance", "testing"),
       "test": ("governance", "testing"),
       "coverage": ("governance", "testing"),
       "quality": ("governance", "quality"),
       "lint": ("governance", "quality"),
       "commit": ("governance", "commits"),
       "performance": ("governance", "performance"),
       "branch": ("governance", "branch_strategy"),
       "agent": ("agents", "profiles"),
       "directive": ("directives", "directives"),
       "constraint": ("directives", "directives"),
       "rule": ("directives", "directives"),
   }
   ```

2. Implement `_classify_section(heading: str) -> tuple[str, str] | None`:
   - Lowercase heading, check for keyword matches
   - Return best match (longest keyword match wins)
   - Return None for unclassifiable sections (→ AI fallback candidates)

**Files**:

- `src/specify_cli/constitution/extractor.py`

**Notes**:

- Case-insensitive matching
- A section can match multiple keywords — use first match or highest-ranked
- Unmapped sections become AI fallback candidates

### Subtask T015 – Implement Merge Logic for Multi-Section Extraction

**Purpose**: Handle cases where governance data is scattered across multiple constitution sections.

**Steps**:

1. Implement `_merge_governance_data(sections: list[ConstitutionSection]) -> GovernanceConfig`:
   - Collect all governance-classified sections
   - For each section, extract keyword data and table data
   - Merge into a single `GovernanceConfig`, with later sections overriding earlier ones for conflicts
   - Example: "Testing" section has `min_coverage`, "Quality Gates" section has `pr_approvals`

2. Implement `_merge_agents_data(sections: list[ConstitutionSection]) -> AgentsConfig`:
   - Similar merge for agent-related sections
   - Look for agent profiles in tables or lists

3. Implement `_merge_directives_data(sections: list[ConstitutionSection]) -> DirectivesConfig`:
   - Collect numbered items across sections
   - Assign auto-generated IDs: `DIR-001`, `DIR-002`, etc.

**Files**:

- `src/specify_cli/constitution/extractor.py`

**Notes**:

- Merging must be deterministic — same input → same output (idempotency requirement FR-1.6)
- Sort sections by document order to ensure consistent override behavior

### Subtask T016 – Implement AI Fallback Interface

**Purpose**: Define the interface for AI-assisted extraction of prose sections that can't be parsed deterministically.

**Steps**:

1. Create AI fallback function:

   ```python
   def extract_with_ai(
       prose_sections: list[ConstitutionSection],
       schema_hint: dict[str, Any],
   ) -> dict[str, Any]:
       """Send prose sections to configured AI agent for structured extraction.

       Returns extracted data as a dict matching the schema hint.
       If AI is unavailable, returns empty dict.
       """
   ```

2. Build structured prompt template:

   ```
   Extract structured configuration from the following constitution text.

   Expected output schema (YAML):
   {schema_hint as YAML}

   Constitution text:
   ---
   {prose_section_content}
   ---

   Respond with ONLY valid YAML matching the schema above.
   ```

3. Implement subprocess invocation (stub for now — actual agent invocation is out of scope for this WP):
   - Check if agent is configured via `.kittify/config.yaml`
   - Log info: "AI extraction available" or "AI agent not configured, skipping prose sections"
   - If agent available: build prompt, invoke via subprocess, parse YAML response
   - If unavailable: return empty dict, log warning

4. Integrate into `Extractor.extract()`:
   - After deterministic extraction, identify sections with `requires_ai = True`
   - If AI available: call `extract_with_ai()` and merge results
   - Update metadata: `extraction_mode = "hybrid"` if AI was used, `"deterministic"` if not

**Files**:

- `src/specify_cli/constitution/extractor.py`

**Parallel?**: Yes — independent of T013-T015 (deterministic pipeline).

**Notes**:

- The AI fallback is optional and graceful — extraction works without it
- For this WP, the subprocess invocation can be a stub that returns empty dict
- The actual agent integration will be refined in WP05

### Subtask T017 – Implement YAML File Writer

**Purpose**: Write validated Pydantic models to `.kittify/constitution/*.yaml` files.

**Steps**:

1. Implement `write_extraction_result(result: ExtractionResult, constitution_dir: Path) -> None`:

   ```python
   def write_extraction_result(result: ExtractionResult, constitution_dir: Path) -> None:
       """Write all YAML files from an extraction result."""
       constitution_dir.mkdir(parents=True, exist_ok=True)
       emit_yaml(result.governance, constitution_dir / "governance.yaml")
       emit_yaml(result.agents, constitution_dir / "agents.yaml")
       emit_yaml(result.directives, constitution_dir / "directives.yaml")
       emit_yaml(result.metadata, constitution_dir / "metadata.yaml")
   ```

2. Use `emit_yaml()` from WP01 (T011)

**Files**:

- `src/specify_cli/constitution/extractor.py`

**Notes**:

- Create directory if it doesn't exist
- Overwrite existing YAML files (one-way flow, no merge)

### Subtask T018 – Write Extractor Unit and Integration Tests

**Purpose**: Comprehensive test coverage for the extraction pipeline.

**Steps**:

1. Create `tests/specify_cli/constitution/test_extractor.py`:

2. **Unit tests**:
   - Test section classification (heading → schema mapping)
   - Test governance extraction from testing/quality sections
   - Test agents extraction from agent-related sections
   - Test directives extraction from numbered lists
   - Test metadata generation (hash, timestamp, mode)
   - Test merge logic (multiple sections → single config)

3. **Integration tests**:
   - Parse real constitution → extract → verify governance values match expectations
   - Test idempotency: extract twice → compare results (must be identical)
   - Test with AI unavailable → verify deterministic-only extraction works
   - Test with empty constitution → verify default values

4. **Edge case tests**:
   - Section with no keywords → skipped
   - Table with unexpected columns → best-effort parsing
   - Conflicting data across sections → last wins

**Files**:

- `tests/specify_cli/constitution/test_extractor.py`

**Target**: 12-15 tests covering all extractor methods and edge cases.

## Test Strategy

- **Unit tests**: Each extractor method tested independently with controlled fixtures
- **Integration test**: Full pipeline with real constitution content
- **Idempotency test**: Run extract twice, assert identical output
- **Run**: `pytest tests/specify_cli/constitution/test_extractor.py -v`
- **Type check**: `mypy --strict src/specify_cli/constitution/extractor.py`
- **Lint**: `ruff check src/specify_cli/constitution/`

## Risks & Mitigations

- **Risk**: Section mapping misclassifies headings → Use conservative keyword matching, test with real constitution
- **Risk**: Merge logic produces non-deterministic output → Sort sections by document order, use ordered dicts
- **Risk**: AI fallback returns malformed YAML → Validate with Pydantic, fall back to empty defaults

## Review Guidance

- Verify extraction is idempotent (same input → same output)
- Check section mapping covers the real constitution's headings
- Ensure AI fallback is graceful (no crash when agent unavailable)
- Confirm metadata correctly reports extraction_mode and section counts
- Test with the real constitution at `.kittify/memory/constitution.md`

## Activity Log

- 2026-02-15T22:11:29Z – system – lane=planned – Prompt created.
- 2026-02-15T22:46:18Z – claude – shell_pid=542720 – lane=doing – Assigned agent via workflow command
- 2026-02-15T23:00:42Z – claude – shell_pid=542720 – lane=for_review – Review passed: 3 fixes applied (input validation, max_wps key match, branch exact match)
- 2026-02-15T23:00:43Z – claude – shell_pid=542720 – lane=done – 90 tests pass, mypy strict clean, ruff clean
