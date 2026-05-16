"""Unit tests for DoctrineService three-layer (shipped/org/project) resolution.

Covers T015 of WP03 in mission ``layered-doctrine-org-layer-01KRNPEE``.

Tests:
- test_no_org_root: org_roots=[] → _org_dir returns None for all repositories
- test_single_org_root: org_roots=[tmp] → _org_dir("directives") resolves correctly
- test_org_root_missing_on_disk: non-existent path → repositories load without error
- test_org_root_artifacts_resolved: org dir with valid directive → service.directives finds it
- test_determinism: same inputs produce identical resolved sets on two calls
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from doctrine.service import DoctrineService

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _write_yaml(path: Path, data: dict) -> None:
    """Write *data* as YAML to *path*, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml = YAML()
    yaml.default_flow_style = False
    with path.open("w", encoding="utf-8") as fh:
        yaml.dump(data, fh)


def _directive_yaml(
    directive_id: str = "DIRECTIVE_001",
    title: str = "Test Directive",
    intent: str = "Test intent.",
    enforcement: str = "required",
) -> dict:
    return {
        "schema_version": "1.0",
        "id": directive_id,
        "title": title,
        "intent": intent,
        "enforcement": enforcement,
    }


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestNoOrgRoot:
    """When org_roots is empty, _org_dir returns None for all artifact types."""

    def test_org_dir_returns_none_when_org_roots_empty(self) -> None:
        service = DoctrineService(org_roots=[])
        assert service._org_dir("directives") is None
        assert service._org_dir("tactics") is None
        assert service._org_dir("styleguides") is None
        assert service._org_dir("toolguides") is None
        assert service._org_dir("paradigms") is None
        assert service._org_dir("procedures") is None
        assert service._org_dir("mission_step_contracts") is None
        assert service._org_dir("agent_profiles") is None

    def test_org_dir_returns_none_when_org_roots_not_provided(self) -> None:
        """Default (None passed for org_roots) is equivalent to empty list."""
        service = DoctrineService()
        assert service._org_dir("directives") is None
        assert service._org_roots == []

    def test_repositories_load_without_error_when_no_org_root(self, tmp_path: Path) -> None:
        """Service with no org roots and empty shipped dir loads cleanly."""
        # Use a tmp shipped root so we don't pick up the real shipped directives
        empty_shipped = tmp_path / "empty-shipped"
        empty_shipped.mkdir()
        service = DoctrineService(shipped_root=empty_shipped, org_roots=[])
        # Accessing the repository must not raise
        repo = service.directives
        assert repo is not None
        assert repo.list_all() == []


class TestSingleOrgRoot:
    """When one org root is configured, _org_dir points into that root."""

    def test_org_dir_returns_correct_path(self, tmp_path: Path) -> None:
        org_root = tmp_path / "org"
        service = DoctrineService(org_roots=[org_root])

        assert service._org_dir("directives") == org_root / "directives"
        assert service._org_dir("tactics") == org_root / "tactics"
        assert service._org_dir("agent_profiles") == org_root / "agent_profiles"

    def test_org_roots_internal_list(self, tmp_path: Path) -> None:
        """org_roots stores the provided paths verbatim."""
        org_root = tmp_path / "org"
        service = DoctrineService(org_roots=[org_root])
        assert service._org_roots == [org_root]

    def test_only_first_org_root_used(self, tmp_path: Path) -> None:
        """Only the first entry in org_roots is used by _org_dir (future-proof)."""
        first = tmp_path / "org-first"
        second = tmp_path / "org-second"
        service = DoctrineService(org_roots=[first, second])

        assert service._org_dir("directives") == first / "directives"


class TestOrgRootMissingOnDisk:
    """A configured org root that does not exist on disk causes no error."""

    def test_nonexistent_org_dir_does_not_raise(self, tmp_path: Path) -> None:
        nonexistent = tmp_path / "no-such-org"
        assert not nonexistent.exists()

        service = DoctrineService(org_roots=[nonexistent])
        # _org_dir still returns the path (existence check is repo's responsibility)
        assert service._org_dir("directives") == nonexistent / "directives"

    def test_repository_loads_without_error_for_nonexistent_org_dir(self, tmp_path: Path) -> None:
        """DirectiveRepository handles a non-existent org_dir gracefully."""
        shipped_root = tmp_path / "shipped-root"
        _write_yaml(
            shipped_root / "directives" / "built-in" / "001.directive.yaml",
            _directive_yaml("DIRECTIVE_001"),
        )

        nonexistent_org = tmp_path / "no-such-org"
        service = DoctrineService(
            shipped_root=shipped_root,
            org_roots=[nonexistent_org],
        )

        # Must not raise; shipped artifact is still accessible
        directive = service.directives.get("DIRECTIVE_001")
        assert directive is not None

    def test_shipped_artifacts_accessible_when_org_dir_missing(self, tmp_path: Path) -> None:
        """Shipped items load normally even when org dir does not exist on disk."""
        shipped_root = tmp_path / "shipped-root"
        _write_yaml(
            shipped_root / "directives" / "built-in" / "001.directive.yaml",
            _directive_yaml("DIRECTIVE_001", title="Shipped Only"),
        )

        service = DoctrineService(
            shipped_root=shipped_root,
            org_roots=[tmp_path / "nonexistent"],
        )

        assert service.directives.get("DIRECTIVE_001") is not None
        assert service.directives.get_provenance("DIRECTIVE_001") == "builtin"


