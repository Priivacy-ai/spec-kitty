"""Project-scoped tracker configuration in .kittify/config.yaml."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from ruamel.yaml import YAML

from specify_cli.core.atomic import atomic_write
from specify_cli.core.paths import locate_project_root


# ---------------------------------------------------------------------------
# Provider classification constants (single source of truth)
# ---------------------------------------------------------------------------
SAAS_PROVIDERS: frozenset[str] = frozenset({"linear", "jira", "github", "gitlab"})
LOCAL_PROVIDERS: frozenset[str] = frozenset({"beads", "fp"})
REMOVED_PROVIDERS: frozenset[str] = frozenset({"azure_devops"})
ALL_SUPPORTED_PROVIDERS: frozenset[str] = SAAS_PROVIDERS | LOCAL_PROVIDERS


class TrackerConfigError(RuntimeError):
    """Raised when tracker configuration is invalid."""


@dataclass(slots=True)
class TrackerProjectConfig:
    """Tracker configuration stored inside .kittify/config.yaml."""

    provider: str | None = None
    binding_ref: str | None = None
    project_slug: str | None = None
    display_label: str | None = None
    provider_context: dict[str, str] | None = None
    workspace: str | None = None
    doctrine_mode: str = "external_authoritative"
    doctrine_field_owners: dict[str, str] = field(default_factory=dict)
    _extra: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def is_configured(self) -> bool:
        if not self.provider:
            return False
        if self.provider in SAAS_PROVIDERS:
            return bool(self.binding_ref) or bool(self.project_slug)
        if self.provider in LOCAL_PROVIDERS:
            return bool(self.workspace)
        return False  # Unknown or removed provider

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            **self._extra,  # Unknown fields first (known fields override)
            "provider": self.provider,
            "binding_ref": self.binding_ref,
            "project_slug": self.project_slug,
            "display_label": self.display_label,
            "provider_context": dict(self.provider_context) if self.provider_context else None,
            "workspace": self.workspace,
            "doctrine": {
                "mode": self.doctrine_mode,
                "field_owners": dict(self.doctrine_field_owners),
            },
        }
        return result

    _KNOWN_KEYS: ClassVar[frozenset[str]] = frozenset({
        "provider", "binding_ref", "project_slug", "display_label",
        "provider_context", "workspace", "doctrine",
    })

    @classmethod
    def from_dict(cls, data: dict[str, object] | None) -> TrackerProjectConfig:
        if not isinstance(data, dict):
            return cls()

        doctrine = data.get("doctrine")
        doctrine_mode = "external_authoritative"
        doctrine_field_owners: dict[str, str] = {}
        if isinstance(doctrine, dict):
            mode_value = doctrine.get("mode")
            if isinstance(mode_value, str) and mode_value.strip():
                doctrine_mode = mode_value.strip()
            field_owners = doctrine.get("field_owners")
            if isinstance(field_owners, dict):
                doctrine_field_owners = {
                    str(key): str(value)
                    for key, value in field_owners.items()
                    if str(key).strip() and str(value).strip()
                }

        provider = data.get("provider")
        binding_ref = data.get("binding_ref")
        project_slug = data.get("project_slug")
        display_label = data.get("display_label")
        provider_context_raw = data.get("provider_context")
        workspace = data.get("workspace")

        provider_context: dict[str, str] | None = None
        if isinstance(provider_context_raw, dict):
            provider_context = {
                str(k): str(v) for k, v in provider_context_raw.items()
            }

        extra = {k: v for k, v in data.items() if k not in cls._KNOWN_KEYS}

        return cls(
            provider=str(provider).strip() if isinstance(provider, str) and provider.strip() else None,
            binding_ref=str(binding_ref).strip() if isinstance(binding_ref, str) and binding_ref.strip() else None,
            project_slug=str(project_slug).strip() if isinstance(project_slug, str) and project_slug.strip() else None,
            display_label=(
                str(display_label).strip()
                if isinstance(display_label, str) and display_label.strip()
                else None
            ),
            provider_context=provider_context,
            workspace=str(workspace).strip() if isinstance(workspace, str) and workspace.strip() else None,
            doctrine_mode=doctrine_mode,
            doctrine_field_owners=doctrine_field_owners,
            _extra=extra,
        )


def require_repo_root() -> Path:
    """Resolve the current project root or raise a user-facing error."""
    repo_root = locate_project_root(Path.cwd())
    if repo_root is None:
        raise TrackerConfigError("Not inside a spec-kitty project. Run this command from a project with .kittify/.")
    return repo_root


def _config_path(repo_root: Path) -> Path:
    return repo_root / ".kittify" / "config.yaml"


def load_tracker_config(repo_root: Path) -> TrackerProjectConfig:
    """Load tracker config from .kittify/config.yaml."""
    config_path = _config_path(repo_root)
    if not config_path.exists():
        return TrackerProjectConfig()

    yaml = YAML()
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            payload = yaml.load(handle) or {}
    except Exception as exc:  # pragma: no cover - defensive
        raise TrackerConfigError(f"Failed to parse {config_path}: {exc}") from exc

    tracker_data = payload.get("tracker") if isinstance(payload, dict) else None
    return TrackerProjectConfig.from_dict(tracker_data if isinstance(tracker_data, dict) else None)


def save_tracker_config(repo_root: Path, config: TrackerProjectConfig) -> None:
    """Persist tracker config into .kittify/config.yaml, preserving other sections."""
    config_path = _config_path(repo_root)

    yaml = YAML()
    yaml.preserve_quotes = True

    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as handle:
            payload = yaml.load(handle) or {}
    else:
        payload = {}

    if not isinstance(payload, dict):
        payload = {}

    payload["tracker"] = config.to_dict()

    buf = io.StringIO()
    yaml.dump(payload, buf)
    atomic_write(config_path, buf.getvalue(), mkdir=True)


def clear_tracker_config(repo_root: Path) -> None:
    """Remove tracker config from .kittify/config.yaml if present."""
    config_path = _config_path(repo_root)
    if not config_path.exists():
        return

    yaml = YAML()
    with config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.load(handle) or {}

    if not isinstance(payload, dict) or "tracker" not in payload:
        return

    del payload["tracker"]

    with config_path.open("w", encoding="utf-8") as handle:
        yaml.dump(payload, handle)
