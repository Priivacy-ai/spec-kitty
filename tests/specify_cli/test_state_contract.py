"""Unit tests for the state contract module."""

import json
from dataclasses import FrozenInstanceError

import pytest

from specify_cli.state_contract import (
    STATE_SURFACES,
    AuthorityClass,
    GitClass,
    StateFormat,
    StateRoot,
    get_runtime_gitignore_entries,
    get_surfaces_by_authority,
    get_surfaces_by_git_class,
    get_surfaces_by_root,
)


# ---------------------------------------------------------------------------
# Uniqueness and completeness
# ---------------------------------------------------------------------------


def test_surface_names_unique():
    """Every surface must have a unique name."""
    names = [s.name for s in STATE_SURFACES]
    assert len(names) == len(set(names)), f"Duplicate names: {[n for n in names if names.count(n) > 1]}"


def test_minimum_surface_count():
    """The registry must contain at least 30 surfaces from the audit."""
    assert len(STATE_SURFACES) >= 30, f"Only {len(STATE_SURFACES)} surfaces registered"


def test_path_patterns_unique():
    """Every surface must have a unique path_pattern."""
    patterns = [s.path_pattern for s in STATE_SURFACES]
    assert len(patterns) == len(set(patterns)), (
        f"Duplicate patterns: {[p for p in patterns if patterns.count(p) > 1]}"
    )


# ---------------------------------------------------------------------------
# Enum coverage
# ---------------------------------------------------------------------------


def test_all_state_roots_used():
    """At least one surface per StateRoot value."""
    roots_used = {s.root for s in STATE_SURFACES}
    for root in StateRoot:
        assert root in roots_used, f"StateRoot.{root.name} has no surfaces"


def test_all_git_classes_used():
    """At least one surface per GitClass value."""
    classes_used = {s.git_class for s in STATE_SURFACES}
    for gc in GitClass:
        assert gc in classes_used, f"GitClass.{gc.name} has no surfaces"


def test_all_authority_classes_used():
    """At least one surface per AuthorityClass value."""
    authorities_used = {s.authority for s in STATE_SURFACES}
    for auth in AuthorityClass:
        assert auth in authorities_used, f"AuthorityClass.{auth.name} has no surfaces"


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def test_to_dict_serializable():
    """to_dict() must produce a JSON-serializable dict with correct keys."""
    for s in STATE_SURFACES:
        d = s.to_dict()
        # Must not raise
        json.dumps(d)
        # Spot-check enum serialization
        assert d["name"] == s.name
        assert d["root"] == s.root.value
        assert d["format"] == s.format.value
        assert d["authority"] == s.authority.value
        assert d["git_class"] == s.git_class.value


def test_enum_values_are_strings():
    """str-based enums must serialize to their string values directly."""
    for root in StateRoot:
        assert isinstance(root.value, str)
    for auth in AuthorityClass:
        assert isinstance(auth.value, str)
    for gc in GitClass:
        assert isinstance(gc.value, str)
    for fmt in StateFormat:
        assert isinstance(fmt.value, str)


# ---------------------------------------------------------------------------
# Frozen dataclass
# ---------------------------------------------------------------------------


def test_frozen():
    """StateSurface instances are immutable."""
    s = STATE_SURFACES[0]
    with pytest.raises(FrozenInstanceError):
        s.name = "modified"  # type: ignore[misc]


def test_frozen_cannot_add_attribute():
    """Cannot add new attributes to frozen dataclass instances."""
    s = STATE_SURFACES[0]
    with pytest.raises(FrozenInstanceError):
        s.extra = "value"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Helper: get_surfaces_by_root
# ---------------------------------------------------------------------------


def test_get_surfaces_by_root_project():
    """PROJECT root returns non-empty list with correct root values."""
    project = get_surfaces_by_root(StateRoot.PROJECT)
    assert len(project) > 0
    assert all(s.root == StateRoot.PROJECT for s in project)


def test_get_surfaces_by_root_feature():
    """FEATURE root returns non-empty list with correct root values."""
    feature = get_surfaces_by_root(StateRoot.FEATURE)
    assert len(feature) > 0
    assert all(s.root == StateRoot.FEATURE for s in feature)


def test_get_surfaces_by_root_all_roots_sum():
    """Surfaces from all roots sum to total count."""
    total = sum(len(get_surfaces_by_root(r)) for r in StateRoot)
    assert total == len(STATE_SURFACES)


