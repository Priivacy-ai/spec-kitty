"""Cross-repo consumer smoke tests for ``spec-kitty-events``.

Originally pinned ``spec_kitty_events.__version__ == "3.2.0"`` against a
hard-coded version string. WP05 (``stability-and-hygiene-hardening-2026-04``,
FR-022 / DIRECTIVE_003) replaces that pattern with a resolved-version
lookup driven by ``uv.lock`` so the test never drifts behind the actual
pinned package.

Companion test:
``tests/contract/test_events_envelope_matches_resolved_version.py`` covers
envelope-shape drift via a snapshot file. This module retains the
fixture-shape smoke checks that validate the canonical mission identity
field set in shipped fixtures.
"""

from __future__ import annotations

import json
import tomllib
import warnings
from importlib import metadata as importlib_metadata
from importlib import resources
from pathlib import Path

import pytest

pytestmark = [pytest.mark.contract]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_UV_LOCK = _REPO_ROOT / "uv.lock"
_PACKAGE_NAME = "spec-kitty-events"


def _resolve_version_from_uv_lock() -> str | None:
    if not _UV_LOCK.is_file():
        return None
    data = tomllib.loads(_UV_LOCK.read_text(encoding="utf-8"))
    for package in data.get("package", []):
        if package.get("name") == _PACKAGE_NAME:
            version = package.get("version")
            if isinstance(version, str) and version:
                return version
    return None


def _resolved_events_version() -> str:
    locked = _resolve_version_from_uv_lock()
    if locked:
        return locked
    warnings.warn(
        f"Could not resolve {_PACKAGE_NAME} from uv.lock; falling back to "
        "importlib.metadata.",
        RuntimeWarning,
        stacklevel=2,
    )
    return importlib_metadata.version(_PACKAGE_NAME)


def test_spec_kitty_events_module_version_matches_resolved_pin() -> None:
    """``spec_kitty_events.__version__`` MUST match the version pinned in uv.lock.

    Replaces the previous hard-coded ``== "3.2.0"`` assertion. A drift here
    means either uv.lock and the installed package are out of sync, or the
    upstream package shipped a build whose ``__version__`` does not match
    its package metadata. Both are real failures.
    """
    import spec_kitty_events

    expected = _resolved_events_version()
    actual = getattr(spec_kitty_events, "__version__", None)
    assert actual == expected, (
        f"spec_kitty_events.__version__ = {actual!r}, but uv.lock / "
        f"importlib.metadata pin {expected!r}. Either re-run `uv sync` to "
        "align the installed package with uv.lock, or regenerate the "
        "envelope snapshot via "
        "`python scripts/snapshot_events_envelope.py --force` if the bump "
        "is intentional. See docs/development/contract-pinning.md."
    )


def test_spec_kitty_events_fixture_shape_retains_mission_identity_fields() -> None:
    """Pinned downstream fixtures MUST retain the canonical mission identity names."""
    fixture_dir = (
        resources.files("spec_kitty_events") / "conformance" / "fixtures" / "events" / "valid"
    )
    for fixture_name in ("mission_created.json", "mission_closed.json"):
        payload = json.loads((fixture_dir / fixture_name).read_text(encoding="utf-8"))
        assert payload["mission_slug"] == "mission-001"
        assert payload["mission_number"] == 1
        assert payload["mission_type"] == "software-dev"
        assert "feature_slug" not in payload
        assert "feature_number" not in payload
        assert "feature_type" not in payload
