# Quick Start: Mission System Refactoring

**Feature**: 005-refactor-mission-system
**Audience**: Developers implementing or using the enhanced mission system

---

## Overview

This feature refactors the spec-kitty mission system with 6 key improvements:

1. **Shared Pre-flight Checks** - DRY elimination
2. **Schema Validation** - Pydantic-powered mission.yaml validation
3. **Production-Ready Research Mission** - Complete templates + citation validation
4. **Mission Switching CLI** - `spec-kitty mission` command group
5. **Path Enforcement** - Progressive validation
6. **Clear Terminology** - Project/Feature/Mission definitions

---

## For Users: Using the Enhanced Mission System

### Switching Missions

```bash
# List available missions
spec-kitty mission list

# View current mission
spec-kitty mission current

# View mission details
spec-kitty mission info research

# Switch to research mission (only when clean)
spec-kitty mission switch research
```

**Requirements for switching:**
- No active worktrees (`.worktrees/` is empty or all features merged)
- No uncommitted changes (git status clean)
- Target mission exists

**Example workflow:**
```bash
# 1. Start with software-dev (default)
spec-kitty init my-project

# 2. Build a feature
cd my-project
/spec-kitty.specify "authentication system"
# ... complete workflow, merge

# 3. Switch to research mission
spec-kitty mission switch research

# 4. Research security
/spec-kitty.specify "security review for auth"
# ... complete research workflow

# 5. Switch back to software-dev
spec-kitty mission switch software-dev

# 6. Implement security fixes
/spec-kitty.specify "implement auth hardening"
```

---

### Using Research Mission

#### Initialize Research Project

```bash
spec-kitty init my-research --mission research
cd my-research
```

#### Research Workflow

```bash
# 1. Define research question
/spec-kitty.specify "impact of AI code assistants on developer productivity"

# 2. Design methodology
/spec-kitty.plan
# Creates plan.md with methodology sections

# 3. Create research tasks
/spec-kitty.tasks

# 4. Execute research
/spec-kitty.implement
# Agent populates evidence-log.csv and source-register.csv

# 5. Review findings
/spec-kitty.review
# Validates citations, methodology, completeness

# 6. Accept and merge
/spec-kitty.accept
/spec-kitty.merge
```

#### Evidence Tracking

**File**: `research/evidence-log.csv`

```csv
timestamp,source_type,citation,key_finding,confidence,notes
2025-01-16T10:00:00,journal,"Smith et al. (2024). AI Assistants. Nature, 10(2), 45-67.",AI improves speed 30%,high,Meta-analysis of 50 studies
2025-01-16T11:30:00,web,"GitHub Copilot Stats. https://github.blog/...",65% code acceptance rate,medium,Self-reported data
```

**Columns**:
- `timestamp`: ISO format (YYYY-MM-DDTHH:MM:SS)
- `source_type`: journal|conference|book|web|preprint
- `citation`: BibTeX, APA, or Simple format
- `key_finding`: Main takeaway from source
- `confidence`: high|medium|low
- `notes`: Additional context

**Validation**:
- Citation required (non-empty)
- Source type must be valid
- Format warning if doesn't match BibTeX/APA/Simple

---

### Path Conventions

Each mission defines expected directory structure:

**Software-Dev Mission:**
```yaml
paths:
  workspace: "src/"
  tests: "tests/"
  deliverables: "contracts/"
  documentation: "docs/"
```

**Research Mission:**
```yaml
paths:
  workspace: "research/"
  data: "data/"
  deliverables: "findings/"
  documentation: "reports/"
```

**Validation Behavior:**
- **At mission switch**: Warnings if paths missing (non-blocking)
- **At acceptance**: Errors if paths missing (blocking)
- **Suggestions provided**: "Create directory: mkdir -p src/"

---

## For Developers: Implementing Mission Features

### Module 1: Guards (Pre-flight Validation)

**File**: `src/specify_cli/guards.py`

**Purpose**: Shared validation logic for worktree location checks

**Usage in Commands**:
```python
# Before: Inline bash in command prompts (duplicated 8+ times)
git branch --show-current
# ... 20 lines of bash checks

# After: Single Python call
from specify_cli.guards import validate_worktree_location

def command_handler():
    validate_worktree_location()  # Raises error if invalid
    # ... proceed with command
```

**Implementation Checklist**:
- [ ] Create `src/specify_cli/guards.py`
- [ ] Implement `validate_worktree_location()` with clear errors
- [ ] Implement `validate_git_clean()` for mission switching
- [ ] Write unit tests in `tests/unit/test_guards.py`
- [ ] Update command prompts to call Python validation
- [ ] Remove inline bash pre-flight checks from 8 prompt files

