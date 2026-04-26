#!/usr/bin/env python3
"""Generate a JSON snapshot of the resolved ``spec-kitty-events`` envelope.

This script captures the public-surface envelope (Pydantic model schema for
``spec_kitty_events.Event``) at the version actually resolved by the project's
``uv.lock`` and writes it to
``tests/contract/snapshots/spec-kitty-events-<resolved-version>.json``.

Resolution precedence (per FR-022 / ADR 2026-04-26-1):

1. Parse ``uv.lock`` via :mod:`tomllib`.
2. Fall back to :func:`importlib.metadata.version` and emit a warning.

The snapshot file is the load-bearing fixture for
``tests/contract/test_events_envelope_matches_resolved_version.py``. Bumping
``spec-kitty-events`` without regenerating the snapshot is by design a hard
contract failure (mission-review gate, FR-023).

Usage::

    python scripts/snapshot_events_envelope.py
    python scripts/snapshot_events_envelope.py --output-dir tests/contract/snapshots
    python scripts/snapshot_events_envelope.py --force  # overwrite existing snapshot
"""
from __future__ import annotations

import argparse
import json
import sys
import tomllib
import warnings
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "tests" / "contract" / "snapshots"
PACKAGE_NAME = "spec-kitty-events"


def resolve_version_from_uv_lock(uv_lock_path: Path) -> str | None:
    """Return the pinned version of ``spec-kitty-events`` from uv.lock, or None."""
    if not uv_lock_path.is_file():
        return None
    data = tomllib.loads(uv_lock_path.read_text(encoding="utf-8"))
    for package in data.get("package", []):
        if package.get("name") == PACKAGE_NAME:
            version = package.get("version")
            if isinstance(version, str) and version:
                return version
    return None


def resolve_version_from_metadata() -> str | None:
    """Fallback: ask installed metadata for the version."""
    try:
        from importlib.metadata import PackageNotFoundError, version as _meta_version

        return _meta_version(PACKAGE_NAME)
    except PackageNotFoundError:
        return None


def resolve_events_version(repo_root: Path) -> tuple[str, str]:
    """Resolve the version of ``spec-kitty-events`` and report the source.

    Returns ``(version, source)`` where ``source`` is either ``"uv.lock"`` or
    ``"importlib.metadata"``.
    """
    uv_lock_path = repo_root / "uv.lock"
    locked = resolve_version_from_uv_lock(uv_lock_path)
    if locked:
        return locked, "uv.lock"

    warnings.warn(
        f"Could not resolve {PACKAGE_NAME} version from {uv_lock_path}; "
        "falling back to importlib.metadata.",
        RuntimeWarning,
        stacklevel=2,
    )
    meta = resolve_version_from_metadata()
    if meta:
        return meta, "importlib.metadata"
    raise RuntimeError(
        f"Unable to resolve {PACKAGE_NAME} version from uv.lock or "
        "importlib.metadata. Is the package installed and pinned in uv.lock?"
    )


def build_envelope_snapshot(version: str, source: str) -> dict[str, Any]:
    """Capture the envelope schema for the resolved package version."""
    from spec_kitty_events import Event  # late import: depends on installed pkg

    schema = Event.model_json_schema()

    properties = schema.get("properties", {}) or {}
    required = schema.get("required", []) or []

    return {
        "package": PACKAGE_NAME,
        "resolved_version": version,
        "version_source": source,
        "envelope_class": f"{Event.__module__}.{Event.__qualname__}",
        "schema_title": schema.get("title", "Event"),
        "required_fields": sorted(required),
        "field_names": sorted(properties.keys()),
        "schema": schema,
    }


def snapshot_path_for_version(output_dir: Path, version: str) -> Path:
    return output_dir / f"{PACKAGE_NAME}-{version}.json"


def write_snapshot(snapshot: dict[str, Any], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    destination.write_text(payload, encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Snapshot the resolved spec-kitty-events envelope to "
            "tests/contract/snapshots/."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for the snapshot file (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root used to locate uv.lock (default: auto-detected).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the snapshot even if it already exists.",
    )
    parser.add_argument(
        "--print-version",
        action="store_true",
        help="Print only the resolved version and exit; do not write a snapshot.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    version, source = resolve_events_version(args.repo_root)
    print(f"Resolved {PACKAGE_NAME} version: {version} (source: {source})")

    if args.print_version:
        return 0

    destination = snapshot_path_for_version(args.output_dir, version)
    if destination.exists() and not args.force:
        print(f"Snapshot already exists, leaving in place: {destination}")
        print("(Re-run with --force to overwrite.)")
        return 0

    snapshot = build_envelope_snapshot(version, source)
    write_snapshot(snapshot, destination)
    print(f"Wrote envelope snapshot: {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
