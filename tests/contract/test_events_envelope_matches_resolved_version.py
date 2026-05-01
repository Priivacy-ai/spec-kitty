"""Contract: ``spec-kitty-events`` envelope matches the resolved-version snapshot.

Implements FR-022 and DIRECTIVE_003 from the
``stability-and-hygiene-hardening-2026-04`` mission. The snapshot file at
``tests/contract/snapshots/spec-kitty-events-<version>.json`` is produced by
``scripts/snapshot_events_envelope.py`` and pinned to the version actually
resolved by the project's ``uv.lock``. Bumping ``spec-kitty-events`` without
regenerating the snapshot is meant to fail loudly.

See:
- ``kitty-specs/stability-and-hygiene-hardening-2026-04-01KQ4ARB/contracts/events-envelope.md``
- ``architecture/2.x/adr/2026-04-26-1-contract-pinning-resolved-version.md``
- ``docs/development/contract-pinning.md``
"""

from __future__ import annotations

import json
import tomllib
import warnings
from importlib import metadata as importlib_metadata
from pathlib import Path

import pytest

pytestmark = [pytest.mark.contract]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_UV_LOCK = _REPO_ROOT / "uv.lock"
_SNAPSHOT_DIR = _REPO_ROOT / "tests" / "contract" / "snapshots"
_PACKAGE_NAME = "spec-kitty-events"
_REGEN_HINT = (
    "Run `python scripts/snapshot_events_envelope.py --force` from the repo root after bumping spec-kitty-events. See docs/development/contract-pinning.md."
)


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


def _resolve_version_from_metadata() -> str | None:
    try:
        return importlib_metadata.version(_PACKAGE_NAME)
    except importlib_metadata.PackageNotFoundError:
        return None


def _resolve_version() -> tuple[str, str]:
    locked = _resolve_version_from_uv_lock()
    if locked:
        return locked, "uv.lock"
    warnings.warn(
        f"Could not resolve {_PACKAGE_NAME} from uv.lock; falling back to importlib.metadata.",
        RuntimeWarning,
        stacklevel=2,
    )
    meta = _resolve_version_from_metadata()
    if meta:
        return meta, "importlib.metadata"
    pytest.fail(f"Cannot resolve {_PACKAGE_NAME} version from uv.lock or importlib.metadata. {_REGEN_HINT}")


def _snapshot_path(version: str) -> Path:
    return _SNAPSHOT_DIR / f"{_PACKAGE_NAME}-{version}.json"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_resolved_version_snapshot_exists() -> None:
    """A snapshot file MUST exist for the version pinned in uv.lock.

    This is the load-bearing assertion behind FR-022: without a snapshot at
    the resolved version, the contract test cannot pin anything and the
    mission-review gate (FR-023) is meaningless.
    """
    version, source = _resolve_version()
    path = _snapshot_path(version)
    assert path.is_file(), f"Missing envelope snapshot for {_PACKAGE_NAME} {version} (resolved via {source}). Expected at {path}. {_REGEN_HINT}"


def test_envelope_field_names_match_resolved_snapshot() -> None:
    """The live ``Event`` envelope MUST expose the same field set as the snapshot."""
    from spec_kitty_events import Event

    version, _source = _resolve_version()
    path = _snapshot_path(version)
    if not path.is_file():
        pytest.fail(f"Snapshot missing for {_PACKAGE_NAME} {version}: {path}. {_REGEN_HINT}")

    snapshot = json.loads(path.read_text(encoding="utf-8"))
    expected_fields = set(snapshot.get("field_names", []))
    actual_fields = set(Event.model_json_schema().get("properties", {}).keys())

    missing = sorted(expected_fields - actual_fields)
    extra = sorted(actual_fields - expected_fields)
    assert not missing and not extra, (
        f"Envelope field drift detected for {_PACKAGE_NAME} {version}.\n"
        f"  Missing (snapshot has, runtime lacks): {missing}\n"
        f"  Extra (runtime has, snapshot lacks):   {extra}\n"
        f"{_REGEN_HINT}"
    )


def test_envelope_required_fields_match_resolved_snapshot() -> None:
    """The required-field set MUST match the snapshot exactly."""
    from spec_kitty_events import Event

    version, _source = _resolve_version()
    path = _snapshot_path(version)
    if not path.is_file():
        pytest.fail(f"Snapshot missing for {_PACKAGE_NAME} {version}: {path}. {_REGEN_HINT}")

    snapshot = json.loads(path.read_text(encoding="utf-8"))
    expected_required = set(snapshot.get("required_fields", []))
    actual_required = set(Event.model_json_schema().get("required", []) or [])

    missing = sorted(expected_required - actual_required)
    extra = sorted(actual_required - expected_required)
    assert not missing and not extra, (
        f"Envelope required-field drift for {_PACKAGE_NAME} {version}.\n"
        f"  No-longer-required (snapshot req'd, runtime optional): {missing}\n"
        f"  Newly required (runtime req'd, snapshot optional):     {extra}\n"
        f"{_REGEN_HINT}"
    )


def test_snapshot_metadata_self_consistent() -> None:
    """The snapshot's stored ``resolved_version`` must match its filename.

    Guards against operator error where the snapshot file is renamed but its
    payload still references the old version (or vice versa).
    """
    version, _source = _resolve_version()
    path = _snapshot_path(version)
    if not path.is_file():
        pytest.skip("Snapshot missing -- handled by sibling test.")
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    assert snapshot.get("resolved_version") == version, (
        f"Snapshot at {path} stores resolved_version={snapshot.get('resolved_version')!r} but filename pins {version!r}. {_REGEN_HINT}"
    )
    assert snapshot.get("package") == _PACKAGE_NAME, f"Snapshot at {path} is for package {snapshot.get('package')!r}; expected {_PACKAGE_NAME!r}."
