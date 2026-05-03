---
work_package_id: WP05
title: Architectural tests + ResourceModel marker
dependencies:
- WP02
- WP04
requirement_refs:
- C-003
- C-006
- FR-008
- FR-009
- FR-010
- FR-011
planning_base_branch: feature/650-dashboard-ui-ux-overhaul
merge_target_branch: feature/650-dashboard-ui-ux-overhaul
branch_strategy: Planning artifacts for this feature were generated on feature/650-dashboard-ui-ux-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/650-dashboard-ui-ux-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
agent: claude
history:
- date: '2026-05-03'
  event: created
  note: Auto-generated alongside tasks.md
agent_profile: implementer-ivan
authoritative_surface: tests/architectural/
execution_mode: code_change
owned_files:
- src/dashboard/api/models.py
- tests/architectural/test_transport_does_not_import_scanner.py
- tests/architectural/test_url_naming_convention.py
- tests/architectural/test_resource_models_have_links.py
role: implementer
tags:
- architectural-tests
- enforcement
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

You are Implementer Ivan. Your responsibility is comprehensive test coverage. Per mission-wide rule C-003, every architectural test ships with a positive AND a negative meta-test. Failure messages are actionable (name the violating file, name the rule violated, link the doctrine artefact).

## Objective

Land the three architectural tests that enforce this mission's three new doctrine artefacts (delivered by WP02). Land the `ResourceModel` + `Link` Pydantic marker classes so mission B can subclass.

The third test (`test_resource_models_have_links.py`) lights up vacuously in this mission per spec C-006 — no class subclasses `ResourceModel` here. The marker class is in place; the test is in place; mission B activates the enforcement when it introduces the first resource-oriented endpoint.

## Context

The contracts for each test are fully specified in `kitty-specs/mission-registry-and-api-boundary-doctrine-01KQPDBB/contracts/architectural-test-contracts.md`. Read all three contracts before writing any test code; the contract is the source of truth.

The directives this WP enforces (`DIRECTIVE_API_DEPENDENCY_DIRECTION`, `DIRECTIVE_REST_RESOURCE_ORIENTATION`, `HATEOAS-LITE`) are delivered by WP02. The router-side compliance (every router uses the registry, no scanner imports in transport) is delivered by WP04. This WP layers the enforcement on top.

## Subtasks

### T014 — `Link` and `ResourceModel` Pydantic marker classes

**File**: `src/dashboard/api/models.py`.

**Action**: append the marker classes per `data-model.md`:

```python
# --- HATEOAS-LITE marker classes (introduced by mission
# mission-registry-and-api-boundary-doctrine-01KQPDBB; mission B will
# subclass ResourceModel for the new resource-oriented endpoints) ---


class Link(BaseModel):
    """A single HATEOAS-LITE hyperlink. Subset of HAL's link object.

    See doctrine paradigm `hateoas-lite` (src/doctrine/paradigms/shipped/
    hateoas-lite.paradigm.yaml) for the full convention and future-graduation
    triggers (HAL / JSON:API).
    """

    href: str
    method: str = "GET"


class ResourceModel(BaseModel):
    """Marker base class for resource-oriented response models.

    Subclasses MUST declare a `_links: dict[str, Link]` field. Enforced by
    `tests/architectural/test_resource_models_have_links.py`.

    No subclass exists in this mission (per spec C-006). Mission B introduces
    the first subclass when it ships the new resource-oriented endpoints.
    """

    pass
```

Append `Link` and `ResourceModel` to the module's `__all__`.

**No backward incompatibility**: this is a strict addition; existing models do NOT subclass `ResourceModel` and are unaffected.

### T015 — `test_transport_does_not_import_scanner.py`

**File**: `tests/architectural/test_transport_does_not_import_scanner.py` (new).

**Action**: implement per `contracts/architectural-test-contracts.md` § 1. The full skeleton:

