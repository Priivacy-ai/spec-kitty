"""Path-canonicalising read helpers for intake (WP02 T008–T012).

The functions here form the read-side of the intake security surface:

* :func:`assert_under_root` — raise :class:`IntakePathEscapeError` if a
  candidate resolves outside the intake root.  Symlinks are followed
  *before* the containment check, so symlinks that escape the root are
  rejected.
* :func:`load_max_brief_bytes` — read the configurable size cap from
  ``.kittify/config.yaml`` (key ``intake.max_brief_bytes``) with a 5 MB
  default.
* :func:`read_brief` — read a candidate file, enforcing the cap with
  ``os.stat`` *before* opening, and distinguishing missing vs.
  unreadable failure modes.
* :func:`read_stdin_capped` — read at most ``cap + 1`` bytes from a
  stream and reject if more arrive.
"""

from __future__ import annotations

from pathlib import Path
from typing import IO, Any

from .errors import (
    IntakeFileMissingError,
    IntakeFileUnreadableError,
    IntakePathEscapeError,
    IntakeTooLargeError,
)

# ---------------------------------------------------------------------------
# Size cap configuration
# ---------------------------------------------------------------------------

DEFAULT_MAX_BRIEF_BYTES: int = 5 * 1024 * 1024  # 5 MB


def load_max_brief_bytes(repo_root: Path) -> int:
    """Read ``intake.max_brief_bytes`` from ``.kittify/config.yaml``.

    Returns :data:`DEFAULT_MAX_BRIEF_BYTES` when the key is missing,
    malformed, or unreadable.  Never raises.
    """
    config_path = repo_root / ".kittify" / "config.yaml"
    if not config_path.is_file():
        return DEFAULT_MAX_BRIEF_BYTES
    try:
        import yaml

        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 — config errors fall back to default
        return DEFAULT_MAX_BRIEF_BYTES
    if not isinstance(data, dict):
        return DEFAULT_MAX_BRIEF_BYTES
    intake_section = data.get("intake")
    if not isinstance(intake_section, dict):
        return DEFAULT_MAX_BRIEF_BYTES
    raw = intake_section.get("max_brief_bytes")
    if not isinstance(raw, str | int | float):
        return DEFAULT_MAX_BRIEF_BYTES
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_MAX_BRIEF_BYTES
    if value <= 0:
        return DEFAULT_MAX_BRIEF_BYTES
    return value


def load_allow_cross_fs(repo_root: Path) -> bool:
    """Read ``intake.allow_cross_fs`` from ``.kittify/config.yaml`` (default False)."""
    config_path = repo_root / ".kittify" / "config.yaml"
    if not config_path.is_file():
        return False
    try:
        import yaml

        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return False
    if not isinstance(data, dict):
        return False
    intake_section = data.get("intake")
    if not isinstance(intake_section, dict):
        return False
    return bool(intake_section.get("allow_cross_fs", False))


# ---------------------------------------------------------------------------
# Path canonicalisation + symlink guard (T008)
# ---------------------------------------------------------------------------


def assert_under_root(candidate: Path, intake_root: Path) -> Path:
    """Resolve ``candidate`` and assert it lives under ``intake_root``.

    Both paths are resolved with ``strict=True`` so symlinks are
    followed before the containment check.  If ``candidate`` resolves
    outside the resolved root, :class:`IntakePathEscapeError` is raised
    *before* the file is opened.

    Returns the resolved candidate path on success.

    Raises:
        IntakeFileMissingError: when ``candidate`` does not exist.
        IntakePathEscapeError: when ``candidate`` resolves outside
            ``intake_root`` or when the root cannot be resolved.
    """
    try:
        intake_root_resolved = Path(intake_root).resolve(strict=True)
    except FileNotFoundError as exc:
        raise IntakePathEscapeError(
            candidate=Path(candidate),
            intake_root=Path(intake_root),
        ) from exc

    try:
        candidate_resolved = Path(candidate).resolve(strict=True)
    except FileNotFoundError as exc:
        # Missing != escape — surface a separate error so callers can
        # distinguish the two conditions.
        raise IntakeFileMissingError(path=Path(candidate)) from exc
    except OSError as exc:
        # Other OS errors (permission, loop) → treat as unreadable so
        # the caller still sees the underlying cause rather than a
        # generic escape error.
        raise IntakeFileUnreadableError(path=Path(candidate), cause=exc) from exc

    try:
        candidate_resolved.relative_to(intake_root_resolved)
    except ValueError as exc:
        raise IntakePathEscapeError(
            candidate=candidate_resolved,
            intake_root=intake_root_resolved,
        ) from exc
    return candidate_resolved


