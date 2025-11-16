---
work_package_id: "WP05"
subtasks:
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
  - "T036"
  - "T037"
  - "T038"
  - "T039"
  - "T040"
title: "Research Citation Validators"
phase: "Phase 3 - Research Mission"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "96219"
history:
  - timestamp: "2025-01-16T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 – Research Citation Validators

## Objectives & Success Criteria

**Goal**: Create Python validators for research mission that enforce citation completeness and quality, providing clear feedback on bibliography issues.

**Success Criteria**:
- Citation validation module exists at `src/specify_cli/validators/research.py`
- Validates evidence-log.csv and source-register.csv
- Progressive validation: errors for completeness, warnings for format
- Supports BibTeX, APA, and Simple citation formats
- Clear, actionable error messages with line numbers and suggestions
- Integration with research mission review workflow
- All 10 subtasks (T031-T040) completed
- Unit tests achieve >90% coverage

## Context & Constraints

**Problem Statement**: Research mission has CSV templates (evidence-log.csv, source-register.csv) but they're not validated:
- Agents don't know if their citations are properly formatted
- No enforcement of source documentation
- CSV files could be empty or malformed without detection
- Research integrity depends on proper citation tracking

**User Story** (Spec User Story 3, Scenario 3):
> "When running `/spec-kitty.review`, validation checks that all sources are documented and cited properly"

**Supporting Documents**:
- Spec: `kitty-specs/005-refactor-mission-system/spec.md` (User Story 3, FR-009 through FR-011)
- Research: `kitty-specs/005-refactor-mission-system/research.md` (R2: Citation format validation - progressive validation decision)
- Data Model: `kitty-specs/005-refactor-mission-system/data-model.md` (CitationValidationResult, EvidenceEntry, SourceEntry)

**Design Decisions from Research**:
- **Strategy**: Progressive validation (completeness required, format warnings)
- **Formats**: Support BibTeX, APA, Simple - don't enforce single style
- **Implementation**: Python stdlib only (csv + re), zero new dependencies
- **Integration**: Called from research mission review workflow

**Validation Levels**:
1. **Level 1 - Completeness** (errors, blocking):
   - Citation field non-empty
   - source_type in valid values
   - Required columns present

2. **Level 2 - Format** (warnings, non-blocking):
   - Citation matches BibTeX, APA, or Simple pattern
   - If no match, warn with suggestions

3. **Level 3 - Quality** (future enhancement):
   - DOI/URL presence
   - Year reasonableness (1900-2030)
   - Source ID uniqueness

**Citation Format Patterns** (from research.md):
```python
BIBTEX_PATTERN = r'@\w+\{[\w-]+,'
APA_PATTERN = r'^[\w\s,\.]+\(\d{4}\)\.'
SIMPLE_PATTERN = r'^.+\(\d{4}\)\..+\.'
```

## Subtasks & Detailed Guidance

### Subtask T031 – Create validators directory

**Purpose**: Establish module directory for validation logic.

**Steps**:
1. Create directory: `src/specify_cli/validators/`
2. Create `__init__.py`:
   ```python
   """Validation modules for spec-kitty missions.

   This package contains mission-specific validators:
   - research.py: Citation and bibliography validation for research mission
   - paths.py: Path convention validation for all missions
   """

   from . import research, paths

   __all__ = ["research", "paths"]
   ```

3. Verify module is importable: `python -c "import specify_cli.validators"`

**Files**: `src/specify_cli/validators/__init__.py` (new)

**Parallel?**: No (foundation for other subtasks)

**Notes**: Simple directory structure. May be used by other missions in future.

---

### Subtask T032 – Create research.py module structure

**Purpose**: Establish research validation module with imports and exceptions.

