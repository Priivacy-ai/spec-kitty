"""Common Docs retrieval index — packaged schema + query store.

Public surface for the ``docs query`` CLI (mission ``common-docs-query``):
the ``DocsQueryEntry``/``Anchor`` schema, the deterministic render/parse pair,
the ``IndexDrift`` comparator, and the in-memory ``DocsIndexStore``. See
``index_model`` for the full module docstring on the packaging split — this
package deliberately imports nothing from ``scripts`` so the installed CLI
can load it (the build-tooling generator lives in ``scripts/docs/docs_index.py``
and imports these symbols back down).
"""

from __future__ import annotations

from .index_model import (
    DEFAULT_INDEX_PATH,
    Anchor,
    DocsIndexStore,
    DocsQueryEntry,
    IndexDrift,
    compare_index,
    parse_index,
    render_index,
)

__all__ = [
    "DEFAULT_INDEX_PATH",
    "Anchor",
    "DocsIndexStore",
    "DocsQueryEntry",
    "IndexDrift",
    "compare_index",
    "parse_index",
    "render_index",
]
