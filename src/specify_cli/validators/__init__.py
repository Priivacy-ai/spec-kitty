"""Validation helpers for Spec Kitty missions.

This package hosts mission-specific validators that keep artifacts such
as CSV trackers and path conventions consistent. Modules included:

- ``documentation`` – documentation mission state and gap analysis validation
- ``research`` – citation + bibliography validation for research mission
- ``paths`` – (placeholder) path convention validation shared by missions
"""

from __future__ import annotations

from . import documentation, paths, research

__all__ = ["documentation", "paths", "research"]