**Steps**:
1. Create file: `src/specify_cli/validators/research.py`
2. Add module docstring and imports:
   ```python
   """Citation and bibliography validation for research mission.

   This module provides validation for research-specific artifacts:
   - evidence-log.csv: Research findings with citations
   - source-register.csv: Master bibliography

   Validation is progressive:
   - Level 1 (errors): Completeness checks (non-empty citations, valid types)
   - Level 2 (warnings): Format checks (BibTeX, APA, Simple patterns)
   - Level 3 (future): Quality checks (DOI presence, year validity)
   """

   from __future__ import annotations

   import csv
   import re
   from dataclasses import dataclass
   from datetime import datetime
   from pathlib import Path
   from typing import List, Literal, Optional

   # Citation format patterns (from research.md)
   BIBTEX_PATTERN = r'@\w+\{[\w-]+,'
   APA_PATTERN = r'^[\w\s,\.]+\(\d{4}\)\.'
   SIMPLE_PATTERN = r'^.+\(\d{4}\)\..+\.'

   VALID_SOURCE_TYPES = ['journal', 'conference', 'book', 'web', 'preprint']
   VALID_CONFIDENCE_LEVELS = ['high', 'medium', 'low']
   VALID_RELEVANCE_LEVELS = ['high', 'medium', 'low']
   VALID_SOURCE_STATUS = ['reviewed', 'pending', 'archived']
   ```

3. Define exception class:
   ```python
   class ResearchValidationError(Exception):
       """Raised when research validation fails."""
       pass
   ```

**Files**: `src/specify_cli/validators/research.py` (new)

**Parallel?**: No (foundation for validation functions)

**Notes**: Clear module organization, well-documented constants.

---

### Subtask T033 – Define validation result dataclasses

**Purpose**: Create typed result objects for validation outcomes.

**Steps**:
1. Add dataclasses to research.py (based on data-model.md):
   ```python
   @dataclass
   class CitationIssue:
       """Single citation validation issue."""
       line_number: int
       field: str
       issue_type: Literal["error", "warning"]
       message: str

   @dataclass
   class CitationValidationResult:
       """Result of citation validation."""
       file_path: Path
       total_entries: int
       valid_entries: int
       issues: List[CitationIssue]

       @property
       def has_errors(self) -> bool:
           """True if any errors (not warnings)."""
           return any(issue.issue_type == "error" for issue in self.issues)

       @property
       def error_count(self) -> int:
           return sum(1 for i in self.issues if i.issue_type == "error")

       @property
       def warning_count(self) -> int:
           return sum(1 for i in self.issues if i.issue_type == "warning")

       def format_report(self) -> str:
           """Format validation report for display."""
           output = [
               f"Citation Validation: {self.file_path.name}",
               f"Total entries: {self.total_entries}",
               f"Valid: {self.valid_entries}",
               f"Errors: {self.error_count}",
               f"Warnings: {self.warning_count}",
               ""
           ]

           if self.issues:
               errors = [i for i in self.issues if i.issue_type == "error"]
               warnings = [i for i in self.issues if i.issue_type == "warning"]

               if errors:
                   output.append("ERRORS (must fix):")
                   for issue in errors:
                       output.append(f"  Line {issue.line_number} ({issue.field}): {issue.message}")
                   output.append("")

               if warnings:
                   output.append("WARNINGS (recommended fixes):")
                   for issue in warnings:
                       output.append(f"  Line {issue.line_number} ({issue.field}): {issue.message}")

           return "\n".join(output)
   ```

**Files**: `src/specify_cli/validators/research.py`

**Parallel?**: No (required by validation functions)

**Notes**: Follow data-model.md specifications exactly.

---

### Subtask T034 – Implement BibTeX citation pattern

**Purpose**: Define and test BibTeX format detection.

**Steps**:
1. Add BibTeX validation function to research.py:
   ```python
   def is_bibtex_format(citation: str) -> bool:
       """Check if citation appears to be BibTeX format.

       BibTeX format: @article{key, author={...}, title={...}}

       Args:
           citation: Citation string to check

       Returns:
           True if citation matches BibTeX pattern
       """
       return bool(re.match(BIBTEX_PATTERN, citation.strip()))
   ```

2. Add test cases:
   ```python
   # In tests/unit/test_validators.py
   def test_bibtex_format_detection():
       valid_bibtex = [
           "@article{smith2024, author={Smith}, title={Title}}",
           "@inproceedings{jones2024,author={Jones et al.}}",
           "@book{brown2023,title={Book Title}}"
       ]
       for citation in valid_bibtex:
           assert is_bibtex_format(citation)

       invalid_bibtex = [
           "Smith, J. (2024). Title.",  # APA format
           "Smith (2024). Title. Journal.",  # Simple format
           "Not a citation"
       ]
       for citation in invalid_bibtex:
           assert not is_bibtex_format(citation)
   ```

