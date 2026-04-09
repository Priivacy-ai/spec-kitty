"""OAuth HTTP transport layer.

Provides `OAuthHttpClient`, an httpx-based async HTTP client that injects bearer
tokens from the process-wide `TokenManager` and automatically retries once on
401 responses after refreshing the access token.
"""

from __future__ import annotations

from .transport import OAuthHttpClient

__all__ = ["OAuthHttpClient"]
