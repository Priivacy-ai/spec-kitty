# Research: Mission System Technical Decisions

**Feature**: 005-refactor-mission-system
**Date**: 2025-01-16
**Status**: Complete

## Research Questions

This research addresses three critical technical decisions for the mission system refactoring:

1. **Schema Validation Library**: Which library should validate mission.yaml structure?
2. **Citation Format Validation**: How should we validate citations in research mission?
3. **Dashboard Integration**: How should dashboard display and update active mission?

---

## R1: Schema Validation Library Comparison

### Research Question
Which schema validation library provides the best balance of error messages, zero dependencies, type safety, and Python 3.11+ compatibility for validating mission.yaml?

### Options Evaluated

#### Option A: Pydantic v2

**Pros**:
- Industry-standard for data validation in Python
- Excellent error messages with field-level details
- Full type hint integration
- Auto-generates schema documentation
- Coercion support (e.g., int ’ str)
- Fast (Rust core in v2)
- Active development and community

**Cons**:
- External dependency (adds ~5MB to install)
- Heavier than alternatives
- May be overkill for simple YAML validation

**Error Message Quality** (A+):
```python
# Missing required field
ValidationError: 1 validation error for MissionConfig
name
  Field required [type=missing, input_value={'domain': 'software'}, input_type=dict]

# Typo in field name
ValidationError: 1 validation error for MissionConfig
validaton
  Extra inputs are not permitted [type=extra_forbidden, input_value='git_clean', input_type=list]
```

**Example Usage**:
```python
from pydantic import BaseModel, Field

class MissionConfig(BaseModel):
    name: str
    domain: Literal["software", "research", "writing"]
    version: str
    workflow: WorkflowConfig

mission = MissionConfig(**yaml.safe_load(config_file))
```

**Verdict**: Best-in-class validation with clear errors. Worth the dependency for production use.

---

#### Option B: attrs + cattrs

**Pros**:
- Lighter weight than Pydantic (~400KB)
- Type hint support
- Good performance
- Mature and stable
- Composable validation

**Cons**:
- Two packages required (attrs + cattrs)
- Error messages less polished than Pydantic
- Less community adoption
- Manual schema documentation

**Error Message Quality** (B+):
```python
# Missing required field
cattrs.errors.ClassValidationError: While structuring MissionConfig (1 sub-exception)
  + Exception Group Traceback (most recent call last):
  |   File "<stdin>", line 1, in <module>
  | cattrs.errors.ClassValidationError: While structuring MissionConfig (1 sub-exception)
  +-+---------------- 1 ----------------
    | TypeError: __init__() missing 1 required positional argument: 'name'
```

**Example Usage**:
```python
import attrs
import cattrs

@attrs.define
class MissionConfig:
    name: str
    domain: str
    version: str

converter = cattrs.Converter()
mission = converter.structure(yaml_data, MissionConfig)
```

**Verdict**: Good middle ground. Lighter than Pydantic but requires two packages.

---

#### Option C: jsonschema

**Pros**:
- Standard JSON Schema format
- Language-agnostic schema
- Good error messages
- Well-documented
- Widely used

**Cons**:
- External dependency
- No type hint integration
- Schema separate from code
- Verbose schema definitions
- No auto-completion in IDEs

**Error Message Quality** (B):
```python
# Missing required field
jsonschema.exceptions.ValidationError: 'name' is a required property
Failed validating 'required' in schema:
    {'properties': {'name': {'type': 'string'}, ...}, 'required': ['name', 'domain']}
On instance:
    {'domain': 'software'}
```

**Example Usage**:
```python
import jsonschema

schema = {
    "type": "object",
    "required": ["name", "domain"],
    "properties": {
        "name": {"type": "string"},
        "domain": {"enum": ["software", "research"]}
    }
}

jsonschema.validate(yaml_data, schema)
```

**Verdict**: Decent but schema definitions are verbose and separate from code.

---

#### Option D: Dataclasses + Manual Validation

**Pros**:
- **Zero external dependencies** (Python 3.11+ stdlib)
- Full type hint integration
- IDE auto-completion
- Lightweight
- Complete control over error messages

**Cons**:
- Manual validation code required
- Error messages only as good as we write them
- More code to maintain
- No automatic coercion