**Files**: `src/specify_cli/validators/research.py`, `tests/unit/test_validators.py`

**Parallel?**: Yes (independent from APA and Simple patterns)

**Notes**: Pattern from research.md. Be permissive - match common BibTeX variants.

---

### Subtask T035 – Implement APA citation pattern

**Purpose**: Define and test APA format detection.

**Steps**:
1. Add APA validation function:
   ```python
   def is_apa_format(citation: str) -> bool:
       """Check if citation appears to be APA 7th edition format.

       APA format: Author, F. (Year). Title. Journal Name, vol(issue), pages.

       Args:
           citation: Citation string to check

       Returns:
           True if citation matches APA pattern
       """
       return bool(re.match(APA_PATTERN, citation.strip()))
   ```

2. Add test cases:
   ```python
   def test_apa_format_detection():
       valid_apa = [
           "Smith, J. (2024). Title of paper. Journal Name, 10(2), 123-145.",
           "Jones, A., & Lee, B. (2023). Study title. Conference Proceedings.",
           "Brown, C. (2025). Book title. Publisher Name."
       ]
       for citation in valid_apa:
           assert is_apa_format(citation)

       invalid_apa = [
           "@article{smith2024,...}",  # BibTeX
           "Smith 2024",  # Too simple
           ""
       ]
       for citation in invalid_apa:
           assert not is_apa_format(citation)
   ```

**Files**: `src/specify_cli/validators/research.py`, `tests/unit/test_validators.py`

**Parallel?**: Yes (independent from BibTeX and Simple)

**Notes**: APA 7th edition is most common in social sciences. Pattern from research.md.

---

### Subtask T036 – Implement Simple citation pattern

**Purpose**: Define fallback format for non-standard citations.

**Steps**:
1. Add Simple format validation:
   ```python
   def is_simple_format(citation: str) -> bool:
       """Check if citation matches simple citation format.

       Simple format: Author (Year). Title. Source.

       Args:
           citation: Citation string to check

       Returns:
           True if citation matches simple pattern
       """
       return bool(re.match(SIMPLE_PATTERN, citation.strip()))

   def detect_citation_format(citation: str) -> Literal["bibtex", "apa", "simple", "unknown"]:
       """Detect citation format.

       Args:
           citation: Citation string to analyze

       Returns:
           Detected format or "unknown"
       """
       if is_bibtex_format(citation):
           return "bibtex"
       elif is_apa_format(citation):
           return "apa"
       elif is_simple_format(citation):
           return "simple"
       else:
           return "unknown"
   ```

2. Add tests for format detection:
   ```python
   def test_citation_format_detection():
       assert detect_citation_format("@article{key,}") == "bibtex"
       assert detect_citation_format("Smith, J. (2024). Title.") == "apa"
       assert detect_citation_format("Smith (2024). Title. Source.") == "simple"
       assert detect_citation_format("not a citation") == "unknown"
   ```

**Files**: `src/specify_cli/validators/research.py`, `tests/unit/test_validators.py`

**Parallel?**: Yes (independent from BibTeX and APA)

**Notes**: Simple pattern is fallback. Be permissive to avoid blocking workflows.

---

### Subtask T037 – Implement validate_citations() for evidence-log

**Purpose**: Core validation logic for evidence-log.csv.

