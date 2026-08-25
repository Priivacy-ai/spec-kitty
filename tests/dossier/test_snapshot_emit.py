"""Tests for the CLI snapshot-hash emit + validation migration (WP02, FR-008).

The CLI snapshot producer and its emit-side validation are migrated off the
retired concat/bare-hex form onto WP01's canonical
``compute_dossier_snapshot_hash`` (``sha256:``-prefixed). These tests pin:

- the producer (``compute_parity_hash_from_dossier`` and ``compute_snapshot``)
  now yields the canonical ``sha256:``-prefixed value;
- the sync-emitter-side validator accepts the canonical form (and the bare-hex
  form, transitional for not-yet-rebaselined drift baselines) while still
  rejecting genuinely malformed values.

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
from specify_cli.sync.emitter import _PAYLOAD_RULES, _is_canonical_snapshot_hash

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


class TestCanonicalSnapshotHashValidator:
    """T006/T008: validation accepts canonical + rejects malformed."""

    def test_accepts_canonical_prefixed(self) -> None:
        assert _is_canonical_snapshot_hash("sha256:" + "a" * 64) is True

    def test_accepts_bare_hex_backcompat(self) -> None:
        # Transitional: drift baselines recorded pre-rebaseline are still bare
        # hex until WP05 runs; the validator must not reject them outright.
        assert _is_canonical_snapshot_hash("a" * 64) is True

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "sha256:",
            "sha256:" + "a" * 63,
            "sha256:" + "g" * 64,
            "a" * 63,
            "a" * 65,
            "SHA256:" + "a" * 64,
            "sha1:" + "a" * 64,
            None,
            12345,
        ],
    )
    def test_rejects_malformed(self, value: object) -> None:
        assert _is_canonical_snapshot_hash(value) is False

    def test_emit_rule_wires_canonical_validator_for_hash_fields(self) -> None:
        # The MissionDossierSnapshotComputed and ParityDriftDetected hash fields
        # must validate through the canonical-accepting successor.
        snap_validators = _PAYLOAD_RULES["MissionDossierSnapshotComputed"]["validators"]
        assert snap_validators["snapshot_hash"] is _is_canonical_snapshot_hash

        drift_validators = _PAYLOAD_RULES["MissionDossierParityDriftDetected"]["validators"]
        assert drift_validators["expected_hash"] is _is_canonical_snapshot_hash
        assert drift_validators["actual_hash"] is _is_canonical_snapshot_hash
