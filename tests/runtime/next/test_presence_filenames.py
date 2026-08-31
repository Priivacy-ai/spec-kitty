"""Characterization tests for ``_presence_filenames_for`` (WP02, #3770, T007).

Mission expected-artifacts-loader-unification-01M1C9VQ, WP02 (FR-005):
``runtime.next.runtime_bridge_io._presence_filenames_for`` used to duplicate
the org->built-in precedence + ``model_validate`` load logic locally. It now
delegates the whole manifest load to
:func:`charter.activation.manifest_loader.load_manifest` (WP01's relocated,
cached authority) and keeps ONLY the
:func:`~charter.offering.missions.step_projection.project_artifact_name_set`
-> ``frozenset`` projection step.

This WP is all characterization (green-stays-green) -- nothing here carries
``@pytest.mark.regression``. Two things are pinned:

1. Absent manifest -> ``frozenset()``, never ``None`` -- this is the
   projection's own absence output, distinct from the
   ``blocking_artifact_names`` ``None``-vs-``frozenset()`` tri-state
   :func:`runtime.next.runtime_bridge_io._expected_artifacts_manifest_resolves`
   governs (C-002, untouched by this WP).
2. A malformed (YAML-syntax-broken) BUILT-IN manifest still propagates
   ``MalformedManifestError`` unchanged -- this behavior already shipped
   (``1763bf2ae3``) before this WP; the delegate must not re-swallow it. The
   analogous ORG-tier fail-loud widening is WP03/#3412, a distinct,
   not-yet-landed work package -- not characterized here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# Absent manifest -> frozenset(), never None (the projection's own absence
# output; NOT the blocking_artifact_names tri-state).
# ---------------------------------------------------------------------------


class TestPresenceFilenamesAbsentManifest:
    def test_unregistered_family_projects_to_empty_frozenset(self) -> None:
        from runtime.next.runtime_bridge_io import _presence_filenames_for

        result = _presence_filenames_for("totally-unregistered-family")

        assert result == frozenset()
        assert result is not None

    def test_repo_root_given_but_no_manifest_anywhere_still_projects_to_empty_frozenset(
        self, tmp_path: Path
    ) -> None:
        """``repo_root`` supplied, resolves no org roots (no ``.kittify/config.yaml``
        at all) -- the org-tier consult's "no match" path must fall through
        cleanly to the built-in tier, which also has nothing for this family."""
        from runtime.next.runtime_bridge_io import _presence_filenames_for

        project_root = tmp_path / "project-no-config"
        project_root.mkdir()

        result = _presence_filenames_for(
            "totally-unregistered-family", repo_root=project_root
        )

        assert result == frozenset()


# ---------------------------------------------------------------------------
# Malformed (YAML-syntax-broken) built-in manifest -> MalformedManifestError
# propagates BEFORE the projection is ever reached (already-shipped
# built-in-tier behavior, 1763bf2ae3; this delegate must not re-swallow it).
# ---------------------------------------------------------------------------

_MALFORMED_MISSION_TYPE = "malformed-presence-manifest"


class TestPresenceFilenamesMalformedManifestPropagates:
    def test_malformed_builtin_manifest_propagates_malformed_manifest_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import charter.activation.manifest_loader as manifest_loader_module
        from charter.offering.missions.repository import MalformedManifestError
        from runtime.next.runtime_bridge_io import _presence_filenames_for

        offending_path = Path("/fake/doctrine") / _MALFORMED_MISSION_TYPE / "expected-artifacts.yaml"

        class _FakeRepository:
            def get_expected_artifacts(self, mission: str) -> None:
                raise MalformedManifestError(offending_path, ValueError("bad indentation"))

        monkeypatch.setattr(
            manifest_loader_module, "_doctrine_repository", lambda: _FakeRepository()
        )

        with pytest.raises(MalformedManifestError) as exc_info:
            _presence_filenames_for(_MALFORMED_MISSION_TYPE)

        assert exc_info.value.path == offending_path


# ---------------------------------------------------------------------------
# T009 -- routes through the authority: proves the delegation is live, not
# an inert local copy that happens to agree with the authority today.
# ---------------------------------------------------------------------------


class TestPresenceFilenamesRoutesThroughAuthority:
    def test_delegates_to_manifest_loader_load_manifest(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import charter.activation.manifest_loader as manifest_loader_module
        from runtime.next.runtime_bridge_io import _presence_filenames_for

        calls: list[tuple[str, Path | None]] = []
        original_load_manifest = manifest_loader_module.load_manifest

        def _tracking_load_manifest(mission_type: str, repo_root: Path | None = None) -> object:
            calls.append((mission_type, repo_root))
            return original_load_manifest(mission_type, repo_root=repo_root)

        monkeypatch.setattr(manifest_loader_module, "load_manifest", _tracking_load_manifest)

        _presence_filenames_for("software-dev")

        assert calls == [("software-dev", None)]
