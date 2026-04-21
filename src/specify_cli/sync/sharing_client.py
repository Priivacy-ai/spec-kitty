"""Authenticated client for repository sharing APIs."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlencode

import httpx

from specify_cli.auth.http import OAuthHttpClient

from .config import SyncConfig


class RepositorySharingClientError(RuntimeError):
    """Structured failure for repository sharing API calls."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def __str__(self) -> str:
        return self.message


def _base_url() -> str:
    return SyncConfig().get_server_url().rstrip("/")


def _error_from_response(response: httpx.Response) -> RepositorySharingClientError:
    payload: dict[str, Any] | None = None
    message = f"Repository sharing API failed with HTTP {response.status_code}."
    try:
        parsed = response.json()
        if isinstance(parsed, dict):
            payload = parsed
            detail = parsed.get("error") or parsed.get("detail")
            if isinstance(detail, str) and detail.strip():
                message = detail.strip()
    except Exception:
        payload = None
    return RepositorySharingClientError(
        message=message,
        status_code=response.status_code,
        payload=payload,
    )


async def list_repository_shares(*, source_project_uuid: str | None = None) -> list[dict[str, Any]]:
    """List repository shares visible to the current user."""
    query = ""
    if source_project_uuid:
        query = "?" + urlencode({"source_project_uuid": source_project_uuid})
    url = f"{_base_url()}/api/v1/sync/repository-shares/{query}"

    async with OAuthHttpClient() as client:
        response = await client.get(url)
    if response.status_code != 200:
        raise _error_from_response(response)

    data = response.json()
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        return data["results"]
    if isinstance(data, list):
        return data
    raise RepositorySharingClientError("Unexpected repository share response shape.")


async def request_repository_share(*, source_project_uuid: str, destination_team_slug: str) -> dict[str, Any]:
    """Create or refresh a repository share request."""
    url = f"{_base_url()}/api/v1/sync/repository-shares/"
    payload = {
        "source_project_uuid": source_project_uuid,
        "destination_team_slug": destination_team_slug,
    }

    async with OAuthHttpClient() as client:
        response = await client.post(url, json=payload)
    if response.status_code not in {200, 201}:
        raise _error_from_response(response)
    data = response.json()
    if not isinstance(data, dict):
        raise RepositorySharingClientError("Unexpected repository share response shape.")
    return data


def list_repository_shares_sync(*, source_project_uuid: str | None = None) -> list[dict[str, Any]]:
    """Synchronous wrapper for CLI command code."""
    return asyncio.run(list_repository_shares(source_project_uuid=source_project_uuid))


def request_repository_share_sync(*, source_project_uuid: str, destination_team_slug: str) -> dict[str, Any]:
    """Synchronous wrapper for CLI command code."""
    return asyncio.run(
        request_repository_share(
            source_project_uuid=source_project_uuid,
            destination_team_slug=destination_team_slug,
        )
    )


async def delete_private_project(*, source_project_uuid: str) -> dict[str, Any]:
    """Delete private-only SaaS data for one checkout/project."""
    url = f"{_base_url()}/api/v1/sync/projects/{source_project_uuid}/forget-private/"

    async with OAuthHttpClient() as client:
        response = await client.post(url, json={})
    if response.status_code != 200:
        raise _error_from_response(response)
    data = response.json()
    if not isinstance(data, dict):
        raise RepositorySharingClientError("Unexpected private-project deletion response shape.")
    return data


def delete_private_project_sync(*, source_project_uuid: str) -> dict[str, Any]:
    """Synchronous wrapper for CLI command code."""
    return asyncio.run(delete_private_project(source_project_uuid=source_project_uuid))
