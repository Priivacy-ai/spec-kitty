"""Tests for ``charter.bundle.compute_bundle_content_hash`` (WP01 / T007, WP02 / T003).

Unit coverage for the content-identity hash helper (synthesized-drg-stale-refresh
+ bundle-freshness-hash-input-and-activation missions, C-005). Writers (promote/
resynthesize) and the freshness reader route through this single recipe.

Covers:
- happy path: deterministic, mtime-agnostic ``"sha256:..."`` digest
- fail-safe ``None`` returns: missing charter dir, missing single triad file
- **C1**: non-UTF-8 file → ``None`` (proves the ``UnicodeDecodeError`` arm is
  caught — this test fails with an uncaught exception if the implementation
  only catches ``OSError``)
- per-file BOM/CRLF independence (guards the per-file-hashing rationale)

WP02 recipe change (#2758/#2759):
- ``references.yaml`` is REMOVED from the hashed file set (#2758) — a missing/
  pruned ``references.yaml`` can no longer force ``None``.
- A directive-activation digest (via ``resolve_synthesis_graph_directives``) is
  APPENDED (#2759) — activating/deactivating a directive moves the hash.
- The resolver read is fail-safe: a drifted activated stem
  (``UnknownArtifactIdError``) or malformed ``config.yaml``
  (``CharterPackConfigError``) → ``None``, never a raise (never-raise contract).
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from charter.bundle import BUNDLE_CONTENT_HASH_FILES, compute_bundle_content_hash
from charter.compiler import (
    resolve_config_activated_roots,
    resolve_synthesis_graph_directives,
)
from charter.kind_vocabulary import UnknownArtifactIdError
from charter.pack_context import CharterPackConfigError, PackContext

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

# The triad the WP02 recipe actually hashes (references.yaml removed, #2758).
_TRIAD: dict[str, str] = {
    "governance.yaml": _GOVERNANCE,
    "directives.yaml": _DIRECTIVES,
    "metadata.yaml": _METADATA,
}


def _seed_bundle(repo_root: Path, contents: dict[str, str] | None = None) -> Path:
    """Write all four bundle files under ``repo_root/.kittify/charter/``."""
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    for name, text in (contents or _CONTENTS).items():
        (charter_dir / name).write_text(text, encoding="utf-8")
    return charter_dir


def _seed_config(repo_root: Path, text: str) -> Path:
    """Write ``.kittify/config.yaml`` with *text* (the activation source)."""
    config_path = repo_root / ".kittify" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(text, encoding="utf-8")
    return config_path


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


# ---------------------------------------------------------------------------
# WP02 (#2758): references.yaml removed from the hashed set
# ---------------------------------------------------------------------------


def test_missing_references_yaml_still_returns_real_hash(tmp_path: Path) -> None:
    """#2758 flip: with the triad present and ``references.yaml`` absent,
    ``compute_bundle_content_hash`` returns a REAL hash — not ``None``.

    Pre-fix, ``references.yaml`` was one of the hashed files, so its absence
    forced ``None`` (→ permanent stale). Post-fix it is not hashed at all, so a
    missing/pruned ``references.yaml`` has no effect on the content identity.
    """
    _seed_bundle(tmp_path, _TRIAD)  # triad only — no references.yaml

    result = compute_bundle_content_hash(tmp_path)

    assert result is not None
    assert result.startswith("sha256:")


# ---------------------------------------------------------------------------
# WP02 (#2759): directive-activation digest moves the hash
# ---------------------------------------------------------------------------


def test_changed_directive_set_changes_hash(tmp_path: Path) -> None:
    """Activating different directives (a different resolved set) changes the
    hash — even though the triad file bytes are byte-identical.

    Expected divergence is derived FROM the resolver (the two configs yield
    different ``resolve_synthesis_graph_directives`` results), never hardcoded.
    """
    repo_a = tmp_path / "a"
    repo_b = tmp_path / "b"
    _seed_bundle(repo_a, _TRIAD)
    _seed_bundle(repo_b, _TRIAD)
    _seed_config(repo_a, "activated_directives:\n  - 010-specification-fidelity-requirement\n")
    _seed_config(repo_b, "activated_directives:\n  - 024-locality-of-change\n")

    # Precondition (resolver-derived, not hardcoded): the resolved directive
    # sets genuinely differ, so any difference in the hash is attributable to
    # the directive digest, not incidental file content.
    assert resolve_synthesis_graph_directives(repo_a) != resolve_synthesis_graph_directives(repo_b)

    hash_a = compute_bundle_content_hash(repo_a)
    hash_b = compute_bundle_content_hash(repo_b)

    assert hash_a is not None
    assert hash_b is not None
    assert hash_a != hash_b


def test_noop_directive_set_keeps_hash_stable(tmp_path: Path) -> None:
    """A no-op for the resolved directive set (same config, recomputed) keeps
    the hash stable — the directive digest is deterministic (SC-003)."""
    _seed_bundle(tmp_path, _TRIAD)
    _seed_config(tmp_path, "activated_directives:\n  - 010-specification-fidelity-requirement\n")

    first = compute_bundle_content_hash(tmp_path)
    second = compute_bundle_content_hash(tmp_path)

    assert first is not None
    assert first == second


# ---------------------------------------------------------------------------
# WP02 fail-posture (never-raise): resolver errors → None
# ---------------------------------------------------------------------------


def test_drifted_activated_stem_returns_none_not_raises(tmp_path: Path) -> None:
    """A drifted activated stem (an id absent from the catalog) makes the
    resolver raise ``UnknownArtifactIdError`` (a ``ValueError``); the hash
    helper catches it → ``None``, never propagating the raise (NFR-003)."""
    _seed_bundle(tmp_path)  # full bundle present — so the ONLY None cause is the stem
    _seed_config(tmp_path, "activated_directives:\n  - 999-does-not-exist\n")

    # Prove the resolver genuinely raises on this stem (the path under test).
    with pytest.raises(UnknownArtifactIdError):
        resolve_config_activated_roots(repo_root=tmp_path)

    # The hash helper must swallow it, returning None rather than crashing.
    assert compute_bundle_content_hash(tmp_path) is None


def test_malformed_config_returns_none_not_raises(tmp_path: Path) -> None:
    """A malformed ``config.yaml`` (non-mapping root → ``CharterPackConfigError``)
    makes ``PackContext.from_config`` raise; the hash helper catches it → ``None``
    (never-raise contract). ``CharterPackConfigError`` is NOT a ``ValueError``
    subclass, so this pins the explicit arm of the catch tuple."""
    _seed_bundle(tmp_path)  # full bundle present — so the ONLY None cause is the config
    _seed_config(tmp_path, "just a scalar, not a mapping\n")

    # Prove the config genuinely raises (the path under test).
    with pytest.raises(CharterPackConfigError):
        PackContext.from_config(tmp_path)

    assert compute_bundle_content_hash(tmp_path) is None


def test_directive_digest_is_collision_free(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Two DISTINCT resolved directive sets must never produce the same digest.

    RED-FIRST guard against a #2759-class false-fresh: the resolved directive
    ``id:`` field is not schema-validated at the resolution point
    (``kind_vocabulary`` reads the raw YAML ``id:``), so an org-pack directive
    whose id contains the ``,`` join delimiter (e.g. ``"A,B"``) would, under a
    naive ``",".join`` serialization, collide with a two-id set ``["A", "B"]`` —
    both yielding ``"directives=A,B"``. A transition between those two activation
    states genuinely changes ``graph.yaml``'s seed input, so a collision would
    report ``fresh`` when it must be ``stale``. The digest must use a
    collision-free (JSON) encoding.
    """
    import charter.compiler as compiler_mod

    _seed_bundle(tmp_path)  # triad present so the per-file digests succeed

    def _one_comma_id(repo_root: Path, *, config_roots: object = None) -> list[str]:
        return ["A,B"]

    def _two_ids(repo_root: Path, *, config_roots: object = None) -> list[str]:
        return ["A", "B"]

    monkeypatch.setattr(compiler_mod, "resolve_synthesis_graph_directives", _one_comma_id)
    hash_comma = compute_bundle_content_hash(tmp_path)

    monkeypatch.setattr(compiler_mod, "resolve_synthesis_graph_directives", _two_ids)
    hash_two = compute_bundle_content_hash(tmp_path)

    assert hash_comma is not None and hash_two is not None
    assert hash_comma != hash_two, (
        "distinct directive sets must not collide in the digest — the ',' join "
        "delimiter is a legal (unvalidated) character inside a resolved directive id"
    )


def test_resolver_oserror_returns_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The ``OSError`` arm of the resolver-read catch → ``None`` (never-raise).

    Pins the third arm of the ``(CharterPackConfigError, ValueError, OSError)``
    catch tuple: a filesystem fault while loading config / the doctrine catalog
    must degrade to a recoverable ``stale``, not crash ``charter status``.
    """
    import charter.compiler as compiler_mod

    _seed_bundle(tmp_path)

    def _raise_oserror(repo_root: Path, *, config_roots: object = None) -> list[str]:
        raise OSError("simulated catalog/config read fault")

    monkeypatch.setattr(compiler_mod, "resolve_synthesis_graph_directives", _raise_oserror)

    assert compute_bundle_content_hash(tmp_path) is None
