"""Deterministic audit finding detail helpers."""

from __future__ import annotations


def format_exception_detail(exc: Exception) -> str:
    """Return exception detail with OSError filename data removed."""
    if isinstance(exc, OSError):
        return _format_os_error_detail(exc)
    return str(exc)


def _format_os_error_detail(exc: OSError) -> str:
    exc_type = type(exc).__name__
    errno = getattr(exc, "errno", None)
    strerror = getattr(exc, "strerror", None)

    if errno is not None and strerror:
        return f"{exc_type}: [Errno {errno}] {strerror}"
    if strerror:
        return f"{exc_type}: {strerror}"

    return exc_type