**Error Message Quality** (C+ with effort, F without):
```python
# With custom validation
class MissionConfigError(Exception):
    pass

# Example validation
if "name" not in data:
    raise MissionConfigError(
        "Mission config missing required field: 'name'\n"
        f"Available fields: {list(data.keys())}\n"
        f"Required fields: name, domain, version, workflow, artifacts"
    )
```

**Example Usage**:
```python
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class MissionConfig:
    name: str
    domain: str
    version: str
    workflow: Dict

    @classmethod
    def from_dict(cls, data: Dict) -> 'MissionConfig':
        # Manual validation
        required = ["name", "domain", "version"]
        missing = [f for f in required if f not in data]
        if missing:
            raise MissionConfigError(f"Missing required fields: {missing}")
        return cls(**{k: data[k] for k in required})
```

**Verdict**: Zero dependencies but significant manual work required for quality errors.

---

### Decision Matrix

| Criterion | Pydantic | attrs+cattrs | jsonschema | dataclasses |
|-----------|----------|--------------|------------|-------------|
| Error Quality | A+ | B+ | B | C+ (manual) |
| Dependencies | 1 (5MB) | 2 (400KB) | 1 (300KB) | 0 |
| Type Hints |  Full |  Full | L None |  Full |
| IDE Support |  Excellent |  Good | L Limited |  Excellent |
| Maintenance |  Low |  Low | =á Medium | L High |
| Performance |  Fast |  Fast | =á Medium |  Fastest |
| Learning Curve | =á Medium | =á Medium |  Low |  Low |
| Community |  Huge | =á Small |  Large |  Stdlib |

### Recommended Decision

**Primary Recommendation: Pydantic v2**

**Rationale**:
1. **Error Quality**: Critical for FR-007 (helpful error messages). Pydantic's field-level errors with suggestions are far superior
2. **User Experience**: Custom mission creators need excellent feedback. 5MB dependency is acceptable for this quality
3. **Future-Proofing**: If spec-kitty grows (API server, web dashboard), Pydantic is already integrated
4. **Development Speed**: Less manual validation code = faster implementation
5. **Type Safety**: Full type checking prevents bugs in mission.py refactoring

**Alternative if Zero Dependencies Required: Dataclasses + Manual Validation**

If adding Pydantic is blocked for dependency reasons:
- Use dataclasses with comprehensive manual validation
- Invest 2-3 extra days building quality error messages
- Create validation helpers in `src/specify_cli/validation_utils.py`
- Trade-off: More code to maintain, but zero external dependencies

**Rejected Options**:
- **attrs+cattrs**: Two dependencies for marginal benefit over Pydantic
- **jsonschema**: Poor IDE experience, no type hints

---

## R2: Citation Format Validation

### Research Question
How should we validate citations in evidence-log.csv and source-register.csv for the research mission?

### Citation Formats to Support

#### BibTeX Format
```
@article{key2025,
  author = {Last, First},
  title = {Title of Paper},
  journal = {Journal Name},
  year = {2025}
}
```

**Regex Pattern**:
```python
BIBTEX_PATTERN = r'@\w+\{[\w-]+,[\s\S]+?\}'
```

#### APA 7th Edition
```
Last, F. (2025). Title of paper. Journal Name, 10(2), 123-145. https://doi.org/...
```

**Regex Pattern**:
```python
APA_PATTERN = r'^[\w\s,\.]+\(\d{4}\)\.[\s\S]+\.$'
```

#### Simple Citation (Fallback)
```
Author (Year). Title. Source. URL
```

**Regex Pattern**:
```python
SIMPLE_PATTERN = r'^.+\(\d{4}\)\..+\..+\.'
```

### Validation Approach

**Progressive Validation Strategy**:

1. **Level 1 - Completeness** (Always enforced):
   - Citation field is non-empty
   - Source type is one of: journal, conference, book, web, preprint
   - Year is 4-digit number

2. **Level 2 - Format** (Warning only):
   - Citation matches one of the supported patterns (BibTeX, APA, Simple)
   - If no match, warn: "Citation format not recognized. Consider using BibTeX or APA format."

3. **Level 3 - Quality** (Optional, for strict mode):
   - Check for DOI/URL presence
   - Validate journal/conference names against known lists
   - Check year is reasonable (1900-2030)

