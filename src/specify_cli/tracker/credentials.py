"""Tracker credential storage in ~/.spec-kitty/credentials."""

from __future__ import annotations

import json
import os
import sys
import tomllib
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

try:  # pragma: no cover - optional dependency
    import toml  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    toml = None  # type: ignore[assignment]

if sys.platform == "win32":
    import msvcrt
else:  # pragma: no cover - platform-specific
    import fcntl


class TrackerCredentialError(RuntimeError):
    """Raised when credentials cannot be loaded or stored."""


def _spec_kitty_dir() -> Path:
    return Path.home() / ".spec-kitty"


def _credentials_path() -> Path:
    return _spec_kitty_dir() / "credentials"


def _toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_scalar(item) for item in value) + "]"
    if value is None:
        return '""'
    return json.dumps(str(value), ensure_ascii=False)


def _write_toml(payload: dict[str, Any]) -> str:
    if toml is not None:  # pragma: no branch
        return str(toml.dumps(payload))

    lines: list[str] = []

    def emit_table(prefix: str, table: dict[str, Any]) -> None:
        lines.append(f"[{prefix}]")
        scalar_keys = sorted(key for key, value in table.items() if not isinstance(value, dict))
        nested_keys = sorted(key for key, value in table.items() if isinstance(value, dict))

        for key in scalar_keys:
            lines.append(f"{key} = {_toml_scalar(table[key])}")

        for key in nested_keys:
            lines.append("")
            emit_table(f"{prefix}.{key}", table[key])

    root_scalar_keys = sorted(key for key, value in payload.items() if not isinstance(value, dict))
    root_table_keys = sorted(key for key, value in payload.items() if isinstance(value, dict))

    for key in root_scalar_keys:
        lines.append(f"{key} = {_toml_scalar(payload[key])}")

    for key in root_table_keys:
        if lines:
            lines.append("")
        emit_table(key, payload[key])

    return ("\n".join(lines).rstrip() + "\n") if lines else ""


@contextmanager
def _locked_file(path: Path, mode: str) -> Iterator[Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode, encoding="utf-8") as handle:
        if sys.platform == "win32":
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:  # pragma: no cover - platform-specific
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield handle
        finally:
            if sys.platform == "win32":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:  # pragma: no cover - platform-specific
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class TrackerCredentialStore:
    """Store tracker provider credentials in ~/.spec-kitty/credentials."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or _credentials_path()

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}

        try:
            with _locked_file(self.path, "r") as handle:
                raw = handle.read()
            payload = tomllib.loads(raw) if raw.strip() else {}
        except Exception as exc:  # pragma: no cover - defensive
            raise TrackerCredentialError(f"Failed to load credentials: {exc}") from exc

        return payload if isinstance(payload, dict) else {}

    def save(self, payload: dict[str, Any]) -> None:
        try:
            with _locked_file(self.path, "w") as handle:
                handle.write(_write_toml(payload))
            if os.name != "nt":
                os.chmod(self.path, 0o600)
        except Exception as exc:  # pragma: no cover - defensive
            raise TrackerCredentialError(f"Failed to save credentials: {exc}") from exc

    def get_provider(self, provider: str) -> dict[str, Any]:
        payload = self.load()
        tracker = payload.get("tracker") if isinstance(payload, dict) else None
        providers = tracker.get("providers") if isinstance(tracker, dict) else None
        provider_payload = providers.get(provider) if isinstance(providers, dict) else None
        return dict(provider_payload) if isinstance(provider_payload, dict) else {}

    def set_provider(self, provider: str, values: dict[str, Any]) -> None:
        payload = self.load()
        tracker = payload.setdefault("tracker", {})
        if not isinstance(tracker, dict):
            tracker = {}
            payload["tracker"] = tracker

        providers = tracker.setdefault("providers", {})
        if not isinstance(providers, dict):
            providers = {}
            tracker["providers"] = providers

        providers[provider] = {
            str(key): value
            for key, value in values.items()
            if str(key).strip() and value is not None and str(value).strip()
        }
        self.save(payload)

    def clear_provider(self, provider: str) -> None:
        payload = self.load()
        tracker = payload.get("tracker") if isinstance(payload, dict) else None
        providers = tracker.get("providers") if isinstance(tracker, dict) else None
        if not isinstance(providers, dict) or provider not in providers:
            return

        del providers[provider]
        self.save(payload)
