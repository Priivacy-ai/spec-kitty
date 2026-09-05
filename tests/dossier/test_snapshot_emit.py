"""Tests for the CLI snapshot-hash canonical-form migration (WP02, FR-008).

The CLI snapshot producer is migrated off the retired concat/bare-hex form onto
WP01's canonical ``compute_dossier_snapshot_hash`` (``sha256:``-prefixed).
These tests pin that the producer (``compute_parity_hash_from_dossier`` and
``compute_snapshot``) yields the canonical ``sha256:``-prefixed value.

The former sync-emitter-side payload validators (which accepted the bare-hex
form transitionally) died with the sync transport (issue #5); the surviving
consumer of hash-shape classification is
:func:`specify_cli.dossier.rebaseline.is_canonical_snapshot_hash`, covered by
``tests/dossier/test_rebaseline.py``.

See: kitty-specs/dossier-parity-reconciler-01KXYXVP/spec.md (FR-003, FR-008).
"""

from __future__ import annotations

import pytest

from specify_cli.dossier import (
    compute_dossier_snapshot_hash,
    compute_parity_hash_from_dossier,
    compute_snapshot,
)
from specify_cli.dossier.models import ArtifactRef, MissionDossier

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _artifact(key: str, path: str, content_hash: str, *, present: bool = True) -> ArtifactRef:
    return ArtifactRef(
        artifact_key=key,
        artifact_class="input",
        relative_path=path,
        content_hash_sha256=content_hash if present else "",
        size_bytes=1000,
        wp_id=None,
        step_id=None,
        required_status="required",
        is_present=present,
        error_reason=None if present else "not_found",
    )


def _dossier(artifacts: list[ArtifactRef]) -> MissionDossier:
    return MissionDossier(
        mission_type="software-dev",
        mission_run_id="run-wp02",
        mission_slug="042-local-mission-dossier",
        feature_dir="/test/feature",
        artifacts=artifacts,
        manifest={"test": "manifest"},
        latest_snapshot=None,
    )


class TestProducerCanonicalMigration:
    """T007: the producer calls WP01's canonical function (sha256:-prefixed)."""

    def test_compute_parity_hash_returns_canonical_prefixed(self) -> None:
        dossier = _dossier(
            [
                _artifact("spec", "spec.md", "a" * 64),
                _artifact("plan", "plan.md", "b" * 64),
            ]
        )
        result = compute_parity_hash_from_dossier(dossier)
        assert result.startswith("sha256:")
        # Byte-identical to the canonical function over (path, content_hash).
        expected = compute_dossier_snapshot_hash([("spec.md", "a" * 64), ("plan.md", "b" * 64)])
        assert result == expected

    def test_compute_parity_hash_excludes_missing_artifacts(self) -> None:
        with_missing = _dossier(
            [
                _artifact("present", "present.md", "a" * 64),
                _artifact("missing", "missing.md", "b" * 64, present=False),
            ]
        )
        present_only = _dossier([_artifact("present", "present.md", "a" * 64)])
        assert compute_parity_hash_from_dossier(with_missing) == compute_parity_hash_from_dossier(present_only)

    def test_compute_parity_hash_order_independent(self) -> None:
        arts = [_artifact(f"a{i}", f"a{i}.md", hex(i)[2:].zfill(64)) for i in range(5)]
        forward = compute_parity_hash_from_dossier(_dossier(arts))
        backward = compute_parity_hash_from_dossier(_dossier(list(reversed(arts))))
        assert forward == backward

    def test_compute_snapshot_carries_canonical_hash(self) -> None:
        dossier = _dossier([_artifact("spec", "spec.md", "a" * 64)])
        snapshot = compute_snapshot(dossier)
        assert snapshot.parity_hash_sha256.startswith("sha256:")
        assert snapshot.parity_hash_sha256 == compute_dossier_snapshot_hash([("spec.md", "a" * 64)])