---

### Module 2: Mission Schema Validation

**File**: `src/specify_cli/mission.py` (modified)

**Purpose**: Pydantic models for mission.yaml validation

**Usage**:
```python
# Before: Silent failures with .get()
validation_checks = self.config.get("validation", {}).get("checks", [])

# After: Explicit errors from Pydantic
validation_checks = self.config.validation.checks  # Type-safe, validated
```

**Implementation Checklist**:
- [ ] Add `pydantic>=2.0` dependency
- [ ] Define Pydantic models (MissionConfig, WorkflowConfig, etc.)
- [ ] Update Mission.__init__ to use Pydantic validation
- [ ] Add helpful error formatting
- [ ] Write unit tests for valid/invalid configs
- [ ] Test with intentional typos

---

### Module 3: Mission CLI Commands

**File**: `src/specify_cli/cli/commands/mission.py` (new)

**Purpose**: Top-level mission management commands

**Usage**:
```bash
spec-kitty mission list
spec-kitty mission current
spec-kitty mission switch research
spec-kitty mission info software-dev
```

**Implementation Checklist**:
- [ ] Create Typer command group
- [ ] Implement `list_cmd()` - show all missions
- [ ] Implement `current_cmd()` - show active mission details
- [ ] Implement `info_cmd()` - show specific mission info
- [ ] Implement `switch_cmd()` with validation
- [ ] Register command group in main CLI
- [ ] Write integration tests

---

### Module 4: Research Mission Validators

**File**: `src/specify_cli/validators/research.py` (new)

**Purpose**: Citation and bibliography validation

**Usage in Review Workflow**:
```python
from specify_cli.validators.research import validate_research_citations

result = validate_research_citations(feature_dir)
if result.has_errors:
    print(result.format_report())
    raise ValidationError("Citation validation failed")
```

**Implementation Checklist**:
- [ ] Create validators/research.py module
- [ ] Implement citation format patterns (BibTeX, APA, Simple)
- [ ] Implement progressive validation (completeness → format → quality)
- [ ] Create validation result models
- [ ] Write unit tests with sample citations
- [ ] Integrate into research mission review workflow

---

### Module 5: Path Convention Validators

**File**: `src/specify_cli/validators/paths.py` (new)

**Purpose**: Validate mission path conventions

**Usage**:
```python
from specify_cli.validators.paths import validate_mission_paths

# At mission switch - warnings only
result = validate_mission_paths(mission, project_root, strict=False)
if result.warnings:
    print(result.format_warnings())

# At acceptance - errors block
result = validate_mission_paths(mission, project_root, strict=True)
if not result.is_valid:
    raise AcceptanceError(result.format_warnings())
```

**Implementation Checklist**:
- [ ] Create validators/paths.py module
- [ ] Implement path existence checking
- [ ] Generate helpful suggestions
- [ ] Support strict/non-strict modes
- [ ] Write unit tests
- [ ] Integrate into acceptance workflow

---

### Module 6: Documentation Updates

**Files**: README.md, command help text, error messages

**Purpose**: Clarify Project/Feature/Mission terminology

**Terminology**:
- **Project**: The entire codebase (e.g., "spec-kitty project", "priivacy_rust project")
- **Feature**: A single unit of work (e.g., "001-mission-system-architecture feature")
- **Mission**: The domain mode/adapter (e.g., "software-dev mission", "research mission")

**Implementation Checklist**:
- [ ] Add glossary section to README
- [ ] Search/replace inconsistent terminology
- [ ] Update error messages
- [ ] Update command help text
- [ ] Review all user-facing strings

---

### Module 7: Dashboard Mission Display

**File**: `src/specify_cli/dashboard/server.py` (modified)

**Purpose**: Show active mission in dashboard

**Implementation Checklist**:
- [ ] Add mission to server context
- [ ] Update dashboard template with mission display
- [ ] Add refresh button (optional)
- [ ] Test mission display
- [ ] Test after mission switch (with refresh)

---

## Testing Strategy

### Unit Tests

**Test Files**:
- `tests/unit/test_guards.py` - Pre-flight validation
- `tests/unit/test_mission_schema.py` - Pydantic validation
- `tests/unit/test_mission_cli.py` - CLI commands
- `tests/unit/test_validators.py` - Citation & path validation

**Coverage Goals**:
- Guards module: 100% (critical path)
- Schema validation: 100% (all field types)
- Validators: 90%+ (edge cases)
- CLI commands: 80%+ (happy path + errors)

