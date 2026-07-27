# Quickstart: Glossary Seed File Schema Validation

## For Implementers

### Module Layout

```
src/specify_cli/glossary/
├── seed_schema.py         # Pydantic models: GlossarySeedFile, GlossarySeedTerm
├── seed_validation.py     # validate_seed_file_data(), scope filename validation
├── exceptions.py          # SeedValidationError, SeedFileValidationError (add to existing)
├── scope.py               # Update validate_seed_file(), load_seed_file(), save_seed_file()
└── ...

src/specify_cli/cli/commands/
└── glossary.py            # Add validate subcommand to existing typer app
```

### Key Patterns

**Pydantic model pattern** (follow doctrine `src/doctrine/directives/models.py`):
```python
from pydantic import BaseModel, ConfigDict, field_validator

class GlossarySeedTerm(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    # ... fields and validators
```

**Validation orchestration** (new pattern for glossary):
```python
from pydantic import ValidationError

def validate_seed_file_data(data: Any, file_path: Path) -> GlossarySeedFile:
    try:
        return GlossarySeedFile.model_validate(data)
    except ValidationError as e:
        errors = _translate_pydantic_errors(e, data, file_path)
        raise SeedFileValidationError(file_path, errors) from e
```

**Integration into load_seed_file()** — replace old validation call:
```python
# Before (scope.py):
validate_seed_file(data)  # minimal structural check
sense = TermSense(surface=TermSurface(term_data["surface"]), ...)  # fails here on bad data

# After:
from .seed_validation import validate_seed_file_data
validated = validate_seed_file_data(data, seed_path)  # full Pydantic validation
# TermSurface construction now guaranteed to succeed
```

### Testing Strategy

- **Unit tests** (`test_seed_schema.py`): Pydantic model validation — valid inputs, each invariant violation, edge cases
- **Unit tests** (`test_seed_validation.py`): Error translation, file-level vs term-level errors, scope filename validation
- **Integration tests** (`test_glossary_validate.py`): CLI command with real YAML files — valid, invalid, directory mode, JSON output
- **Regression tests**: Update `test_scope.py` to verify `load_seed_file()` raises `SeedFileValidationError` instead of `ValueError`

### Implementation Order

1. Fix bad data in `.kittify/glossaries/spec_kitty_core.yaml`
2. Add `SeedValidationError`/`SeedFileValidationError` to `exceptions.py`
3. Create `seed_schema.py` with Pydantic models
4. Create `seed_validation.py` with validation orchestration
5. Update `scope.py` (`validate_seed_file()`, `load_seed_file()`, `save_seed_file()`)
6. Add CLI `validate` command to `glossary.py`
7. Update dashboard handler in `src/specify_cli/dashboard/handlers/glossary.py`
8. Add CI integration
9. Full test suite

### CI Integration

Add to existing CI workflow (or document for user setup):
```yaml
- name: Validate glossary seed files
  run: spec-kitty glossary validate .kittify/glossaries/
```
