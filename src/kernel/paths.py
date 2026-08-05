"""Cross-platform path resolution for the spec-kitty runtime.

Provides the canonical functions for locating:
- The user-global ~/.kittify/ directory (cross-platform)
- The package-bundled mission assets (for ensure_runtime to copy from)

These functions have no spec-kitty-specific dependencies and are consumed
by multiple packages in the stack (specify_cli, charter).  They live
in kernel so that neither package needs to import from the other.
"""

from __future__ import annotations

import os
from pathlib import Path, PurePath, PurePosixPath

from kernel.sibling_paths import SiblingPathNotFound, resolve_installed_sibling


def _is_windows() -> bool:
    """Return True when running on Windows."""
    return os.name == "nt"


def get_kittify_home() -> Path:
    """Return the path to the user-global ~/.kittify/ directory.

    Resolution order:
    1. SPEC_KITTY_HOME environment variable (all platforms)
    2. ~/.kittify/ on macOS/Linux (Path.home() / ".kittify")
    3. %LOCALAPPDATA%\\spec-kitty\\ on Windows (via platformdirs, app name "spec-kitty")

    On Windows the app name used is ``"spec-kitty"`` so that ``kernel.paths``
    resolves to the same root as ``specify_cli.paths.get_runtime_root().base``
    (FR-005 / C-002: unified Windows root, no long-term dual root).
    The ``roaming=False`` flag matches ``get_runtime_root()`` exactly so that
    both resolve to ``%LOCALAPPDATA%\\spec-kitty``.

    On POSIX the behaviour is unchanged: ``~/.kittify/``.

    Returns:
        Path: Absolute path to the global runtime directory.

    Raises:
        RuntimeError: If the home directory cannot be determined.
    """
    if env_home := os.environ.get("SPEC_KITTY_HOME"):
        return Path(env_home)

    if _is_windows():
        # platformdirs is the only sanctioned third-party import in kernel/.
        # Use app name "spec-kitty" (not "kittify") so this matches
        # specify_cli.paths.get_runtime_root().base — the two resolutions must
        # agree to satisfy the single-root invariant (FR-005 / C-002).
        # kernel/ must not import specify_cli (architectural layer rule), so we
        # call platformdirs directly with the same arguments.
        from platformdirs import user_data_dir  # noqa: PLC0415

        return Path(str(user_data_dir("spec-kitty", appauthor=False, roaming=False)))

    return Path.home() / ".kittify"


#: The relative shape sought for the *env-var* override branch below: either
#: the mission-assets directory itself, or a checkout/package root one or two
#: levels above it. Generic (a bare directory name, not a package name) --
#: see ``_looks_like_missions_root`` for the content sniff that disambiguates
#: an actual hit from an unrelated directory that happens to be named this.
_MISSION_ASSETS_DIR_NAME = "missions"

#: The relative shape handed to :func:`kernel.sibling_paths.resolve_installed_sibling`
#: for the non-env-var (ancestor-walk) branch. Mission
#: ``doctrine-consumer-surface-missions-extraction-01KZ6G6H`` (FR-005, WP05)
#: relocated the missions *data* subdirectories from ``src/doctrine/missions``
#: to ``packs/built-in/missions`` -- ``packs/`` ships as a fixed-name,
#: site-packages-level sibling of every top-level package (the root
#: ``pyproject.toml``'s ``force-include = {"packs" = "packs"}``), so this
#: pattern is a **literal** relative path, not a per-package wildcard: it can
#: only ever match the one real data location, never accidentally the
#: still-existing-but-now-data-less ``src/doctrine/missions`` package
#: directory (the ``.py`` logic modules stay there) that a generic
#: ``"*/missions"`` wildcard pattern would keep matching post-move. This is
#: the exact self-match trap the mission's reader inventory names as the
#: highest-severity finding: a bare wildcard pattern still finds *a* directory
#: named "missions" one ancestor level up from ``src/doctrine/missions``
#: itself, it is just the wrong (data-less) one. A fully-qualified pattern
#: naming ``packs/built-in/missions`` structurally cannot make that mistake.
_MISSION_ASSETS_SIBLING_PATTERN = PurePosixPath("packs") / "built-in" / _MISSION_ASSETS_DIR_NAME

