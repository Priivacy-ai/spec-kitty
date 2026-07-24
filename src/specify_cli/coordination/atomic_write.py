"""Confined, symlink-safe filesystem primitives + the single generated-artifact compensator.

Extracted from ``transaction.py`` (WP08 campsite split, NFR-007) so the
coordination-branch write chokepoint lands in a smaller module. WP09 (T052 /
FR-007, FR-008, NFR-002) generalises the module further:

* The confined-artifact orchestration helpers (``_resolve_confined_artifact_path``,
  ``_write_confined_artifact_bytes``, ``_unlink_confined_artifact_path``) now live
  here behind a **dependency-injection seam** — the write/unlink helpers accept a
  ``resolve`` callable so ``transaction.py`` can inject its own module-level
  ``_resolve_confined_artifact_path`` and keep the oracle's symlink-swap-on-resolve
  confinement attack exercisable through ``transaction._resolve_confined_artifact_path``
  (the campsite oracle patches that name). Moving the bodies out lands
  ``transaction.py`` ≤ 1000 LOC (C-010) even after the owner gains its new
  capabilities.

* ``capture_generated_artifact_snapshots`` / ``restore_generated_artifact_snapshots``
  are the **single** byte-snapshot rollback compensator (TAO-3): exactly one restore
  implementation, consumed by BOTH the coordination ``BookkeepingTransaction`` and
  the merge executor. The trust-root containment that used to live beside the merge
  executor's snapshot capture folds into ``capture_*`` via ``trusted_roots`` /
  ``trusted_files``, so the owner (not the ``merge/`` package) owns containment for
  bytes it generates on ANY surface — including non-coord (primary-checkout)
  destinations.

* ``enroll_subprocess_byproducts`` / ``subprocess_created_paths`` enrol the bytes a
  spec-kitty-spawned child process creates (a gate's pytest run) into the same
  compensator (C3): committed on success, reverted on abort — never detected,
  warned about, and abandoned.

Spec source: FR-005, FR-007, FR-008, C-009, NFR-002, NFR-008.
"""

from __future__ import annotations

import errno
import logging
import os
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path

import ulid as _ulid_mod

from specify_cli.core.utils import ensure_within_any

logger = logging.getLogger(__name__)


def _generate_ulid() -> str:
    """Generate a new ULID string (same convention as status.emit)."""
    if hasattr(_ulid_mod, "new"):
        return str(_ulid_mod.new().str)
    return str(_ulid_mod.ULID())


# ---------------------------------------------------------------------------
# Low-level leaf primitives (containment + fd-relative no-follow writes)
# ---------------------------------------------------------------------------


def _confine_path_to_worktree(worktree_root: Path, path: Path) -> Path:
    """Resolve ``path`` relative to ``worktree_root`` and reject escapes."""
    candidate = path if path.is_absolute() else worktree_root / path
    try:
        resolved_worktree = worktree_root.resolve()
        resolved_candidate = candidate.resolve(strict=False)
    except OSError as exc:
        raise ValueError(
            f"Path {candidate} could not be resolved under worktree {worktree_root}: {exc}"
        ) from exc
    if not resolved_candidate.is_relative_to(resolved_worktree):
        raise ValueError(
            f"Path {candidate} resolves outside worktree {worktree_root}: "
            f"{resolved_candidate}"
        )
    return candidate


