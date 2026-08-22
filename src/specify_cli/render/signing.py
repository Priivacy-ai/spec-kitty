"""Content-addressed signing envelope for the D2 narrow renderer.

"Signed" here means a deterministic SHA-256 content digest over canonical
bytes, not a cryptographic keypair signature — the same content-addressing
idiom already used by ``docs/CONTROL_PROTOCOL.md``'s bundle hashing and by
F1's ``support_matrix_digest()`` (m1-contract-drafts/D2.md §3.3, §6 decision
2). It gives a caller (D1) a stable identifier to prove which exact markdown
source produced a given rendered artifact, and gives D5 the one string
(``renderer_contract_version``) its cache key names.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .engine import RenderedDocument

__all__ = ["SignedRenderedArtifact", "sign_rendered_document"]


@dataclass(frozen=True)
class SignedRenderedArtifact:
    """A :class:`RenderedDocument` plus its content-addressed digests."""

    document: RenderedDocument
    source_digest: str  # "sha256:<hex>" over the exact markdown source bytes
    artifact_digest: str  # "sha256:<hex>" over canonical (html, renderer_contract_version, source_digest)
    renderer_contract_version: str


def _sha256_hex(data: bytes) -> str:
    """Content-addressing digest for the signed artifact envelope (not a charter-hash reimplementation)."""
    return hashlib.sha256(data).hexdigest()  # noqa: TID251 - production raw SHA-256 owner


def sign_rendered_document(doc: RenderedDocument, source: str) -> SignedRenderedArtifact:
    """Compute the deterministic content digests for ``doc``/``source``.

    Equal ``source`` bytes always yield an equal ``source_digest``. Equal
    ``(html, renderer_contract_version, source_digest)`` always yields an
    equal ``artifact_digest`` — across separate process runs, since the
    canonical encoding below has no reference to memory addresses, wall
    clocks, or dict/set iteration order (D2.md §4 row D16).
    """
    source_digest = f"sha256:{_sha256_hex(source.encode('utf-8'))}"
    canonical = json.dumps(
        {
            "html": doc.html,
            "renderer_contract_version": doc.renderer_contract_version,
            "source_digest": source_digest,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    artifact_digest = f"sha256:{_sha256_hex(canonical.encode('utf-8'))}"
    return SignedRenderedArtifact(
        document=doc,
        source_digest=source_digest,
        artifact_digest=artifact_digest,
        renderer_contract_version=doc.renderer_contract_version,
    )
