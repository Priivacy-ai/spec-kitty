"""Connector factory for spec-kitty tracker integrations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class TrackerFactoryError(RuntimeError):
    """Raised when connector construction fails."""


SUPPORTED_PROVIDERS: tuple[str, ...] = (
    "jira",
    "linear",
    "azure_devops",
    "github",
    "gitlab",
    "beads",
    "fp",
)

_PROVIDER_ALIASES = {
    "azure-devops": "azure_devops",
    "azure": "azure_devops",
}


def normalize_provider(provider: str) -> str:
    key = provider.strip().lower()
    return _PROVIDER_ALIASES.get(key, key)


def _require(values: Mapping[str, Any], key: str, provider: str) -> str:
    value = values.get(key)
    if value is None or not str(value).strip():
        raise TrackerFactoryError(f"Missing required credential '{key}' for provider '{provider}'")
    return str(value).strip()


def build_connector(
    *,
    provider: str,
    workspace: str,
    credentials: Mapping[str, Any],
) -> Any:
    """Build a TaskTrackerConnector instance from provider+credentials."""
    provider_name = normalize_provider(provider)
    if provider_name not in SUPPORTED_PROVIDERS:
        raise TrackerFactoryError(
            f"Unsupported provider '{provider}'. Supported: {', '.join(SUPPORTED_PROVIDERS)}"
        )

    try:
        from spec_kitty_tracker import (
            AzureDevOpsConnector,
            AzureDevOpsConnectorConfig,
            BeadsConnector,
            BeadsConnectorConfig,
            FPConnector,
            FPConnectorConfig,
            GitHubConnector,
            GitHubConnectorConfig,
            GitLabConnector,
            GitLabConnectorConfig,
            JiraConnector,
            JiraConnectorConfig,
            LinearConnector,
            LinearConnectorConfig,
        )
    except Exception as exc:  # pragma: no cover - dependency boundary
        raise TrackerFactoryError(
            "spec-kitty-tracker is not installed. Install it to use tracker commands."
        ) from exc

    if provider_name == "jira":
        config = JiraConnectorConfig(
            base_url=_require(credentials, "base_url", provider_name),
            email=_require(credentials, "email", provider_name),
            api_token=_require(credentials, "api_token", provider_name),
            project_key=_require(credentials, "project_key", provider_name),
        )
        return JiraConnector(config)

    if provider_name == "linear":
        config = LinearConnectorConfig(
            api_key=_require(credentials, "api_key", provider_name),
            team_id=_require(credentials, "team_id", provider_name),
            workspace=workspace,
            graphql_url=str(credentials.get("graphql_url") or "https://api.linear.app/graphql"),
        )
        return LinearConnector(config)

    if provider_name == "azure_devops":
        pat = credentials.get("personal_access_token") or credentials.get("pat")
        config = AzureDevOpsConnectorConfig(
            organization=_require(credentials, "organization", provider_name),
            project=_require(credentials, "project", provider_name),
            personal_access_token=_require({"personal_access_token": pat}, "personal_access_token", provider_name),
            base_url=str(credentials.get("base_url") or "https://dev.azure.com"),
        )
        return AzureDevOpsConnector(config)

    if provider_name == "github":
        config = GitHubConnectorConfig(
            owner=_require(credentials, "owner", provider_name),
            repo=_require(credentials, "repo", provider_name),
            token=_require(credentials, "token", provider_name),
            base_url=str(credentials.get("base_url") or "https://api.github.com"),
        )
        return GitHubConnector(config)

    if provider_name == "gitlab":
        config = GitLabConnectorConfig(
            project_id=_require(credentials, "project_id", provider_name),
            token=_require(credentials, "token", provider_name),
            base_url=str(credentials.get("base_url") or "https://gitlab.com/api/v4"),
        )
        return GitLabConnector(config)

    if provider_name == "beads":
        config = BeadsConnectorConfig(
            workspace=workspace,
            command=str(credentials.get("command") or "bd"),
            cwd=str(credentials.get("cwd")) if credentials.get("cwd") else None,
        )
        return BeadsConnector(config)

    if provider_name == "fp":
        config = FPConnectorConfig(
            workspace=workspace,
            command=str(credentials.get("command") or "fp"),
            cwd=str(credentials.get("cwd")) if credentials.get("cwd") else None,
        )
        return FPConnector(config)

    raise TrackerFactoryError(f"Unhandled provider: {provider_name}")