```python
"""Enforces DIRECTIVE_API_DEPENDENCY_DIRECTION.

Doctrine: src/doctrine/directives/shipped/api-dependency-direction.directive.yaml

No transport-side module (FastAPI router, dashboard CLI command body) may
import from specify_cli.dashboard.scanner or specify_cli.scanner directly.
The MissionRegistry in src/dashboard/services/registry.py is the single
sanctioned reader.

Owned by WP05 of mission mission-registry-and-api-boundary-doctrine-01KQPDBB.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

REPO_ROOT = Path(__file__).resolve().parents[2]

SCAN_PATHS: tuple[Path, ...] = (
    REPO_ROOT / "src" / "dashboard" / "api" / "routers",
    REPO_ROOT / "src" / "specify_cli" / "cli" / "commands" / "dashboard.py",
)

FORBIDDEN_PREFIXES: tuple[str, ...] = (
    "specify_cli.dashboard.scanner",
    "specify_cli.scanner",
)


def _scan_for_forbidden_imports(paths: list[Path]) -> list[str]:
    """Walk each path; return list of (file:line: import_name) violation strings."""
    violations: list[str] = []
    for path in paths:
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            module_name = None
            if isinstance(node, ast.ImportFrom) and node.module:
                module_name = node.module
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if any(alias.name.startswith(p) for p in FORBIDDEN_PREFIXES):
                        violations.append(
                            f"{path.relative_to(REPO_ROOT)}:{node.lineno}: import '{alias.name}'"
                        )
                continue
            if module_name and any(module_name.startswith(p) for p in FORBIDDEN_PREFIXES):
                violations.append(
                    f"{path.relative_to(REPO_ROOT)}:{node.lineno}: from '{module_name}' import ..."
                )
    return violations


def _collect_files(roots: tuple[Path, ...]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            files.extend(root.rglob("*.py"))
    return files


def test_no_transport_module_imports_scanner_directly() -> None:
    """The main scan: every transport-side file is clean."""
    files = _collect_files(SCAN_PATHS)
    violations = _scan_for_forbidden_imports(files)
    assert violations == [], (
        "Transport-side modules MUST consume mission/WP data via the registry, "
        "not by importing the scanner directly. See "
        "src/doctrine/directives/shipped/api-dependency-direction.directive.yaml.\n\n"
        "Violations:\n  " + "\n  ".join(violations) + "\n\n"
        "Fix: replace `from specify_cli.dashboard.scanner import ...` with "
        "`from dashboard.services.registry import MissionRegistry`."
    )


def test_meta_scanner_detects_synthetic_violator(tmp_path: Path) -> None:
    """Positive meta-test: synthetic forbidden import MUST be detected."""
    fake_router = tmp_path / "synthetic_router.py"
    fake_router.write_text(
        "from specify_cli.dashboard.scanner import scan_all_features\n"
        "router = ...\n",
        encoding="utf-8",
    )
    violations = _scan_for_forbidden_imports([fake_router])
    assert len(violations) == 1
    assert "specify_cli.dashboard.scanner" in violations[0]


def test_meta_scanner_accepts_synthetic_clean_module(tmp_path: Path) -> None:
    """Negative meta-test: synthetic clean module MUST NOT be flagged."""
    clean_router = tmp_path / "synthetic_router.py"
    clean_router.write_text(
        "from dashboard.services.registry import MissionRegistry\n"
        "router = ...\n",
        encoding="utf-8",
    )
    violations = _scan_for_forbidden_imports([clean_router])
    assert violations == []
```

### T016 — `test_url_naming_convention.py`

**File**: `tests/architectural/test_url_naming_convention.py` (new).

**Action**: implement per `contracts/architectural-test-contracts.md` § 2. Walk the FastAPI app's `/openapi.json` paths; for each path, assert it matches the resource-noun regex OR is in the action allowlist OR is `/`, `/api-docs`, `/static/...`.

Key implementation points:

```python
"""Enforces DIRECTIVE_REST_RESOURCE_ORIENTATION.

Doctrine: src/doctrine/directives/shipped/rest-resource-orientation.directive.yaml

Every URL in the published OpenAPI document either:
  1. matches the resource-noun convention, OR
  2. is in the action allowlist (with rationale), OR
  3. is a non-API surface (root, docs, static).

Owned by WP05 of mission mission-registry-and-api-boundary-doctrine-01KQPDBB.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

# Resource-noun regex: /api/<collection>[/{param}[/<sub-collection>...]]
RESOURCE_NOUN_PATTERN = re.compile(
    r"^/api/[a-z][a-z0-9-]*(/\{[a-z_]+\}(/[a-z][a-z0-9-]*)?)*$"
)

# Action-shaped URLs: permitted but tagged with rationale.
ACTION_ALLOWLIST: dict[str, str] = {
    "/api/sync/trigger": "POST: action verb in URL acceptable for triggered side effect",
    "/api/shutdown": "POST: action verb in URL acceptable for lifecycle command",
    "/api/charter-lint": "GET: historical name; flagged for rename in mission B",
    "/api/glossary-health": "GET: historical name; flagged for rename in mission B",
    "/api/glossary-terms": "GET: historical name; flagged for rename in mission B",
    "/api/glossary": "GET: historical name; flagged for rename in mission B",
    # WP04's migration leaves these in place per spec C-005 (no contract change here).
    "/api/features": "GET: historical name; renamed to /api/missions in mission B",
    "/api/kanban/{feature_id}": "GET: historical name; renamed in mission B",
    "/api/research/{feature_id}": "GET: file-tree style; acceptable for artifact serving",
    "/api/research/{feature_id}/{file_name}": "GET: file-tree style",
    "/api/contracts/{feature_id}": "GET: file-tree style; acceptable for artifact serving",
    "/api/contracts/{feature_id}/{file_name}": "GET: file-tree style",
    "/api/checklists/{feature_id}": "GET: file-tree style",
    "/api/checklists/{feature_id}/{file_name}": "GET: file-tree style",
    "/api/artifact/{feature_id}/{name}": "GET: file-tree style",
}

# Non-API surfaces.
NON_API_PREFIXES: tuple[str, ...] = ("/", "/api-docs", "/docs", "/redoc", "/openapi.json", "/static")


def _walk_openapi_paths() -> list[str]:
    """Build the FastAPI app and return every path key in its OpenAPI doc."""
    from pathlib import Path
    from dashboard.api import create_app
    app = create_app(project_dir=Path("."), project_token=None)
    return list(app.openapi().get("paths", {}).keys())


def _classify(path: str) -> str:
    if path in ACTION_ALLOWLIST:
        return "action-allowlisted"
    if any(path == p or path.startswith(p + "/") for p in NON_API_PREFIXES):
        return "non-api"
    if RESOURCE_NOUN_PATTERN.match(path):
        return "resource-noun"
    return "violation"


def test_every_openapi_path_is_compliant() -> None:
    paths = _walk_openapi_paths()
    violations = [p for p in paths if _classify(p) == "violation"]
    assert violations == [], (
        "Some OpenAPI paths violate DIRECTIVE_REST_RESOURCE_ORIENTATION.\n"
        "Each path must match the resource-noun convention OR be in the "
        "ACTION_ALLOWLIST with rationale.\n\n"
        "Violations: " + ", ".join(violations) + "\n\n"
        "See src/doctrine/directives/shipped/rest-resource-orientation.directive.yaml"
    )


def test_meta_classifier_detects_bad_shape() -> None:
    """Positive meta-test: synthetic verb-shaped URL MUST be classified violation."""
    assert _classify("/api/badShape!") == "violation"
    assert _classify("/api/CamelCase") == "violation"


def test_meta_classifier_accepts_resource_noun() -> None:
    """Negative meta-test: well-formed URLs MUST classify cleanly."""
    assert _classify("/api/missions") == "resource-noun"
    assert _classify("/api/missions/{id}") == "resource-noun"
    assert _classify("/api/missions/{id}/workpackages") == "resource-noun"
    assert _classify("/api/missions/{id}/workpackages/{wp_id}") == "resource-noun"


def test_meta_action_allowlist_works() -> None:
    """Negative meta-test: allowlisted action URL MUST classify."""
    assert _classify("/api/sync/trigger") == "action-allowlisted"
```

### T017 — `test_resource_models_have_links.py`

**File**: `tests/architectural/test_resource_models_have_links.py` (new).

**Action**: implement per `contracts/architectural-test-contracts.md` § 3. Walk the Pydantic class hierarchy under `src/dashboard/api/models.py`. For every class subclassing `ResourceModel`, assert it declares a `_links: dict[str, Link]` field.

In this mission: ZERO subclasses exist. The test passes vacuously. The marker is in place; mission B activates enforcement.