**Implementation**:
```python
# src/specify_cli/validators/research.py

import csv
import re
from pathlib import Path
from typing import List, Tuple

class CitationError(Exception):
    pass

def validate_citations(evidence_log_path: Path) -> List[str]:
    """Validate citations in evidence-log.csv.

    Returns:
        List of validation issues (empty if all valid)
    """
    issues = []

    with open(evidence_log_path) as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # Start at 2 (header is line 1)
            citation = row.get('citation', '').strip()
            source_type = row.get('source_type', '').strip()

            # Level 1 - Completeness
            if not citation:
                issues.append(f"Line {i}: Citation is empty")
                continue

            valid_types = ['journal', 'conference', 'book', 'web', 'preprint']
            if source_type not in valid_types:
                issues.append(
                    f"Line {i}: Invalid source_type '{source_type}'. "
                    f"Must be one of: {', '.join(valid_types)}"
                )

            # Level 2 - Format (warning only)
            patterns = [
                (r'@\w+\{[\w-]+,', "BibTeX"),
                (r'^[\w\s,\.]+\(\d{4}\)\.', "APA"),
                (r'^.+\(\d{4}\)\..+\..+', "Simple")
            ]

            matched = False
            for pattern, fmt in patterns:
                if re.match(pattern, citation):
                    matched = True
                    break

            if not matched:
                issues.append(
                    f"Line {i}: Citation format not recognized. "
                    f"Consider using BibTeX or APA format."
                )

    return issues
```

**Decision**: Progressive validation with helpful error messages. Don't block on format (warning only), but enforce completeness.

**Rationale**:
- Researchers use varied citation styles
- Format enforcement would be too rigid
- Completeness is what matters for research integrity
- Warnings educate users without blocking workflow

---

## R3: Dashboard Integration for Active Mission Display

### Research Question
How should the dashboard display and update the active mission?

### Options Evaluated

#### Option A: Server-Side Rendering (Simplest)

**Approach**: Include active mission in initial page load context.

**Implementation**:
```python
# src/specify_cli/dashboard/server.py

from specify_cli.mission import get_active_mission

@app.get("/")
def index():
    mission = get_active_mission(project_root)
    return templates.TemplateResponse("index.html", {
        "project": project_root.name,
        "active_mission": {
            "name": mission.name,
            "domain": mission.domain
        },
        # ... other context
    })
```

**UI Update After Switch**: User must refresh page manually

**Pros**:
- Zero complexity
- No JavaScript required
- Immediate implementation

**Cons**:
- Manual refresh required
- Doesn't feel "real-time"

---

#### Option B: Polling (Simple Real-Time)

**Approach**: Frontend polls `/api/mission/current` every 5-10 seconds.

**Implementation**:
```python
# Backend
@app.get("/api/mission/current")
def get_current_mission():
    mission = get_active_mission(project_root)
    return {
        "name": mission.name,
        "domain": mission.domain,
        "updated_at": datetime.now().isoformat()
    }
```

```javascript
// Frontend
setInterval(async () => {
    const response = await fetch('/api/mission/current');
    const data = await response.json();
    updateMissionDisplay(data);
}, 5000);  // Poll every 5 seconds
```

**Pros**:
- Simple to implement
- No WebSocket complexity
- Updates automatically

**Cons**:
- Polling overhead (5-10 req/minute)
- 5-10 second delay before update shows

---

#### Option C: WebSocket (True Real-Time)

**Approach**: Server pushes mission change events via WebSocket.

**Implementation**:
- Requires FastAPI WebSocket support or socket.io
- File watcher on `.kittify/active-mission`
- Push event to connected clients immediately

**Pros**:
- Instant updates (<1 second)
- No polling overhead
- Professional UX

**Cons**:
- Significant complexity
- Requires WebSocket library
- File watching mechanism needed
- Connection management

---

#### Option D: Hybrid (Pragmatic)

**Approach**: Server-side rendering + manual refresh with prominent indicator.

**Implementation**:
- Mission shown on initial load (Option A)
- Add "Refresh" button near mission display
- Optionally: Detect mission change via localStorage timestamp on focus

**Pros**:
- Simple like Option A
- User-controlled refresh
- No dependencies
- Clear UX (button makes refresh obvious)

**Cons**:
- Not automatic
- Requires user action

---

### Decision Matrix

| Criterion | Server-Side | Polling | WebSocket | Hybrid |
|-----------|-------------|---------|-----------|--------|
| Complexity |  Minimal | =á Low | L High |  Minimal |
| Dependencies |  Zero |  Zero | L New libs |  Zero |
| Update Speed | L Manual | =á 5-10sec |  <1sec | L Manual |
| User Experience | =á Acceptable |  Good |  Excellent |  Good |
| Maintenance |  Low |  Low | L Medium |  Low |

