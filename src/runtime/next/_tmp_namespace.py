"""Shared, per-repo, sweepable ``/tmp`` root for spec-kitty prompt writers.

WP02 / FR-003: three prompt writers previously rooted their output directly
at ``tempfile.gettempdir()`` (a flat, unbounded ``/tmp``):

- ``runtime.next.prompt_builder`` (``spec-kitty-next-*``)
- ``runtime.next.decision`` (``spec-kitty-composed-{action}-*``, two
  ``mkstemp`` sites — unbounded, a unique suffix per call)
- ``specify_cli.cli.commands.agent.workflow`` (``spec-kitty-{implement,review}-*``)

This module is the single source of truth for the namespace all three write
under. Callers must build their prompt path under :func:`prompt_tmp_dir`
(e.g. pass ``dir=prompt_tmp_dir(repo_root)`` to ``tempfile.mkstemp`` /
``NamedTemporaryFile``, or join their filename onto the returned path)
instead of rooting at the bare ``tempfile.gettempdir()``.

WP01's session reaper imports :data:`SPEC_KITTY_PROMPT_NAMESPACE` /
:func:`prompt_tmp_dir` from here to find and sweep this run's prompt
residue — it must never hand-copy the prefix, or the two can silently drift
apart.
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

#: Directory name under ``tempfile.gettempdir()`` that roots every
#: spec-kitty prompt writer. The single shared constant: writers AND the
#: WP01 reaper import this — never hand-copy the literal.
SPEC_KITTY_PROMPT_NAMESPACE = "spec-kitty-prompts"


def _repo_identity(repo_root: Path) -> str:
    """Return a short, stable, filesystem-safe identity for *repo_root*.

    Hashing the resolved absolute path keeps the namespace directory name
    short while still giving each distinct repo checkout (including each
    lane's own worktree path) its own subdirectory, so concurrent runs never
    collide and one run's sweep never touches another's residue.
    """
    resolved = str(Path(repo_root).expanduser().resolve())
    digest = hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:16]  # noqa: TID251 - production raw SHA-256 owner (directory-naming hash, non-security)
    return digest


def prompt_tmp_dir(repo_root: Path) -> Path:
    """Return the shared, per-repo prompt temp-root, creating it if absent.

    All flat-``/tmp`` prompt writers must write their filenames under this
    directory instead of rooting at ``tempfile.gettempdir()``. This is what
    WP01's session reaper sweeps at session finish.
    """
    tmp_dir = Path(tempfile.gettempdir()) / SPEC_KITTY_PROMPT_NAMESPACE / _repo_identity(repo_root)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return tmp_dir