**Steps**:
1. Add main validation function:
   ```python
   def validate_citations(evidence_log_path: Path) -> CitationValidationResult:
       """Validate citations in evidence-log.csv.

       Performs progressive validation:
       - Level 1 (errors): Completeness checks
       - Level 2 (warnings): Format checks

       Args:
           evidence_log_path: Path to evidence-log.csv file

       Returns:
           Validation result with issues list
       """
       if not evidence_log_path.exists():
           return CitationValidationResult(
               file_path=evidence_log_path,
               total_entries=0,
               valid_entries=0,
               issues=[CitationIssue(
                   line_number=0,
                   field="file",
                   issue_type="error",
                   message=f"Evidence log not found: {evidence_log_path}"
               )]
           )

       issues = []
       total = 0
       valid = 0

       try:
           with open(evidence_log_path, 'r', encoding='utf-8') as f:
               reader = csv.DictReader(f)

               # Validate headers
               required_columns = ['timestamp', 'source_type', 'citation', 'key_finding', 'confidence', 'notes']
               if not all(col in reader.fieldnames for col in required_columns):
                   missing = [col for col in required_columns if col not in reader.fieldnames]
                   issues.append(CitationIssue(
                       line_number=1,
                       field="headers",
                       issue_type="error",
                       message=f"Missing required columns: {', '.join(missing)}"
                   ))
                   return CitationValidationResult(evidence_log_path, 0, 0, issues)

               # Validate each row
               for i, row in enumerate(reader, start=2):  # Line 2 is first data row
                   total += 1
                   entry_valid = True

                   # Level 1: Completeness checks (errors)
                   citation = row.get('citation', '').strip()
                   source_type = row.get('source_type', '').strip()
                   confidence = row.get('confidence', '').strip()
                   key_finding = row.get('key_finding', '').strip()

                   if not citation:
                       issues.append(CitationIssue(
                           line_number=i,
                           field="citation",
                           issue_type="error",
                           message="Citation is empty"
                       ))
                       entry_valid = False

                   if source_type not in VALID_SOURCE_TYPES:
                       issues.append(CitationIssue(
                           line_number=i,
                           field="source_type",
                           issue_type="error",
                           message=f"Invalid source_type '{source_type}'. Must be one of: {', '.join(VALID_SOURCE_TYPES)}"
                       ))
                       entry_valid = False

                   if confidence and confidence not in VALID_CONFIDENCE_LEVELS:
                       issues.append(CitationIssue(
                           line_number=i,
                           field="confidence",
                           issue_type="error",
                           message=f"Invalid confidence '{confidence}'. Must be one of: {', '.join(VALID_CONFIDENCE_LEVELS)}"
                       ))
                       entry_valid = False

                   if not key_finding:
                       issues.append(CitationIssue(
                           line_number=i,
                           field="key_finding",
                           issue_type="warning",
                           message="Key finding is empty - consider documenting main takeaway"
                       ))

                   # Level 2: Format checks (warnings)
                   if citation:  # Only check format if citation exists
                       fmt = detect_citation_format(citation)
                       if fmt == "unknown":
                           issues.append(CitationIssue(
                               line_number=i,
                               field="citation",
                               issue_type="warning",
                               message="Citation format not recognized. Consider using BibTeX or APA format for consistency."
                           ))

                   if entry_valid:
                       valid += 1

       except csv.Error as e:
           issues.append(CitationIssue(
               line_number=0,
               field="file",
               issue_type="error",
               message=f"CSV parsing error: {e}"
           ))

       return CitationValidationResult(
           file_path=evidence_log_path,
           total_entries=total,
           valid_entries=valid,
           issues=issues
       )
   ```

2. Test with sample evidence-log.csv files (valid and invalid)

**Files**: `src/specify_cli/validators/research.py`

**Parallel?**: No (core validation logic)

**Notes**: Most complex function in this WP. Progressive validation is key - errors block, warnings educate.

---

### Subtask T038 – Implement validate_source_register()

**Purpose**: Validate source-register.csv for bibliography completeness.

