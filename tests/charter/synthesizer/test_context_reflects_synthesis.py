"""End-to-end test: charter context reflects synthesized doctrine (FR-018 / SC-005).

After a synthesis run writes project-local artifacts to `.kittify/doctrine/`,
``DoctrineService`` (wired through ``_build_doctrine_service`` in both
``compiler.py`` and ``context.py``) must surface at least one project-specific
item that was NOT present before synthesis.

This test proves SC-005: context sees project-local doctrine when the
``.kittify/doctrine/`` directory is present.

Approach:
1. Build a ``DoctrineService`` with no project root → verify the project
   directive is absent (pre-synthesis baseline).
2. Write a minimal project directive YAML under a temp ``.kittify/doctrine/``
   tree (simulating what the synthesizer would produce).
3. Build a ``DoctrineService`` with the new project root → verify the project
   directive is now present (post-synthesis assertion).

This tests the wiring, not the full synthesis pipeline (which is WP02/WP03).
"""

from __future__ import annotations

from pathlib import Path

from charter._doctrine_paths import resolve_project_root
from charter.compiler import _default_doctrine_service
from charter.context import _build_doctrine_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PROJECT_DIRECTIVE_ID = "PROJECT_001"
_PROJECT_DIRECTIVE_SLUG = "project-decision-doc-directive"
_PROJECT_DIRECTIVE_YAML = f"""\
schema_version: "1.0"
id: {_PROJECT_DIRECTIVE_ID}
title: Project Decision Documentation Directive
intent: >
  All significant project decisions must be documented with context, rationale,
  and considered alternatives to ensure team alignment and future traceability.
enforcement: required
scope: >
  Applies to all architectural and process decisions made within this project.
"""

_PROJECT_TACTIC_ID = "how-we-apply-directive-003"
_PROJECT_TACTIC_YAML = f"""\
schema_version: "1.0"
id: {_PROJECT_TACTIC_ID}
name: How We Apply Decision Documentation
purpose: >
  Operationalises DIRECTIVE_003 for this project's specific context.
applies_to:
  - directive: DIRECTIVE_003
"""


def _create_project_doctrine_tree(base_dir: Path) -> Path:
    """Create a minimal ``.kittify/doctrine/`` tree under *base_dir*.

    Writes one project directive so the repository scan can find it.
    Returns the ``.kittify/doctrine/`` path.
    """
    kittify_doctrine = base_dir / ".kittify" / "doctrine"
    directives_dir = kittify_doctrine / "directives"
    directives_dir.mkdir(parents=True)

    directive_file = directives_dir / f"001-{_PROJECT_DIRECTIVE_SLUG}.directive.yaml"
    directive_file.write_text(_PROJECT_DIRECTIVE_YAML, encoding="utf-8")
    return kittify_doctrine


def _project_root_for(repo_root: Path) -> Path | None:
    return resolve_project_root(repo_root)


# ---------------------------------------------------------------------------
# 1. Pre-synthesis baseline: project directive absent without synthesis
# ---------------------------------------------------------------------------

class TestPreSynthesisBaseline:
    """Before synthesis, project-specific directive is absent from the service."""

    def test_no_kittify_doctrine_dir_means_no_project_root(
        self, tmp_path: Path
    ) -> None:
        """Without .kittify/doctrine/, project_root is None (pre-synthesis)."""
        project_root = _project_root_for(tmp_path)
        assert project_root is None

    def test_doctrine_service_without_project_root_misses_project_directive(
        self, tmp_path: Path
    ) -> None:
        """DoctrineService with project_root=None cannot see project directives."""
        svc = _default_doctrine_service(tmp_path)
        directive = svc.directives.get(_PROJECT_DIRECTIVE_ID)
        assert directive is None, (
            f"Expected {_PROJECT_DIRECTIVE_ID} to be absent before synthesis, "
            f"but found: {directive}"
        )

    def test_context_build_service_without_kittify_misses_project_directive(
        self, tmp_path: Path
    ) -> None:
        """context._build_doctrine_service without .kittify/doctrine/ misses project directive."""
        svc = _build_doctrine_service(tmp_path)
        directive = svc.directives.get(_PROJECT_DIRECTIVE_ID)  # type: ignore[attr-defined]
        assert directive is None


# ---------------------------------------------------------------------------
# 2. Post-synthesis: project directive present after writing artifacts
# ---------------------------------------------------------------------------

