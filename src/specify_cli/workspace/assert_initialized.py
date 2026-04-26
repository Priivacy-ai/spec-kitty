"""Fail-loud uninitialized-repo guard (FR-032, WP07/T039).

The ``specify``/``plan``/``tasks`` Typer commands must never silently
fall back to a parent or sibling initialized repository when the cwd
is not itself a Spec Kitty project. :func:`assert_initialized` is the
single entry point that enforces that invariant: it resolves the
canonical mission repo root via :mod:`specify_cli.workspace.root_resolver`
and raises :class:`SpecKittyNotInitialized` if required project markers
are missing.

Callers should invoke this at the very top of their command handler,
*before* any side-effecting work, so a wrong cwd never produces a
file-system write to an unrelated repo.
"""

from __future__ import annotations

from pathlib import Path

from .root_resolver import (
    WorkspaceRootNotFound,
    resolve_canonical_root,
)

__all__ = [
    "SPEC_KITTY_REPO_NOT_INITIALIZED",
    "SpecKittyNotInitialized",
    "assert_initialized",
]

SPEC_KITTY_REPO_NOT_INITIALIZED = "SPEC_KITTY_REPO_NOT_INITIALIZED"


class SpecKittyNotInitialized(Exception):
    """Raised when the canonical repo root is not a Spec Kitty project.

    Attributes:
        root: The canonical repo root that was inspected (or the cwd
            when no git repo was found at all).
        missing: List of expected paths that did not exist.
    """

    def __init__(self, root: Path, missing: list[Path]) -> None:
        self.root = Path(root)
        self.missing = list(missing)
        bullets = "\n".join(f"  - {p}" for p in self.missing)
        message = (
            f"{SPEC_KITTY_REPO_NOT_INITIALIZED}: Spec Kitty is not initialized "
            "at the resolved repo root.\n"
            f"  Resolved root: {self.root}\n"
            "  Missing:\n"
            f"{bullets}\n"
            "Fix: cd into a Spec Kitty project, or run "
            "`spec-kitty init` from the desired project root."
        )
        super().__init__(message)


def assert_initialized(root: Path | None = None, *, require_specs: bool = True) -> Path:
    """Verify that ``root`` (or its canonical resolution) is initialized.

    Resolution rules:

    * When ``root`` is ``None`` (the typical command-handler path), the
      canonical root is resolved from :func:`Path.cwd` using
      :func:`resolve_canonical_root` so that worktree cwds map to their
      main checkout (FR-013).
    * When ``root`` is supplied (test-friendly path), it is used as-is
      and not redirected to a parent or sibling project.

    A repo is considered initialized when ``<root>/.kittify/config.yaml``
    exists. Commands that operate on existing mission artifacts should
    leave ``require_specs=True`` so ``<root>/kitty-specs/`` is also
    required. ``specify`` passes ``require_specs=False`` because mission
    creation is the code path that lazily creates ``kitty-specs/``.

    Args:
        root: Optional explicit repo root. When omitted the cwd is used.
        require_specs: Require an existing ``kitty-specs/`` directory.

    Returns:
        The validated repo root path.

    Raises:
        SpecKittyNotInitialized: When the resolved root is missing the
            expected initialization markers.
    """
    if root is None:
        try:
            resolved_root = resolve_canonical_root(Path.cwd())
        except WorkspaceRootNotFound as exc:
            cwd = Path(exc.cwd)
            # No git repo at all -- treat as uninitialized at the cwd.
            raise SpecKittyNotInitialized(
                cwd,
                missing=(
                    [cwd / ".kittify" / "config.yaml", cwd / "kitty-specs"]
                    if require_specs
                    else [cwd / ".kittify" / "config.yaml"]
                ),
            ) from exc
    else:
        resolved_root = Path(root).resolve()

    config_path = resolved_root / ".kittify" / "config.yaml"
    specs_dir = resolved_root / "kitty-specs"

    missing: list[Path] = []
    if not config_path.exists():
        missing.append(config_path)
    if require_specs and not specs_dir.is_dir():
        missing.append(specs_dir)

    if missing:
        raise SpecKittyNotInitialized(resolved_root, missing=missing)
    return resolved_root
