"""Shared fixtures for tests/integration suite."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_saas_sync_for_integration_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable the SaaS sync boundary preflight for integration tests.

    The root conftest enables SPEC_KITTY_ENABLE_SAAS_SYNC=1 to keep legacy
    sync/auth tests live, but the planning/commit-boundary integration tests
    invoke ``setup-plan`` which gates on the boundary preflight with
    ``require_auth=True``. Tests run without hosted auth credentials, so the
    gate refuses with SAAS_SYNC_UNAUTHENTICATED before the actual behavior
    being tested can run. These tests don't intentionally test the boundary
    preflight, so we disable the gate here.
    """
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
