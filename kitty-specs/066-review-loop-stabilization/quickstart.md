# Quickstart: 066 Review Loop Stabilization

**Mission**: 066-review-loop-stabilization
**Date**: 2026-04-06

## Prerequisites

- Python 3.11+
- spec-kitty-cli installed (`pipx install --force --pip-args="--pre" spec-kitty-cli`)
- Repository cloned with all dependencies installed (`poetry install`)
- mypy and pytest available

## Key Files to Read First

Before implementing any WP, read these files to understand the current state:

| File | Why | Lines |
|------|-----|-------|
| `src/specify_cli/cli/commands/agent/tasks.py` | `_persist_review_feedback()` (245-265), `_validate_ready_for_review()` (468-750), `move_task()` (854-1246) | Core review loop logic |
| `src/specify_cli/cli/commands/agent/workflow.py` | `_resolve_review_feedback_pointer()` (87-100), review prompt template (917-1310), implement action feedback detection (526-662) | Prompt generation and pointer resolution |
| `src/specify_cli/status/models.py` | StatusEvent, ReviewApproval, DoneEvidence | Data model patterns to follow |
| `kitty-specs/066-review-loop-stabilization/data-model.md` | New data models for this mission | Schema reference |

## Running Tests

```bash
# Run all tests
pytest tests/

# Run only review-related tests
pytest tests/review/ tests/agent/test_review_feedback_pointer_2x_unit.py tests/agent/test_review_validation_unit.py

# Type checking
mypy --strict src/specify_cli/review/

# Coverage check (new code must be 90%+)
pytest tests/review/ --cov=src/specify_cli/review --cov-report=term-missing
```

## WP Implementation Order

### Track A (sequential — must follow this order)

1. **WP01**: Create `src/specify_cli/review/artifacts.py`, rewrite `_persist_review_feedback()`, update pointer resolver
2. **WP02**: Create `src/specify_cli/review/fix_prompt.py`, add fix-mode switching to implement path

### Track B (independent — any order, parallelizable)

3. **WP03**: Create `src/specify_cli/review/dirty_classifier.py`, update `_validate_ready_for_review()`
4. **WP04**: Create `src/specify_cli/review/baseline.py`, add baseline context to review prompt
5. **WP05**: Create `src/specify_cli/review/lock.py`, add lock acquire/release to review action
6. **WP06**: Create `src/specify_cli/review/arbiter.py`, add structured override to move-task

## New Module: `src/specify_cli/review/`

All new domain logic lives in this module. The CLI commands (`tasks.py`, `workflow.py`) call into it.

```
src/specify_cli/review/
├── __init__.py           # Public API: ReviewCycleArtifact, generate_fix_prompt, etc.
├── artifacts.py          # WP01: ReviewCycleArtifact, AffectedFile
├── fix_prompt.py         # WP02: generate_fix_prompt()
├── dirty_classifier.py   # WP03: classify_dirty_paths()
├── baseline.py           # WP04: BaselineTestResult, capture_baseline(), diff_baseline()
├── lock.py               # WP05: ReviewLock
└── arbiter.py            # WP06: ArbiterDecision, ArbiterChecklist, ArbiterCategory
```

## Code Patterns to Follow

### Dataclass pattern (from status/models.py)

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class MyModel:
    field_a: str
    field_b: int
    optional_field: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return { ... }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MyModel:
        return cls( ... )
```

### YAML frontmatter pattern (using ruamel.yaml)

```python
from ruamel.yaml import YAML

yaml = YAML()
yaml.preserve_quotes = True

def parse_frontmatter(path: Path) -> tuple[dict, str]:
    """Parse YAML frontmatter and body from markdown file."""
    content = path.read_text()
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    fm = yaml.load(parts[1])
    body = parts[2].lstrip("\n")
    return fm, body
```

### Pointer format

- Legacy: `feedback://<mission_slug>/<task_id>/<filename>`
- New: `review-cycle://<mission_slug>/<wp_slug>/review-cycle-{N}.md`

## Verification Checklist

After implementing each WP, verify:

- [ ] `pytest tests/review/` passes
- [ ] `mypy --strict src/specify_cli/review/` passes
- [ ] New code has 90%+ test coverage
- [ ] No regressions in existing tests (`pytest tests/`)
- [ ] CLI help text uses "mission" not "feature" for any new flags