### Recommended Decision

**Primary Recommendation: Option D (Hybrid)**

**Rationale**:
1. **User Constraint**: "Resist the urge to complicate the dashboard unless necessary"
2. **Usage Pattern**: Mission switching is infrequent (per user feedback)
3. **Zero Dependencies**: Aligns with preference for no new runtime dependencies
4. **Clear UX**: Refresh button makes the action explicit
5. **Implementation Time**: 1-2 hours vs 1-2 days for WebSocket

**Implementation Details**:
- Add mission info to initial server context
- Display in header: `<div>Mission: {mission.name} <button>Refresh</button></div>`
- Optionally: Check timestamp on page focus and suggest refresh if stale

**Future Enhancement Path**:
If mission switching becomes frequent, upgrade to Option B (Polling) with minimal changes.

**Alternative if Real-Time Required: Option B (Polling)**

If automatic updates are critical:
- Use polling with 10-second interval
- Low overhead (6 requests/minute)
- Simple to implement
- Upgrade from Option D requires minimal changes

**Rejected Options**:
- **Option A**: No visual feedback when mission changes
- **Option C**: Over-engineered for infrequent operation

---

## Summary of Decisions

### Schema Validation Library

**Decision**: Pydantic v2

**Rationale**: Superior error messages (A+ quality) justify the 5MB dependency. Critical for SC-003 (immediate error feedback) and SC-005 (clear feedback within 5 seconds). Industry-standard choice with excellent type safety.

**Alternatives Considered**:
- attrs+cattrs (lighter but worse errors)
- jsonschema (no type hints)
- dataclasses (zero dependencies but high maintenance)

**Impact**:
- Add `pydantic>=2.0` to `pyproject.toml` or `requirements.txt`
- Mission loading gains automatic validation
- Custom mission creators get professional-grade feedback

---

### Citation Format Validation

**Decision**: Progressive validation with completeness enforcement, format warnings

**Rationale**: Research citation styles vary widely. Enforcing specific format would be too rigid. Focus on completeness (non-empty, valid source type) with helpful format suggestions.

**Implementation**:
- Python stdlib only (csv + re)
- Three-level validation: completeness (error), format (warning), quality (optional strict mode)
- Support BibTeX, APA, Simple citation patterns

**Alternatives Considered**:
- Strict format enforcement (rejected - too rigid)
- No validation (rejected - defeats purpose of research mission)
- External citation library integration (rejected - over-engineered)

**Impact**:
- Create `src/specify_cli/validators/research.py`
- Add validation to research mission review workflow
- Users get feedback on citation quality without workflow blocking

---

### Dashboard Mission Display

**Decision**: Hybrid (server-side rendering + refresh button)

**Rationale**: Aligns with user guidance to "resist complication." Mission switching is infrequent. Manual refresh with clear button provides good UX without complexity.

**Implementation**:
- Add mission to server context on page load
- Display in header with refresh button
- Optional: Check for staleness on page focus

**Alternatives Considered**:
- Polling (adds unnecessary overhead for infrequent operation)
- WebSocket (over-engineered for mission switching frequency)
- Server-side only (no feedback mechanism)

**Impact**:
- Minimal dashboard code changes
- Zero new dependencies
- Clear user experience
- Easy upgrade path to polling if needed

---

## Implementation Risks

### Risk 1: Pydantic Dependency Size

**Concern**: 5MB dependency may be unwanted
**Mitigation**: Document in assumptions. If rejected, fall back to dataclasses with 2-3 days additional work
**Likelihood**: Low (Pydantic is widely accepted)

### Risk 2: Citation Validation Too Loose

**Concern**: Warning-only format validation may allow poor citations
**Mitigation**: Provide clear examples in docs. Add strict mode flag for future if needed
**Likelihood**: Medium (depends on research mission adoption)

### Risk 3: Dashboard Refresh UX

**Concern**: Manual refresh may frustrate users
**Mitigation**: Make button prominent. Track user feedback. Upgrade to polling if complaints arise
**Likelihood**: Low (mission switching is infrequent per user)

---

## Next Steps

Phase 0 research complete. Proceed to Phase 1 (Design & Contracts):

1. **data-model.md**: Define Pydantic models for mission schema
2. **quickstart.md**: Developer guide for new features
3. **Update agent context**: Run agent script with new technologies
