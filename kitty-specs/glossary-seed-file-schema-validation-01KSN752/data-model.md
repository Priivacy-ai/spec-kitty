# Data Model: Glossary Seed File Schema Validation

## Pydantic Validation Models

### GlossarySeedTerm

Child entity within the `GlossarySeedFile` aggregate. Validates a single term entry from a glossary seed YAML file.

```python
class GlossarySeedTerm(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    surface: str
    definition: str
    confidence: float = 1.0
    status: Literal["active", "draft", "deprecated"] = "draft"

    @field_validator("surface")
    @classmethod
    def surface_must_be_normalized(cls, v: str) -> str:
        if v != v.lower().strip():
            raise ValueError(
                f"surface must be normalized (lowercase, trimmed): got {v!r}, "
                f"expected {v.lower().strip()!r}"
            )
        if not v:
            raise ValueError("surface must not be empty")
        return v

    @field_validator("definition")
    @classmethod
    def definition_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("definition must not be empty")
        return v

    @field_validator("confidence")
    @classmethod
    def confidence_in_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be 0.0..1.0, got {v}")
        return v
```

**Fields:**

| Field | Type | Required | Default | Invariant |
|-------|------|----------|---------|-----------|
| `surface` | `str` | yes | — | `surface == surface.lower().strip()`, non-empty |
| `definition` | `str` | yes | — | Non-empty after strip |
| `confidence` | `float` | no | `1.0` | `0.0 <= confidence <= 1.0` |
| `status` | `Literal` | no | `"draft"` | One of `active`, `draft`, `deprecated` |

### GlossarySeedFile

Aggregate root for a glossary seed file. Validates the entire file structure.

```python
class GlossarySeedFile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    terms: list[GlossarySeedTerm]

    @field_validator("terms")
    @classmethod
    def terms_must_not_be_empty(cls, v: list[GlossarySeedTerm]) -> list[GlossarySeedTerm]:
        # Allow empty list — a scope may have no terms yet
        return v
```

**Fields:**

| Field | Type | Required | Default | Invariant |
|-------|------|----------|---------|-----------|
| `terms` | `list[GlossarySeedTerm]` | yes | — | Must be present (may be empty list) |

## Error Models

### SeedValidationError (dataclass)

A single validation error with location context.

```python
@dataclass(frozen=True)
class SeedValidationError:
    file_path: Path
    term_index: int | None     # None for file-level errors
    term_surface: str | None   # None when surface itself is missing/invalid
    field: str | None          # None for term-level or file-level errors
    message: str
```

### SeedFileValidationError (exception)

Aggregated validation failure for a seed file.

```python
class SeedFileValidationError(GlossaryError):
    def __init__(self, file_path: Path, errors: list[SeedValidationError]):
        self.file_path = file_path
        self.errors = errors
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        # Multi-line: "N validation error(s) in <path>:\n  - term[0] 'foo': surface: ..."
```

## Validation Function

### validate_seed_file_data()

Orchestrates Pydantic validation and translates `ValidationError` into `SeedValidationError` list.

```python
def validate_seed_file_data(
    data: Any,
    file_path: Path,
) -> GlossarySeedFile:
    """Validate parsed YAML data against the glossary seed file schema.

    Returns the validated GlossarySeedFile on success.
    Raises SeedFileValidationError on failure with all errors collected.
    """
```

**Translation logic**: Pydantic v2 `ValidationError.errors()` returns a list of dicts with `loc`, `msg`, `type` fields. The translator maps:
- `loc = ("terms", 2, "surface")` → `term_index=2, field="surface"`
- `loc = ("terms",)` → file-level error (missing terms key)
- `term_surface` extracted from the input `data["terms"][term_index]["surface"]` when available

## Scope Validation

### validate_scope_filename()

Validates that a seed filename corresponds to a known `GlossaryScope`.

```python
VALID_SCOPE_FILENAMES: set[str] = {f"{s.value}.yaml" for s in GlossaryScope}

def validate_scope_filename(file_path: Path) -> GlossaryScope | None:
    """Return the GlossaryScope for a seed filename, or None if unknown."""
```

## Relationships to Existing Models

```
GlossarySeedFile (Pydantic, validation layer)
    │ contains
    ▼
GlossarySeedTerm (Pydantic, validation layer)
    │ validated data feeds into
    ▼
TermSurface (dataclass, runtime domain model)
    │ composed into
    ▼
TermSense (dataclass, runtime domain model)
```

The Pydantic models validate raw YAML data. After validation succeeds, `load_seed_file()` constructs `TermSurface` and `TermSense` dataclass instances from the validated data. The Pydantic models do not replace the existing domain model — they are the input validation gate.
