"""Linear-time regular expression engine with stdlib re fallback.

Drop-in replacement for ``import re`` that uses Google's RE2 engine when
available (``google-re2``).  RE2 guarantees O(n) matching time, preventing
catastrophic backtracking (ReDoS).

Usage::

    from kernel._safe_re import re

    # All stdlib re idioms continue to work:
    re.compile(r"\\d+")
    re.search(r"\\w+", text)
    isinstance(obj, re.Pattern)
    re.MULTILINE | re.DOTALL

When ``google-re2`` is not installed the module transparently falls back to
stdlib ``re``.  Install the extra to enable RE2::

    pip install "spec-kitty-cli[safe-re]"

Limitations of RE2 (not supported, falls back to stdlib ``re``)
----------------------------------------------------------------
- Lookahead/lookbehind assertions (``(?=...)``, ``(?!...)``, ``(?<=...)``, ``(?<!...)``)
- Back-references (``\\1``, ``\\g<name>``)
- Possessive quantifiers
- ``re.VERBOSE`` (``(?x)`` flag) -- RE2 does not support this syntax

For those patterns the module silently delegates to stdlib ``re``.  Call
:func:`is_re2_active` to determine which engine is in use at runtime.
"""

from __future__ import annotations

import re as _stdlib_re
import sys
import types

__all__ = ["re", "is_re2_active"]

# ── Attempt RE2 import ──────────────────────────────────────────────────────

try:
    import re2 as _re2_mod  # type: ignore[import-untyped]

    _RE2_AVAILABLE = True
except ImportError:  # pragma: no cover
    _RE2_AVAILABLE = False
    _re2_mod = None  # type: ignore[assignment]


# ── Inline-flag prefix map ───────────────────────────────────────────────────
# RE2 does not expose re.MULTILINE / re.DOTALL etc. as constants.  Instead,
# these must be expressed as inline flags prepended to the pattern string.

_FLAG_TO_INLINE: dict[int, str] = {
    _stdlib_re.IGNORECASE: "i",
    _stdlib_re.MULTILINE: "m",
    _stdlib_re.DOTALL: "s",
}

# Flags that are NOT translatable to RE2 inline flags → fall back to stdlib re
_UNSUPPORTED_FLAGS: int = _stdlib_re.VERBOSE | _stdlib_re.LOCALE


def _prepend_flags(pattern: str, flags: int) -> tuple[str, bool]:
    """Return ``(modified_pattern, needs_fallback)``.

    Prepends inline-flag modifiers that RE2 understands and signals when
    the flag set contains unsupported items so the caller can fall back to
    stdlib ``re``.
    """
    if flags & _UNSUPPORTED_FLAGS:
        return pattern, True  # cannot handle in RE2

    inline: list[str] = []
    for flag_val, letter in _FLAG_TO_INLINE.items():
        if flags & flag_val:
            inline.append(letter)

    if inline:
        prefix = "(?{})".format("".join(inline))
        pattern = prefix + pattern

    return pattern, False


def _is_pcre_only(pattern: str) -> bool:
    """Return True when the pattern contains RE2-incompatible PCRE syntax."""
    # Lookahead/lookbehind assertions
    if "(?=" in pattern or "(?!" in pattern:
        return True
    if "(?<=" in pattern or "(?<!" in pattern:
        return True
    return False


def _safe_compile(pattern: str, flags: int = 0) -> _stdlib_re.Pattern:  # type: ignore[type-arg]
    """Compile *pattern* using RE2 when safe; otherwise fall back to stdlib."""
    if not _RE2_AVAILABLE or _is_pcre_only(pattern) or flags & _UNSUPPORTED_FLAGS:
        return _stdlib_re.compile(pattern, flags)

    re2_pattern, needs_fallback = _prepend_flags(pattern, flags)
    if needs_fallback:
        return _stdlib_re.compile(pattern, flags)

    try:
        return _re2_mod.compile(re2_pattern)  # type: ignore[no-any-return]
    except Exception:  # noqa: BLE001
        # RE2 rejected the pattern (e.g. unsupported syntax) — fall back
        return _stdlib_re.compile(pattern, flags)


# ── Build a fake module that mirrors stdlib re ───────────────────────────────
# Using types.ModuleType so that re.Pattern, re.RegexFlag, re.Match, etc.
# all resolve correctly at runtime and in type checkers.

_mod = types.ModuleType("kernel._safe_re.re")
_mod.__doc__ = "RE2-backed drop-in for stdlib re (kernel._safe_re)"

# ── Type aliases forwarded from stdlib (so re.Pattern[str] etc. work) ────
_mod.Pattern = _stdlib_re.Pattern  # type: ignore[attr-defined]
_mod.Match = _stdlib_re.Match  # type: ignore[attr-defined]
_mod.RegexFlag = _stdlib_re.RegexFlag  # type: ignore[attr-defined]
_mod.error = _stdlib_re.error  # type: ignore[attr-defined]

