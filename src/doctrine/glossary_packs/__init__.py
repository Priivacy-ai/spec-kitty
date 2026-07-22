"""
Glossary packs domain model - public API.

This package provides the ``GlossaryPack`` / ``GlossaryTerm`` domain entities
and ``GlossaryPackRepository`` for loading, querying, and (per
``contracts/pack-schema.md`` §6) migrating canonical Spec Kitty terminology as
static doctrine assets. It deliberately has no import-time coupling to the
retiring runtime ``glossary`` package (C-002); see
``tests/architectural/test_glossary_pack_boundary.py``.
"""

from doctrine.glossary_packs.models import GlossaryPack, GlossaryTerm
from doctrine.glossary_packs.repository import GlossaryPackRepository

__all__ = [
    "GlossaryPack",
    "GlossaryPackRepository",
    "GlossaryTerm",
]
