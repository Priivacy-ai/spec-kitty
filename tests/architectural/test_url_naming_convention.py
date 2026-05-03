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
    # Dossier and glossary: historical action-shaped or non-standard path structure.
    "/api/dossier/overview": "GET: historical action-shaped sub-resource; flagged for rename in mission B",
    "/api/dossier/artifacts": "GET: historical action-shaped sub-resource; flagged for rename in mission B",
    "/api/dossier/artifacts/{artifact_key}": "GET: file-tree style under dossier",
    "/api/dossier/snapshots/export": "POST: action verb; export trigger acceptable",
    "/glossary": "GET: root-level legacy path; flagged for rename under /api/ in mission B",
}

# Non-API surfaces.
NON_API_PREFIXES: tuple[str, ...] = ("/", "/api-docs", "/docs", "/redoc", "/openapi.json", "/static")


def _walk_openapi_paths() -> list[str]:
    """Build the FastAPI app and return every path key in its OpenAPI doc."""
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