**Steps**:
1. Add validation function:
   ```python
   def validate_source_register(source_register_path: Path) -> CitationValidationResult:
       """Validate source registry.

       Checks:
       - All required columns present
       - source_id is unique
       - Citations non-empty
       - Relevance and status values valid

       Args:
           source_register_path: Path to source-register.csv

       Returns:
           Validation result
       """
       if not source_register_path.exists():
           return CitationValidationResult(
               file_path=source_register_path,
               total_entries=0,
               valid_entries=0,
               issues=[CitationIssue(
                   line_number=0,
                   field="file",
                   issue_type="error",
                   message=f"Source register not found: {source_register_path}"
               )]
           )

       issues = []
       total = 0
       valid = 0
       seen_ids = set()

       try:
           with open(source_register_path, 'r', encoding='utf-8') as f:
               reader = csv.DictReader(f)

               # Validate headers
               required_columns = ['source_id', 'citation', 'url', 'accessed_date', 'relevance', 'status']
               if not all(col in reader.fieldnames for col in required_columns):
                   missing = [col for col in required_columns if col not in reader.fieldnames]
                   issues.append(CitationIssue(
                       line_number=1,
                       field="headers",
                       issue_type="error",
                       message=f"Missing required columns: {', '.join(missing)}"
                   ))
                   return CitationValidationResult(source_register_path, 0, 0, issues)

               # Validate rows
               for i, row in enumerate(reader, start=2):
                   total += 1
                   entry_valid = True

                   source_id = row.get('source_id', '').strip()
                   citation = row.get('citation', '').strip()
                   relevance = row.get('relevance', '').strip()
                   status = row.get('status', '').strip()

                   # Check source_id unique
                   if not source_id:
                       issues.append(CitationIssue(
                           line_number=i,
                           field="source_id",
                           issue_type="error",
                           message="source_id is empty"
                       ))
                       entry_valid = False
                   elif source_id in seen_ids:
                       issues.append(CitationIssue(
                           line_number=i,
                           field="source_id",
                           issue_type="error",
                           message=f"Duplicate source_id '{source_id}' (must be unique)"
                       ))
                       entry_valid = False
                   else:
                       seen_ids.add(source_id)

                   # Check citation
                   if not citation:
                       issues.append(CitationIssue(
                           line_number=i,
                           field="citation",
                           issue_type="error",
                           message="Citation is empty"
                       ))
                       entry_valid = False

                   # Check relevance
                   if relevance and relevance not in VALID_RELEVANCE_LEVELS:
                       issues.append(CitationIssue(
                           line_number=i,
                           field="relevance",
                           issue_type="error",
                           message=f"Invalid relevance '{relevance}'. Must be: {', '.join(VALID_RELEVANCE_LEVELS)}"
                       ))
                       entry_valid = False

                   # Check status
                   if status and status not in VALID_SOURCE_STATUS:
                       issues.append(CitationIssue(
                           line_number=i,
                           field="status",
                           issue_type="error",
                           message=f"Invalid status '{status}'. Must be: {', '.join(VALID_SOURCE_STATUS)}"
                       ))
                       entry_valid = False

                   if entry_valid:
                       valid += 1

       except csv.Error as e:
           issues.append(CitationIssue(
               line_number=0,
               field="file",
               issue_type="error",
               message=f"CSV parsing error: {e}"
           ))

       return CitationValidationResult(
           file_path=source_register_path,
           total_entries=total,
           valid_entries=valid,
           issues=issues
       )
   ```

**Files**: `src/specify_cli/validators/research.py`

**Parallel?**: Yes (can implement alongside T037)

**Notes**: Source register is master bibliography - uniqueness is critical.

---

### Subtask T039 – Write comprehensive validator tests

**Purpose**: Ensure citation validators are thoroughly tested.

**Steps**:
1. Create test file: `tests/unit/test_validators.py`
2. Setup test fixtures:
   ```python
   import pytest
   import tempfile
   from pathlib import Path

   @pytest.fixture
   def valid_evidence_log(tmp_path):
       """Create valid evidence-log.csv for testing."""
       csv_file = tmp_path / "evidence-log.csv"
       csv_file.write_text(
           "timestamp,source_type,citation,key_finding,confidence,notes\n"
           "2025-01-15T10:00:00,journal,\"Smith (2024). Title. Journal.\",Finding text,high,Notes here\n"
           "2025-01-15T11:00:00,conference,\"@inproceedings{jones2024,}\",Another finding,medium,\n"
       )
       return csv_file

   @pytest.fixture
   def invalid_evidence_log(tmp_path):
       """Create invalid evidence-log.csv for testing."""
       csv_file = tmp_path / "evidence-log.csv"
       csv_file.write_text(
           "timestamp,source_type,citation,key_finding,confidence,notes\n"
           "2025-01-15T10:00:00,invalid_type,,Empty citation,high,\n"  # Invalid source_type, empty citation
           "2025-01-15T11:00:00,journal,Not a real citation,Finding,wrong,\n"  # Invalid confidence
       )
       return csv_file
   ```

