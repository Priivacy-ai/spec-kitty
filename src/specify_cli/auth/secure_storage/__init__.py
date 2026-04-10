"""Pluggable secure storage backends for the spec-kitty auth subsystem.

Public entry point: :class:`SecureStorage`. Use
``SecureStorage.from_environment()`` to obtain the best backend available on
the current platform.
"""

from __future__ import annotations

from .abstract import SecureStorage

__all__ = ["SecureStorage"]
