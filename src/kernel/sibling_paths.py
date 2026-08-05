"""Domain-agnostic sibling-path-resolution primitive (FR-004).

Kernel-owned resolution algorithm for locating a directory that ships as a
filesystem sibling of the *calling* module's own package -- either inside an
editable (development) checkout, or inside an installed wheel where a shared
tree was force-included as a top-level sibling of every package (see the
root ``pyproject.toml``'s ``force-include`` mapping for ``packs/``).

This module holds no ``doctrine``-, ``specify_cli``-, or mission-type-
identifying string anywhere: every caller supplies its own ``__file__`` as
``anchor_file`` and the relative shape it is looking for as
``sibling_relative_path``. Three call sites converge on this primitive:
``kernel.paths.get_package_asset_root()``,
``doctrine.pack_paths._resolve_built_in()``, and
``doctrine.missions.repository.MissionTemplateRepository.default_missions_root()``
-- see the mission's ``contracts/kernel-resolution-primitive.md`` for the
full behavioural contract this implements.

Resolution order (a 3-step collapse of ``doctrine.pack_paths._resolve_built_in``'s
pre-existing *shape* -- see the note below on why its distinct third step does
not carry over unchanged):

1. **Env override** wins, if the caller-resolved override directory (already
   joined by the *caller* -- this primitive does not know environment
   variable names, or how a given caller's env var should be joined with a
   sibling path) exists.
2. **Ancestor walk**: walk ``anchor_file.resolve().parents``, looking for
   ``sibling_relative_path`` at each ancestor. ``.resolve()`` happens
   *before* the walk so a symlinked editable install still reaches the real
   repository root. This single walk covers *both* the editable-checkout case
   (a ``src/`` ancestor holding a sibling package) and the installed-wheel
   case (the site-packages directory itself is always one of
   ``anchor_file``'s ancestors, so a force-included sibling tree living next
   to every top-level package is found here too, at the ancestor equal to
   ``anchor_file.resolve().parent.parent``) -- there is no separate probe for
   the installed-wheel case because ``anchor.parent.parent`` is always a
   member of ``anchor.parents``, making a distinct third step redundant with
   this walk.
3. **Fail closed**: :class:`SiblingPathNotFound`, naming what was sought and
   where it was not found. Never returns a nonexistent path; never falls
   back to an arbitrary tree.

Note on the pre-existing ``_resolve_built_in`` shape this primitive replaces:
that function's own step 3 was *not* redundant, because it read
``files("doctrine").parent`` -- a different path source (installed-package
metadata via :func:`importlib.resources.files`) than a filesystem walk. This
primitive intentionally has no equivalent, since it must stay
package-name-agnostic (it only ever receives the caller's own ``__file__``);
the ancestor walk above is sufficient in practice because the site-packages
level is always reached by it.

``sibling_relative_path`` may contain glob wildcards (e.g. ``"*/missions"``) so
a caller can express "some sibling package's own asset directory"
generically, without hard-coding any package name. A pattern with a leading
``src/`` segment is a caller bug, not a stricter match: an installed wheel has
no ``src/`` directory at any level (the root ``pyproject.toml``'s wheel-target
``packages`` mapping drops it), so such a pattern can never match there --
callers needing "some sibling under ``src/``" should let the ancestor walk
reach the ``src/`` ancestor itself and match the bare shape below it (e.g.
``"*/missions"``, not ``"src/*/missions"``). When a pattern matches more than
one directory at a given anchor, matches are sorted for a deterministic pick.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

__all__ = ["SiblingPathNotFound", "resolve_installed_sibling"]


class SiblingPathNotFound(Exception):
    """Raised when no sibling path can be resolved (fail-closed).

    Names both what was being sought (``sibling_relative_path``) and the
    anchor it was sought relative to (``anchor_file``), so a caller-facing
    translation (e.g. ``doctrine.pack_paths.PackRootNotFound``) can still
    produce an informative message.
    """

    def __init__(self, sibling_relative_path: PurePosixPath, anchor_file: Path) -> None:
        self.sibling_relative_path = sibling_relative_path
        self.anchor_file = anchor_file
        super().__init__(
            f"Could not resolve {sibling_relative_path.as_posix()!r} as a sibling of "
            f"{anchor_file}: no env override or ancestor sibling directory matched."
        )


def _first_match(root: Path, pattern: str) -> Path | None:
    """Return the first (sorted, for determinism) directory under ``root`` matching ``pattern``.

    ``pattern`` may be a plain relative path (no wildcards), in which case this
    behaves as a simple existence check, or contain glob wildcards to express
    "any sibling with this shape" generically.
    """
    if not root.is_dir():
        return None
    matches = sorted(candidate for candidate in root.glob(pattern) if candidate.is_dir())
    return matches[0] if matches else None


def resolve_installed_sibling(
    *,
    anchor_file: Path,
    env_override: Path | None,
    sibling_relative_path: PurePosixPath,
) -> Path:
    """Resolve a directory shipped as a filesystem sibling of ``anchor_file``'s package.

    See the module docstring for the full 3-step resolution order.

    :param anchor_file: The calling module's own ``__file__`` -- must be the
        caller's own file, never a string naming another package.
    :param env_override: An already-resolved candidate directory the caller
        derived from its own environment-variable override, or ``None``. This
        primitive performs no further joining on it -- environment-variable
        *names* and how they combine with a sibling path stay caller-specific.
    :param sibling_relative_path: The relative shape being sought (e.g.
        ``PurePosixPath("packs/built-in")``); may contain glob wildcards.
    :raises SiblingPathNotFound: when no candidate resolves to a directory.
    """
    if env_override is not None and env_override.is_dir():
        return env_override

    pattern = sibling_relative_path.as_posix()

    anchor = anchor_file.resolve()
    for ancestor in anchor.parents:
        # This walk alone covers both the editable-checkout case (a src/
        # ancestor holding a sibling package) and the installed-wheel case:
        # anchor.parent.parent (the site-packages level) is always one of
        # anchor.parents, so a distinct "installed wheel" probe would be
        # redundant with this loop -- see the module docstring.
        ancestor_candidate = _first_match(ancestor, pattern)
        if ancestor_candidate is not None:
            return ancestor_candidate

    raise SiblingPathNotFound(sibling_relative_path, anchor_file)
