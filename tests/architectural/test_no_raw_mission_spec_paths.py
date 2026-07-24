"""Ratchets for issue #1681 raw mission-spec path remediation."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import re

import pytest

from tests.architectural.conftest import SourceFile


pytestmark = [pytest.mark.architectural]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = Path("src")
# ``kitty_specs`` matches the standalone path-holding identifier/token only.
# The identifier-boundary guards (``(?<![A-Za-z0-9_])`` / ``(?![A-Za-z0-9_])``)
# stop the token from matching when it is an inner substring of a longer Python
# identifier (e.g. the validator name ``_check_kitty_specs_contamination``),
# which is a function name, not a raw mission-spec path construction.
_RAW_PATTERN = re.compile(
    r'"kitty-specs"|"kitty\.specs"|(?<![A-Za-z0-9_])kitty_specs(?![A-Za-z0-9_])'
)
_SEMANTIC_PATTERN = re.compile(r"KITTY_SPECS_DIR\s*/\s*\w")

_RAW_EXEMPT_PARTS = (
    "status/",
    # core/execution_context.py removed in WP03 (relocated to mission_runtime,
    # then deleted once unreferenced — FR-003). mission_runtime does not
    # construct raw mission-spec paths, so it needs no exemption.
    "upgrade/migrations/",
    "core/constants.py",
    "core/paths.py",
    "missions/_read_path_resolver.py",
    "migration/",
    # charter/ uses "kitty-specs" for string membership testing on path parts
    # (e.g. `if _SPECS_DIR_NAME in parts:`), not for path construction.
    # It is a separate package that does not import from specify_cli.
    "charter/",
)

_SEMANTIC_CONSTRUCTOR_FILES = {
    Path("src/specify_cli/core/git_ops.py"),
    Path("src/specify_cli/core/mission_creation.py"),
    Path("src/specify_cli/core/project_resolver.py"),
    Path("src/specify_cli/core/worktree.py"),
    Path("src/specify_cli/core/worktree_topology.py"),
    Path("src/specify_cli/coordination/surface_resolver.py"),
    Path("src/specify_cli/coordination/status_transition.py"),
    Path("src/specify_cli/coordination/transaction.py"),
    # WP08 campsite split (behaviour-free): transaction.py's legacy-mission
    # meta reads (the `KITTY_SPECS_DIR / <slug>-<mid8>` feature-dir construction)
    # moved verbatim into legacy_resolution.py. Code follows the move — same
    # sanctioned constructor, new home.
    Path("src/specify_cli/coordination/legacy_resolution.py"),
    Path("src/specify_cli/events/decision_log.py"),
    # missions/feature_dir_resolver.py retired in WP07 (FR-007); its raw-slug
    # primary anchor relocated into missions/_read_path_resolver.py, which is
    # already covered by _RAW_EXEMPT_PARTS above.
    Path("src/specify_cli/workspace/root_resolver.py"),
    # Mission-identity routing (WP10, #1918 fallout): these three CLI command
    # entrypoints construct a `KITTY_SPECS_DIR / <raw-handle>` primary dir for the
    # SOLE purpose of `load_meta(...)`-bootstrapping the declared `mission_id`,
    # which is then fed into the authoritative `resolve_mission_read_path` seam
    # (so disambiguation has the mission_id and never silently falls back). The
    # path is a meta-read seed, not an independent resolution path — the canonical
    # resolver still owns the final read. Named individually (not a blanket
    # pattern) so the constructor inventory stays explicit.
    Path("src/specify_cli/cli/commands/agent/context.py"),
    Path("src/specify_cli/cli/commands/agent/mission.py"),
    Path("src/specify_cli/cli/commands/decision.py"),
}


def _rel(path: Path) -> Path:
    """Repo-relative ``src/...`` path for cached absolute keys.

    The cached ``src_source_tree`` keys are absolute under ``SRC``; the
    exemption tables (``_RAW_EXEMPT_PARTS``/``_SEMANTIC_CONSTRUCTOR_FILES``) are
    expressed relative to the repo root, so normalise before comparing.
    """
    return path.relative_to(_REPO_ROOT)


def _is_raw_exempt(path: Path) -> bool:
    normalized = path.as_posix()
    return any(part in normalized for part in _RAW_EXEMPT_PARTS)


def test_no_raw_mission_spec_path_strings_outside_exempt_owners(
    src_source_tree: Mapping[Path, SourceFile],
) -> None:
    """T011: route through the cached source tree instead of re-walking ``src/``."""
    offenders: list[str] = []
    for abs_path, entry in sorted(src_source_tree.items()):
        rel = _rel(abs_path)
        if _is_raw_exempt(rel):
            continue
        for line_no, line in enumerate(entry.source.splitlines(), 1):
            if _RAW_PATTERN.search(line):
                offenders.append(f"{rel}:{line_no}: {line.strip()}")

    assert offenders == []


def test_constant_based_mission_spec_path_construction_stays_in_constructor_files(
    src_source_tree: Mapping[Path, SourceFile],
) -> None:
    """T011: route through the cached source tree instead of re-walking ``src/``."""
    offenders: list[str] = []
    for abs_path, entry in sorted(src_source_tree.items()):
        rel = _rel(abs_path)
        if rel in _SEMANTIC_CONSTRUCTOR_FILES or _is_raw_exempt(rel):
            continue
        for line_no, line in enumerate(entry.source.splitlines(), 1):
            if _SEMANTIC_PATTERN.search(line):
                offenders.append(f"{rel}:{line_no}: {line.strip()}")

    assert offenders == []
