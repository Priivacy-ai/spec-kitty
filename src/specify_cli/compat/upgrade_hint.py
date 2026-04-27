"""Upgrade-hint catalog for the upgrade-nag planner.

Public surface
--------------
UpgradeHint      -- frozen dataclass per data-model §1.8.
build_upgrade_hint -- factory function; one call per InstallMethod value.

Security properties enforced here
-----------------------------------
CHK028  ``command`` is sanitised against ``^[A-Za-z0-9 .\\-+_/=:]{1,128}$``
        at dataclass construction time; ANSI escapes and shell metacharacters
        are rejected.
CHK031  SOURCE and UNKNOWN hints carry ``command=None`` (a note instead),
        so they are never accidentally executed as shell commands.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from specify_cli.compat._detect.install_method import InstallMethod


# ---------------------------------------------------------------------------
# Validation regex (CHK028)
# ---------------------------------------------------------------------------

_COMMAND_RE = re.compile(r"^[A-Za-z0-9 .\-+_/=:]{1,128}$")


# ---------------------------------------------------------------------------
# UpgradeHint dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UpgradeHint:
    """A sanitised, copy-pasteable (or manual) upgrade hint for a given install method.

    Exactly one of ``command`` or ``note`` is non-None (invariant enforced in
    ``__post_init__``).

    Attributes:
        install_method: The detected install method that produced this hint.
        command: A short shell command string the user can copy-paste to upgrade.
            ``None`` for install methods where a single runnable command is
            inappropriate (SOURCE, SYSTEM_PACKAGE, UNKNOWN).
        note: A human-readable multi-line instruction string.  ``None`` when
            ``command`` is set.
    """

    install_method: InstallMethod
    command: str | None
    note: str | None

    def __post_init__(self) -> None:
        """Validate the invariant and sanitise *command* if present."""
        if (self.command is None) == (self.note is None):
            raise ValueError(f"UpgradeHint: exactly one of 'command' or 'note' must be non-None; got command={self.command!r}, note={self.note!r}")
        if self.command is not None and not _COMMAND_RE.match(self.command):
            raise ValueError(
                f"UpgradeHint.command contains disallowed characters or is out of range: "
                f"{self.command!r}. "
                "Only [A-Za-z0-9 .\\-+_/=:] (1-128 chars) is permitted (CHK028)."
            )


# ---------------------------------------------------------------------------
# Static hint table
# ---------------------------------------------------------------------------

# Each entry: (command_or_None, note_or_None).
# Validated at module load time (any bad value raises ValueError immediately).
_HINT_TABLE: dict[InstallMethod, tuple[str | None, str | None]] = {
    InstallMethod.PIPX: (
        "pipx upgrade spec-kitty-cli",
        None,
    ),
    InstallMethod.PIP_USER: (
        "pip install --user --upgrade spec-kitty-cli",
        None,
    ),
    InstallMethod.PIP_SYSTEM: (
        "pip install --upgrade spec-kitty-cli",
        None,
    ),
    InstallMethod.BREW: (
        "brew upgrade spec-kitty-cli",
        None,
    ),
    InstallMethod.SYSTEM_PACKAGE: (
        None,
        ("Use your system package manager (apt/dnf/pacman/yum/zypper) to upgrade spec-kitty-cli."),
    ),
    InstallMethod.SOURCE: (
        None,
        "Rebuild from source: pip install -e . (or your normal dev workflow).",
    ),
    InstallMethod.UNKNOWN: (
        None,
        (
            "Your install method could not be detected automatically. "
            "Upgrade Spec Kitty using the same method you used to install it. "
            "See https://spec-kitty.dev/docs/how-to/install-and-upgrade for guidance."
        ),
    ),
}

# Eagerly validate all table entries at import time so misconfiguration is
# caught before any runtime call.
for _method, (_cmd, _note) in _HINT_TABLE.items():
    UpgradeHint(install_method=_method, command=_cmd, note=_note)


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def build_upgrade_hint(
    install_method: InstallMethod,
    *,
    package: str = "spec-kitty-cli",  # noqa: ARG001  (reserved for future parametrisation)
) -> UpgradeHint:
    """Return the :class:`UpgradeHint` for *install_method*.

    The returned hint satisfies the invariant that exactly one of ``command``
    or ``note`` is non-None.

    Args:
        install_method: The detected :class:`InstallMethod`.
        package: Reserved for future parametrisation (currently unused; the
            table is keyed solely on *install_method*).

    Returns:
        A :class:`UpgradeHint` from the static table.
    """
    command, note = _HINT_TABLE[install_method]
    return UpgradeHint(install_method=install_method, command=command, note=note)