### Integration Tests

**Test Files**:
- `tests/integration/test_mission_switching.py` - Full switch workflow
- `tests/integration/test_research_workflow.py` - Research mission end-to-end

**Scenarios**:
1. **Mission Switch Happy Path**: Clean project → switch → verify templates
2. **Mission Switch Blocked**: Active worktree → switch → error
3. **Research Workflow**: Init research → specify → plan → tasks → implement → review → accept
4. **Citation Validation**: Valid citations → pass, invalid → clear errors
5. **Path Validation**: Missing dirs → warnings at switch, errors at acceptance

---

## Development Workflow

### Phase 0: Foundation (Sequential)

```bash
# 1. Create guards module
src/specify_cli/guards.py

# 2. Write tests first (TDD)
tests/unit/test_guards.py

# 3. Implement validation functions
# 4. Run tests: pytest tests/unit/test_guards.py
# 5. Commit: "Add guards module with pre-flight validation"
```

### Phase 1: Parallel Streams

**Stream A - Schema & CLI** (can start after research):
```bash
# 1. Add Pydantic models to mission.py
# 2. Create mission CLI commands
# 3. Write tests
# 4. Integration test mission switching
```

**Stream B - Research Mission** (can start after research):
```bash
# 1. Update research templates
# 2. Create citation validators
# 3. Update research command prompts
# 4. Integration test research workflow
```

**Stream C - Command Prompts** (requires guards.py):
```bash
# 1. Update plan.md prompt
# 2. Update implement.md prompt
# 3. Update review.md prompt
# 4. Update merge.md prompt
# 5. Test pre-flight failures
```

**Stream D - Docs** (can start immediately):
```bash
# 1. Add glossary to README
# 2. Update terminology throughout
# 3. Update dashboard with mission display
```

---

## Common Patterns

### Adding Validation to a Module

```python
# 1. Define result model
@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]

# 2. Implement validation function
def validate_something(context) -> ValidationResult:
    errors = []
    warnings = []

    # Check conditions
    if condition_failed:
        errors.append("Clear error message with suggestion")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )

# 3. Use in workflow
result = validate_something(context)
if not result.is_valid:
    for error in result.errors:
        print(f"[red]{error}[/red]")
    raise ValidationError()
```

### Updating Command Prompts

```markdown
<!-- Before: Inline bash (20+ lines) -->
## Location Pre-flight Check

**Check your current branch:**
```bash
git branch --show-current
```
[... 15 more lines ...]

<!-- After: Call Python (2 lines) -->
## Location Pre-flight Check

Run pre-flight validation:
```bash
python -m specify_cli.guards validate_worktree
```
```

---

## FAQ

**Q: Why Pydantic instead of dataclasses?**
A: Error message quality. Pydantic provides field-level errors with suggestions. Worth the 5MB dependency.

**Q: Will existing custom missions break?**
A: Only if they have typos or malformed YAML. Schema validation catches these errors explicitly instead of silently ignoring them.

**Q: Can I switch missions mid-feature?**
A: No. Must complete and merge current feature first. This ensures clean state.

**Q: What if research mission evidence-log.csv doesn't exist?**
A: Validation error at review/acceptance with clear message to create the file.

**Q: Are path conventions enforced?**
A: Progressively. Warnings at mission switch (non-blocking), errors at acceptance (blocking).

---

## Troubleshooting

### Mission Config Validation Errors

**Error**: `Extra inputs are not permitted [validaton]`
**Fix**: Typo in field name. Change `validaton:` to `validation:`

**Error**: `Field required [name]`
**Fix**: Add missing required field to mission.yaml

**Error**: `String should match pattern '^\d+\.\d+\.\d+$'`
**Fix**: Version must be semver format (e.g., "1.0.0" not "1.0")

### Mission Switching Blocked

**Error**: "Cannot switch: active features exist"
**Fix**: Complete and merge all features first, then switch

**Error**: "Uncommitted changes detected"
**Fix**: Commit or stash changes before switching

### Citation Validation Warnings

**Warning**: "Citation format not recognized"
**Fix**: Use BibTeX, APA, or Simple format. Examples in evidence-log.csv template.

---

## Next Steps

After implementing this feature:

1. **Update CI/CD**: Add Pydantic to dependencies
2. **Update Documentation**: User guide for mission switching
3. **Community Outreach**: Blog post on mission system capabilities
4. **Monitor Usage**: Track which missions are used, gather feedback
5. **Iterate**: Based on user feedback, refine validation rules
