"""Release-channel preference — the single authority for the rc opt-in (T021).

Consumer slice of the pre-release/rc release channel (mission
``operator-config-ergonomics-01M04YK8``, contract C-CHN-1..3). CI rc-cadence
and publication are out of scope here (tracked separately in #3047); this
module owns only the operator-facing "am I opted into rc's?" read.

``SPEC_KITTY_PRERELEASE`` is a default-OFF flag: with it unset (the default),
every "latest version" surface in the CLI reports the latest **stable**
release only, never a release candidate. Since WP02's ``.kitty.env`` loader
seeds the file into ``os.environ`` before any command body runs, this module
never reads the file itself — just the process environment, mirroring the
single-read style used elsewhere in this codebase (e.g. ``core/env.py``'s
``is_interactive``).
"""

from __future__ import annotations

import os

from specify_cli.core.env import is_truthy

__all__ = ["prerelease_enabled"]

_PRERELEASE_ENV_VAR = "SPEC_KITTY_PRERELEASE"


def prerelease_enabled() -> bool:
    """Return True iff the operator opted into the pre-release (rc) channel.

    Reads ``SPEC_KITTY_PRERELEASE`` via :func:`specify_cli.core.env.is_truthy`
    (default OFF — unset, empty, or any non-truthy token all resolve to
    ``False``). Callers should call this **once** per invocation and thread
    the resulting bool down through the "latest version" call graph rather
    than re-reading the environment at each site.
    """
    return is_truthy(os.environ.get(_PRERELEASE_ENV_VAR))
