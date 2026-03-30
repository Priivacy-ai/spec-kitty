"""Tests for TrackerProjectConfig: project_slug, provider-aware is_configured, constants."""

from __future__ import annotations

import pytest

from specify_cli.tracker.config import (
    ALL_SUPPORTED_PROVIDERS,
    LOCAL_PROVIDERS,
    REMOVED_PROVIDERS,
    SAAS_PROVIDERS,
    TrackerProjectConfig,
    load_tracker_config,
    save_tracker_config,
)


# ---------------------------------------------------------------------------
# YAML roundtrip tests
# ---------------------------------------------------------------------------


def test_project_slug_roundtrip(tmp_path: object) -> None:
    """SaaS binding: project_slug survives save + load cycle."""
    from pathlib import Path

    root = Path(str(tmp_path))
    config = TrackerProjectConfig(provider="linear", project_slug="my-proj")
    save_tracker_config(root, config)
    loaded = load_tracker_config(root)
    assert loaded.project_slug == "my-proj"
    assert loaded.provider == "linear"


def test_workspace_roundtrip(tmp_path: object) -> None:
    """Local binding: workspace survives save + load cycle."""
    from pathlib import Path

    root = Path(str(tmp_path))
    config = TrackerProjectConfig(provider="beads", workspace="my-ws")
    save_tracker_config(root, config)
    loaded = load_tracker_config(root)
    assert loaded.workspace == "my-ws"
    assert loaded.provider == "beads"


def test_project_slug_and_workspace_roundtrip(tmp_path: object) -> None:
    """Both fields can coexist in YAML (even if only one matters per provider type)."""
    from pathlib import Path

    root = Path(str(tmp_path))
    config = TrackerProjectConfig(
        provider="linear", project_slug="proj", workspace="ws"
    )
    save_tracker_config(root, config)
    loaded = load_tracker_config(root)
    assert loaded.project_slug == "proj"
    assert loaded.workspace == "ws"


def test_project_slug_none_when_absent(tmp_path: object) -> None:
    """project_slug defaults to None when not present in YAML."""
    from pathlib import Path

    root = Path(str(tmp_path))
    config = TrackerProjectConfig(provider="beads", workspace="ws")
    save_tracker_config(root, config)
    loaded = load_tracker_config(root)
    assert loaded.project_slug is None


# ---------------------------------------------------------------------------
# is_configured tests — SaaS providers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("provider", sorted(SAAS_PROVIDERS))
def test_is_configured_saas_with_project_slug(provider: str) -> None:
    """SaaS provider with project_slug is configured."""
    assert TrackerProjectConfig(provider=provider, project_slug="p").is_configured


@pytest.mark.parametrize("provider", sorted(SAAS_PROVIDERS))
def test_is_configured_saas_without_project_slug(provider: str) -> None:
    """SaaS provider without project_slug is NOT configured."""
    assert not TrackerProjectConfig(provider=provider).is_configured


def test_is_configured_saas_workspace_alone_insufficient() -> None:
    """SaaS provider with only workspace (no project_slug) is NOT configured."""
    assert not TrackerProjectConfig(provider="linear", workspace="w").is_configured


# ---------------------------------------------------------------------------
# is_configured tests — local providers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
def test_is_configured_local_with_workspace(provider: str) -> None:
    """Local provider with workspace is configured."""
    assert TrackerProjectConfig(provider=provider, workspace="w").is_configured


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
def test_is_configured_local_without_workspace(provider: str) -> None:
    """Local provider without workspace is NOT configured."""
    assert not TrackerProjectConfig(provider=provider).is_configured


def test_is_configured_local_project_slug_alone_insufficient() -> None:
    """Local provider with only project_slug (no workspace) is NOT configured."""
    assert not TrackerProjectConfig(provider="beads", project_slug="p").is_configured


# ---------------------------------------------------------------------------
# is_configured tests — edge cases
# ---------------------------------------------------------------------------


def test_is_configured_no_provider() -> None:
    """No provider at all is NOT configured."""
    assert not TrackerProjectConfig().is_configured


def test_is_configured_removed_provider() -> None:
    """Removed provider (azure_devops) is NOT configured regardless of fields."""
    assert not TrackerProjectConfig(
        provider="azure_devops", project_slug="p", workspace="w"
    ).is_configured


def test_is_configured_unknown_provider() -> None:
    """Unknown provider is NOT configured."""
    assert not TrackerProjectConfig(
        provider="some_unknown", project_slug="p", workspace="w"
    ).is_configured


# ---------------------------------------------------------------------------
# Provider classification constants
# ---------------------------------------------------------------------------


def test_provider_constants_membership() -> None:
    """Spot-check key providers are in the right sets."""
    assert "linear" in SAAS_PROVIDERS
    assert "jira" in SAAS_PROVIDERS
    assert "github" in SAAS_PROVIDERS
    assert "gitlab" in SAAS_PROVIDERS
    assert "beads" in LOCAL_PROVIDERS
    assert "fp" in LOCAL_PROVIDERS
    assert "azure_devops" in REMOVED_PROVIDERS


def test_provider_sets_disjoint() -> None:
    """SaaS, local, and removed sets must not overlap."""
    assert not SAAS_PROVIDERS & LOCAL_PROVIDERS
    assert not SAAS_PROVIDERS & REMOVED_PROVIDERS
    assert not LOCAL_PROVIDERS & REMOVED_PROVIDERS


def test_all_supported_is_union() -> None:
    """ALL_SUPPORTED_PROVIDERS == SAAS | LOCAL (removed excluded)."""
    assert ALL_SUPPORTED_PROVIDERS == SAAS_PROVIDERS | LOCAL_PROVIDERS
    assert not REMOVED_PROVIDERS & ALL_SUPPORTED_PROVIDERS


def test_provider_constants_are_frozensets() -> None:
    """Constants are immutable frozensets."""
    assert isinstance(SAAS_PROVIDERS, frozenset)
    assert isinstance(LOCAL_PROVIDERS, frozenset)
    assert isinstance(REMOVED_PROVIDERS, frozenset)
    assert isinstance(ALL_SUPPORTED_PROVIDERS, frozenset)


# ---------------------------------------------------------------------------
# from_dict / to_dict serialization
# ---------------------------------------------------------------------------


def test_to_dict_includes_project_slug() -> None:
    """to_dict emits project_slug key."""
    config = TrackerProjectConfig(provider="linear", project_slug="slug-1")
    d = config.to_dict()
    assert d["project_slug"] == "slug-1"


def test_from_dict_parses_project_slug() -> None:
    """from_dict reads project_slug from raw dict."""
    config = TrackerProjectConfig.from_dict(
        {"provider": "github", "project_slug": "my-repo"}
    )
    assert config.project_slug == "my-repo"
    assert config.provider == "github"


def test_from_dict_strips_whitespace() -> None:
    """from_dict strips surrounding whitespace from project_slug."""
    config = TrackerProjectConfig.from_dict(
        {"provider": "linear", "project_slug": "  padded  "}
    )
    assert config.project_slug == "padded"


def test_from_dict_empty_string_becomes_none() -> None:
    """from_dict treats empty/whitespace-only project_slug as None."""
    config = TrackerProjectConfig.from_dict(
        {"provider": "linear", "project_slug": "   "}
    )
    assert config.project_slug is None
