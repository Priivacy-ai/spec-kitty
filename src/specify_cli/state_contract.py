"""Backward-compat shim — canonical home is specify_cli.state.contract."""

from specify_cli.state.contract import (  # noqa: F401
    AuthorityClass,
    GitClass,
    STATE_SURFACES,
    StateFormat,
    StateRoot,
    StateSurface,
    get_runtime_gitignore_entries,
    get_surfaces_by_authority,
    get_surfaces_by_git_class,
    get_surfaces_by_root,
)