3. Write comprehensive test suite:
   ```python
   from specify_cli.validators.research import (
       validate_citations,
       validate_source_register,
       is_bibtex_format,
       is_apa_format,
       is_simple_format,
       detect_citation_format
   )

   def test_validate_citations_valid_file(valid_evidence_log):
       """Valid evidence log should pass validation."""
       result = validate_citations(valid_evidence_log)
       assert result.total_entries == 2
       assert result.error_count == 0  # May have warnings but no errors

   def test_validate_citations_invalid_file(invalid_evidence_log):
       """Invalid evidence log should catch errors."""
       result = validate_citations(invalid_evidence_log)
       assert result.has_errors
       assert result.error_count >= 2  # Invalid source_type, empty citation

   def test_validate_citations_missing_file(tmp_path):
       """Missing file should return error."""
       result = validate_citations(tmp_path / "nonexistent.csv")
       assert result.has_errors
       assert "not found" in result.issues[0].message.lower()

   def test_citation_format_detection():
       """Should correctly identify citation formats."""
       assert detect_citation_format("@article{smith2024,}") == "bibtex"
       assert detect_citation_format("Smith, J. (2024). Title.") == "apa"
       assert detect_citation_format("Smith (2024). Title. Source.") == "simple"
       assert detect_citation_format("invalid") == "unknown"

   def test_validation_result_formatting():
       """Should format validation results clearly."""
       issues = [
           CitationIssue(2, "citation", "error", "Citation empty"),
           CitationIssue(3, "source_type", "warning", "Format warning")
       ]
       result = CitationValidationResult(
           file_path=Path("test.csv"),
           total_entries=3,
           valid_entries=1,
           issues=issues
       )
       report = result.format_report()
       assert "ERRORS" in report
       assert "WARNINGS" in report
       assert "Line 2" in report
   ```

4. Run tests: `pytest tests/unit/test_validators.py -v`
5. Check coverage: `pytest tests/unit/test_validators.py --cov=src/specify_cli/validators/research`

**Files**: `tests/unit/test_validators.py` (new)

**Parallel?**: Yes (can write while validation functions are implemented)

**Notes**: Comprehensive testing critical - validators must be reliable for research integrity.

---

### Subtask T040 – Integrate into review workflow

**Purpose**: Call citation validation from research mission review workflow.

**Steps**:
1. Locate research review command prompt: `.kittify/missions/research/commands/review.md`
2. Add validation step in review workflow (after "Load task prompt" section):
   ```markdown
   ## Citation Validation (Research Mission Specific)

   Before reviewing research tasks, validate all citations and sources:

   ```python
   from specify_cli.validators.research import validate_citations, validate_source_register
   from pathlib import Path

   # Validate evidence log
   evidence_log = FEATURE_DIR / "research" / "evidence-log.csv"
   if evidence_log.exists():
       result = validate_citations(evidence_log)
       if result.has_errors:
           print(result.format_report())
           print("\nERROR: Citation validation failed. Fix errors before proceeding.")
           exit(1)
       elif result.warning_count > 0:
           print(result.format_report())
           print("\nWarnings found - consider addressing for better citation quality.")

   # Validate source register
   source_register = FEATURE_DIR / "research" / "source-register.csv"
   if source_register.exists():
       result = validate_source_register(source_register)
       if result.has_errors:
           print(result.format_report())
           print("\nERROR: Source register validation failed.")
           exit(1)
   ```

   **Validation Requirements**:
   - All sources must be documented
   - Citations must be properly formatted (errors block, warnings inform)
   - Source IDs must be unique
   - Confidence levels must be assigned

   If validation fails, return task to implementer with specific citation issues to fix.
   ```

3. Test integration: Create research feature, populate CSVs, run review

**Files**: `.kittify/missions/research/commands/review.md`

**Parallel?**: No (depends on T037-T038)

**Notes**: This makes citation validation actionable - errors block review progression.

---

## Test Strategy

**Unit Testing (T039)**:

1. **Format Detection Tests**:
   - Test BibTeX pattern with various entry types (@article, @book, @inproceedings)
   - Test APA pattern with different author counts (single, multiple, et al.)
   - Test Simple pattern with minimal citations
   - Test unknown format detection

