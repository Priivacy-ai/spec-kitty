"""Unit tests for ``charter.pack_context.PackContext`` (WP06, T040).

Covers:
- T040-1: ``PackContext.from_config()`` with minimal config.yaml produces
  correct ``activated_mission_types``.
- T040-2: ``PackContext.from_config()`` with no config.yaml returns fallback
  PackContext with all built-in mission types.
- T040-3: ``PackContext`` is immutable (``FrozenInstanceError`` on mutation).
- T040-4: ``pack_roots`` is a ``tuple`` (not a list).
- T040-5: ``activated_kinds`` is a ``frozenset``.
- T040-6: ``PackContext`` can be used as a dict key (frozen dataclasses are
  hashable).
- T040-7: ``activated_kinds`` defaults to all eight built-in kinds when key
  is absent.
- T040-8: ``activated_kinds`` is read from config when key is present.
- T040-9: ``mission_type_activations`` list is read from config when present.
- T040-10: ``org_pack_names`` and extra pack roots populated from config.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from charter.pack_context import (
    PackContext,
    _BUILTIN_ARTIFACT_KINDS,
    _BUILTIN_MISSION_TYPE_IDS,
)


pytestmark = [pytest.mark.fast]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_CONFIG = """\
vcs:
  type: git
agents:
  available:
    - claude
"""

_CONFIG_WITH_ACTIVATIONS = """\
vcs:
  type: git
mission_type_activations:
  - software-dev
  - documentation
activated_kinds:
  - directives
  - tactics
"""

_CONFIG_WITH_ORG_PACKS = """\
vcs:
  type: git
doctrine:
  org:
    packs:
      - name: acme-pack
        local_path: {pack_path}
