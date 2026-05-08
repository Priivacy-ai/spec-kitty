# Contract — Architectural Test Contracts

Three new architectural tests ship in this mission. Each one enforces one of the new doctrine artefacts. Per mission-wide constraint C-003, every test ships with a positive AND a negative meta-test.

## 1. `tests/architectural/test_transport_does_not_import_scanner.py` (FR-009)

**Enforces**: `DIRECTIVE_API_DEPENDENCY_DIRECTION`

**What the test asserts**: AST-walk every Python file under
- `src/dashboard/api/routers/`
- `src/specify_cli/cli/commands/dashboard.py`

For each file, scan for `Import` and `ImportFrom` nodes. Fail if any node references:
- `specify_cli.dashboard.scanner`
- `specify_cli.scanner`
- any module path matching `*scanner*` outside an explicit allowlist

**Allowlist**:
- `src/dashboard/services/registry.py` — the registry IS the canonical reader; it imports the scanner internally. (This file is NOT under `src/dashboard/api/` so the scan does not see it; the allowlist is documented for completeness.)

**Module docstring** must reference `DIRECTIVE_API_DEPENDENCY_DIRECTION` and link to the directive YAML path.

**Positive meta-test** (synthetic violator MUST fail the scan):

```python
def test_meta_scanner_detects_violation(tmp_path):
    """Inject a synthetic forbidden import; assert the scanner flags it."""
    fake_router = tmp_path / "synthetic_router.py"
    fake_router.write_text(
        "from specify_cli.dashboard.scanner import scan_all_features\n"
        "router = ...\n",
        encoding="utf-8",
    )
    violations = _scan_for_forbidden_imports([fake_router])
    assert violations  # MUST be non-empty
    assert "specify_cli.dashboard.scanner" in violations[0]
```

**Negative meta-test** (synthetic clean module MUST pass the scan):

```python
def test_meta_scanner_accepts_registry_import(tmp_path):
    """Inject a synthetic compliant import; assert the scanner does NOT flag."""
    clean_router = tmp_path / "synthetic_router.py"
    clean_router.write_text(
        "from dashboard.services.registry import MissionRegistry\n"
        "router = ...\n",
        encoding="utf-8",
    )
    violations = _scan_for_forbidden_imports([clean_router])
    assert violations == []
```

**Pytest marker**: `pytestmark = pytest.mark.architectural`

## 2. `tests/architectural/test_url_naming_convention.py` (FR-010)

**Enforces**: `DIRECTIVE_REST_RESOURCE_ORIENTATION`

**What the test asserts**: Construct the FastAPI app via `dashboard.api.create_app(project_dir, project_token=None)`. Walk `app.openapi()['paths']`. For each path:
- It matches the resource-noun convention if it follows `^/api/[a-z][a-z-]*(/{[a-z_]+}(/[a-z][a-z-]*)?)*$` (collection / item / sub-collection).
- OR it is in the action allowlist.
- OR it is `/` or `/api-docs` or `/static/...` (non-API surfaces).

**Action allowlist** (documented inline with rationale):

```python
ACTION_ALLOWLIST = {
    "/api/sync/trigger",   # POST — action verb in URL acceptable for triggered side effect
    "/api/shutdown",       # POST — action verb in URL acceptable for lifecycle command
    "/api/charter-lint",   # GET — historical name; flagged for rename in mission B
    "/api/glossary-health",     # historical name; same
    "/api/glossary-terms",      # historical name; same
}
```

**Migration tolerance**: This mission does NOT rename the historical paths (per spec C-005). The allowlist documents which paths are exceptions. Mission B will rename `/api/features` → `/api/missions` and reduce the allowlist accordingly.

**Module docstring** references `DIRECTIVE_REST_RESOURCE_ORIENTATION` and links to the directive YAML.

**Positive meta-test**: synthetic OpenAPI dict with a `/api/badShape!` path → scanner flags it.

**Negative meta-test**: synthetic OpenAPI dict with `/api/missions/{id}/workpackages` → scanner does NOT flag.

**Pytest marker**: `pytestmark = pytest.mark.architectural`

## 3. `tests/architectural/test_resource_models_have_links.py` (FR-011)

**Enforces**: `HATEOAS-LITE` paradigm

**What the test asserts**: Walk the Pydantic class hierarchy under `src/dashboard/api/models.py`. For every class that subclasses `dashboard.api.models.ResourceModel`:
- Class MUST declare a field named `_links` (or `links` if Pydantic field-name policy disallows leading underscores; check Pydantic v2 config).
- The field MUST be typed `dict[str, Link]`.
- The field MUST be required (no default; or default `Field(default_factory=dict)` with documentation).

**Mission-A behaviour**: ZERO subclasses exist at this mission's merge time (per spec C-006). The test passes vacuously. The marker class is in place so mission B can subclass.

**Module docstring** references the `HATEOAS-LITE` paradigm and explains that mission A's pass is vacuous, mission B activates the enforcement.

**Positive meta-test**: synthetic `BadResource(ResourceModel)` without `_links` → scanner flags it.

**Negative meta-test**: synthetic `GoodResource(ResourceModel)` with `_links: dict[str, Link]` → scanner does NOT flag.

**Pytest marker**: `pytestmark = pytest.mark.architectural`

## Common test conventions (apply to all three)

- **Real production code paths only** (mission-wide rule C-003): the tests walk the real source tree and the real FastAPI app, not synthetic fixtures masquerading as production.
- **Failure messages are actionable**: each `assert` failure message names the violating file/line, the rule violated, and the doctrine artefact link.
- **Test runtime budget**: each test runs in < 1 second on a modern dev machine. The AST walks are O(N) over the file count; the JSON walk is O(P) over the path count.
- **Exemption pattern**: NO `# noqa` or skip markers in production code to bypass these tests. If an exemption is genuinely needed, it goes in the test's allowlist with explicit rationale, not in source code.