def _open_confined_parent_fd(worktree_root: Path, path: Path) -> int:
    """Open ``path.parent`` component-by-component without following symlinks."""
    if not (
        os.open in os.supports_dir_fd
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
    ):
        raise ValueError(
            "Refusing to write artifact outside coordination worktree "
            "(fd-relative no-follow writes unsupported on this platform): "
            f"{path}"
        )

    resolved_worktree = worktree_root.resolve()
    relative_parent = path.parent.relative_to(resolved_worktree)
    dir_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(resolved_worktree, dir_flags)
    try:
        for part in relative_parent.parts:
            next_fd = os.open(part, dir_flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
    except Exception:
        os.close(fd)
        raise
    return fd


def _write_and_replace_via_parent_fd(
    *,
    parent_fd: int,
    target_name: str,
    tmp_name: str,
    content: bytes,
    existing_mode: int | None,
) -> None:
    """Create temp file and replace target relative to an already-open parent."""
    tmp_fd = os.open(
        tmp_name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=parent_fd,
    )
    try:
        if existing_mode is not None:
            os.fchmod(tmp_fd, existing_mode)
        remaining = memoryview(content)
        while remaining:
            written = os.write(tmp_fd, remaining)
            remaining = remaining[written:]
    finally:
        os.close(tmp_fd)
    os.replace(tmp_name, target_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)


# ---------------------------------------------------------------------------
# Confined-artifact orchestration (moved from transaction.py; DI ``resolve`` seam)
#
# ``_write_confined_artifact_bytes`` / ``_unlink_confined_artifact_path`` accept a
# ``resolve`` callable rather than calling ``_resolve_confined_artifact_path``
# directly, so a caller (``transaction.py``) can inject its own module-level
# resolver. This keeps the campsite oracle's symlink-swap-on-resolve attack
# exercisable through ``transaction._resolve_confined_artifact_path`` even though
# the write body now lives here.
# ---------------------------------------------------------------------------


ResolveConfined = Callable[[Path, Path], Path]


def _resolve_confined_artifact_path(worktree_root: Path, path: Path) -> Path:
    """Return a canonical artifact path that remains inside ``worktree_root``."""
    candidate = _confine_path_to_worktree(worktree_root, path)
    resolved_worktree = worktree_root.resolve()
    resolved_path = candidate.resolve(strict=False)
    if resolved_path == resolved_worktree:
        raise ValueError(
            "Refusing to write artifact outside coordination worktree "
            "(target is worktree root): "
            f"{path}"
        )
    if not resolved_path.is_relative_to(resolved_worktree):
        raise ValueError(
            "Refusing to write artifact outside coordination worktree "
            "(outside worktree): "
            f"{resolved_path}"
        )
    return resolved_path


def _write_confined_artifact_bytes(
    worktree_root: Path,
    path: Path,
    content: bytes,
    *,
    resolve: ResolveConfined,
) -> Path:
    """Write bytes after revalidating containment at the I/O boundary.

    ``resolve`` is injected so the caller's module-level resolver (patchable by the
    oracle) governs both the pre-write and post-mkdir containment checks.
    """
    resolved_path = resolve(worktree_root, path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path = resolve(worktree_root, resolved_path)
    if resolved_path.exists() and not resolved_path.is_file():
        raise ValueError(
            "Refusing to write artifact outside coordination worktree "
            "(target is not a regular file): "
            f"{resolved_path}"
        )
    existing_mode = (
        resolved_path.stat().st_mode & 0o777
        if resolved_path.exists()
        else None
    )

    parent_fd: int | None = None
    tmp_name = f".spec-kitty-{_generate_ulid()}.tmp"
    try:
        parent_fd = _open_confined_parent_fd(worktree_root, resolved_path)
        _write_and_replace_via_parent_fd(
            parent_fd=parent_fd,
            target_name=resolved_path.name,
            tmp_name=tmp_name,
            content=content,
            existing_mode=existing_mode,
        )
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOENT, errno.ENOTDIR}:
            raise ValueError(
                "Refusing to write artifact outside coordination worktree "
                "(unsafe path changed during write): "
                f"{resolved_path}"
            ) from exc
        raise
    finally:
        if parent_fd is not None:
            try:
                os.unlink(tmp_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
            except OSError:
                logger.debug(
                    "atomic_write: failed to remove temp artifact %s/%s",
                    resolved_path.parent,
                    tmp_name,
                )
            os.close(parent_fd)
    return resolved_path


def _unlink_confined_artifact_path(
    worktree_root: Path,
    path: Path,
    *,
    resolve: ResolveConfined,
) -> None:
    """Unlink an artifact relative to a verified no-follow parent directory."""
    resolved_path = resolve(worktree_root, path)
    parent_fd: int | None = None
    try:
        parent_fd = _open_confined_parent_fd(worktree_root, resolved_path)
        os.unlink(resolved_path.name, dir_fd=parent_fd)
    except FileNotFoundError:
        pass
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise ValueError(
                "Refusing to unlink artifact outside coordination worktree "
                "(unsafe path changed during unlink): "
                f"{resolved_path}"
            ) from exc
        raise
    finally:
        if parent_fd is not None:
            os.close(parent_fd)


# ---------------------------------------------------------------------------
# The single generated-artifact byte-snapshot compensator (TAO-3)
#
# Exactly one rollback implementation, consumed by BOTH
# ``coordination.transaction.BookkeepingTransaction`` (confined worktree writes)
# and ``merge.executor`` (primary-checkout bookkeeping — the non-coord
# destination). The per-site I/O strategy (confined fd-relative vs plain) is
# injected; the capture/restore ledger logic is defined here, once.
# ---------------------------------------------------------------------------


def _plain_write_bytes(path: Path, content: bytes) -> None:
    """Default restore writer: create parents, then write the snapshot bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _plain_unlink(path: Path) -> None:
    """Default restore unlinker: remove the path if present."""
    path.unlink(missing_ok=True)


def capture_generated_artifact_snapshots(
    *paths: Path,
    trusted_roots: Sequence[Path],
    trusted_files: Sequence[Path] = (),
) -> dict[Path, bytes | None]:
    """Snapshot the pre-transaction bytes of each generated-artifact path (TAO-1).

    Each candidate is first constrained to the owner's trusted surface via
    :func:`ensure_within_any` (the containment that used to live beside the merge
    executor as a retired snapshot-trust helper — folded in here so the owner, not
    the ``merge/`` package, owns containment for bytes it generates). A path that
    does not yet exist snapshots as ``None`` so the single compensator unlinks it on
    rollback.
    """
    snapshots: dict[Path, bytes | None] = {}
    for candidate in paths:
        trusted = ensure_within_any(
            candidate, roots=list(trusted_roots), files=list(trusted_files)
        )
        snapshots[trusted] = trusted.read_bytes() if trusted.exists() else None
    return snapshots


def restore_generated_artifact_snapshots(
    snapshots: Mapping[Path, bytes | None],
    *,
    write: Callable[[Path, bytes], object] = _plain_write_bytes,
    unlink: Callable[[Path], object] = _plain_unlink,
    on_error: Callable[[Path, BaseException], None] | None = None,
) -> None:
    """Restore every enrolled path to its pre-transaction bytes (TAO-3).

    THE single rollback implementation. For each captured ``{path: pre_bytes}``
    entry: write the snapshot back, or unlink when the path did not exist
    pre-transaction (``None``). Best-effort — a per-path ``OSError`` / ``ValueError``
    is routed to ``on_error`` (default: swallow) so one bad path never aborts the
    rest. The ``write`` / ``unlink`` strategy is injected: the coordination
    transaction supplies confined fd-relative helpers; the merge executor uses the
    plain default.
    """
    for path, original in snapshots.items():
        try:
            if original is None:
                unlink(path)
            else:
                write(path, original)
        except (OSError, ValueError) as exc:
            if on_error is not None:
                on_error(path, exc)


def subprocess_created_paths(
    before: Iterable[Path], after: Iterable[Path]
) -> list[Path]:
    """Paths present after a spawned child ran that were absent before (C3)."""
    return sorted(set(after) - set(before))


def enroll_subprocess_byproducts(
    created_paths: Iterable[Path],
    *,
    trusted_roots: Sequence[Path],
    trusted_files: Sequence[Path] = (),
) -> dict[Path, bytes | None]:
    """Enrol subprocess-created byproducts into the single compensator (C3/TAO-1).

    A spec-kitty-spawned child (a gate's pytest run) may CREATE files. Their
    pre-transaction state is *absent*, so enrolling each with a ``None`` snapshot
    makes :func:`restore_generated_artifact_snapshots` UNLINK it on abort — the
    byproduct is committed on success and reverted on failure, like any other
    generated write, instead of being detected, warned about, and abandoned as the
    orphan a later gate must then be taught to ignore.
    """
    snapshots: dict[Path, bytes | None] = {}
    for path in created_paths:
        trusted = ensure_within_any(
            path, roots=list(trusted_roots), files=list(trusted_files)
        )
        snapshots[trusted] = None
    return snapshots