def test_get_surfaces_by_root_returns_new_list():
    """Helper returns a new list, not a view."""
    a = get_surfaces_by_root(StateRoot.PROJECT)
    b = get_surfaces_by_root(StateRoot.PROJECT)
    assert a == b
    assert a is not b


# ---------------------------------------------------------------------------
# Helper: get_surfaces_by_git_class
# ---------------------------------------------------------------------------


def test_get_surfaces_by_git_class_tracked():
    """TRACKED git class returns non-empty list."""
    tracked = get_surfaces_by_git_class(GitClass.TRACKED)
    assert len(tracked) > 0
    assert all(s.git_class == GitClass.TRACKED for s in tracked)


def test_get_surfaces_by_git_class_ignored():
    """IGNORED git class returns non-empty list."""
    ignored = get_surfaces_by_git_class(GitClass.IGNORED)
    assert len(ignored) > 0
    assert all(s.git_class == GitClass.IGNORED for s in ignored)


# ---------------------------------------------------------------------------
# Helper: get_surfaces_by_authority
# ---------------------------------------------------------------------------


def test_get_surfaces_by_authority_authoritative():
    """AUTHORITATIVE authority returns non-empty list."""
    auth = get_surfaces_by_authority(AuthorityClass.AUTHORITATIVE)
    assert len(auth) > 0
    assert all(s.authority == AuthorityClass.AUTHORITATIVE for s in auth)


def test_get_surfaces_by_authority_derived():
    """DERIVED authority returns non-empty list."""
    derived = get_surfaces_by_authority(AuthorityClass.DERIVED)
    assert len(derived) > 0
    assert all(s.authority == AuthorityClass.DERIVED for s in derived)


# ---------------------------------------------------------------------------
# Helper: get_runtime_gitignore_entries
# ---------------------------------------------------------------------------


def test_runtime_gitignore_entries_exact():
    """Gitignore entries must contain all expected canonical patterns."""
    entries = get_runtime_gitignore_entries()
    expected = [
        ".kittify/.dashboard",
        ".kittify/constitution/context-state.json",
        ".kittify/constitution/directives.yaml",
        ".kittify/constitution/governance.yaml",
        ".kittify/constitution/metadata.yaml",
        ".kittify/dossiers/",
        ".kittify/events/",
        ".kittify/merge-state.json",
        ".kittify/missions/",
        ".kittify/runtime/",
        ".kittify/workspaces/",
    ]
    assert entries == expected


def test_runtime_gitignore_entries_no_placeholders():
    """Gitignore entries must not contain placeholder tokens."""
    entries = get_runtime_gitignore_entries()
    for entry in entries:
        assert "<" not in entry, f"Placeholder in gitignore entry: {entry}"
        assert "*" not in entry or entry.endswith("__pycache__/"), (
            f"Wildcard in gitignore entry: {entry}"
        )


def test_runtime_gitignore_entries_sorted():
    """Gitignore entries must be sorted."""
    entries = get_runtime_gitignore_entries()
    assert entries == sorted(entries)


def test_runtime_gitignore_entries_only_project_ignored():
    """Every gitignore entry must trace back to a PROJECT/IGNORED surface."""
    entries = get_runtime_gitignore_entries()
    for entry in entries:
        # Entry is either a concrete path or a directory-level collapse
        # Either way, at least one registry surface must match
        if entry.endswith("/"):
            # Directory pattern: at least one surface path_pattern must start with this prefix
            matching = [
                s
                for s in STATE_SURFACES
                if s.root == StateRoot.PROJECT
                and s.git_class == GitClass.IGNORED
                and s.path_pattern.startswith(entry.rstrip("/"))
            ]
        else:
            matching = [
                s
                for s in STATE_SURFACES
                if s.root == StateRoot.PROJECT
                and s.git_class == GitClass.IGNORED
                and s.path_pattern == entry
            ]
        assert len(matching) >= 1, f"Gitignore entry {entry!r} has no backing surface"


# ---------------------------------------------------------------------------
# Deprecated surfaces
# ---------------------------------------------------------------------------


def test_deprecated_surfaces():
    """At least one deprecated surface exists and active_mission_marker is deprecated."""
    deprecated = [s for s in STATE_SURFACES if s.deprecated]
    assert len(deprecated) >= 1
    assert any(s.name == "active_mission_marker" for s in deprecated)


