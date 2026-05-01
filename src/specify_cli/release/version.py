"""Version-string manipulation for spec-kitty release preparation.

All functions are pure: no I/O, no network calls, no side effects.
"""

from __future__ import annotations

import re
from typing import Literal

ReleaseChannel = Literal["alpha", "beta", "stable"]

# Matches PEP 440 alpha/beta pre-release suffixes.
# Group 1: base version (e.g., "3.1.0")
# Group 2: pre-release type ("a" or "b")
# Group 3: pre-release number (e.g., "7")
_PRE_RE = re.compile(r"^(\d+\.\d+\.\d+)(a|b)(\d+)$")

# Matches a plain stable version (no pre-release suffix).
# Group 1: major, Group 2: minor, Group 3: patch
_STABLE_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def propose_version(current: str, channel: ReleaseChannel) -> str:
    """Compute the next version string per release channel.

    Bump-level rules:
      - alpha: increments the alpha number.
          3.1.0a7  -> 3.1.0a8
      - beta: starts a fresh beta-1 line if current is an alpha release;
          otherwise increments the beta number.
          3.1.0a7  -> 3.1.0b1
          3.1.0b1  -> 3.1.0b2
      - stable: drops the pre-release suffix if current is alpha or beta;
          otherwise always proposes a patch bump.
          3.1.0a7  -> 3.1.0
          3.1.0b3  -> 3.1.0
          3.1.0    -> 3.1.1

    Stable-to-stable always proposes a patch bump. Minor or major bumps
    require manual editing of pyproject.toml before running release prep.
    This matches spec-kitty's actual release cadence (mostly alpha increments
    and patches); a ``--bump-level`` parameter would be dead weight 99% of
    the time and is intentionally omitted.

    Raises:
      ValueError: if ``current`` cannot be parsed as a supported version form,
          or if ``current`` has an unsupported pre-release type (e.g., ``rc``,
          ``.dev``). Rather than guessing, we raise clearly.
    """
    pre_match = _PRE_RE.match(current)
    stable_match = _STABLE_RE.match(current)

    if pre_match is None and stable_match is None:
        raise ValueError(
            f"Cannot parse version {current!r}. "
            "Expected 'X.Y.Za<N>', 'X.Y.Zb<N>', or 'X.Y.Z'. "
            "If current version uses 'rc' or '.dev', edit pyproject.toml manually "
            "before running release prep."
        )

    if channel == "alpha":
        if pre_match and pre_match.group(2) == "a":
            # Increment alpha number: 3.1.0a7 -> 3.1.0a8
            base = pre_match.group(1)
            n = int(pre_match.group(3))
            return f"{base}a{n + 1}"
        if stable_match:
            # Stable -> alpha: start alpha-1 on the current stable base
            return f"{current}a1"
        if pre_match and pre_match.group(2) == "b":
            # Beta -> alpha: not a supported promotion direction.
            raise ValueError(f"Cannot promote a beta release ({current!r}) to alpha. Beta is ahead of alpha in the release sequence.")

    if channel == "beta":
        if pre_match and pre_match.group(2) == "a":
            # Alpha -> beta-1: 3.1.0a7 -> 3.1.0b1
            base = pre_match.group(1)
            return f"{base}b1"
        if pre_match and pre_match.group(2) == "b":
            # Increment beta number: 3.1.0b1 -> 3.1.0b2
            base = pre_match.group(1)
            n = int(pre_match.group(3))
            return f"{base}b{n + 1}"
        if stable_match:
            # Stable -> beta: start beta-1 on the current stable base
            return f"{current}b1"

    if channel == "stable":
        if pre_match:
            # Drop pre-release suffix: 3.1.0a7 -> 3.1.0, 3.1.0b3 -> 3.1.0
            return pre_match.group(1)
        if stable_match:
            # Stable -> stable: always patch bump
            major = int(stable_match.group(1))
            minor = int(stable_match.group(2))
            patch = int(stable_match.group(3))
            return f"{major}.{minor}.{patch + 1}"

    # Should never reach here for valid inputs
    raise ValueError(  # pragma: no cover
        f"Unhandled combination: current={current!r}, channel={channel!r}"
    )
