"""D2 signed narrow renderer contract (specify_cli.render).

One Python module that converts markdown text into a deliberately narrow,
self-contained HTML subset, plus the content-addressed signing/versioning
envelope that makes its output a citable artifact
(m1-contract-drafts/D2.md §3.1-3.3). Pure functions only: no service, no
daemon, no persisted state.
"""

from __future__ import annotations

from .engine import (
    RENDERER_CONTRACT_VERSION,
    NarrowRenderError,
    RenderedDocument,
    render_markdown,
)
from .signing import SignedRenderedArtifact, sign_rendered_document

__all__ = [
    "RENDERER_CONTRACT_VERSION",
    "NarrowRenderError",
    "RenderedDocument",
    "SignedRenderedArtifact",
    "render_markdown",
    "sign_rendered_document",
]