def test_deprecated_authority_class():
    """Deprecated surfaces use AuthorityClass.DEPRECATED."""
    deprecated = [s for s in STATE_SURFACES if s.deprecated]
    for s in deprecated:
        assert s.authority == AuthorityClass.DEPRECATED, (
            f"{s.name} is deprecated but authority is {s.authority}"
        )


# ---------------------------------------------------------------------------
# Constitution deferred notes
# ---------------------------------------------------------------------------


def test_constitution_deferred_notes():
    """Constitution surfaces with deferred git decisions have notes."""
    deferred = [s for s in STATE_SURFACES if "deferred" in s.notes.lower()]
    assert len(deferred) >= 3, (
        f"Expected at least 3 deferred surfaces (answers, references, library), got {len(deferred)}"
    )
    deferred_names = {s.name for s in deferred}
    assert "constitution_interview_answers" in deferred_names
    assert "constitution_references" in deferred_names
    assert "constitution_library" in deferred_names


def test_constitution_deferred_git_class():
    """Constitution deferred surfaces use INSIDE_REPO_NOT_IGNORED."""
    deferred_names = {
        "constitution_interview_answers",
        "constitution_references",
        "constitution_library",
    }
    for s in STATE_SURFACES:
        if s.name in deferred_names:
            assert s.git_class == GitClass.INSIDE_REPO_NOT_IGNORED, (
                f"{s.name} should use INSIDE_REPO_NOT_IGNORED, got {s.git_class}"
            )


# ---------------------------------------------------------------------------
# Section coverage (spot checks)
# ---------------------------------------------------------------------------


def test_section_a_project_surfaces_present():
    """Key Section A surfaces exist."""
    names = {s.name for s in STATE_SURFACES}
    expected = {
        "project_config",
        "project_metadata",
        "dashboard_control",
        "workspace_context",
        "merge_resume_state",
        "runtime_feature_index",
        "runtime_run_snapshot",
        "runtime_run_event_log",
        "runtime_frozen_template",
        "glossary_fallback_events",
        "dossier_snapshot",
        "dossier_parity_baseline",
    }
    missing = expected - names
    assert not missing, f"Missing Section A surfaces: {missing}"


def test_section_b_constitution_surfaces_present():
    """Key Section B surfaces exist."""
    names = {s.name for s in STATE_SURFACES}
    expected = {
        "constitution_source",
        "constitution_interview_answers",
        "constitution_references",
        "constitution_library",
        "constitution_governance",
        "constitution_directives",
        "constitution_sync_metadata",
        "constitution_context_state",
    }
    missing = expected - names
    assert not missing, f"Missing Section B surfaces: {missing}"


def test_section_c_feature_surfaces_present():
    """Key Section C surfaces exist."""
    names = {s.name for s in STATE_SURFACES}
    expected = {
        "feature_metadata",
        "canonical_status_log",
        "canonical_status_snapshot",
        "wp_prompt_frontmatter",
        "wp_activity_log",
        "tasks_status_block",
    }
    missing = expected - names
    assert not missing, f"Missing Section C surfaces: {missing}"


def test_section_d_git_internal_present():
    """Section D git-internal surface exists."""
    names = {s.name for s in STATE_SURFACES}
    assert "review_feedback_artifact" in names


def test_section_e_sync_surfaces_present():
    """Key Section E surfaces exist."""
    names = {s.name for s in STATE_SURFACES}
    expected = {
        "sync_config",
        "sync_credentials",
        "credential_lock",
        "lamport_clock",
        "active_queue_scope",
        "legacy_queue",
        "scoped_queue",
        "tracker_cache",
    }
    missing = expected - names
    assert not missing, f"Missing Section E surfaces: {missing}"


def test_section_f_global_runtime_present():
    """Key Section F surfaces exist."""
    names = {s.name for s in STATE_SURFACES}
    expected = {
        "runtime_version_stamp",
        "runtime_update_lock",
        "runtime_staging_dirs",
    }
    missing = expected - names
    assert not missing, f"Missing Section F surfaces: {missing}"


def test_section_g_legacy_present():
    """All Section G legacy surfaces exist."""
    names = {s.name for s in STATE_SURFACES}
    expected = {
        "active_mission_marker",
        "legacy_session_json",
        "legacy_lamport_clock",
        "legacy_mission_sessions",
        "legacy_reset_backups",
    }
    missing = expected - names
    assert not missing, f"Missing Section G surfaces: {missing}"