```python
"""Enforces HATEOAS-LITE paradigm.

Doctrine: src/doctrine/paradigms/shipped/hateoas-lite.paradigm.yaml

Every Pydantic class subclassing dashboard.api.models.ResourceModel MUST
declare a `_links: dict[str, Link]` field.

In this mission (mission-registry-and-api-boundary-doctrine-01KQPDBB), zero
subclasses exist per spec C-006. The test passes vacuously. Mission B
introduces the first subclass when it ships the new resource-oriented
endpoints.

Owned by WP05.
"""
from __future__ import annotations

import inspect
from typing import get_type_hints

import pytest

pytestmark = pytest.mark.architectural


def _find_resource_model_subclasses() -> list[type]:
    """Walk dashboard.api.models for ResourceModel subclasses (excluding ResourceModel itself)."""
    from dashboard.api import models
    from dashboard.api.models import ResourceModel

    subclasses = []
    for name, obj in inspect.getmembers(models):
        if (
            inspect.isclass(obj)
            and obj is not ResourceModel
            and issubclass(obj, ResourceModel)
        ):
            subclasses.append(obj)
    return subclasses


def test_every_resource_model_subclass_declares_links() -> None:
    """Walk the Pydantic hierarchy; assert _links shape on every subclass.

    In this mission, this test passes vacuously (no subclasses exist).
    Mission B activates enforcement.
    """
    from dashboard.api.models import Link

    subclasses = _find_resource_model_subclasses()

    if not subclasses:
        # Mission A: vacuous pass per spec C-006.
        return

    for cls in subclasses:
        hints = get_type_hints(cls)
        assert "_links" in hints, (
            f"{cls.__name__} subclasses ResourceModel but does NOT declare a "
            f"_links field. Required by HATEOAS-LITE paradigm; see "
            f"src/doctrine/paradigms/shipped/hateoas-lite.paradigm.yaml"
        )
        link_type = hints["_links"]
        assert link_type == dict[str, Link], (
            f"{cls.__name__}._links has wrong type: {link_type}. "
            f"Expected: dict[str, Link]"
        )


def test_meta_detector_flags_synthetic_violator() -> None:
    """Positive meta-test: synthetic ResourceModel subclass without _links is flagged."""
    from dashboard.api.models import ResourceModel

    class SyntheticBadResource(ResourceModel):
        name: str
        # missing _links

    hints = get_type_hints(SyntheticBadResource)
    assert "_links" not in hints  # confirms detector logic


def test_meta_detector_accepts_synthetic_compliant_resource() -> None:
    """Negative meta-test: synthetic compliant subclass passes the check."""
    from dashboard.api.models import ResourceModel, Link

    class SyntheticGoodResource(ResourceModel):
        name: str
        _links: dict[str, Link]

    hints = get_type_hints(SyntheticGoodResource)
    assert "_links" in hints
    assert hints["_links"] == dict[str, Link]
```

## Branch Strategy

Lane-less on `feature/650-dashboard-ui-ux-overhaul`. Four files; commit as a single `feat(WP05-...)` commit.

## Definition of Done

- [ ] `Link` and `ResourceModel` marker classes exist in `src/dashboard/api/models.py` with the documented contract.
- [ ] Three architectural tests exist at the documented paths.
- [ ] Each architectural test ships with the main scan + a positive meta-test + a negative meta-test (mission-wide rule C-003).
- [ ] All three tests pass on the current state of the codebase (after WP04's migration is in place).
- [ ] Failure messages name the violating file/line and link the doctrine artefact.
- [ ] No `# noqa` or test-skip markers added to production code to bypass these tests.

## Reviewer guidance

- **Meta-test discipline**: confirm BOTH meta-tests for each architectural test (positive AND negative). A test that only has a positive meta-test could regress to "always passes"; a test with both catches scanner-logic bugs.
- **Failure-message actionability**: the assertion error message MUST name what failed AND what to do about it. Ideal pattern: "X violates rule Y; fix: do Z; see doctrine path."
- **No source-code escape hatches**: confirm WP04 did not add `# noqa` markers or `if TYPE_CHECKING:` shenanigans to bypass the scan. If the scanner finds a violation, the fix is in the production code, not in the test.
- **Vacuous pass on T017 is OK**: per spec C-006, `test_resource_models_have_links.py` passes with zero subclasses today. Confirm the test is not vacuous on mission B's first subclass.

## Risks

- **WP04's migration left a sneaky scanner import**: T015's main scan would catch it; the WP04 reviewer should have caught it earlier. If T015 fails, send the violation back to WP04, do not patch it from this WP.
- **The action allowlist grows large**: every URL today that doesn't match the resource-noun convention goes in the allowlist with rationale. That's fine for mission A (no rename); mission B prunes the allowlist as it renames URLs.
- **Pydantic field-name policy on `_links`**: Pydantic v2 may warn or reject leading-underscore field names. If so, switch to `links` and update the paradigm YAML + the test accordingly. Document the change in the WP review.
