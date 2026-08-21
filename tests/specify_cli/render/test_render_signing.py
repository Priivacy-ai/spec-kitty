"""Tests for the D2 signed renderer envelope (specify_cli.render.signing).

Fixture rows map to m1-contract-drafts/D2.md §4 (matrix IDs are noted per
test). Covers WP02: renderer-version (D16), cache-key (D17).

"Signed" = deterministic SHA-256 content digest over canonical bytes, not a
cryptographic keypair signature (D2.md §6 decision 2).
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.render import (
    RENDERER_CONTRACT_VERSION,
    RenderedDocument,
    render_markdown,
    sign_rendered_document,
)


def _rendered(tmp_path: Path, source: str) -> tuple[RenderedDocument, str]:
    return render_markdown(source, asset_root=tmp_path), source


# --- D16: determinism + sensitivity to source and version -------------------


def test_d16_same_source_same_version_yields_identical_digest(tmp_path: Path) -> None:
    doc, source = _rendered(tmp_path, "# Title\n\nHello world.\n")
    first = sign_rendered_document(doc, source)
    second = sign_rendered_document(doc, source)
    assert first.artifact_digest == second.artifact_digest
    assert first.source_digest == second.source_digest
    assert first.artifact_digest.startswith("sha256:")
    assert first.source_digest.startswith("sha256:")


def test_d16_source_change_changes_both_digests(tmp_path: Path) -> None:
    doc_a, source_a = _rendered(tmp_path, "Hello world.\n")
    doc_b, source_b = _rendered(tmp_path, "Hello world!\n")  # one character different
    signed_a = sign_rendered_document(doc_a, source_a)
    signed_b = sign_rendered_document(doc_b, source_b)
    assert signed_a.source_digest != signed_b.source_digest
    assert signed_a.artifact_digest != signed_b.artifact_digest


def test_d16_version_change_changes_artifact_digest_for_identical_source(tmp_path: Path) -> None:
    doc, source = _rendered(tmp_path, "Hello world.\n")
    real_signed = sign_rendered_document(doc, source)

    # Simulate a grammar/version bump: identical html+source, different
    # renderer_contract_version. artifact_digest must differ even though
    # source_digest (a pure function of `source`) does not.
    bumped_doc = RenderedDocument(html=doc.html, warnings=doc.warnings, renderer_contract_version="1.1.0")
    bumped_signed = sign_rendered_document(bumped_doc, source)

    assert bumped_signed.source_digest == real_signed.source_digest
    assert bumped_signed.artifact_digest != real_signed.artifact_digest


def test_d16_signed_artifact_carries_the_document_version(tmp_path: Path) -> None:
    doc, source = _rendered(tmp_path, "Hello.\n")
    signed = sign_rendered_document(doc, source)
    assert signed.renderer_contract_version == RENDERER_CONTRACT_VERSION
    assert signed.document is doc


# --- D17: cache-key — the one string D5's cache key names -------------------


def test_d17_renderer_contract_version_pin() -> None:
    # Pin test (D2.md §4 row D17, same idiom as F1's EXPECTED_PAYLOAD_IDS):
    # bumped only with a deliberate contract-change commit, since D5's
    # cache key names this exact string as its `renderer` dimension.
    assert RENDERER_CONTRACT_VERSION == "1.0.0"


def test_d17_signed_artifact_is_the_renderer_cache_key_source(tmp_path: Path) -> None:
    doc, source = _rendered(tmp_path, "content\n")
    signed = sign_rendered_document(doc, source)
    # D5 (spec-kitty-saas, out of D2's repo_scope) keys its cache on exactly
    # this one string — D2 owns the value, D5 owns using it as a cache key.
    assert signed.renderer_contract_version == RENDERER_CONTRACT_VERSION
    assert isinstance(signed.renderer_contract_version, str)
