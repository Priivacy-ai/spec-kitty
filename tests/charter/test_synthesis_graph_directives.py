"""Unit tests for ``charter.compiler.resolve_synthesis_graph_directives`` (WP01, FR-002/FR-004).

RED-FIRST (C-011): committed before the helper exists. Pins the single-authority
contract WP01 extracts from ``_synthesis.py`` (the #2577 absent-key -> ``[]`` rule)
so both ``_synthesis.py`` and WP02's ``charter.bundle`` freshness hash consume the
exact same resolved directive list.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from charter.compiler import resolve_config_activated_roots, resolve_synthesis_graph_directives

pytestmark = [pytest.mark.fast, pytest.mark.unit]


def test_absent_activated_directives_key_returns_empty_list(tmp_path: Path) -> None:
    """No ``.kittify/config.yaml`` at all -- the genuine first-run/absent-key signal.

    Mirrors the #2577 rule: even though ``resolve_config_activated_roots`` itself
    falls back to "every built-in directive" for the absent case (the correct
    default for the ``references.yaml`` consumer), the synthesizer's graph.yaml
    consumer must see ``[]`` instead -- feeding "all built-ins" into the DRG/
    companion-tactic expansion path fails closed on a fresh project.
    """
    assert resolve_synthesis_graph_directives(tmp_path) == []


def test_present_activated_directives_key_returns_resolved_roots(tmp_path: Path) -> None:
    """Explicit ``config.activated_directives`` -- resolved via the shared resolver.

    Expected ids are derived FROM ``resolve_config_activated_roots`` itself (not
    hardcoded) so this test stays correct if the built-in directive catalog
    changes shape.
    """
    config_path = tmp_path / ".kittify" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        "activated_directives:\n  - 010-specification-fidelity-requirement\n",
        encoding="utf-8",
    )

    expected = resolve_config_activated_roots(repo_root=tmp_path).directives

    assert resolve_synthesis_graph_directives(tmp_path) == expected
    assert expected == ["DIRECTIVE_010"]


def test_pre_resolved_config_roots_is_equivalent_present_key(tmp_path: Path) -> None:
    """Passing a pre-resolved ``config_roots`` (to avoid a redundant catalog
    load) yields the same directive list as resolving internally -- present key."""
    config_path = tmp_path / ".kittify" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        "activated_directives:\n  - 010-specification-fidelity-requirement\n",
        encoding="utf-8",
    )

    roots = resolve_config_activated_roots(repo_root=tmp_path)

    assert resolve_synthesis_graph_directives(tmp_path, config_roots=roots) == (
        resolve_synthesis_graph_directives(tmp_path)
    )


def test_pre_resolved_config_roots_is_equivalent_absent_key(tmp_path: Path) -> None:
    """Absent-key case still returns ``[]`` even when a (fully-populated,
    all-built-ins) ``config_roots`` is passed in -- the three-state signal is
    read fresh from ``PackContext``, not inferred from the pre-resolved roots."""
    roots = resolve_config_activated_roots(repo_root=tmp_path)

    assert resolve_synthesis_graph_directives(tmp_path, config_roots=roots) == []
    assert resolve_synthesis_graph_directives(tmp_path, config_roots=roots) == (
        resolve_synthesis_graph_directives(tmp_path)
    )


def test_absent_directives_skips_catalog_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Absent ``activated_directives`` short-circuits to ``[]`` WITHOUT the
    uncached ``load_doctrine_catalog()`` (~2s, 354-file glob) that
    ``resolve_config_activated_roots`` triggers -- NFR-001/NFR-002.

    Since the return value is ``[]`` regardless of the resolved roots on the
    absent-key path, the resolver (and its catalog load) must not be invoked at
    all. This pins the freshness read within budget for projects with no
    activated directives (the state both the ``compute_freshness`` and warm-path
    performance ratchets seed).
    """
    import charter.compiler as compiler_mod
    from charter.compiler import ConfigActivatedRoots

    calls: list[int] = []
    real = compiler_mod.resolve_config_activated_roots

    def _spy(*, repo_root: Path) -> ConfigActivatedRoots:
        calls.append(1)
        return real(repo_root=repo_root)

    monkeypatch.setattr(compiler_mod, "resolve_config_activated_roots", _spy)

    result = compiler_mod.resolve_synthesis_graph_directives(tmp_path)

    assert result == []
    assert calls == [], "absent-directives path must not trigger the catalog load"
