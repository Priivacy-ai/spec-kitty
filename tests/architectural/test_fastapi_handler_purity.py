"""Architectural test: FastAPI route handlers must be pure adapters.

Per FR-009 / NFR-007, route handler bodies in ``src/dashboard/api/routers/``
must NOT construct ``JSONResponse`` (or other ``Response`` subclasses) by
hand. The handler body should call into a service object and return the
result; FastAPI handles serialization. ``PlainTextResponse(content=...)``
and ``HTMLResponse(content=...)`` are explicitly allowed because they are
the documented model-equivalent return for non-JSON content.

Module-level helpers (functions that are NOT decorated as a route) MAY
construct ``JSONResponse`` — the legacy-parity error payloads in
``features.py::_failure`` and ``diagnostics.py::_failure`` live there.

The scanner walks every ``routers/*.py`` module via stdlib ``ast``,
identifies functions decorated with ``@router.<method>(...)`` (the inner
functions returned from ``register(app)``), and inspects their bodies for
disallowed ``JSONResponse(...)`` calls. A meta-test injects a synthetic
violating router into a tmp file and asserts the scanner flags it.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural


ROUTERS_DIR = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "dashboard"
    / "api"
    / "routers"
)

# JSONResponse is forbidden inside decorated route bodies; PlainTextResponse
# and HTMLResponse are allowed (they are the model-equivalent return for
# non-JSON content). The bare ``Response`` class is also forbidden when used
# as a constructor inside the body.
FORBIDDEN_RESPONSE_CLASSES = {"JSONResponse", "Response"}


def _is_router_method_decorator(decorator: ast.expr) -> bool:
    """Return True when the decorator is ``@router.<http_method>(...)``.

    Matches the shape ``router.get("/...")`` / ``router.post("/...")`` /
    etc., which is the FastAPI router decorator surface used by the
    dashboard handler functions.
    """
    if not isinstance(decorator, ast.Call):
        return False
    func = decorator.func
    if not isinstance(func, ast.Attribute):
        return False
    if not isinstance(func.value, ast.Name):
        return False
    if func.value.id != "router":
        return False
    return func.attr.lower() in {
        "get",
        "post",
        "put",
        "delete",
        "patch",
        "options",
        "head",
        "trace",
    }


def _is_decorated_route(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True when this function is decorated as a FastAPI route."""
    return any(_is_router_method_decorator(d) for d in node.decorator_list)