#: The relative shape used only by :func:`_resolve_env_root` below, globbed
#: directly against a caller-supplied ``SPEC_KITTY_TEMPLATE_ROOT`` checkout
#: root -- NOT handed to the sibling-resolution primitive. A checkout root
#: sits *two* levels above the sibling package's missions dir
#: (``<root>/src/<pkg>/missions``), unlike the primitive's own anchor (this
#: module's file, one level below ``src/``), so this candidate needs the
#: ``src/`` segment that :data:`_MISSION_ASSETS_SIBLING_PATTERN` above must
#: not carry.
_MISSION_ASSETS_CHECKOUT_GLOB_PATTERN = PurePosixPath("src") / "*" / _MISSION_ASSETS_DIR_NAME


def _looks_like_missions_root(path: Path) -> bool:
    """Content-sniff: does ``path`` hold mission-type subdirectories with real content?

    Generic by construction: the mission-type segment is a glob wildcard, not
    an enumerated, hard-coded vocabulary of mission-type names.
    """
    has_content_templates = any(path.glob("*/templates/*.md"))
    has_legacy_commands = any(path.glob("*/command-templates/*.md"))
    has_step_prompts = any(path.glob("mission-steps/*/*/prompt.md"))
    return has_content_templates or has_legacy_commands or has_step_prompts


def _find_relocated_missions_ancestor(root: Path) -> Path | None:
    """Walk ``root`` and its ancestors for the real, post-relocation missions root.

    Mission ``doctrine-consumer-surface-missions-extraction-01KZ6G6H`` (FR-005)
    moved the missions data from ``src/doctrine/missions`` to
    ``packs/built-in/missions``. ``SPEC_KITTY_TEMPLATE_ROOT`` may be set to any
    of several legacy shapes (the bare missions directory, a full checkout
    root, a stale sibling-package leaf, ...), each sitting at a *different*
    depth relative to the real repository root -- so this walks every
    ancestor (including ``root`` itself) rather than assuming a fixed number
    of ``.parent`` hops, finding the relocated data uniformly regardless of
    which legacy shape the caller supplied. Unlike the other candidates in
    :func:`_resolve_env_root`, the ``packs/built-in/missions`` shape is
    unambiguous -- no unrelated tree can accidentally satisfy it -- so no
    content-sniff is needed once a candidate is found to exist.
    """
    for ancestor in (root, *root.parents):
        candidate = ancestor / "packs" / "built-in" / _MISSION_ASSETS_DIR_NAME
        if candidate.is_dir():
            return candidate
    return None


def _resolve_env_root(root: Path) -> Path:
    """Resolve ``SPEC_KITTY_TEMPLATE_ROOT`` under its several legacy accepted shapes.

    ``root`` may itself already be the mission-assets directory, a checkout
    root one or two levels above it, or (historically) a stale sibling
    package's own copy -- disambiguated by :func:`_looks_like_missions_root`,
    never by naming a specific package. The relocated ``packs/built-in/missions``
    location (see :func:`_find_relocated_missions_ancestor`) is tried first and
    unconditionally, since every legacy shape below predates mission #3091's
    move and would otherwise resolve into the now data-less
    ``src/doctrine/missions`` package directory or the unrelated
    ``specify_cli/missions`` legacy tree.

    Candidate order matters: the checkout-root candidate (bare ``root``) is
    tried LAST, after the more specific ``src/*/missions`` glob. A real
    checkout root generally also satisfies ``_looks_like_missions_root``'s
    loose content sniff on its own (e.g. via an unrelated ``docs/templates/
    *.md``), so if bare ``root`` were tried first it would short-circuit
    before the glob ever gets a chance to find the actual missions directory
    nested under it.
    """
    if (relocated := _find_relocated_missions_ancestor(root)) is not None:
        return relocated

    candidates: list[Path] = [root / _MISSION_ASSETS_DIR_NAME]
    candidates.extend(sorted(root.glob(str(_MISSION_ASSETS_CHECKOUT_GLOB_PATTERN))))
    if root.name == _MISSION_ASSETS_DIR_NAME:
        candidates.extend(sorted(root.parent.parent.glob(f"*/{_MISSION_ASSETS_DIR_NAME}")))
    candidates.append(root)
    for candidate in candidates:
        if candidate.is_dir() and _looks_like_missions_root(candidate):
            return candidate
    raise FileNotFoundError(
        "SPEC_KITTY_TEMPLATE_ROOT does not contain mission assets: "
        f"{root}. Expected a missions directory or a Spec Kitty checkout root."
    )