# ── Flag constants forwarded from stdlib ──────────────────────────────────
_mod.IGNORECASE = _stdlib_re.IGNORECASE  # type: ignore[attr-defined]
_mod.I = _stdlib_re.IGNORECASE  # type: ignore[attr-defined]
_mod.MULTILINE = _stdlib_re.MULTILINE  # type: ignore[attr-defined]
_mod.M = _stdlib_re.MULTILINE  # type: ignore[attr-defined]
_mod.DOTALL = _stdlib_re.DOTALL  # type: ignore[attr-defined]
_mod.S = _stdlib_re.DOTALL  # type: ignore[attr-defined]
_mod.VERBOSE = _stdlib_re.VERBOSE  # type: ignore[attr-defined]
_mod.X = _stdlib_re.VERBOSE  # type: ignore[attr-defined]
_mod.ASCII = _stdlib_re.ASCII  # type: ignore[attr-defined]
_mod.A = _stdlib_re.ASCII  # type: ignore[attr-defined]
_mod.UNICODE = _stdlib_re.UNICODE  # type: ignore[attr-defined]
_mod.U = _stdlib_re.UNICODE  # type: ignore[attr-defined]
_mod.LOCALE = _stdlib_re.LOCALE  # type: ignore[attr-defined]
_mod.L = _stdlib_re.LOCALE  # type: ignore[attr-defined]
_mod.NOFLAG = _stdlib_re.NOFLAG  # type: ignore[attr-defined]


# ── Module-level functions ────────────────────────────────────────────────


def _compile(pattern: str, flags: int = 0) -> _stdlib_re.Pattern:  # type: ignore[type-arg]
    return _safe_compile(pattern, flags)


def _search(pattern: str, string: str, flags: int = 0) -> _stdlib_re.Match | None:  # type: ignore[type-arg]
    return _safe_compile(pattern, flags).search(string)


def _match(pattern: str, string: str, flags: int = 0) -> _stdlib_re.Match | None:  # type: ignore[type-arg]
    return _safe_compile(pattern, flags).match(string)


def _fullmatch(pattern: str, string: str, flags: int = 0) -> _stdlib_re.Match | None:  # type: ignore[type-arg]
    return _safe_compile(pattern, flags).fullmatch(string)


def _findall(pattern: str, string: str, flags: int = 0) -> list:  # type: ignore[type-arg]
    return _safe_compile(pattern, flags).findall(string)


def _finditer(pattern: str, string: str, flags: int = 0):  # type: ignore[return]
    return _safe_compile(pattern, flags).finditer(string)


def _sub(pattern: str, repl: str, string: str, count: int = 0, flags: int = 0) -> str:
    return _safe_compile(pattern, flags).sub(repl, string, count)


def _subn(pattern: str, repl: str, string: str, count: int = 0, flags: int = 0) -> tuple[str, int]:
    return _safe_compile(pattern, flags).subn(repl, string, count)


def _split(pattern: str, string: str, maxsplit: int = 0, flags: int = 0) -> list:  # type: ignore[type-arg]
    return _safe_compile(pattern, flags).split(string, maxsplit)


def _escape(pattern: str) -> str:
    return _stdlib_re.escape(pattern)


def _purge() -> None:
    if _re2_mod is not None:  # pragma: no cover
        try:
            _re2_mod.purge()
        except AttributeError:
            pass
    _stdlib_re.purge()


_mod.compile = _compile  # type: ignore[attr-defined]
_mod.search = _search  # type: ignore[attr-defined]
_mod.match = _match  # type: ignore[attr-defined]
_mod.fullmatch = _fullmatch  # type: ignore[attr-defined]
_mod.findall = _findall  # type: ignore[attr-defined]
_mod.finditer = _finditer  # type: ignore[attr-defined]
_mod.sub = _sub  # type: ignore[attr-defined]
_mod.subn = _subn  # type: ignore[attr-defined]
_mod.split = _split  # type: ignore[attr-defined]
_mod.escape = _escape  # type: ignore[attr-defined]
_mod.purge = _purge  # type: ignore[attr-defined]

# Register in sys.modules so `import kernel._safe_re.re` also works
sys.modules["kernel._safe_re.re"] = _mod

# ── Public export ────────────────────────────────────────────────────────────

#: Drop-in replacement for the ``re`` module.  Use as::
#:
#:     from kernel._safe_re import re
re = _mod


def is_re2_active() -> bool:
    """Return True when the RE2 engine is active (``google-re2`` installed)."""
    return _RE2_AVAILABLE
