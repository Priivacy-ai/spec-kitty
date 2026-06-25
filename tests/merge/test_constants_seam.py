"""Seam test for ``specify_cli.merge._constants`` (mission #2057, WP02).

Pins the relocated shared literals / type aliases / logger byte-for-byte and
proves the ``cli/commands/merge`` shim re-exports the same objects (identity,
not just equality) so every importer and the public ``__all__`` stay stable
(FR-003, C-008, INV-8).
"""

from __future__ import annotations

import pytest

from specify_cli.cli.commands import merge as shim
from specify_cli.merge import _constants

pytestmark = pytest.mark.fast


def test_linear_history_rejection_tokens_are_locked() -> None:
    """INV-8 / C-008: the rejection-token tuple order and membership are frozen."""
    assert _constants.LINEAR_HISTORY_REJECTION_TOKENS == (
        "merge commits",
        "linear history",
        "fast-forward only",
        "GH006",
        "non-fast-forward",
    )
    assert isinstance(_constants.LINEAR_HISTORY_REJECTION_TOKENS, tuple)


def test_relocated_string_literals_are_byte_identical() -> None:
    """The moved literals carry their exact pre-refactor values."""
    assert _constants.TARGET_BRANCH_NOT_SYNCHRONIZED == "TARGET_BRANCH_NOT_SYNCHRONIZED"
    assert (
        _constants.TARGET_BRANCH_SYNC_INVARIANT
        == "local_target_branch_must_match_tracking_branch"
    )
    assert _constants._STATUS_EVENTS_FILENAME == "status.events.jsonl"
    assert _constants._STATUS_FILENAME == "status.json"
    assert (
        _constants._SAFE_PATH_SEGMENT_DIAGNOSTIC
        == "Mission slug is not a single safe path segment"
    )


def test_type_aliases_are_preserved() -> None:
    """The structural aliases match their pre-refactor definitions."""
    assert _constants.MissionBranchBlocker == dict[str, str | bool]
    assert _constants.HollowReviewWarnings == dict[str, list[str]]


def test_logger_namespace_is_preserved() -> None:
    """The shared logger keeps the historical command-module namespace."""
    assert _constants.logger.name == "specify_cli.cli.commands.merge"


@pytest.mark.parametrize(
    "name",
    [
        "TARGET_BRANCH_NOT_SYNCHRONIZED",
        "TARGET_BRANCH_SYNC_INVARIANT",
        "_STATUS_EVENTS_FILENAME",
        "_STATUS_FILENAME",
        "_SAFE_PATH_SEGMENT_DIAGNOSTIC",
        "LINEAR_HISTORY_REJECTION_TOKENS",
        "MissionBranchBlocker",
        "HollowReviewWarnings",
        "logger",
    ],
)
def test_shim_re_exports_the_same_object(name: str) -> None:
    """The shim re-exports the identical object from ``_constants`` (one-way import)."""
    assert getattr(shim, name) is getattr(_constants, name)


def test_constants_module_does_not_import_the_shim() -> None:
    """One-way imports: the seam never reaches back into the command shim.

    We parse the module's import statements rather than grep the source so the
    logger's namespace string and explanatory comments (which legitimately name
    the command module) don't trip a false positive.
    """
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(_constants))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
        elif isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)

    assert not any(
        mod.startswith("specify_cli.cli") for mod in imported_modules
    ), f"_constants must not import the command shim; imports: {sorted(imported_modules)}"