def get_package_asset_root() -> Path:
    """Return the path to the package's bundled mission assets.

    Resolution order:
    1. SPEC_KITTY_TEMPLATE_ROOT environment variable (CI/testing) -- several
       accepted legacy shapes, see :func:`_resolve_env_root`.
    2. The shared kernel sibling-path-resolution primitive
       (:func:`kernel.sibling_paths.resolve_installed_sibling`): a single
       ancestor walk that covers both an editable-checkout sibling and an
       installed-wheel sibling (the site-packages level is always one of the
       walked ancestors), seeking the fixed ``packs/built-in/missions`` shape
       (:data:`_MISSION_ASSETS_SIBLING_PATTERN`) rather than a per-package
       wildcard -- see that constant's own docstring for why a wildcard
       pattern would self-match the now data-less ``src/doctrine/missions``
       package directory post-relocation.

    The ancestor walk in step 2 is bounded: it stops within a small, fixed
    number of hops of a recognized ``src``/``site-packages`` boundary (or,
    absent one, after a small fixed number of ancestors) rather than
    climbing all the way to the filesystem root -- so a broken install fails
    closed instead of matching an unrelated ``<ancestor>/packs/built-in/missions``
    several levels up. Real layouts (editable checkout or installed wheel)
    match at ancestor depth 1-2, comfortably inside the bound; see
    :mod:`kernel.sibling_paths`'s ``resolve_installed_sibling`` docstring for
    the walk itself and its stop-condition constants.

    Returns:
        Path: Absolute path to the missions directory.

    Raises:
        FileNotFoundError: If no valid asset root can be found.
    """
    # CI/testing override
    if env_root := os.environ.get("SPEC_KITTY_TEMPLATE_ROOT"):
        root = Path(env_root)
        if root.is_dir():
            return _resolve_env_root(root)
        raise FileNotFoundError(f"SPEC_KITTY_TEMPLATE_ROOT path does not exist: {env_root}")

    try:
        return resolve_installed_sibling(
            anchor_file=Path(__file__),
            env_override=None,
            sibling_relative_path=_MISSION_ASSETS_SIBLING_PATTERN,
        )
    except SiblingPathNotFound as exc:
        raise FileNotFoundError(
            "Cannot locate package mission assets. Set SPEC_KITTY_TEMPLATE_ROOT or reinstall spec-kitty-cli."
        ) from exc


def render_runtime_path(path: Path, *, for_user: bool = True) -> str:
    """Render a runtime-state path for user-facing output.

    - On Windows: returns the real absolute path string (no tilde substitution).
    - On POSIX: if ``for_user=True`` and ``path`` is under ``$HOME``, returns
      ``~/<relpath>`` form; otherwise returns the absolute path.

    This helper exists in ``kernel`` so that every layer can render runtime
    paths without reintroducing POSIX-tilde literals in user-facing output
    on Windows (SC-002 of the Windows Compatibility Hardening mission).
    Mirrors :func:`specify_cli.paths.render_runtime_path` with identical
    semantics; kept here to preserve the kernel<-doctrine<-charter<-specify_cli
    dependency direction.
    """
    abs_path = Path(path).resolve(strict=False)
    if not for_user:
        return str(abs_path)
    if _is_windows():
        return str(abs_path)
    try:
        home = Path.home().resolve(strict=False)
        rel = abs_path.relative_to(home)
        return "~/" + to_posix(rel)
    except ValueError:
        return str(abs_path)


