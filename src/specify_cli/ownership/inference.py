"""Best-effort inference of ownership manifest fields from WP content.

All inferred values can be overridden by the user via manual frontmatter edits.
Inference runs at finalization time; it does not block finalization when uncertain.
"""

from __future__ import annotations

import re

from specify_cli.ownership.models import ExecutionMode, OwnershipManifest

__all__ = [
    "infer_execution_mode",
    "infer_owned_files",
    "infer_authoritative_surface",
    "infer_ownership",
    "SRC_FALLBACK_GLOB",
    "SRC_FALLBACK_WARNING",
]

# Constant so callers can detect / test the fallback value.
SRC_FALLBACK_GLOB = "src/**"
SRC_FALLBACK_WARNING = (
    "No file paths found in WP body text; using broad fallback 'src/**'. "
    "Consider adding explicit owned_files to WP frontmatter."
)

# Patterns that strongly suggest planning artifact deliverables.
_PLANNING_SIGNALS = [
    r"\bkitty-specs/",
    r"\bspec\.md\b",
    r"\bplan\.md\b",
    r"\btasks\.md\b",
    r"\bdata-model\.md\b",
    r"\bquickstart\.md\b",
]

# Patterns that strongly suggest code change deliverables.
_CODE_SIGNALS = [
    r"\bsrc/",
    r"\btests?/",
    r"\.py\b",
    r"\.ts\b",
    r"\.js\b",
]

# Regex to extract path-like tokens from WP content.
# Matches things like: src/foo/bar.py, tests/specify_cli/..., kitty-specs/001-feature/...
_PATH_PATTERN = re.compile(
    r"""
    (?:
        (?:src|tests?|kitty-specs|docs)   # known top-level dirs
        /
        [^\s`'")\]>]+                     # rest of path
    )
    """,
    re.VERBOSE,
)


def infer_execution_mode(wp_content: str, wp_files: list[str]) -> ExecutionMode:
    """Infer whether a WP is a code_change or planning_artifact.

    Heuristic (in order of precedence):
    1. If the WP body mentions planning artifact keywords as primary deliverables
       (kitty-specs/, spec.md, plan.md, tasks.md, data-model.md) → planning_artifact.
    2. If the WP body mentions src/, test files, or source-code extensions → code_change.
    3. Default → code_change.

    Args:
        wp_content: Full text of the WP prompt file (frontmatter + body).
        wp_files: Optional list of file paths explicitly listed as WP deliverables.

    Returns:
        Inferred ExecutionMode.
    """
    combined = wp_content + "\n" + "\n".join(wp_files)

    planning_score = sum(
        1 for p in _PLANNING_SIGNALS if re.search(p, combined)
    )
    code_score = sum(
        1 for p in _CODE_SIGNALS if re.search(p, combined)
    )

    if planning_score > 0 and code_score == 0:
        return ExecutionMode.PLANNING_ARTIFACT

    # Default: code_change
    return ExecutionMode.CODE_CHANGE


def infer_owned_files(
    wp_content: str, mission_slug: str
) -> tuple[list[str], list[str]]:
    """Infer owned_files glob patterns from WP body text.

    For planning_artifact WPs: defaults to ``kitty-specs/<mission_slug>/**``.
    For code_change WPs: extracts path prefixes found in the WP body.

    Args:
        wp_content: Full text of the WP prompt file.
        mission_slug: Feature slug (e.g. ``"057-canonical-context-architecture-cleanup"``).

    Returns:
        A 2-tuple of ``(globs, warnings)`` where *globs* is a deduplicated
        list of glob patterns and *warnings* is a list of human-readable
        warning strings (may be empty).
    """
    execution_mode = infer_execution_mode(wp_content, [])

    if execution_mode == ExecutionMode.PLANNING_ARTIFACT:
        return [f"kitty-specs/{mission_slug}/**"], []

    # Extract path tokens mentioned in the WP
    found_paths = set(_PATH_PATTERN.findall(wp_content))

    # Normalise: strip trailing punctuation, deduplicate directory prefixes
    globs: list[str] = []
    seen_prefixes: set[str] = set()

    for path in sorted(found_paths):
        # Convert a path like src/foo/bar.py → src/foo/bar.py (keep as-is)
        # Convert a path like src/foo/ → src/foo/**
        if path.endswith("/"):
            glob = path + "**"
        else:
            # If it looks like a directory (no extension), append /**
            if "." not in path.split("/")[-1]:
                glob = path.rstrip("/") + "/**"
            else:
                glob = path

        # Deduplicate: skip if a parent prefix already captured this path
        parts = glob.split("/")
        skip = False
        for i in range(1, len(parts)):
            candidate = "/".join(parts[:i]) + "/**"
            if candidate in seen_prefixes:
                skip = True
                break
        if not skip:
            seen_prefixes.add(glob)
            globs.append(glob)

    # Fall back to a broad pattern if we couldn't extract anything specific.
    # Warn so operators know the scope is synthetic.
    warnings: list[str] = []
    if not globs:
        globs = [SRC_FALLBACK_GLOB]
        warnings.append(SRC_FALLBACK_WARNING)

    return globs, warnings


def infer_authoritative_surface(owned_files: list[str]) -> str:
    """Derive the authoritative_surface from a list of owned_files patterns.

    Returns the longest common path prefix shared by all owned_files entries.
    Trailing ``/**`` and ``/*`` wildcards are stripped before comparison.

    Args:
        owned_files: List of glob patterns.

    Returns:
        A path prefix string (may be empty if patterns share no common prefix).
    """
    if not owned_files:
        return ""

    def _strip_glob(pattern: str) -> str:
        for suffix in ("/**", "/*", "**", "*"):
            if pattern.endswith(suffix):
                return pattern[: -len(suffix)]
        return pattern

    stripped = [_strip_glob(p) for p in owned_files]

    if len(stripped) == 1:
        # Return with trailing slash to indicate a directory prefix
        return stripped[0].rstrip("/") + "/"

    # Split by "/" and find common prefix segments
    split = [s.split("/") for s in stripped]
    common: list[str] = []
    for segments in zip(*split):
        if len(set(segments)) == 1:
            common.append(segments[0])
        else:
            break

    if not common:
        return ""

    return "/".join(common) + "/"


def infer_ownership(
    wp_content: str,
    mission_slug: str,
    wp_files: list[str] | None = None,
) -> tuple[OwnershipManifest, list[str]]:
    """Convenience function: infer a complete OwnershipManifest from WP content.

    Args:
        wp_content: Full text of the WP prompt file.
        mission_slug: Feature slug string.
        wp_files: Optional explicit list of file paths.

    Returns:
        A 2-tuple of ``(manifest, warnings)`` where *manifest* is a
        best-effort OwnershipManifest and *warnings* is a list of
        human-readable warning strings (may be empty).
    """
    from specify_cli.ownership.models import OwnershipManifest  # local import avoids circularity

    files = wp_files or []
    execution_mode = infer_execution_mode(wp_content, files)
    owned_files, warnings = infer_owned_files(wp_content, mission_slug)
    authoritative_surface = infer_authoritative_surface(owned_files)

    manifest = OwnershipManifest(
        execution_mode=execution_mode,
        owned_files=tuple(owned_files),
        authoritative_surface=authoritative_surface,
    )
    return manifest, warnings
