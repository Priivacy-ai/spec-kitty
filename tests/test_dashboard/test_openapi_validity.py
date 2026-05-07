"""Structural validity test for the OpenAPI document.

Independent from ``test_openapi_snapshot.py``: that test catches *drift*
against the committed snapshot, this test catches *invalid* OpenAPI output
regardless of whether the snapshot is also stale. If an upstream change
breaks the FastAPI->OpenAPI generator, this test fails before the snapshot
test does, surfacing the root cause.

When ``openapi-spec-validator`` is installed in the venv, we use it for
the canonical structural validation. When it is not, we fall back to a
minimal in-tree validator that asserts the OpenAPI document has the
mandatory top-level fields and that every path advertises at least one
HTTP method with a ``responses`` block. Both code paths run the same
``test_openapi_document_is_structurally_valid`` test so the contract is
identical regardless of which path executes.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.fast


try:  # pragma: no cover - exercised by the import-time branch only
    from openapi_spec_validator import validate_spec as _validate_spec  # type: ignore[import-not-found]

    _HAS_VALIDATOR = True
except ImportError:  # pragma: no cover - default in this venv
    _validate_spec = None  # type: ignore[assignment]
    _HAS_VALIDATOR = False


_HTTP_METHODS = {"get", "put", "post", "delete", "patch", "options", "head", "trace"}


def _minimal_structural_check(spec: dict) -> None:
    """Assert the OpenAPI document has the load-bearing structure.

    This is intentionally minimal — when ``openapi-spec-validator`` is
    available we delegate to it. The fallback only catches the *most
    common* breakage modes (missing top-level keys, an empty paths block,
    or a path entry without a single declared HTTP operation).
    """
    assert isinstance(spec, dict), "OpenAPI document must be a JSON object"
    for key in ("openapi", "info", "paths"):
        assert key in spec, f"OpenAPI document missing top-level key: {key!r}"

    assert spec["openapi"].startswith("3."), (
        f"Unexpected OpenAPI version: {spec['openapi']!r} (expected 3.x)"
    )

    info = spec["info"]
    assert isinstance(info, dict), "info must be an object"
    for key in ("title", "version"):
        assert key in info and isinstance(info[key], str) and info[key], (
            f"info.{key} must be a non-empty string"
        )

    paths = spec["paths"]
    assert isinstance(paths, dict), "paths must be an object"
    assert paths, "paths must be non-empty (FastAPI app mounted no routers?)"

    for path, item in paths.items():
        assert isinstance(item, dict), f"paths[{path!r}] must be an object"
        operations = [
            op for op in item.keys() if op.lower() in _HTTP_METHODS
        ]
        assert operations, (
            f"paths[{path!r}] declares no HTTP operations; expected at least one"
        )
        for op in operations:
            entry = item[op]
            assert isinstance(entry, dict), (
                f"paths[{path!r}].{op} must be an object"
            )
            assert "responses" in entry and entry["responses"], (
                f"paths[{path!r}].{op} missing 'responses' block"
            )


def test_openapi_document_is_structurally_valid(tmp_path: Path) -> None:
    """The generated OpenAPI document must be structurally valid.

    Uses ``openapi-spec-validator`` when available; otherwise applies the
    in-tree minimal validator. Either failure mode signals a real problem
    with the FastAPI app's contract surface.
    """
    from dashboard.api import create_app

    app = create_app(project_dir=tmp_path, project_token=None)
    spec = app.openapi()

    if _HAS_VALIDATOR:
        # ``validate_spec`` raises on invalid input; the test fails via the
        # uncaught exception with the upstream library's message.
        _validate_spec(spec)
    else:
        _minimal_structural_check(spec)
