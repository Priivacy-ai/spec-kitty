"""Shared mocked-environment context manager for CLI command tests.

The CLI surface walks several path resolvers when handling a command:

- ``locate_project_root()`` — write-path resolution (canonical serialization
  pins to the primary checkout regardless of where the operator stands).
- ``get_status_read_root()`` — read-path resolution introduced by WP05
  (mission ``01KRC57C``, GitHub #984) so detached-worktree verification
  reads the current worktree's events instead of the primary checkout's
  potentially-divergent state.
- ``_ensure_target_branch_checked_out()`` — pre-mutation branch guard.
- ``_find_mission_slug()`` — mission-handle resolver.
- ``resolve_workspace_for_wp()`` — execution-workspace resolver for
  per-WP lookups.
- ``get_auto_commit_default()`` — global auto-commit setting.

Tests that exercise these commands against a synthetic ``tmp_path``
mission directory previously each redeclared the patch block. When a new
resolver was added (the WP05 case above), every test file that forgot to
update its patch list silently regressed — the resolver fell through to
the real spec-kitty checkout and the test failed with "Mission directory
not found".

``setup_mocked_env()`` bundles the common patches. When a future
stabilization mission adds another resolver, update ``_DEFAULT_RESOLVERS``
or add another optional parameter here once; every test using the helper
inherits the fix.

Example
-------

```python
from tests.mocked_env import setup_mocked_env

def test_status_warns_for_done_wp_with_rejected_review_artifact(tmp_path):
    feature_dir, wp_file = _build_wp_file(tmp_path, "test-mission", "WP01")
    _seed_wp_event(feature_dir, "WP01", "done")
    _write_review_cycle(wp_file.parent / wp_file.stem, 1, "rejected")

    with setup_mocked_env(
        tmp_path,
        mission_slug="test-mission",
        workspace_resolution=FileNotFoundError,
    ):
        result = runner.invoke(app, ["status", "--mission", "test-mission"])
        assert result.exit_code == 0
        assert "review artifact: verdict=rejected" in result.output
```
"""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any
from collections.abc import Iterator
from unittest.mock import patch


# Resolvers patched in every command module that touches a project path.
# Each maps to the helper's ``tmp_path`` argument. Add new entries here when
# a stabilization mission introduces a new project-root resolver — every
# test using ``setup_mocked_env`` inherits the patch automatically.
_DEFAULT_RESOLVERS: tuple[str, ...] = (
    "locate_project_root",
    "get_status_read_root",  # added by WP05 / mission 01KRC57C / GitHub #984
)


@contextmanager
def setup_mocked_env(
    tmp_path: Path,
    *,
    command_module: str = "specify_cli.cli.commands.agent.tasks",
    mission_slug: str | None = None,
    target_branch: str = "main",
    workspace_resolution: Any = None,
    auto_commit_default: bool | None = False,
    extra_patches: dict[str, Any] | None = None,
) -> Iterator[None]:
    """Bundle the resolver patches CLI-command tests typically duplicate.

    Parameters
    ----------
    tmp_path:
        The pytest ``tmp_path`` fixture (or any prebuilt repo root). All
        default resolvers return this value.
    command_module:
        Dotted module path whose attributes are patched. Different command
        surfaces (``...agent.tasks``, ``...upgrade``, ``...plan``) import
        the resolvers separately, so each test file passes its target
        module here. Defaults to the ``agent tasks`` command module, which
        is by far the most common consumer.
    mission_slug:
        When set, also patches ``_find_mission_slug`` to return this slug.
    target_branch:
        Returned as the second element of
        ``_ensure_target_branch_checked_out``'s tuple. Defaults to ``"main"``.
    workspace_resolution:
        Controls ``resolve_workspace_for_wp``:

        * ``None`` (default) — that helper is left unpatched.
        * Exception class (e.g. ``FileNotFoundError``) — used as
          ``side_effect``.
        * Any other value — used as ``return_value``.

    auto_commit_default:
        When not ``None`` (default ``False``), patches
        ``get_auto_commit_default`` to return this value.
    extra_patches:
        Mapping ``{attr_name: return_value}`` for any one-off resolver this
        test needs patched in the same module. Promote frequently-used
        entries into ``_DEFAULT_RESOLVERS`` rather than re-passing them at
        every call site.

    Yields
    ------
    None — used purely as a context manager.
    """

    with ExitStack() as stack:
        # Always patch the path-root resolvers.
        for attr in _DEFAULT_RESOLVERS:
            stack.enter_context(
                patch(f"{command_module}.{attr}", return_value=tmp_path)
            )

        # Pre-mutation branch guard (returns a (path, branch) tuple).
        stack.enter_context(
            patch(
                f"{command_module}._ensure_target_branch_checked_out",
                return_value=(tmp_path, target_branch),
            )
        )

        # Optional patches.
        if mission_slug is not None:
            stack.enter_context(
                patch(
                    f"{command_module}._find_mission_slug",
                    return_value=mission_slug,
                )
            )

        if workspace_resolution is not None:
            if isinstance(workspace_resolution, type) and issubclass(
                workspace_resolution, BaseException
            ):
                kw: dict[str, Any] = {"side_effect": workspace_resolution}
            else:
                kw = {"return_value": workspace_resolution}
            stack.enter_context(
                patch(
                    f"{command_module}.resolve_workspace_for_wp",
                    **kw,
                )
            )

        if auto_commit_default is not None:
            stack.enter_context(
                patch(
                    f"{command_module}.get_auto_commit_default",
                    return_value=auto_commit_default,
                )
            )

        if extra_patches:
            for attr, value in extra_patches.items():
                stack.enter_context(
                    patch(f"{command_module}.{attr}", return_value=value)
                )

        yield