"""


def _write_config(tmp_path: Path, content: str) -> None:
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "config.yaml").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# T040-1: from_config with minimal config → all built-in mission types
# ---------------------------------------------------------------------------


def test_from_config_minimal_config_uses_builtin_mission_types(tmp_path: Path) -> None:
    """Minimal config.yaml with no mission_type_activations → all four built-ins."""
    _write_config(tmp_path, _MINIMAL_CONFIG)

    ctx = PackContext.from_config(tmp_path)

    assert ctx.activated_mission_types == _BUILTIN_MISSION_TYPE_IDS
    assert "software-dev" in ctx.activated_mission_types
    assert "documentation" in ctx.activated_mission_types
    assert "research" in ctx.activated_mission_types
    assert "plan" in ctx.activated_mission_types


# ---------------------------------------------------------------------------
# T040-2: from_config with no config.yaml → fallback PackContext
# ---------------------------------------------------------------------------


def test_from_config_no_config_yaml_returns_fallback(tmp_path: Path) -> None:
    """No .kittify/config.yaml → fallback with all built-in mission types."""
    # Don't write any config
    ctx = PackContext.from_config(tmp_path)

    assert ctx.activated_mission_types == _BUILTIN_MISSION_TYPE_IDS
    assert ctx.activated_kinds == _BUILTIN_ARTIFACT_KINDS
    assert ctx.org_pack_names == ()
    assert ctx.repo_root == tmp_path


# ---------------------------------------------------------------------------
# T040-3: PackContext is immutable
# ---------------------------------------------------------------------------


def test_pack_context_is_immutable(tmp_path: Path) -> None:
    """Attempting to set a field raises FrozenInstanceError."""
    ctx = PackContext.from_config(tmp_path)

    with pytest.raises(dataclasses.FrozenInstanceError):
        ctx.activated_kinds = frozenset({"directives"})  # type: ignore[misc]


# ---------------------------------------------------------------------------
# T040-4: pack_roots is a tuple
# ---------------------------------------------------------------------------


def test_pack_roots_is_tuple(tmp_path: Path) -> None:
    """pack_roots must be a tuple, not a list."""
    _write_config(tmp_path, _MINIMAL_CONFIG)
    ctx = PackContext.from_config(tmp_path)

    assert isinstance(ctx.pack_roots, tuple)


def test_pack_roots_contains_builtin_root(tmp_path: Path) -> None:
    """pack_roots[0] must point at the built-in doctrine root (src/doctrine/)."""
    _write_config(tmp_path, _MINIMAL_CONFIG)
    ctx = PackContext.from_config(tmp_path)

    assert len(ctx.pack_roots) >= 1
    builtin = ctx.pack_roots[0]
    # The built-in doctrine root is src/doctrine/ which exists on disk.
    assert builtin.exists()
    assert builtin.name == "doctrine"


# ---------------------------------------------------------------------------
# T040-5: activated_kinds is a frozenset
# ---------------------------------------------------------------------------


def test_activated_kinds_is_frozenset(tmp_path: Path) -> None:
    """activated_kinds must be a frozenset."""
    ctx = PackContext.from_config(tmp_path)

    assert isinstance(ctx.activated_kinds, frozenset)


# ---------------------------------------------------------------------------
# T040-6: PackContext is hashable (can be used as dict key)
# ---------------------------------------------------------------------------


def test_pack_context_is_hashable(tmp_path: Path) -> None:
    """Frozen dataclasses are hashable; PackContext can be used as a dict key."""
    _write_config(tmp_path, _MINIMAL_CONFIG)
    ctx = PackContext.from_config(tmp_path)

    d: dict[PackContext, str] = {}
    d[ctx] = "value"
    assert d[ctx] == "value"


# ---------------------------------------------------------------------------
# T040-7: activated_kinds defaults to all built-in kinds when key absent
# ---------------------------------------------------------------------------


def test_activated_kinds_defaults_to_all_builtin_when_key_absent(tmp_path: Path) -> None:
    """When activated_kinds key is absent → all eight built-in kinds."""
    _write_config(tmp_path, _MINIMAL_CONFIG)
    ctx = PackContext.from_config(tmp_path)

    assert ctx.activated_kinds == _BUILTIN_ARTIFACT_KINDS
    assert len(ctx.activated_kinds) == 8


# ---------------------------------------------------------------------------
# T040-8: activated_kinds read from config when key present
# ---------------------------------------------------------------------------


def test_activated_kinds_read_from_config_when_present(tmp_path: Path) -> None:
    """When activated_kinds is in config, use that list."""
    _write_config(tmp_path, _CONFIG_WITH_ACTIVATIONS)
    ctx = PackContext.from_config(tmp_path)

    assert ctx.activated_kinds == frozenset({"directives", "tactics"})


# ---------------------------------------------------------------------------
# T040-9: mission_type_activations read from config when present
# ---------------------------------------------------------------------------


def test_activated_mission_types_read_from_config(tmp_path: Path) -> None:
    """When mission_type_activations is in config, use that list."""
    _write_config(tmp_path, _CONFIG_WITH_ACTIVATIONS)
    ctx = PackContext.from_config(tmp_path)

    assert ctx.activated_mission_types == frozenset({"software-dev", "documentation"})


# ---------------------------------------------------------------------------
# T040-10: org_pack_names populated from config
# ---------------------------------------------------------------------------


def test_org_pack_names_and_roots_populated(tmp_path: Path) -> None:
    """When doctrine.org.packs is present, org_pack_names and pack_roots are populated."""
    # Create a fake pack directory
    pack_dir = tmp_path / "acme-pack"
    pack_dir.mkdir()
    content = _CONFIG_WITH_ORG_PACKS.format(pack_path=pack_dir)
    _write_config(tmp_path, content)

    ctx = PackContext.from_config(tmp_path)

    assert "acme-pack" in ctx.org_pack_names
    # pack_roots has the built-in root first, then the org pack root
    assert len(ctx.pack_roots) == 2
    assert ctx.pack_roots[0].name == "doctrine"  # built-in
    assert ctx.pack_roots[1] == pack_dir


# ---------------------------------------------------------------------------
# Additional: repo_root is stored
# ---------------------------------------------------------------------------


def test_repo_root_is_stored(tmp_path: Path) -> None:
    """repo_root field is set to the provided repo_root."""
    ctx = PackContext.from_config(tmp_path)

    assert ctx.repo_root == tmp_path


# ---------------------------------------------------------------------------
# Additional: activated_mission_types is a frozenset
# ---------------------------------------------------------------------------


def test_activated_mission_types_is_frozenset(tmp_path: Path) -> None:
    """activated_mission_types must be a frozenset."""
    ctx = PackContext.from_config(tmp_path)

    assert isinstance(ctx.activated_mission_types, frozenset)


# ---------------------------------------------------------------------------
# Additional: empty mission_type_activations list → fallback to built-ins
# ---------------------------------------------------------------------------


def test_empty_mission_type_activations_uses_builtin_fallback(tmp_path: Path) -> None:
    """An empty mission_type_activations list falls back to built-in defaults."""
    content = """\
vcs:
  type: git
mission_type_activations: []
"""
    _write_config(tmp_path, content)
    ctx = PackContext.from_config(tmp_path)

    assert ctx.activated_mission_types == _BUILTIN_MISSION_TYPE_IDS


# ---------------------------------------------------------------------------
# Additional: empty activated_kinds list → fallback to built-in kinds
# ---------------------------------------------------------------------------


def test_empty_activated_kinds_uses_builtin_fallback(tmp_path: Path) -> None:
    """An empty activated_kinds list falls back to all built-in kinds."""
    content = """\
vcs:
  type: git
activated_kinds: []
"""
    _write_config(tmp_path, content)
    ctx = PackContext.from_config(tmp_path)

    assert ctx.activated_kinds == _BUILTIN_ARTIFACT_KINDS


# ---------------------------------------------------------------------------
# Additional: PackContext exported from charter namespace
# ---------------------------------------------------------------------------


def test_pack_context_exported_from_charter_namespace() -> None:
    """PackContext must be importable from the top-level charter namespace."""
    from charter import PackContext as PackContextFromCharter  # noqa: PLC0415

    assert PackContextFromCharter is PackContext
