"""Machine-readable state contract for spec-kitty CLI state surfaces."""

from dataclasses import dataclass
from enum import StrEnum


# ---------------------------------------------------------------------------
# T001 -- State Enums
# ---------------------------------------------------------------------------


class StateRoot(StrEnum):
    """Root directory that anchors a family of state surfaces."""

    PROJECT = "project"  # .kittify/
    FEATURE = "feature"  # kitty-specs/<feature>/
    GLOBAL_RUNTIME = "global_runtime"  # ~/.kittify/
    GLOBAL_SYNC = "global_sync"  # ~/.spec-kitty/
    GIT_INTERNAL = "git_internal"  # .git/spec-kitty/


class AuthorityClass(StrEnum):
    """How authoritative a surface is for its data domain."""

    AUTHORITATIVE = "authoritative"
    DERIVED = "derived"
    COMPATIBILITY = "compatibility"
    LOCAL_RUNTIME = "local_runtime"
    SECRET = "secret"  # noqa: S105
    GIT_INTERNAL = "git_internal"
    DEPRECATED = "deprecated"


class GitClass(StrEnum):
    """Relationship of the surface to Git version control."""

    TRACKED = "tracked"
    IGNORED = "ignored"
    INSIDE_REPO_NOT_IGNORED = "inside_repo_not_ignored"
    GIT_INTERNAL = "git_internal"
    OUTSIDE_REPO = "outside_repo"


class StateFormat(StrEnum):
    """On-disk serialization format of the surface."""

    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    JSONL = "jsonl"
    SQLITE = "sqlite"
    MARKDOWN = "markdown"
    TEXT = "text"
    LOCKFILE = "lockfile"
    DIRECTORY = "directory"
    SYMLINK = "symlink"


