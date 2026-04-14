"""Validation helpers for Spec Kitty missions.

This package hosts mission-specific validators that keep artifacts such
as CSV trackers and path conventions consistent. Modules included:

- ``research`` – citation + bibliography validation for research mission
- ``paths`` – (placeholder) path convention validation shared by missions
"""

from __future__ import annotations

from . import paths, research

__all__ = ["paths", "research"]
