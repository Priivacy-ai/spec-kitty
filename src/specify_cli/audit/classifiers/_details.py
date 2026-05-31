"""Deterministic audit finding detail helpers."""

from __future__ import annotations

import re

_POSIX_ABSOLUTE_PATH_RE = re.compile(
    r"(?<![\w:/])/(?:[^/:\r\n'\"<>]+/)[^:\r\n'\"<>]*"
)
_WINDOWS_ABSOLUTE_PATH_RE = re.compile(
    r"(?i)\b[A-Z]:\\[^\r\n'\"<>|]*"
)
_WINDOWS_UNC_PATH_RE = re.compile(
    r"\\\\[^\\\r\n'\"<>|]+\\[^\r\n'\"<>|]*"
)


def format_exception_detail(exc: Exception) -> str:
    """Return exception detail with OSError filename data removed."""
    if isinstance(exc, OSError):
        return _format_os_error_detail(exc)
    return str(exc)


def _format_os_error_detail(exc: OSError) -> str:
    exc_type = type(exc).__name__
    errno = getattr(exc, "errno", None)
    strerror = getattr(exc, "strerror", None)
    if strerror:
        strerror = _sanitize_run_varying_paths(strerror)

    if errno is not None and strerror:
        return f"{exc_type}: [Errno {errno}] {strerror}"
    if strerror:
        return f"{exc_type}: {strerror}"
    if len(exc.args) == 1 and isinstance(exc.args[0], str) and exc.args[0]:
        return f"{exc_type}: {_sanitize_run_varying_paths(exc.args[0])}"

    return exc_type


def _sanitize_run_varying_paths(text: str) -> str:
    text = _WINDOWS_UNC_PATH_RE.sub("<path>", text)
    text = _WINDOWS_ABSOLUTE_PATH_RE.sub("<path>", text)
    return _POSIX_ABSOLUTE_PATH_RE.sub("<path>", text)
