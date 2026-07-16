"""Tests for ``charter.bundle.compute_bundle_content_hash`` (WP01 / T007).

New-symbol unit coverage for the PURE, UNWIRED content-identity hash helper
(synthesized-drg-stale-refresh mission, C-005). This helper has zero
production callers as of WP01 — it lands here so WP02 (writers) and WP03
(reader) share exactly one hashing recipe instead of hand-copying it.

Covers:
- happy path: deterministic, mtime-agnostic ``"sha256:..."`` digest
- fail-safe ``None`` returns: missing charter dir, missing single file
- **C1**: non-UTF-8 file → ``None`` (proves the ``UnicodeDecodeError`` arm is
  caught — this test fails with an uncaught exception if the implementation
  only catches ``OSError``)
- per-file BOM/CRLF independence (guards the per-file-hashing rationale)
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from charter.bundle import BUNDLE_CONTENT_HASH_FILES, compute_bundle_content_hash

pytestmark = [pytest.mark.unit]


_GOVERNANCE = "governance:\n  rules: []\n"
_DIRECTIVES = "directives: []\n"
_REFERENCES = "references: []\n"
_METADATA = "metadata:\n  version: 1\n"

_CONTENTS: dict[str, str] = {
    "governance.yaml": _GOVERNANCE,
    "directives.yaml": _DIRECTIVES,
    "references.yaml": _REFERENCES,
    "metadata.yaml": _METADATA,
}


def _seed_bundle(repo_root: Path, contents: dict[str, str] | None = None) -> Path:
    """Write all four bundle files under ``repo_root/.kittify/charter/``."""
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    for name, text in (contents or _CONTENTS).items():
        (charter_dir / name).write_text(text, encoding="utf-8")
    return charter_dir


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_happy_path_returns_sha256_prefixed_digest(tmp_path: Path) -> None:
    """All four files present → a well-formed ``"sha256:..."`` digest."""
    _seed_bundle(tmp_path)

    result = compute_bundle_content_hash(tmp_path)

    assert result is not None
    assert result.startswith("sha256:")
    # 64 hex chars after the prefix.
    assert len(result) == len("sha256:") + 64


def test_deterministic_for_fixed_content(tmp_path: Path) -> None:
    """Calling twice on unchanged content yields the identical digest."""
    _seed_bundle(tmp_path)

    first = compute_bundle_content_hash(tmp_path)
    second = compute_bundle_content_hash(tmp_path)

    assert first == second


def test_mtime_agnostic(tmp_path: Path) -> None:
    """Touching a file's mtime without changing its content does not change
    the digest — the comparison is content-identity, not timestamp-based."""
    charter_dir = _seed_bundle(tmp_path)

    before = compute_bundle_content_hash(tmp_path)

    # Touch mtime forward without altering bytes.
    time.sleep(0.01)
    target = charter_dir / "metadata.yaml"
    target.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")

    after = compute_bundle_content_hash(tmp_path)

    assert before == after


# ---------------------------------------------------------------------------
# Fail-safe None cases
# ---------------------------------------------------------------------------


def test_missing_charter_dir_returns_none(tmp_path: Path) -> None:
    """``.kittify/charter/`` entirely absent → ``None`` (never raises)."""
    result = compute_bundle_content_hash(tmp_path)

    assert result is None


@pytest.mark.parametrize("omit", list(BUNDLE_CONTENT_HASH_FILES))
def test_missing_single_file_returns_none(tmp_path: Path, omit: str) -> None:
    """Omitting exactly one of the four files → ``None``, regardless of which."""
    contents = {name: text for name, text in _CONTENTS.items() if name != omit}
    _seed_bundle(tmp_path, contents)

    result = compute_bundle_content_hash(tmp_path)

    assert result is None


def test_non_utf8_file_returns_none_not_raises(tmp_path: Path) -> None:
    """C1 fail-safe: a non-UTF-8 bundle file must yield ``None``, not crash.

    ``Path.read_text(encoding="utf-8")`` on invalid UTF-8 bytes raises
    ``UnicodeDecodeError`` — a ``ValueError`` subclass, NOT an ``OSError``.
    If the implementation's read guard only catches ``OSError`` this test
    fails with an uncaught ``UnicodeDecodeError`` instead of asserting
    ``None``.
    """
    _seed_bundle(tmp_path)
    charter_dir = tmp_path / ".kittify" / "charter"
    (charter_dir / "directives.yaml").write_bytes(b"\xff\xfe not utf8")

    result = compute_bundle_content_hash(tmp_path)

    assert result is None


# ---------------------------------------------------------------------------
# Per-file BOM/CRLF independence (fact #14)
# ---------------------------------------------------------------------------


def test_bom_on_non_first_file_normalizes_identically(tmp_path: Path) -> None:
    """A BOM/CRLF variant on a NON-first file must not change the digest vs.
    the byte-identical-after-normalization plain variant — per-file hashing
    (not concat-then-hash-once) is what makes this true (fact #14): a single
    whole-payload hash would only strip a *leading* BOM and would see the
    BOM survive on files 2-4."""
    plain_root = tmp_path / "plain"
    variant_root = tmp_path / "variant"
    _seed_bundle(plain_root)

    variant_contents = dict(_CONTENTS)
    # BOM + CRLF on directives.yaml (the SECOND file in declared order) —
    # hash_content() normalizes both away per-file.
    variant_contents["directives.yaml"] = "﻿" + _DIRECTIVES.replace("\n", "\r\n")
    _seed_bundle(variant_root, variant_contents)

    plain_hash = compute_bundle_content_hash(plain_root)
    variant_hash = compute_bundle_content_hash(variant_root)

    assert plain_hash is not None
    assert plain_hash == variant_hash
