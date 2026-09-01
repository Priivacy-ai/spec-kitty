"""Kernel env-var / tilde expansion seam -- the single ``${VAR}``/``$VAR`` +
``~`` expansion authority at the base of the dependency stack (D2 / PPC-2,
PPC-3; contracts/env-expander.md C-EXP-1..5).

One pure transform, three call shapes
--------------------------------------
:func:`expand_raw_template` is the pure, NEVER-raising transform: expand
``${VAR}``/``$VAR`` tokens, then ``~``. When ``environ`` is ``None`` this is
byte-identical to the pre-existing ``os.path.expanduser(os.path.expandvars(raw))``
idiom (real process environment, real platform ``expandvars``/``expanduser``
semantics -- including Windows' ``%VAR%`` form, which the shared ``$``-token
detector below does not itself recognise but ``os.path.expandvars`` still
honours). When ``environ`` is supplied, substitution is sourced from that
mapping instead, via the shared ``${VAR}``/``$VAR`` detector -- ``%VAR%`` is
not honoured in that branch, since it sits outside the detector's ASCII
``$``-token scope.

:func:`find_unresolved_token` / :func:`find_empty_env_token` are the shared
detection primitives (migrated from ``charter.offering.drg.org_pack_config``, T002):
the first finds a surviving ``${VAR}``/``$VAR`` token after expansion; the
second finds a token whose variable is set-but-blank (a case
``expandvars``/``expandraw`` consumes silently, leaving no residue for the
first detector to catch).

:func:`expand_env_template` composes the pure transform with the shared
detector into the two RAISING policies:

* ``inject_defaults=True`` -- a surviving ``${SPEC_KITTY_*}``/``$SPEC_KITTY_*``
  token registered in :data:`_DEFAULT_INJECTORS` (currently just
  ``SPEC_KITTY_PACKS_ROOT``) is filled in from the registry; any other
  surviving token still raises.
* ``inject_defaults=False`` -- ANY surviving token raises
  :class:`UnresolvedEnvTokenError` naming the token.

Why a third, non-raising shape is exposed at all
-------------------------------------------------
``charter.offering.drg.org_pack_config._expand_path_template`` carries its OWN
structured exception (``OrgPackEnvVarUnsetError``) and its own "set but
blank" fail-loud guard, both byte-preserved across this WP (T004). Routing
that caller through the RAISING ``expand_env_template(..., inject_defaults=False)``
would mean the kernel raises ``UnresolvedEnvTokenError`` before the caller
ever gets a chance to construct its own exception type -- changing the
exception TYPE the caller's contract promises. So ``org_pack_config``
delegates the *pure transform and detection primitives only*
(:func:`expand_raw_template`, :func:`find_unresolved_token`,
:func:`find_empty_env_token`) and keeps constructing
``OrgPackEnvVarUnsetError`` itself. This is the documented escape hatch from
the WP01 task spec ("expose the shared token-detector separately so
org_pack_config reconstructs its exact errors") -- one detector/transform
implementation shared by both the raising and non-raising call shapes,
instead of a second regex fork living in ``org_pack_config.py``.

Stdlib + :mod:`kernel.paths` only -- no upward import (arch-gated by
``tests/architectural/test_kernel_env_expand_no_upward_import.py``, C-EXP-5).
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable, Mapping

from kernel.paths import get_packs_root_default

__all__ = [
    "UnresolvedEnvTokenError",
    "expand_env_template",
    "expand_raw_template",
    "find_empty_env_token",
    "find_unresolved_token",
]

#: ``re.ASCII`` is required, not cosmetic: ``os.path.expandvars`` (via
#: ``posixpath``/``ntpath``) recognizes only ASCII variable-name characters
#: internally. Without this flag ``\w`` would match Unicode word characters
#: too, so this detector could report a longer/different token than the one
#: ``expandvars`` actually considered for non-ASCII input. The single shared
#: detector (migrated here from ``charter.offering.drg.org_pack_config``, T002) --
#: downstream callers import :func:`find_unresolved_token` /
#: :func:`find_empty_env_token` rather than re-compiling this pattern.
_ENV_VAR_TOKEN_RE = re.compile(r"\$\{[^}]+\}|\$[A-Za-z_]\w*", re.ASCII)


class UnresolvedEnvTokenError(ValueError):
    """Raised when a ``${VAR}``/``$VAR`` token survives expansion.

    Only raised by :func:`expand_env_template`'s two raising policies; never
    by :func:`expand_raw_template` (the pure, non-raising transform).
    """

    def __init__(self, token: str, raw: str) -> None:
        self.token = token
        self.raw = raw
        super().__init__(
            f"Unresolved environment variable token {token!r} in template {raw!r}."
        )


def _token_var_name(token: str) -> str:
    """Return the bare variable name inside a ``${VAR}``/``$VAR`` token."""
    return token[2:-1] if token.startswith("${") else token[1:]


def find_unresolved_token(expanded: str) -> str | None:
    """Return the first surviving ``${VAR}``/``$VAR`` token in ``expanded``, if any."""
    match = _ENV_VAR_TOKEN_RE.search(expanded)
    return match.group(0) if match else None


def find_empty_env_token(raw: str, environ: Mapping[str, str] | None = None) -> str | None:
    """Return the first token in ``raw`` whose variable is set to the empty string.

    ``os.path.expandvars`` silently consumes a token whose variable is set to
    ``""``, leaving no ``$``-residue for :func:`find_unresolved_token` to
    catch -- this is the companion "set but blank" check for that case,
    checked against ``raw`` (not the expanded output).
    """
    env = os.environ if environ is None else environ
    for match in _ENV_VAR_TOKEN_RE.finditer(raw):
        token = match.group(0)
        if env.get(_token_var_name(token)) == "":
            return token
    return None


def _substitute_tokens(raw: str, environ: Mapping[str, str]) -> str:
    """Replace every ``${VAR}``/``$VAR`` token found in ``environ``; leave the rest verbatim."""

    def _replace(match: re.Match[str]) -> str:
        token = match.group(0)
        value = environ.get(_token_var_name(token))
        return token if value is None else value

    return _ENV_VAR_TOKEN_RE.sub(_replace, raw)


def expand_raw_template(raw: str, environ: Mapping[str, str] | None = None) -> str:
    """Pure ``${VAR}``/``$VAR`` + ``~`` expansion. Never raises.

    When ``environ`` is ``None`` (the default, and the only mode
    ``charter.offering.drg.org_pack_config`` uses -- T004) this delegates directly to
    ``os.path.expanduser(os.path.expandvars(raw))``: the real process
    environment and the real platform-specific expansion semantics, byte-
    identical to the pre-WP01 ``org_pack_config._expand_path_template`` body.
    When ``environ`` is supplied, ``${VAR}``/``$VAR`` substitution is sourced
    from that mapping via the shared detector instead of the real process
    environment (for callers -- e.g. a future ``.kitty.env``-aware loader --
    that need to expand against a merged/synthetic environment without
    mutating ``os.environ``); tilde expansion still uses the real
    ``os.path.expanduser`` in both branches.
    """
    if environ is None:
        return os.path.expanduser(os.path.expandvars(raw))
    return os.path.expanduser(_substitute_tokens(raw, environ))


#: Default-value registry for :func:`expand_env_template`'s ``inject_defaults=True``
#: policy (T003). Deliberately narrow: only ``SPEC_KITTY_PACKS_ROOT`` has a
#: well-defined kernel-floor default today. ``CONFIG_HOME``/locator defaults
#: are a caller concern (a later WP), not this module's.
_DEFAULT_INJECTORS: dict[str, Callable[[], str]] = {
    "SPEC_KITTY_PACKS_ROOT": lambda: str(get_packs_root_default()),
}


def expand_env_template(
    raw: str,
    *,
    inject_defaults: bool,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Expand ``raw``, then apply exactly one of two token policies.

    1. :func:`expand_raw_template` (pure transform, see its docstring for the
       ``environ`` semantics).
    2. If a ``${VAR}``/``$VAR`` token survives that transform:

       * ``inject_defaults=True`` -- filled in from :data:`_DEFAULT_INJECTORS`
         when the variable name is registered; any other surviving token
         still raises.
       * ``inject_defaults=False`` -- always raises.

    Raises:
        UnresolvedEnvTokenError: when a token survives and either
            ``inject_defaults=False`` or the surviving token has no
            registered default.
    """
    expanded = expand_raw_template(raw, environ)
    token = find_unresolved_token(expanded)
    if token is None:
        return expanded

    if inject_defaults:
        injector = _DEFAULT_INJECTORS.get(_token_var_name(token))
        if injector is not None:
            return expanded.replace(token, injector(), 1)

    raise UnresolvedEnvTokenError(token, raw)
