"""Tests for ``charter.bundle.compute_bundle_content_hash`` (WP01 / T007;
re-pointed at ``charter.yaml`` by consolidate-charter-bundle WP06 / T027).

New-symbol unit coverage for the content-identity hash helper
(synthesized-drg-stale-refresh mission, C-005; consolidate-charter-bundle
mission, contracts/manifest-v2.md M1/M3). ``BUNDLE_CONTENT_HASH_FILES`` was
narrowed from the four legacy bundle files (governance/directives/
references/metadata) to the single tracked, authored ``charter.yaml``
(data-model.md Landmine 1) — this suite seeds that single file.

Covers:
- happy path: deterministic, mtime-agnostic ``"sha256:..."`` digest
- fail-safe ``None`` returns: missing charter dir, missing charter.yaml
- **C1**: non-UTF-8 file → ``None`` (proves the ``UnicodeDecodeError`` arm is
  caught — this test fails with an uncaught exception if the implementation
  only catches ``OSError``)
- BOM/CRLF normalization (guards the per-file-hashing recipe, #2732)
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from charter.bundle import BUNDLE_CONTENT_HASH_FILES, compute_bundle_content_hash

pytestmark = [pytest.mark.unit]


_CHARTER_YAML_BODY = (
    "schema_version: '2.0.0'\n"
    "governance: {}\n"
    "directives:\n"
    "  directives: []\n"
    "catalog:\n"
    "  mission: test-mission\n"
    "  template_set: default\n"
    "  languages: []\n"
    "  references: []\n"
    "metadata:\n"
    "  generated_at: '2026-01-01T00:00:00+00:00'\n"
    "  bundle_schema_version: 2\n"
)


def _seed_bundle(repo_root: Path, body: str = _CHARTER_YAML_BODY) -> Path:
    """Write ``charter.yaml`` under ``repo_root/.kittify/charter/``."""
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    (charter_dir / "charter.yaml").write_text(body, encoding="utf-8")
    return charter_dir


def test_content_hash_input_is_charter_yaml_only() -> None:
    """M1 (contracts/manifest-v2.md): the content-hash input set is exactly
    ``{charter.yaml}`` — the historic four-legacy-file set is retired."""
    assert tuple(BUNDLE_CONTENT_HASH_FILES) == ("charter.yaml",)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_happy_path_returns_sha256_prefixed_digest(tmp_path: Path) -> None:
    """``charter.yaml`` present → a well-formed ``"sha256:..."`` digest."""
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
    """Touching the file's mtime without changing its content does not
    change the digest — the comparison is content-identity, not
    timestamp-based."""
    charter_dir = _seed_bundle(tmp_path)

    before = compute_bundle_content_hash(tmp_path)

    # Touch mtime forward without altering bytes.
    time.sleep(0.01)
    target = charter_dir / "charter.yaml"
    target.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")

    after = compute_bundle_content_hash(tmp_path)

    assert before == after


def test_content_change_flips_the_digest(tmp_path: Path) -> None:
    """A genuine content edit (e.g. authoring ``governance``) changes the
    digest — the sibling side of the mtime-agnostic guarantee above."""
    charter_dir = _seed_bundle(tmp_path)
    before = compute_bundle_content_hash(tmp_path)

    (charter_dir / "charter.yaml").write_text(
        _CHARTER_YAML_BODY.replace("governance: {}", "governance:\n  rules: []\n"),
        encoding="utf-8",
    )

    after = compute_bundle_content_hash(tmp_path)

    assert before != after


# ---------------------------------------------------------------------------
# Fail-safe None cases
# ---------------------------------------------------------------------------


def test_missing_charter_dir_returns_none(tmp_path: Path) -> None:
    """``.kittify/charter/`` entirely absent → ``None`` (never raises)."""
    result = compute_bundle_content_hash(tmp_path)

    assert result is None


def test_missing_charter_yaml_returns_none(tmp_path: Path) -> None:
    """``.kittify/charter/`` present but ``charter.yaml`` absent → ``None``."""
    (tmp_path / ".kittify" / "charter").mkdir(parents=True, exist_ok=True)

    result = compute_bundle_content_hash(tmp_path)

    assert result is None


def test_non_utf8_file_returns_none_not_raises(tmp_path: Path) -> None:
    """C1 fail-safe: a non-UTF-8 ``charter.yaml`` must yield ``None``, not
    crash.

    ``Path.read_text(encoding="utf-8")`` on invalid UTF-8 bytes raises
    ``UnicodeDecodeError`` — a ``ValueError`` subclass, NOT an ``OSError``.
    If the implementation's read guard only catches ``OSError`` this test
    fails with an uncaught ``UnicodeDecodeError`` instead of asserting
    ``None``.
    """
    charter_dir = _seed_bundle(tmp_path)
    (charter_dir / "charter.yaml").write_bytes(b"\xff\xfe not utf8")

    result = compute_bundle_content_hash(tmp_path)

    assert result is None


# ---------------------------------------------------------------------------
# BOM/CRLF normalization (fact #14 / #2732 recipe)
# ---------------------------------------------------------------------------


def test_bom_and_crlf_normalize_identically(tmp_path: Path) -> None:
    """A BOM/CRLF variant of the SAME content must not change the digest vs.
    the plain variant — ``hash_content``'s per-file BOM-strip/CRLF-normalize
    recipe (#2732) is what makes this true."""
    plain_root = tmp_path / "plain"
    variant_root = tmp_path / "variant"
    _seed_bundle(plain_root)

    variant_body = "﻿" + _CHARTER_YAML_BODY.replace("\n", "\r\n")
    _seed_bundle(variant_root, variant_body)

    plain_hash = compute_bundle_content_hash(plain_root)
    variant_hash = compute_bundle_content_hash(variant_root)

    assert plain_hash is not None
    assert plain_hash == variant_hash