class TestOrgRootArtifactsResolved:
    """When the org dir contains valid artifacts they are merged above shipped."""

    def test_org_directive_visible_via_service(self, tmp_path: Path) -> None:
        shipped_root = tmp_path / "shipped-root"
        org_root = tmp_path / "org-root"

        # Shipped baseline
        _write_yaml(
            shipped_root / "directives" / "built-in" / "001.directive.yaml",
            _directive_yaml("DIRECTIVE_001", title="Shipped Title"),
        )
        # Org adds a new directive
        _write_yaml(
            org_root / "directives" / "org-new.directive.yaml",
            _directive_yaml("DIRECTIVE_ORG", title="Org Title"),
        )

        service = DoctrineService(
            shipped_root=shipped_root,
            org_roots=[org_root],
        )

        org_directive = service.directives.get("DIRECTIVE_ORG")
        assert org_directive is not None
        assert org_directive.title == "Org Title"
        assert service.directives.get_provenance("DIRECTIVE_ORG") == "org"

    def test_org_overrides_shipped_directive(self, tmp_path: Path) -> None:
        shipped_root = tmp_path / "shipped-root"
        org_root = tmp_path / "org-root"

        _write_yaml(
            shipped_root / "directives" / "built-in" / "001.directive.yaml",
            _directive_yaml("DIRECTIVE_001", title="Shipped Title"),
        )
        _write_yaml(
            org_root / "directives" / "001.directive.yaml",
            _directive_yaml("DIRECTIVE_001", title="Org Override"),
        )

        service = DoctrineService(
            shipped_root=shipped_root,
            org_roots=[org_root],
        )

        directive = service.directives.get("DIRECTIVE_001")
        assert directive is not None
        assert directive.title == "Org Override"
        assert service.directives.get_provenance("DIRECTIVE_001") == "org"

    def test_project_overrides_org(self, tmp_path: Path) -> None:
        shipped_root = tmp_path / "shipped-root"
        org_root = tmp_path / "org-root"
        project_root = tmp_path / "project-root"

        _write_yaml(
            shipped_root / "directives" / "built-in" / "001.directive.yaml",
            _directive_yaml("DIRECTIVE_001", title="Shipped"),
        )
        _write_yaml(
            org_root / "directives" / "001.directive.yaml",
            _directive_yaml("DIRECTIVE_001", title="Org Override"),
        )
        _write_yaml(
            project_root / "directives" / "001.directive.yaml",
            _directive_yaml("DIRECTIVE_001", title="Project Override"),
        )

        service = DoctrineService(
            shipped_root=shipped_root,
            org_roots=[org_root],
            project_root=project_root,
        )

        directive = service.directives.get("DIRECTIVE_001")
        assert directive is not None
        assert directive.title == "Project Override"
        assert service.directives.get_provenance("DIRECTIVE_001") == "project"

    def test_cache_is_invalidated_between_service_instances(self, tmp_path: Path) -> None:
        """Two separate service instances with the same paths produce independent caches."""
        shipped_root = tmp_path / "shipped-root"
        org_root = tmp_path / "org-root"

        _write_yaml(
            shipped_root / "directives" / "built-in" / "001.directive.yaml",
            _directive_yaml("DIRECTIVE_001"),
        )
        _write_yaml(
            org_root / "directives" / "org.directive.yaml",
            _directive_yaml("DIRECTIVE_ORG"),
        )

        svc_a = DoctrineService(shipped_root=shipped_root, org_roots=[org_root])
        svc_b = DoctrineService(shipped_root=shipped_root, org_roots=[org_root])

        assert svc_a.directives is not svc_b.directives


class TestDeterminism:
    """Identical inputs produce identical resolved sets on repeated accesses."""

    def test_same_inputs_produce_identical_sets(self, tmp_path: Path) -> None:
        shipped_root = tmp_path / "shipped-root"
        org_root = tmp_path / "org-root"

        _write_yaml(
            shipped_root / "directives" / "built-in" / "001.directive.yaml",
            _directive_yaml("DIRECTIVE_001", title="Shipped"),
        )
        _write_yaml(
            org_root / "directives" / "002.directive.yaml",
            _directive_yaml("DIRECTIVE_002", title="Org"),
        )

        service_a = DoctrineService(shipped_root=shipped_root, org_roots=[org_root])
        service_b = DoctrineService(shipped_root=shipped_root, org_roots=[org_root])

        ids_a = {d.id for d in service_a.directives.list_all()}
        ids_b = {d.id for d in service_b.directives.list_all()}

        assert ids_a == ids_b
        assert "DIRECTIVE_001" in ids_a
        assert "DIRECTIVE_002" in ids_a

    def test_repeated_property_access_returns_cached_object(self, tmp_path: Path) -> None:
        """The lazy cache returns the same repository object on subsequent accesses."""
        service = DoctrineService(org_roots=[tmp_path / "org"])

        first = service.directives
        second = service.directives
        assert first is second

    def test_org_roots_empty_matches_no_org_roots_behavior(self, tmp_path: Path) -> None:
        """org_roots=[] is equivalent to not passing org_roots at all."""
        shipped_root = tmp_path / "shipped-root"
        _write_yaml(
            shipped_root / "directives" / "built-in" / "001.directive.yaml",
            _directive_yaml("DIRECTIVE_001"),
        )

        svc_explicit = DoctrineService(shipped_root=shipped_root, org_roots=[])
        svc_default = DoctrineService(shipped_root=shipped_root)

        ids_explicit = {d.id for d in svc_explicit.directives.list_all()}
        ids_default = {d.id for d in svc_default.directives.list_all()}

        assert ids_explicit == ids_default