class TestPostSynthesisArtifactVisible:
    """After writing project artifacts, DoctrineService surfaces them."""

    def test_project_root_resolves_to_kittify_doctrine(
        self, tmp_path: Path
    ) -> None:
        """After synthesis writes .kittify/doctrine/, resolve_project_root points there."""
        _create_project_doctrine_tree(tmp_path)
        project_root = _project_root_for(tmp_path)
        assert project_root == tmp_path / ".kittify" / "doctrine"

    def test_compiler_service_sees_project_directive_post_synthesis(
        self, tmp_path: Path
    ) -> None:
        """compiler._default_doctrine_service surfaces project directive after synthesis."""
        _create_project_doctrine_tree(tmp_path)
        svc = _default_doctrine_service(tmp_path)
        directive = svc.directives.get(_PROJECT_DIRECTIVE_ID)
        assert directive is not None, (
            f"Expected {_PROJECT_DIRECTIVE_ID} to be present post-synthesis "
            f"(via compiler._default_doctrine_service) but was absent."
        )
        assert directive.id == _PROJECT_DIRECTIVE_ID
        assert "Decision" in directive.title

    def test_context_service_sees_project_directive_post_synthesis(
        self, tmp_path: Path
    ) -> None:
        """context._build_doctrine_service surfaces project directive after synthesis."""
        _create_project_doctrine_tree(tmp_path)
        svc = _build_doctrine_service(tmp_path)
        directive = svc.directives.get(_PROJECT_DIRECTIVE_ID)  # type: ignore[attr-defined]
        assert directive is not None, (
            f"Expected {_PROJECT_DIRECTIVE_ID} to be present post-synthesis "
            f"(via context._build_doctrine_service) but was absent."
        )
        assert directive.id == _PROJECT_DIRECTIVE_ID

    def test_project_directive_not_in_baseline_service(
        self, tmp_path: Path
    ) -> None:
        """SC-005: project-specific item is absent pre-synthesis, present post-synthesis."""
        # --- Pre-synthesis ---
        svc_before = _default_doctrine_service(tmp_path)
        directive_before = svc_before.directives.get(_PROJECT_DIRECTIVE_ID)
        assert directive_before is None, "Pre-synthesis: directive must be absent"

        # --- Synthesis simulation: write project artifacts ---
        _create_project_doctrine_tree(tmp_path)

        # --- Post-synthesis ---
        svc_after = _default_doctrine_service(tmp_path)
        directive_after = svc_after.directives.get(_PROJECT_DIRECTIVE_ID)
        assert directive_after is not None, "Post-synthesis: directive must be present"

        # Structural assertion: ID matches exactly
        assert directive_after.id == _PROJECT_DIRECTIVE_ID

    def test_at_least_one_project_item_appears_after_synthesis(
        self, tmp_path: Path
    ) -> None:
        """SC-005 floor: at least one project-specific item appears post-synthesis.

        This is intentionally broad (matches the spec's 'at least one' criterion)
        so that regressions are caught without over-specifying the exact artifact.
        """
        _create_project_doctrine_tree(tmp_path)
        svc = _default_doctrine_service(tmp_path)

        # list_all() returns a list of directive objects; extract ids
        all_directives = svc.directives.list_all()
        all_ids = [d.id for d in all_directives]
        assert _PROJECT_DIRECTIVE_ID in all_ids, (
            f"Expected {_PROJECT_DIRECTIVE_ID} in list_all() but got: {all_ids}"
        )


# ---------------------------------------------------------------------------
# 3. Empty .kittify/doctrine/ produces no spurious items (R-2.3 impact check)
# ---------------------------------------------------------------------------

class TestEmptyKittifyDoctrineNoSideEffects:
    """R-2.3: empty .kittify/doctrine/ resolves project_root but adds nothing."""

    def test_empty_kittify_doctrine_resolves_root_but_no_extra_directives(
        self, tmp_path: Path
    ) -> None:
        # Create the directory but don't write any doctrine files
        empty_kittify = tmp_path / ".kittify" / "doctrine"
        empty_kittify.mkdir(parents=True)

        svc_before = _default_doctrine_service(tmp_path)
        ids_before = {d.id for d in svc_before.directives.list_all()}

        # project_root resolves even though dir is empty
        project_root = _project_root_for(tmp_path)
        assert project_root == empty_kittify

        svc_after = _default_doctrine_service(tmp_path)
        ids_after = {d.id for d in svc_after.directives.list_all()}

        # No extra directives appear (empty overlay has no impact on shipped layer)
        extra = ids_after - ids_before
        assert extra == set(), f"Empty overlay added unexpected directives: {extra}"
