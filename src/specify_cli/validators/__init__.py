"""Validation helpers for Spec Kitty missions.

This package hosts mission-specific validators that keep artifacts such
as CSV trackers and path conventions consistent. Modules included:

- ``research`` – citation + bibliography validation for research mission
- ``paths`` – (placeholder) path convention validation shared by missions
- ``doctrine_curation`` – import candidate validation for doctrine curation
"""

from __future__ import annotations

from . import doctrine_curation, paths, research

__all__ = ["paths", "research", "doctrine_curation"]
