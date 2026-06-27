"""Architectural test: centralized auth transport boundary (FR-030).

Pins the invariant from
``architecture/2.x/adr/2026-04-26-2-auth-transport-boundary.md``: the
sync, tracker, and websocket subsystems MUST acquire HTTP transports
from ``specify_cli.auth.transport`` (or the auth-internal SaaS-fallback
helper). Direct ``httpx.Client(...)`` / ``httpx.AsyncClient(...)``
calls in those subsystems are a regression of FR-030.

Walked subsystems
-----------------
* ``src/specify_cli/sync/``
* ``src/specify_cli/tracker/``
* ``src/specify_cli/auth/websocket/`` (the websocket-token provisioning
  surface — the actual websocket connection lives in
  ``src/specify_cli/sync/client.py`` which is already covered above)

Allowlist
---------
The only modules permitted to instantiate ``httpx.Client`` /
``httpx.AsyncClient`` directly are the auth transport modules
themselves:

* ``src/specify_cli/auth/transport.py`` (this WP)
* ``src/specify_cli/auth/http/transport.py`` (pre-existing)

Re-introducing a direct ``httpx.Client(...)`` call in any other module
under the walked subsystems must fail this test.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src" / "specify_cli"

# Subsystems that MUST go through the centralized auth transport.
_WALKED_SUBSYSTEMS: tuple[Path, ...] = (
    _SRC / "sync",
    _SRC / "tracker",
    _SRC / "auth" / "websocket",
)

# The only modules permitted to instantiate httpx clients directly.
#
# The two auth transport modules are the canonical owners (WP06 T032).
# ``tracker/saas_client.py`` is a *temporary* legacy entry: 130+
# downstream tests under ``tests/sync/tracker/`` patch
# ``specify_cli.tracker.saas_client.httpx.Client`` directly, and
# migrating those mocks to the centralized client is out of scope for
# WP06. The intent is documented inside ``saas_client._request``'s
# docstring; the next sweep should remove this entry along with the
# corresponding test-mock migration. See ADR
# ``architecture/2.x/adr/2026-04-26-2-auth-transport-boundary.md`` for
# the broader boundary decision.
_TRANSPORT_ALLOWLIST: frozenset[Path] = frozenset(
    {
        _SRC / "auth" / "transport.py",
        _SRC / "auth" / "http" / "transport.py",
        _SRC / "tracker" / "saas_client.py",
    }
)

_FORBIDDEN_HTTPX_CTORS: frozenset[str] = frozenset({"Client", "AsyncClient"})


def _collect_python_sources(root: Path) -> list[Path]:
    """Return every ``.py`` file under *root* (excluding ``__pycache__``)."""
    return [
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
    ]


def _is_httpx_constructor_call(node: ast.AST) -> bool:
    """Return True when *node* is ``httpx.Client(...)`` or ``httpx.AsyncClient(...)``.

    Only matches the constructor invocation pattern. Type annotations,
    parameter defaults referencing the type by name, and attribute
    accesses to ``httpx.Response`` are NOT matched.
    """
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr not in _FORBIDDEN_HTTPX_CTORS:
        return False
    target = func.value
    if isinstance(target, ast.Name) and target.id == "httpx":
        return True
    return False


def _find_violations(path: Path) -> list[tuple[int, str]]:
    """Return a list of ``(lineno, snippet)`` for every forbidden call in *path*."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # Production sources should always parse; if they don't, that's
        # a louder problem than this rule.
        return []

    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if _is_httpx_constructor_call(node):
            try:
                snippet = ast.unparse(node)
            except Exception:  # pragma: no cover - older interpreters
                snippet = "<unparse-unavailable>"
            violations.append((node.lineno, snippet))
    return violations


class TestAuthTransportSingleton:
    """FR-030: only the auth transport may instantiate ``httpx`` clients."""

    def test_walked_subsystems_have_no_direct_httpx_clients(self) -> None:
        """No direct ``httpx.Client(...)`` / ``httpx.AsyncClient(...)`` calls.

        Walks every Python source under the walked subsystems; for each
        ``ast.Call`` node, asserts it does not match the forbidden
        constructor pattern unless the file is on the allowlist.
        """
        offenders: list[tuple[Path, int, str]] = []
        for subsystem in _WALKED_SUBSYSTEMS:
            if not subsystem.exists():
                continue
            for source_file in _collect_python_sources(subsystem):
                if source_file in _TRANSPORT_ALLOWLIST:
                    continue
                for lineno, snippet in _find_violations(source_file):
                    offenders.append(
                        (source_file.relative_to(_REPO_ROOT), lineno, snippet)
                    )

        if offenders:
            formatted = "\n".join(
                f"  {path}:{lineno}: {snippet}" for path, lineno, snippet in offenders
            )
            pytest.fail(
                "FR-030 violation: direct httpx.Client / httpx.AsyncClient "
                "instantiation outside the auth transport boundary "
                f"({len(offenders)} site(s)):\n{formatted}\n\n"
                "Route the call through specify_cli.auth.transport "
                "(AuthenticatedClient / AsyncAuthenticatedClient) or the "
                "auth-internal request_with_fallback_sync helper."
            )

    def test_transport_module_exists(self) -> None:
        """The centralized transport module must exist (T032)."""
        transport = _SRC / "auth" / "transport.py"
        assert transport.exists(), (
            "Expected centralized auth transport at "
            f"{transport.relative_to(_REPO_ROOT)} (FR-030, T032)."
        )

    def test_transport_exports_authenticated_client(self) -> None:
        """``AuthenticatedClient`` must be importable from the transport module."""
        from specify_cli.auth.transport import (
            AuthenticatedClient,
            AuthRefreshFailed,
            get_client,
        )

        assert AuthenticatedClient is not None
        assert AuthRefreshFailed is not None
        assert callable(get_client)

    def test_allowlisted_files_actually_exist(self) -> None:
        """The allowlist must point at real files; no stale entries.

        Prevents the allowlist from silently masking a deleted file or
        a typo that would otherwise let a violation slip through.
        """
        for allowed in _TRANSPORT_ALLOWLIST:
            assert allowed.exists(), (
                f"Allowlisted file does not exist: {allowed.relative_to(_REPO_ROOT)}"
            )

    def test_negative_control_detects_violation(self, tmp_path: Path) -> None:
        """Reintroducing a direct ``httpx.Client(...)`` call is detected.

        Synthesizes a Python source with a forbidden call and asserts
        the AST scanner finds it. This guards against the scanner
        silently passing because the AST shape changed.
        """
        bad_source = tmp_path / "bad.py"
        bad_source.write_text(
            "import httpx\n"
            "def go():\n"
            "    return httpx.Client(timeout=1.0)\n",
            encoding="utf-8",
        )
        violations = _find_violations(bad_source)
        assert violations, "Scanner failed to flag a direct httpx.Client call"
        assert violations[0][0] == 3
