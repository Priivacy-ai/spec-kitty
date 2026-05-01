"""Structural regression test: every legacy transport file is rewired.

Verifies that the rewire done in WP08/WP09/WP10 stuck and that no future
refactor accidentally reintroduces the deleted ``specify_cli.sync.auth``
module or its ``AuthClient`` / ``CredentialStore`` classes.

This is a non-runtime test: it uses :mod:`inspect` to read source files
and asserts the presence of :func:`get_token_manager` imports and the
absence of legacy class references.

FR coverage: FR-016 (TokenManager is sole credential surface), FR-017
(HTTP callers must obtain tokens from TokenManager).

Test isolation: this file does not drive the CLI directly, but it is
grouped under ``tests/auth/integration/`` because it enforces the same
structural contract as the CliRunner-based tests.
"""

from __future__ import annotations

import inspect
import subprocess
from pathlib import Path

import pytest


def test_sync_client_imports_get_token_manager() -> None:
    """``sync/client.py`` must import ``get_token_manager`` from the auth pkg.

    Any refactor that removes this import is a regression: it means
    ``sync/client.py`` is no longer obtaining tokens through the TokenManager
    single-flight pipeline and would be reading credentials directly from
    disk (a violation of FR-017).
    """
    import specify_cli.sync.client as client_mod

    source = inspect.getsource(client_mod)
    assert (
        "get_token_manager" in source
    ), "sync/client.py must import get_token_manager (FR-017)"
    assert (
        "from specify_cli.auth" in source
    ), "sync/client.py must import from specify_cli.auth"


def test_sync_client_does_not_reference_legacy_classes() -> None:
    """``sync/client.py`` must not mention ``AuthClient`` or ``CredentialStore``."""
    import specify_cli.sync.client as client_mod

    source = inspect.getsource(client_mod)
    assert "AuthClient" not in source
    assert "CredentialStore" not in source


def test_tracker_saas_client_imports_get_token_manager() -> None:
    """``tracker/saas_client.py`` must obtain tokens through the factory."""
    import specify_cli.tracker.saas_client as t

    source = inspect.getsource(t)
    assert "get_token_manager" in source
    assert "from specify_cli.auth" in source


def test_tracker_saas_client_does_not_reference_legacy_classes() -> None:
    """``tracker/saas_client.py`` must not hold legacy password-era classes.

    Note: a historical test shim exposes ``AuthClient`` as an attribute on
    the module for older tests. That shim lives in tests/, NOT in src/.
    This test scans the source file itself.
    """
    import specify_cli.tracker.saas_client as t

    source = inspect.getsource(t)
    # The real source file must not define or import AuthClient or
    # CredentialStore. A test-only shim lives in tests/sync/tracker/conftest.py
    # and is NOT part of production source.
    assert "class AuthClient" not in source
    assert "class CredentialStore" not in source
    assert "from specify_cli.sync.auth" not in source


def test_legacy_sync_auth_module_does_not_exist() -> None:
    """``src/specify_cli/sync/auth.py`` must be deleted (WP10).

    A real import attempt must raise :class:`ImportError`, not just fail at
    attribute access.
    """
    with pytest.raises(ImportError):
        import specify_cli.sync.auth  # noqa: F401  # pragma: no cover


def test_get_token_manager_has_at_least_five_production_callers() -> None:
    """FR-017: at least 5 non-auth production modules use ``get_token_manager``.

    Mirrors the grep audit in WP08's T046: if the factory is not actually
    called by the sync / tracker / websocket surfaces, the rewire was
    superficial and tokens are being read from disk again.
    """
    # Resolve the src directory from THIS file rather than cwd so the test
    # is robust against pytest invocation from any directory.
    src_root = Path(__file__).resolve().parents[3] / "src" / "specify_cli"
    assert src_root.is_dir(), f"expected src tree at {src_root}"

    result = subprocess.run(
        [
            "grep",
            "-rln",
            "get_token_manager",
            str(src_root),
            "--include=*.py",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    # Each match line is a filename (``grep -l``). Exclude files inside the
    # auth package itself — we want to count downstream consumers.
    all_files = [line for line in result.stdout.splitlines() if line]
    auth_pkg_prefix = str(src_root / "auth")
    downstream = [line for line in all_files if not line.startswith(auth_pkg_prefix)]
    assert len(downstream) >= 5, (
        f"FR-017 expects at least 5 downstream callers of get_token_manager; "
        f"found {len(downstream)}: {downstream}"
    )


def test_websocket_provisioning_uses_factory() -> None:
    """WebSocket token provisioning must call ``get_token_manager`` (FR-016)."""
    import specify_cli.auth.websocket.token_provisioning as wp

    source = inspect.getsource(wp)
    assert "get_token_manager" in source


def test_sync_batch_uses_factory() -> None:
    """``sync/batch.py`` must obtain tokens via the factory (FR-017)."""
    import specify_cli.sync.batch as batch_mod

    source = inspect.getsource(batch_mod)
    assert "get_token_manager" in source
    assert "AuthClient" not in source


def test_sync_background_uses_factory() -> None:
    """``sync/background.py`` must obtain tokens via the factory (FR-017)."""
    import specify_cli.sync.background as bg_mod

    source = inspect.getsource(bg_mod)
    assert "get_token_manager" in source
    assert "AuthClient" not in source