def _find_forbidden_calls(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[tuple[int, str]]:
    """Return ``[(lineno, class_name)]`` for every disallowed Response call.

    A ``Call`` whose function is a ``Name`` matching one of the forbidden
    classes (``JSONResponse``, ``Response``) is a violation. Calls to
    ``PlainTextResponse(...)`` and ``HTMLResponse(...)`` are *not*
    violations.
    """
    violations: list[tuple[int, str]] = []
    for child in ast.walk(func_node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Name) and func.id in FORBIDDEN_RESPONSE_CLASSES:
            violations.append((child.lineno, func.id))
        elif isinstance(func, ast.Attribute) and func.attr in FORBIDDEN_RESPONSE_CLASSES:
            violations.append((child.lineno, func.attr))
    return violations


def _scan_module(source: str, file_label: str) -> list[str]:
    """Scan a single router module for impure route bodies.

    Walks every top-level ``register(app)`` style module and collects the
    inner decorated functions. Module-level helpers (functions whose
    decorators do NOT match ``@router.<method>``) are intentionally
    excluded — that is where ``_failure(...)`` helpers live.

    Returns a list of human-readable violation strings; an empty list
    means the module is clean.
    """
    tree = ast.parse(source, filename=file_label)
    violations: list[str] = []

    # Walk EVERY function node in the module, regardless of nesting depth.
    # Route handlers are defined inside ``register(app)`` (one level of
    # nesting), so a recursive walk is the simplest way to find them all.
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _is_decorated_route(node):
            continue
        for lineno, class_name in _find_forbidden_calls(node):
            violations.append(
                f"{file_label}:{lineno}: route handler {node.name!r} "
                f"constructs {class_name}(...) directly — move it to a "
                f"private module-level helper or rely on the global "
                f"exception handlers."
            )
    return violations


def _iter_router_modules() -> list[Path]:
    """Return every ``routers/*.py`` module (excluding ``__init__.py``)."""
    return sorted(
        p for p in ROUTERS_DIR.glob("*.py") if p.name != "__init__.py"
    )


class TestFastAPIHandlerPurity:
    """Route handler bodies must not construct ``Response``/``JSONResponse``."""

    def test_routers_directory_exists(self) -> None:
        """Sanity: the routers directory must exist for the scan to be meaningful."""
        assert ROUTERS_DIR.is_dir(), (
            f"Expected routers directory at {ROUTERS_DIR}. "
            "Update the test if the layout changed."
        )

    def test_no_forbidden_response_calls_in_decorated_routes(self) -> None:
        """Every decorated route in ``routers/*.py`` must be a thin adapter."""
        modules = _iter_router_modules()
        assert modules, "No router modules found — scan would be vacuous."

        all_violations: list[str] = []
        for module_path in modules:
            source = module_path.read_text(encoding="utf-8")
            label = str(module_path.relative_to(ROUTERS_DIR.parents[3]))
            all_violations.extend(_scan_module(source, label))

        assert not all_violations, (
            "FastAPI route handler bodies must not construct Response / "
            "JSONResponse directly (FR-009 / NFR-007).\n"
            "Move legacy-parity error payloads to a module-level _failure() "
            "helper, or rely on the global exception handlers in errors.py.\n"
            "Violations:\n" + "\n".join(f"  {v}" for v in all_violations)
        )

    def test_module_level_helpers_are_not_flagged(self, tmp_path: Path) -> None:
        """A module-level ``_failure`` helper must NOT be reported.

        Mirrors the real ``features.py::_failure`` shape: a top-level
        function (no ``@router.*`` decorator) returning a JSONResponse.
        The scanner must ignore it because it is not a decorated route.
        """
        source = (
            "from fastapi import APIRouter, FastAPI\n"
            "from fastapi.responses import JSONResponse\n"
            "\n"
            "def _failure(detail: str) -> JSONResponse:\n"
            "    return JSONResponse(status_code=500, content={'detail': detail})\n"
            "\n"
            "def register(app: FastAPI) -> None:\n"
            "    router = APIRouter()\n"
            "\n"
            "    @router.get('/api/things')\n"
            "    def list_things():\n"
            "        return {'ok': True}\n"
            "\n"
            "    app.include_router(router)\n"
        )
        violations = _scan_module(source, "synthetic_clean.py")
        assert violations == [], (
            "Scanner false-positive: module-level helper was flagged.\n"
            + "\n".join(violations)
        )

    def test_meta_scanner_detects_violation(self, tmp_path: Path) -> None:
        """Meta-test: inject a violating router and confirm the scanner flags it.

        This is the load-bearing self-check: if the scanner regresses to
        being a no-op, this test fails first, before a real router slips
        a violation past CI.
        """
        violating_source = (
            "from fastapi import APIRouter, FastAPI\n"
            "from fastapi.responses import JSONResponse\n"
            "\n"
            "def register(app: FastAPI) -> None:\n"
            "    router = APIRouter()\n"
            "\n"
            "    @router.get('/api/oops')\n"
            "    def oops():\n"
            "        # Forbidden: JSONResponse inside a decorated route body.\n"
            "        return JSONResponse(status_code=500, content={'error': 'bad'})\n"
            "\n"
            "    app.include_router(router)\n"
        )
        violations = _scan_module(violating_source, "synthetic_violating.py")
        assert violations, (
            "Meta-test failed: scanner did not flag the injected "
            "JSONResponse(...) call inside a decorated route body."
        )
        assert any("oops" in v and "JSONResponse" in v for v in violations), (
            "Meta-test failed: violation message must reference the offending "
            f"function and class. Got: {violations!r}"
        )