# ---------------------------------------------------------------------------
# Size cap (T009) + missing/corrupt distinction (T011)
# ---------------------------------------------------------------------------


def read_brief(
    path: Path,
    *,
    cap: int,
    intake_root: Path | None = None,
) -> str:
    """Read a brief file, enforcing the size cap and surfacing structured errors.

    Order of checks:

    1. If ``intake_root`` is supplied, the candidate is canonicalised
       and checked against the root *before* any I/O.
    2. ``os.stat()`` is called.  ``FileNotFoundError`` →
       :class:`IntakeFileMissingError`; any other ``OSError`` →
       :class:`IntakeFileUnreadableError`.
    3. If ``stat.st_size > cap`` → :class:`IntakeTooLargeError` raised
       before the file is opened.
    4. The file is opened, read, and decoded as UTF-8.  Read or decode
       failures → :class:`IntakeFileUnreadableError`.

    Returns the decoded text on success.
    """
    candidate = Path(path)
    if intake_root is not None:
        # Containment check first: surfaces escapes before stat().
        candidate = assert_under_root(candidate, intake_root)

    try:
        stat_result = candidate.stat()
    except FileNotFoundError as exc:
        raise IntakeFileMissingError(path=candidate) from exc
    except OSError as exc:
        raise IntakeFileUnreadableError(path=candidate, cause=exc) from exc

    size = stat_result.st_size
    if size > cap:
        raise IntakeTooLargeError(path=candidate, size=size, cap=cap)

    try:
        return candidate.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        # Race between stat and open — still missing, not corrupt.
        raise IntakeFileMissingError(path=candidate) from exc
    except OSError as exc:
        raise IntakeFileUnreadableError(path=candidate, cause=exc) from exc
    except UnicodeDecodeError as exc:
        raise IntakeFileUnreadableError(path=candidate, cause=exc) from exc


def read_stdin_capped(
    stream: IO[Any] | None,
    *,
    cap: int,
    label: str = "stdin",
) -> str:
    """Read at most ``cap + 1`` bytes from a stream and reject overflow.

    Used for STDIN intake where ``os.stat()`` cannot tell us the size.
    The implementation reads ``cap + 1`` bytes — if more arrive, we
    know the input exceeded the cap without buffering more than
    ``cap + 1`` bytes in memory.

    The ``stream`` argument is the raw bytes / text stream from which to
    read.  ``None`` raises :class:`IntakeFileUnreadableError` so callers
    do not silently swallow a missing pipe.
    """
    if stream is None:
        raise IntakeFileUnreadableError(
            path=label,
            cause=RuntimeError("stdin stream is unavailable"),
        )

    buf = stream.read(cap + 1)
    if buf is None:
        raise IntakeFileUnreadableError(
            path=label,
            cause=RuntimeError("stdin returned no bytes"),
        )

    # Normalise to bytes for the length check, then to str.
    if isinstance(buf, str):
        # `len(str)` counts code points but the cap is byte-denominated;
        # encode to be precise.
        encoded = buf.encode("utf-8")
        if len(encoded) > cap:
            raise IntakeTooLargeError(path=label, size=len(encoded), cap=cap)
        return buf

    if len(buf) > cap:
        raise IntakeTooLargeError(path=label, size=len(buf), cap=cap)
    try:
        decoded = buf.decode("utf-8")
        return str(decoded)
    except UnicodeDecodeError as exc:
        raise IntakeFileUnreadableError(path=label, cause=exc) from exc


__all__ = [
    "DEFAULT_MAX_BRIEF_BYTES",
    "assert_under_root",
    "load_allow_cross_fs",
    "load_max_brief_bytes",
    "read_brief",
    "read_stdin_capped",
]