# ---------------------------------------------------------------------------
# T002 -- StateSurface frozen dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StateSurface:
    """A single durable state surface in the spec-kitty CLI."""

    name: str
    path_pattern: str
    root: StateRoot
    format: StateFormat
    authority: AuthorityClass
    git_class: GitClass
    owner_module: str
    creation_trigger: str
    deprecated: bool = False
    atomic_write: bool = False
    notes: str = ""

    def to_dict(self) -> dict:
        """Return a JSON-serializable dictionary representation."""
        return {
            "name": self.name,
            "path_pattern": self.path_pattern,
            "root": self.root.value,
            "format": self.format.value,
            "authority": self.authority.value,
            "git_class": self.git_class.value,
            "owner_module": self.owner_module,
            "creation_trigger": self.creation_trigger,
            "deprecated": self.deprecated,
            "atomic_write": self.atomic_write,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# T003 -- STATE_SURFACES registry
# ---------------------------------------------------------------------------

STATE_SURFACES: tuple[StateSurface, ...] = (
    # -----------------------------------------------------------------------
    # Section A -- Project-Level State (.kittify/)
    # -----------------------------------------------------------------------
    StateSurface(
        name="project_config",
        path_pattern=".kittify/config.yaml",
        root=StateRoot.PROJECT,
        format=StateFormat.YAML,
        authority=AuthorityClass.AUTHORITATIVE,
        git_class=GitClass.TRACKED,
        owner_module="init/config writers",
        creation_trigger="spec-kitty init",
    ),
    StateSurface(
        name="project_metadata",
        path_pattern=".kittify/metadata.yaml",
        root=StateRoot.PROJECT,
        format=StateFormat.YAML,
        authority=AuthorityClass.AUTHORITATIVE,
        git_class=GitClass.TRACKED,
        owner_module="init/upgrade",
        creation_trigger="spec-kitty init or upgrade",
    ),
    StateSurface(
        name="dashboard_control",
        path_pattern=".kittify/.dashboard",
        root=StateRoot.PROJECT,
        format=StateFormat.TEXT,
        authority=AuthorityClass.LOCAL_RUNTIME,
        git_class=GitClass.IGNORED,
        owner_module="dashboard lifecycle",
        creation_trigger="spec-kitty dashboard start",
    ),
    StateSurface(
        name="workspace_context",
        path_pattern=".kittify/workspaces/<feature>-<WP>.json",
        root=StateRoot.PROJECT,
        format=StateFormat.JSON,
        authority=AuthorityClass.LOCAL_RUNTIME,
        git_class=GitClass.IGNORED,
        owner_module="workspace_context",
        creation_trigger="spec-kitty implement",
    ),
    StateSurface(
        name="merge_resume_state",
        path_pattern=".kittify/merge-state.json",
        root=StateRoot.PROJECT,
        format=StateFormat.JSON,
        authority=AuthorityClass.LOCAL_RUNTIME,
        git_class=GitClass.IGNORED,
        owner_module="merge/state",
        creation_trigger="spec-kitty merge",
    ),
    StateSurface(
        name="runtime_feature_index",
        path_pattern=".kittify/runtime/feature-runs.json",
        root=StateRoot.PROJECT,
        format=StateFormat.JSON,
        authority=AuthorityClass.LOCAL_RUNTIME,
        git_class=GitClass.IGNORED,
        owner_module="next/runtime_bridge",
        creation_trigger="spec-kitty next (runtime mode)",
        notes="Legacy filename. Stores mission-slug to mission-run linkage until compatibility rename is completed.",
    ),
    StateSurface(
        name="runtime_run_snapshot",
        path_pattern=".kittify/runtime/runs/<run_id>/state.json",
        root=StateRoot.PROJECT,
        format=StateFormat.JSON,
        authority=AuthorityClass.LOCAL_RUNTIME,
        git_class=GitClass.IGNORED,
        owner_module="spec-kitty-runtime",
        creation_trigger="mission run start",
    ),
    StateSurface(
        name="runtime_run_event_log",
        path_pattern=".kittify/runtime/runs/<run_id>/run.events.jsonl",
        root=StateRoot.PROJECT,
        format=StateFormat.JSONL,
        authority=AuthorityClass.LOCAL_RUNTIME,
        git_class=GitClass.IGNORED,
        owner_module="spec-kitty-runtime",
        creation_trigger="mission run events",
    ),
    StateSurface(
        name="runtime_frozen_template",
        path_pattern=".kittify/runtime/runs/<run_id>/mission_template_frozen.yaml",
        root=StateRoot.PROJECT,
        format=StateFormat.YAML,
        authority=AuthorityClass.LOCAL_RUNTIME,
        git_class=GitClass.IGNORED,
        owner_module="spec-kitty-runtime",
        creation_trigger="mission run start",
    ),
    StateSurface(
        name="glossary_fallback_events",
        path_pattern=".kittify/events/glossary/<mission_id>.events.jsonl",
        root=StateRoot.PROJECT,
        format=StateFormat.JSONL,
        authority=AuthorityClass.LOCAL_RUNTIME,
        git_class=GitClass.IGNORED,
        owner_module="glossary event adapter",
        creation_trigger="glossary event persistence",
    ),
    StateSurface(
        name="dossier_snapshot",
        path_pattern=".kittify/dossiers/<feature>/snapshot-latest.json",
        root=StateRoot.PROJECT,
        format=StateFormat.JSON,
        authority=AuthorityClass.DERIVED,
        git_class=GitClass.IGNORED,
        owner_module="dossier snapshot save",
        creation_trigger="dossier snapshot",
    ),
    StateSurface(
        name="mission_pycache",
        path_pattern=".kittify/missions/__pycache__/",
        root=StateRoot.PROJECT,
        format=StateFormat.DIRECTORY,
        authority=AuthorityClass.LOCAL_RUNTIME,
        git_class=GitClass.IGNORED,
        owner_module="python runtime",
        creation_trigger="Python bytecode compilation",
        notes="Python cache artifact, not architectural state",
    ),
    StateSurface(
        name="dossier_parity_baseline",
        path_pattern=".kittify/dossiers/<feature>/parity-baseline.json",
        root=StateRoot.PROJECT,
        format=StateFormat.JSON,
        authority=AuthorityClass.LOCAL_RUNTIME,
        git_class=GitClass.IGNORED,
        owner_module="dossier drift detector",
        creation_trigger="dossier parity baseline accept",
    ),
    # -----------------------------------------------------------------------
    # Section B -- Constitution State (.kittify/constitution/)
    # -----------------------------------------------------------------------
    StateSurface(
        name="constitution_source",
        path_pattern=".kittify/constitution/constitution.md",
        root=StateRoot.PROJECT,
        format=StateFormat.MARKDOWN,
        authority=AuthorityClass.AUTHORITATIVE,
        git_class=GitClass.TRACKED,
        owner_module="constitution compiler",
        creation_trigger="constitution init or user edit",
    ),
    StateSurface(
        name="constitution_interview_answers",
        path_pattern=".kittify/constitution/interview/answers.yaml",
        root=StateRoot.PROJECT,
        format=StateFormat.YAML,
        authority=AuthorityClass.AUTHORITATIVE,
        git_class=GitClass.TRACKED,
        owner_module="constitution interview",
        creation_trigger="constitution interview flow",
        notes="Policy enforced in feature 054: commit answers + library, ignore references",
    ),
    StateSurface(
        name="constitution_references",
        path_pattern=".kittify/constitution/references.yaml",
        root=StateRoot.PROJECT,
        format=StateFormat.YAML,
        authority=AuthorityClass.LOCAL_RUNTIME,
        git_class=GitClass.IGNORED,
        owner_module="constitution compiler",
        creation_trigger="constitution compile",
        notes="Policy enforced in feature 054: commit answers + library, ignore references",
    ),
    StateSurface(
        name="constitution_library",
        path_pattern=".kittify/constitution/library/*.md",
        root=StateRoot.PROJECT,
        format=StateFormat.MARKDOWN,
        authority=AuthorityClass.AUTHORITATIVE,
        git_class=GitClass.TRACKED,
        owner_module="constitution compiler",
        creation_trigger="constitution compile",
        notes="Policy enforced in feature 054: commit answers + library, ignore references",
    ),
    StateSurface(
        name="constitution_governance",
        path_pattern=".kittify/constitution/governance.yaml",
        root=StateRoot.PROJECT,
        format=StateFormat.YAML,
        authority=AuthorityClass.DERIVED,
        git_class=GitClass.IGNORED,
        owner_module="constitution sync",
        creation_trigger="constitution sync",
    ),
    StateSurface(
        name="constitution_directives",
        path_pattern=".kittify/constitution/directives.yaml",
        root=StateRoot.PROJECT,
        format=StateFormat.YAML,
        authority=AuthorityClass.DERIVED,
        git_class=GitClass.IGNORED,
        owner_module="constitution sync",
        creation_trigger="constitution sync",
    ),
    StateSurface(
        name="constitution_sync_metadata",
        path_pattern=".kittify/constitution/metadata.yaml",
        root=StateRoot.PROJECT,
        format=StateFormat.YAML,
        authority=AuthorityClass.DERIVED,
        git_class=GitClass.IGNORED,
        owner_module="constitution sync",
        creation_trigger="constitution sync",
    ),
    StateSurface(
        name="constitution_context_state",
        path_pattern=".kittify/constitution/context-state.json",
        root=StateRoot.PROJECT,
        format=StateFormat.JSON,
        authority=AuthorityClass.LOCAL_RUNTIME,
        git_class=GitClass.IGNORED,
        owner_module="constitution context",
        creation_trigger="constitution context bootstrap",
    ),
    # -----------------------------------------------------------------------
    # Section C -- Feature State (kitty-specs/<feature>/)
    # -----------------------------------------------------------------------
    StateSurface(
        name="feature_metadata",
        path_pattern="kitty-specs/<feature>/meta.json",
        root=StateRoot.FEATURE,
        format=StateFormat.JSON,
        authority=AuthorityClass.AUTHORITATIVE,
        git_class=GitClass.TRACKED,
        owner_module="feature creation/acceptance",
        creation_trigger="spec-kitty specify",
        atomic_write=True,
    ),
    StateSurface(
        name="canonical_status_log",
        path_pattern="kitty-specs/<feature>/status.events.jsonl",
        root=StateRoot.FEATURE,
        format=StateFormat.JSONL,
        authority=AuthorityClass.AUTHORITATIVE,
        git_class=GitClass.TRACKED,
        owner_module="status emit",
        creation_trigger="first status transition",
        atomic_write=True,
    ),
    StateSurface(
        name="canonical_status_snapshot",
        path_pattern="kitty-specs/<feature>/status.json",
        root=StateRoot.FEATURE,
        format=StateFormat.JSON,
        authority=AuthorityClass.DERIVED,
        git_class=GitClass.TRACKED,
        owner_module="status reducer",
        creation_trigger="status materialize",
        atomic_write=True,
    ),
    StateSurface(
        name="wp_prompt_frontmatter",
        path_pattern="kitty-specs/<feature>/tasks/WP*.md",
        root=StateRoot.FEATURE,
        format=StateFormat.YAML,
        authority=AuthorityClass.COMPATIBILITY,
        git_class=GitClass.TRACKED,
        owner_module="task creation/move-task/legacy bridge",
        creation_trigger="spec-kitty tasks",
        notes="YAML frontmatter in WP markdown files",
    ),
    StateSurface(
        name="wp_activity_log",
        path_pattern="kitty-specs/<feature>/tasks/WP*.md body",
        root=StateRoot.FEATURE,
        format=StateFormat.MARKDOWN,
        authority=AuthorityClass.COMPATIBILITY,
        git_class=GitClass.TRACKED,
        owner_module="move-task/manual edits",
        creation_trigger="status transitions and manual edits",
        notes="Markdown body section of WP files",
    ),
    StateSurface(
        name="tasks_status_block",
        path_pattern="kitty-specs/<feature>/tasks.md",
        root=StateRoot.FEATURE,
        format=StateFormat.MARKDOWN,
        authority=AuthorityClass.DERIVED,
        git_class=GitClass.TRACKED,
        owner_module="legacy bridge",
        creation_trigger="status materialize/legacy bridge",
    ),
    # -----------------------------------------------------------------------
    # Section D -- Git-Internal State
    # -----------------------------------------------------------------------
    StateSurface(
        name="review_feedback_artifact",
        path_pattern=".git/spec-kitty/feedback/<feature>/<WP>/<timestamp>-<id>.md",
        root=StateRoot.GIT_INTERNAL,
        format=StateFormat.MARKDOWN,
        authority=AuthorityClass.GIT_INTERNAL,
        git_class=GitClass.GIT_INTERNAL,
        owner_module="agent tasks move-task",
        creation_trigger="move-task --review-feedback-file",
    ),
    # -----------------------------------------------------------------------
    # Section E -- User-Home Sync (~/.spec-kitty/)
    # -----------------------------------------------------------------------
    StateSurface(
        name="sync_config",
        path_pattern="~/.spec-kitty/config.toml",
        root=StateRoot.GLOBAL_SYNC,
        format=StateFormat.TOML,
        authority=AuthorityClass.AUTHORITATIVE,
        git_class=GitClass.OUTSIDE_REPO,
        owner_module="sync/config",
        creation_trigger="spec-kitty sync configure",
    ),
    StateSurface(
        name="sync_credentials",
        path_pattern="~/.spec-kitty/credentials",
        root=StateRoot.GLOBAL_SYNC,
        format=StateFormat.TOML,
        authority=AuthorityClass.SECRET,
        git_class=GitClass.OUTSIDE_REPO,
        owner_module="sync/auth + tracker/credentials",
        creation_trigger="spec-kitty sync login",
    ),
    StateSurface(
        name="credential_lock",
        path_pattern="~/.spec-kitty/credentials.lock",
        root=StateRoot.GLOBAL_SYNC,
        format=StateFormat.LOCKFILE,
        authority=AuthorityClass.LOCAL_RUNTIME,
        git_class=GitClass.OUTSIDE_REPO,
        owner_module="sync/auth",
        creation_trigger="credential write serialization",
    ),
    StateSurface(
        name="lamport_clock",
        path_pattern="~/.spec-kitty/clock.json",
        root=StateRoot.GLOBAL_SYNC,
        format=StateFormat.JSON,
        authority=AuthorityClass.AUTHORITATIVE,
        git_class=GitClass.OUTSIDE_REPO,
        owner_module="sync/clock",
        creation_trigger="first sync event",
    ),
    StateSurface(
        name="active_queue_scope",
        path_pattern="~/.spec-kitty/active_queue_scope",
        root=StateRoot.GLOBAL_SYNC,
        format=StateFormat.TEXT,
        authority=AuthorityClass.LOCAL_RUNTIME,
        git_class=GitClass.OUTSIDE_REPO,
        owner_module="sync/queue",
        creation_trigger="queue scope activation",
    ),
    StateSurface(
        name="legacy_queue",
        path_pattern="~/.spec-kitty/queue.db",
        root=StateRoot.GLOBAL_SYNC,
        format=StateFormat.SQLITE,
        authority=AuthorityClass.AUTHORITATIVE,
        git_class=GitClass.OUTSIDE_REPO,
        owner_module="sync/queue",
        creation_trigger="first offline event (unauthenticated)",
    ),
    StateSurface(
        name="scoped_queue",
        path_pattern="~/.spec-kitty/queues/queue-<hash>.db",
        root=StateRoot.GLOBAL_SYNC,
        format=StateFormat.SQLITE,
        authority=AuthorityClass.AUTHORITATIVE,
        git_class=GitClass.OUTSIDE_REPO,
        owner_module="sync/queue",
        creation_trigger="first offline event (authenticated scope)",
    ),
    StateSurface(
        name="tracker_cache",
        path_pattern="~/.spec-kitty/trackers/<scope>.db",
        root=StateRoot.GLOBAL_SYNC,
        format=StateFormat.SQLITE,
        authority=AuthorityClass.AUTHORITATIVE,
        git_class=GitClass.OUTSIDE_REPO,
        owner_module="tracker/store",
        creation_trigger="tracker sync or cache init",
    ),
    # -----------------------------------------------------------------------
    # Section F -- Global Runtime (~/.kittify/)
    # -----------------------------------------------------------------------
    StateSurface(
        name="runtime_version_stamp",
        path_pattern="~/.kittify/cache/version.lock",
        root=StateRoot.GLOBAL_RUNTIME,
        format=StateFormat.TEXT,
        authority=AuthorityClass.LOCAL_RUNTIME,
        git_class=GitClass.OUTSIDE_REPO,
        owner_module="runtime/bootstrap",
        creation_trigger="runtime bootstrap",
    ),
    StateSurface(
        name="runtime_update_lock",
        path_pattern="~/.kittify/cache/.update.lock",
        root=StateRoot.GLOBAL_RUNTIME,
        format=StateFormat.LOCKFILE,
        authority=AuthorityClass.LOCAL_RUNTIME,
        git_class=GitClass.OUTSIDE_REPO,
        owner_module="runtime/bootstrap",
        creation_trigger="runtime asset update",
    ),
    StateSurface(
        name="runtime_staging_dirs",
        path_pattern="~/.kittify_update_*",
        root=StateRoot.GLOBAL_RUNTIME,
        format=StateFormat.DIRECTORY,
        authority=AuthorityClass.LOCAL_RUNTIME,
        git_class=GitClass.OUTSIDE_REPO,
        owner_module="runtime/bootstrap",
        creation_trigger="runtime asset update",
        notes="Transient staging area, removed after update completes",
    ),
    # -----------------------------------------------------------------------
    # Section G -- Legacy
    # -----------------------------------------------------------------------
    StateSurface(
        name="legacy_session_json",
        path_pattern="~/.spec-kitty/session.json",
        root=StateRoot.GLOBAL_SYNC,
        format=StateFormat.JSON,
        authority=AuthorityClass.DEPRECATED,
        git_class=GitClass.OUTSIDE_REPO,
        owner_module="legacy",
        creation_trigger="historical",
        deprecated=True,
        notes="Historical residue, not referenced by current 2.x source",
    ),
    StateSurface(
        name="legacy_lamport_clock",
        path_pattern="~/.spec-kitty/events/lamport_clock.json",
        root=StateRoot.GLOBAL_SYNC,
        format=StateFormat.JSON,
        authority=AuthorityClass.DEPRECATED,
        git_class=GitClass.OUTSIDE_REPO,
        owner_module="legacy",
        creation_trigger="historical",
        deprecated=True,
        notes="Historical residue, not referenced by current 2.x source",
    ),
    StateSurface(
        name="legacy_mission_sessions",
        path_pattern="~/.spec-kitty/missions/*/session.json",
        root=StateRoot.GLOBAL_SYNC,
        format=StateFormat.JSON,
        authority=AuthorityClass.DEPRECATED,
        git_class=GitClass.OUTSIDE_REPO,
        owner_module="legacy",
        creation_trigger="historical",
        deprecated=True,
        notes="Historical residue, not referenced by current 2.x source",
    ),
    StateSurface(
        name="legacy_reset_backups",
        path_pattern="~/.spec-kitty/reset-backup-*",
        root=StateRoot.GLOBAL_SYNC,
        format=StateFormat.DIRECTORY,
        authority=AuthorityClass.DEPRECATED,
        git_class=GitClass.OUTSIDE_REPO,
        owner_module="legacy",
        creation_trigger="historical",
        deprecated=True,
        notes="Historical residue, not referenced by current 2.x source",
    ),
)


# ---------------------------------------------------------------------------
# T004 -- Helper functions
# ---------------------------------------------------------------------------


def get_surfaces_by_root(root: StateRoot) -> list[StateSurface]:
    """Return all surfaces that belong to the given root."""
    return [s for s in STATE_SURFACES if s.root == root]


def get_surfaces_by_git_class(git_class: GitClass) -> list[StateSurface]:
    """Return all surfaces that have the given git class."""
    return [s for s in STATE_SURFACES if s.git_class == git_class]


def get_surfaces_by_authority(authority: AuthorityClass) -> list[StateSurface]:
    """Return all surfaces that have the given authority class."""
    return [s for s in STATE_SURFACES if s.authority == authority]


def _fully_ignored_top_dirs() -> set[str]:
    """Return top-level subdirectory patterns where ALL project surfaces are IGNORED.

    For example, if every surface under ``.kittify/runtime/`` is IGNORED,
    ``".kittify/runtime/"`` is returned. Directories with mixed git classes
    (some TRACKED, some IGNORED) are excluded.

    Surfaces whose path ends with ``__pycache__/`` are excluded from collapse
    consideration because they are Python cache artifacts, not representative
    of the parent directory's actual contents.
    """
    project_surfaces = [s for s in STATE_SURFACES if s.root == StateRoot.PROJECT]
    top_dir_git_classes: dict[str, list[GitClass]] = {}
    for s in project_surfaces:
        # Skip __pycache__ entries — they are cache artifacts and should not
        # cause their parent directory to be collapsed.
        if s.path_pattern.rstrip("/").endswith("__pycache__"):
            continue
        parts = s.path_pattern.split("/")
        if len(parts) >= 3:  # noqa: PLR2004
            top_dir = "/".join(parts[:2])
            top_dir_git_classes.setdefault(top_dir, []).append(s.git_class)
    return {
        d + "/"
        for d, classes in top_dir_git_classes.items()
        if all(gc == GitClass.IGNORED for gc in classes)
    }


def _collapse_placeholder_pattern(pattern: str) -> str | None:
    """Collapse a path pattern with placeholders to its clean parent directory.

    Returns ``None`` if no clean prefix exists.
    """
    parts = pattern.split("/")
    clean_parts: list[str] = []
    for part in parts:
        if "<" in part or "*" in part:
            break
        clean_parts.append(part)
    return "/".join(clean_parts) + "/" if clean_parts else None


def _remove_subsumed(entries: set[str]) -> set[str]:
    """Remove entries that are subsumed by a parent directory entry."""
    return {
        entry
        for entry in entries
        if not any(
            other != entry and other.endswith("/") and entry.startswith(other)
            for other in entries
        )
    }


def get_runtime_gitignore_entries() -> list[str]:
    """Return deduplicated gitignore patterns for project-root runtime surfaces.

    Includes all PROJECT-rooted surfaces with git_class=IGNORED.
    Patterns containing placeholder tokens (``<...>``) or wildcards are
    collapsed to their parent directory (with trailing ``/``), then
    deduplicated so the result is directly consumable by ``.gitignore``.

    When ALL project surfaces under a top-level subdirectory (e.g.
    ``.kittify/runtime/``) are IGNORED, the entire subdirectory is emitted
    as a single entry rather than listing individual files/subdirs.
    """
    fully_ignored = _fully_ignored_top_dirs()
    raw: set[str] = set()

    for s in STATE_SURFACES:
        if s.root != StateRoot.PROJECT or s.git_class != GitClass.IGNORED:
            continue
        pattern = s.path_pattern

        # Check if this surface falls under a fully-ignored top dir
        parts = pattern.split("/")
        if len(parts) >= 3:  # noqa: PLR2004
            top_dir_pattern = "/".join(parts[:2]) + "/"
            if top_dir_pattern in fully_ignored:
                raw.add(top_dir_pattern)
                continue

        # Collapse placeholders to parent directory
        if "<" in pattern or "*" in pattern:
            collapsed = _collapse_placeholder_pattern(pattern)
            if collapsed:
                raw.add(collapsed)
            continue

        raw.add(pattern)

    return sorted(_remove_subsumed(raw))
