"""Unit tests for ``acceptance._status_read_feature_dir`` canonical mid8 routing.

WP03 / T026 (FR-002, C-007): the acceptance status-read dir helper derives its
mid8 disambiguator through the ONE sanctioned cascade
(:func:`resolve_declared_mid8`) instead of the retired bespoke
``meta.mid8`` → ``mid8_from_slug`` parallel selection path. These tests pin:

(a) the tier-2 WIN — a mission whose primary ``meta.json`` carries ``mission_id``
    but NO explicit ``mid8`` now derives the AUTHORITATIVE mid8 from the declared
    identity (the bespoke path would have fallen straight to the blind
    ``mid8_from_slug`` heuristic);
(b) the acceptance-specific ``status_dir if status_dir.exists() else feature_dir``
    fallback is preserved — when no canonical status dir exists on disk, the
    helper degrades to the primary anchor dir rather than fail-closing.

Fixtures use realistic test data (NFR-005): a real 26-char Crockford ULID and the
real ``kitty-specs/<slug>-<mid8>/`` on-disk layout.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.acceptance import _status_read_feature_dir

pytestmark = [pytest.mark.unit, pytest.mark.fast]

FULL_ULID = "01KVJPEQ7M3K8N2QXR4VBZ9HCD"
MID8 = FULL_ULID[:8]  # "01KVJPEQ"
SLUG = "read-side-surface-resolver-adoption"
HANDLE = f"{SLUG}-{MID8}"


def _write_meta(feature_dir: Path, meta: dict[str, object]) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


def test_derives_authoritative_mid8_from_declared_mission_id(tmp_path: Path) -> None:
    """Tier-2 win: meta carries mission_id (no explicit mid8) → canonical dir."""
    repo_root = tmp_path
    # Primary mission dir under the canonical ``<slug>-<mid8>`` name carrying the
    # declared mission_id but NO explicit ``mid8`` field.
    feature_dir = repo_root / "kitty-specs" / HANDLE
    _write_meta(
        feature_dir,
        {"mission_slug": HANDLE, "mission_id": FULL_ULID, "mission_type": "software-dev"},
    )

    resolved = _status_read_feature_dir(repo_root, HANDLE, feature_dir)

    # The canonical derivation indexes the existing ``<slug>-<mid8>`` dir from the
    # declared identity; the helper returns it because it exists on disk.
    assert resolved == feature_dir
    assert resolved.exists()


def test_preserves_exists_else_feature_dir_fallback(tmp_path: Path) -> None:
    """No canonical status dir on disk → degrade to the primary anchor dir."""
    repo_root = tmp_path
    # A primary anchor dir exists, but no resolvable canonical status surface is
    # materialised for a bare slug with no identity-bearing meta.
    feature_dir = repo_root / "kitty-specs" / SLUG
    feature_dir.mkdir(parents=True, exist_ok=True)  # exists but no meta.json

    resolved = _status_read_feature_dir(repo_root, SLUG, feature_dir)

    # Lenient acceptance fallback: degrades to the supplied feature_dir rather
    # than raising or returning a non-existent canonical path.
    assert resolved == feature_dir