2. **Validation Function Tests**:
   - Valid CSV → no errors
   - Empty citation → error
   - Invalid source_type → error
   - Invalid confidence → error
   - Unknown citation format → warning (not error)
   - Missing file → error
   - Malformed CSV → error
   - Duplicate source_id → error

3. **Result Formatting Tests**:
   - Verify error/warning separation
   - Verify line numbers included
   - Verify suggestions helpful

**Integration Testing** (in WP10):
- Full research workflow with citation validation
- Review workflow blocks on citation errors
- Warnings shown but don't block

**Manual Testing**:
```bash
# Create test evidence log
cat > test-evidence.csv << EOF
timestamp,source_type,citation,key_finding,confidence,notes
2025-01-15T10:00:00,invalid,,Empty citation,wrong,
EOF

# Test validation
python -c "
from pathlib import Path
from specify_cli.validators.research import validate_citations
result = validate_citations(Path('test-evidence.csv'))
print(result.format_report())
"
# Should show clear errors
```

---

## Risks & Mitigations

**Risk 1**: Citation patterns too strict, reject valid citations
- **Mitigation**: Make format checks warnings not errors, test with diverse real citations

**Risk 2**: CSV parsing fails on edge cases (quoted fields, special characters)
- **Mitigation**: Use Python csv.DictReader (handles RFC 4180 CSV standard)

**Risk 3**: Validation too slow for large evidence logs (100+ sources)
- **Mitigation**: Keep validation lightweight, measure performance, optimize if needed

**Risk 4**: Researchers use citation styles we don't support
- **Mitigation**: Warnings guide but don't block, support multiple common formats

**Risk 5**: Integration with review workflow breaks existing behavior
- **Mitigation**: Only add validation for research mission, don't affect software-dev

---

## Definition of Done Checklist

- [ ] `src/specify_cli/validators/` directory created
- [ ] `validators/__init__.py` created
- [ ] `validators/research.py` module complete
- [ ] CitationValidationResult and CitationIssue dataclasses defined
- [ ] BibTeX pattern implemented and tested
- [ ] APA pattern implemented and tested
- [ ] Simple pattern implemented and tested
- [ ] `validate_citations()` function complete
- [ ] `validate_source_register()` function complete
- [ ] Unit tests in `tests/unit/test_validators.py` pass
- [ ] Test coverage >90% for validators
- [ ] Integration with research review workflow complete
- [ ] Manual testing with real citations passed
- [ ] No performance regression (validation <1 second for typical evidence logs)

---

## Review Guidance

**Critical Checkpoints**:
1. Citation validation must be progressive (errors for critical, warnings for style)
2. Error messages must include line numbers and specific issues
3. Supported formats (BibTeX, APA, Simple) must all work
4. Review workflow must call validation and block on errors
5. Test coverage must be comprehensive

**What Reviewers Should Verify**:
- Create evidence-log.csv with mixed citations → validate → check warnings helpful
- Create evidence-log.csv with errors (empty citation, invalid source_type) → validate → check errors clear
- Run full research workflow → verify review calls validation
- Check test coverage report → should show >90%
- Verify format patterns work with real academic citations

**Acceptance Criteria from Spec**:
- User Story 3, Scenarios 3-5 satisfied
- FR-009, FR-010, FR-011 implemented
- SC-007, SC-008 measurable outcomes achieved

---

## Activity Log

- 2025-01-16T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-11-16T13:09:10Z – codex – shell_pid=60030 – lane=doing – Started implementation
- 2025-11-16T13:14:28Z – codex – shell_pid=60030 – lane=doing – Implemented citation validators and unit tests
- 2025-11-16T13:15:41Z – codex – shell_pid=60030 – lane=for_review – Ready for review
- 2025-11-16T13:21:19Z – claude – shell_pid=96219 – lane=done – Code review complete: APPROVED. Comprehensive citation validation with 11/11 tests passing. Supports BibTeX/APA/Simple formats with progressive validation (errors for completeness, warnings for format). Integrated into research review workflow. Clean code with proper dataclasses and CitationFormat enum. Python stdlib only. Ready for research mission use.
