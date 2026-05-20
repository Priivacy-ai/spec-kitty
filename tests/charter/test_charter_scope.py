"""Slice F WP09 — CharterScope unit suite.

Targets `src/charter/scope.py`. Exercises:
  - CharterScope.default(repo_root) constructor (FR-009, FR-011)
  - CharterScope.resolve(repo_root, feature_dir) — happy + edge paths (FR-010)
  - CharterScopeConfig Pydantic round-trip (FR-140 bridge — turns the
    `charter.scope.CharterScopeConfig` round-trip case from SKIPPED to PASSED)
  - CharterScopeConflict / CharterScopeNotFound exception surface (FR-008)

covers: FR-008, FR-009, FR-010, FR-011 — expected GREEN at: WP09 final commit
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]

import dataclasses

import yaml


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_repo_without_config(tmp_path: Path) -> Path:
    """Repo with no .kittify/config.yaml — single-project default path."""
    (tmp_path / ".kittify").mkdir()
    return tmp_path


@pytest.fixture
def tmp_repo_with_empty_scopes(tmp_path: Path) -> Path:
    """Repo with config.yaml that omits charter_scopes entirely."""
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "config.yaml").write_text(
        yaml.safe_dump({"some_other_key": "value"})
    )
    return tmp_path


@pytest.fixture
def tmp_monorepo(tmp_path: Path) -> Path:
    """Two-scope monorepo: packages/auth + packages/web."""
    (tmp_path / ".kittify").mkdir()
    config = {
        "charter_scopes": [
            {"root": "packages/auth", "name": "auth"},
            {"root": "packages/web", "name": "web"},
        ]
    }
    (tmp_path / ".kittify" / "config.yaml").write_text(yaml.safe_dump(config))
    (tmp_path / "packages" / "auth" / "src" / "internal").mkdir(parents=True)
    (tmp_path / "packages" / "web").mkdir(parents=True)
    return tmp_path


# ---------------------------------------------------------------------------
# CharterScope.default — single-project constructor
# ---------------------------------------------------------------------------


def test_default_scope_constructs_with_repo_root() -> None:
    from charter.scope import CharterScope

    repo_root = Path("/tmp/some-repo")
    scope = CharterScope.default(repo_root)

    assert scope.root == repo_root
    assert scope.name is None
    assert scope.config_source == "repo_root_default"


def test_default_scope_is_frozen() -> None:
    """CharterScope is a frozen dataclass: cannot mutate after construction."""
    from charter.scope import CharterScope

    scope = CharterScope.default(Path("/tmp/repo"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        scope.name = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CharterScope.resolve — without config (default path)
# ---------------------------------------------------------------------------


def test_resolve_without_config_returns_default(
    tmp_repo_without_config: Path,
) -> None:
    from charter.scope import CharterScope

    scope = CharterScope.resolve(tmp_repo_without_config, tmp_repo_without_config)
    assert scope.config_source == "repo_root_default"
    assert scope.name is None


def test_resolve_with_empty_scopes_returns_default(
    tmp_repo_with_empty_scopes: Path,
) -> None:
    """config.yaml without charter_scopes key — still default path."""
    from charter.scope import CharterScope

    scope = CharterScope.resolve(
        tmp_repo_with_empty_scopes, tmp_repo_with_empty_scopes
    )
    assert scope.config_source == "repo_root_default"


# ---------------------------------------------------------------------------
# CharterScope.resolve — monorepo resolution
# ---------------------------------------------------------------------------


def test_resolve_with_config_walks_upward(tmp_monorepo: Path) -> None:
    from charter.scope import CharterScope

    deep = tmp_monorepo / "packages" / "auth" / "src" / "internal"
    scope = CharterScope.resolve(tmp_monorepo, deep)
    assert scope.name == "auth"
    assert scope.config_source == "monorepo_config"


def test_resolve_returns_scope_root_at_exact_match(tmp_monorepo: Path) -> None:
    from charter.scope import CharterScope

    feature_dir = tmp_monorepo / "packages" / "web"
    scope = CharterScope.resolve(tmp_monorepo, feature_dir)
    assert scope.name == "web"


def test_charter_scope_not_found_when_feature_dir_outside_any_scope(
    tmp_monorepo: Path,
) -> None:
    from charter.scope import CharterScope, CharterScopeNotFound

    outside = tmp_monorepo / "not-a-package" / "deep"
    outside.mkdir(parents=True)
    with pytest.raises(CharterScopeNotFound) as exc_info:
        CharterScope.resolve(tmp_monorepo, outside)

    message = str(exc_info.value)
    assert "packages/auth" in message
    assert "packages/web" in message


# ---------------------------------------------------------------------------
# CharterScopeConfig Pydantic model — FR-140 round-trip case
# ---------------------------------------------------------------------------


def test_charter_scope_config_accepts_valid_payload() -> None:
    """Valid charter_scopes payload round-trips through CharterScopeConfig."""
    from charter.scope import CharterScopeConfig

    payload = {
        "charter_scopes": [
            {"root": "packages/auth", "name": "auth"},
            {"root": "packages/web", "name": "web"},
        ]
    }
    model = CharterScopeConfig.model_validate(payload)
    assert len(model.charter_scopes) == 2
    assert model.charter_scopes[0].root == "packages/auth"
    assert model.charter_scopes[1].name == "web"


def test_charter_scope_config_accepts_entry_without_name() -> None:
    """`name` is optional per the contract."""
    from charter.scope import CharterScopeConfig

    payload = {"charter_scopes": [{"root": "packages/auth"}]}
    model = CharterScopeConfig.model_validate(payload)
    assert model.charter_scopes[0].name is None


def test_charter_scope_config_rejects_empty_root() -> None:
    """Empty root is rejected — matches the invalid round-trip case."""
    import pydantic

    from charter.scope import CharterScopeConfig

    payload = {
        "charter_scopes": [
            {"root": "packages/auth"},
            {"root": ""},
        ]
    }
    with pytest.raises(pydantic.ValidationError):
        CharterScopeConfig.model_validate(payload)


# ---------------------------------------------------------------------------
# Module surface — C-007 __all__ binding
# ---------------------------------------------------------------------------


def test_scope_module_declares_all() -> None:
    """C-007: scope.py declares __all__ with the public surface."""
    import charter.scope as scope_mod

    assert hasattr(scope_mod, "__all__")
    public_names = set(scope_mod.__all__)
    assert "CharterScope" in public_names
    assert "CharterScopeConfig" in public_names
    assert "CharterScopeConflict" in public_names
    assert "CharterScopeNotFound" in public_names


def test_scope_router_module_declares_all() -> None:
    """C-007: scope_router.py declares __all__ with the public surface."""
    import charter.scope_router as router_mod

    assert hasattr(router_mod, "__all__")
    assert "build_with_scope" in router_mod.__all__


def test_scope_router_does_not_import_specify_cli() -> None:
    """NFR-003: charter layer must not depend on specify_cli."""
    from pathlib import Path as _P

    src = _P(__file__).resolve().parents[2] / "src" / "charter" / "scope_router.py"
    text = src.read_text()
    assert "from specify_cli" not in text
    assert "import specify_cli" not in text
