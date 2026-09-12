"""DRG writer registry — derived, enumerable inventory of every graph writer.

See :mod:`specify_cli.drg_writers.registry` for the three writer shapes
(``MappingWriter`` / ``DocumentWriter`` / ``ModelBridge``) and the ``Final``
tuples that enumerate their members.
"""

from __future__ import annotations

from specify_cli.drg_writers.registry import (
    DOCUMENT_WRITERS,
    MAPPING_WRITERS,
    MODEL_BRIDGES,
    DocumentWriter,
    MappingWriter,
    ModelBridge,
)

__all__ = [
    "DOCUMENT_WRITERS",
    "MAPPING_WRITERS",
    "MODEL_BRIDGES",
    "DocumentWriter",
    "MappingWriter",
    "ModelBridge",
]