def to_posix(path: Path | str) -> str:
    """Normalize a path (or path-like string) to a forward-slashed string.

    The single separator-normalization seam. For a ``PurePath`` it returns
    ``.as_posix()``; for a ``str`` (git stdout, a glob pattern, user input) it
    swaps ``\\`` for ``/``. Git object/pathspec syntax and cross-platform path
    comparison require forward slashes (#2836); scattering
    ``str(x).replace(...)`` across the tree re-invited the exact per-site Windows
    drift #2836 fixed, so every such normalization routes here. Only the
    separator is touched — surrounding concerns (``.strip()``, ``.rstrip("/")``,
    splitting) stay at the call site.
    """
    if isinstance(path, PurePath):
        return path.as_posix()
    return path.replace("\\", "/")


def posix_tree_path(parts: tuple[str, ...]) -> str:
    """Join path ``parts`` into a git tree path (always forward-slashed).

    Git's ``HEAD:<path>`` object syntax and ``ls-files`` pathspec require
    forward slashes. Rendering with ``str(Path(*parts))`` uses ``os.sep`` — a
    backslash on Windows — which git rejects, making committed specs misreport
    as uncommitted (#2836). ``PurePosixPath`` renders with ``/`` on every host,
    closing the defect by construction: the string is built from the
    separator-agnostic ``parts`` tuple, never re-parsed through a host-native
    ``Path``.

    This lives in ``kernel`` as the single behaviour-agnostic tree-path seam so
    consumers in different layers (``specify_cli.missions._substantive`` and
    ``cli.commands.agent.mission_finalize``) render tree paths identically
    without importing from one another. It is the seam the #2836 regression is
    witnessed against: because the bug is a POSIX/Windows *rendering* difference
    it cannot be caught by a black-box input test on POSIX, so the guard
    substitutes ``PureWindowsPath`` for the module ``Path`` symbol to prove a
    reverted ``str(Path(*parts))`` form would reintroduce backslashes.
    """
    return PurePosixPath(*parts).as_posix() if parts else ""


def repo_tree_path(file_path: Path, repo_root: Path) -> tuple[Path, str]:
    """Return ``(git_cwd, tree_path)`` for a repo file; tree path forward-slashed.

    ``git_cwd`` is the linked-worktree root when ``file_path`` lives under
    ``.worktrees/<name>/`` — branch tree paths start at that worktree root, so a
    file at ``.worktrees/<name>/kitty-specs/<slug>/spec.md`` is addressed as
    ``kitty-specs/<slug>/spec.md`` — else the primary repo root. The tree path is
    always forward-slashed via :func:`posix_tree_path` (#2836).

    Canonical worktree-aware tree-path seam: both the committedness check
    (``specify_cli.missions._substantive._git_commit_check_context``) and
    finalize's branch-artifact reporting
    (``cli.commands.agent.mission_finalize._branch_tree_relative_path``) route
    through here, so the worktree-strip logic lives in exactly one place. Raises
    ``ValueError`` when ``file_path`` is not under ``repo_root``.
    """
    repo_abs = repo_root.resolve()
    rel = file_path.resolve().relative_to(repo_abs)
    parts = rel.parts
    if len(parts) > 2 and parts[0] == ".worktrees":
        worktree_root = repo_abs / parts[0] / parts[1]
        if worktree_root.is_dir():
            return worktree_root, posix_tree_path(parts[2:])
    return repo_abs, posix_tree_path(parts)


__all__ = [
    "get_kittify_home",
    "get_package_asset_root",
    "render_runtime_path",
    "repo_tree_path",
    "to_posix",
]
# ``posix_tree_path`` is intentionally NOT exported: it is the internal
# forward-slash-join primitive behind ``repo_tree_path`` (the public seam other
# layers consume). It stays a module-level function so the #2836 regression
# witness can substitute ``Path`` and call it directly, but it is not part of the
# public API — keeping it out of ``__all__`` satisfies the dead-symbol gate.
