"""Project-scoped tracker configuration in .kittify/config.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml import YAML

from specify_cli.core.paths import locate_project_root


class TrackerConfigError(RuntimeError):
    """Raised when tracker configuration is invalid."""


@dataclass(slots=True)
class TrackerProjectConfig:
    """Tracker configuration stored inside .kittify/config.yaml."""

    provider: str | None = None
    workspace: str | None = None
    doctrine_mode: str = "external_authoritative"
    doctrine_field_owners: dict[str, str] = field(default_factory=dict)

    @property
    def is_configured(self) -> bool:
        return bool(self.provider and self.workspace)

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "workspace": self.workspace,
            "doctrine": {
                "mode": self.doctrine_mode,
                "field_owners": dict(self.doctrine_field_owners),
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, object] | None) -> "TrackerProjectConfig":
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
        workspace = data.get("workspace")
        return cls(
            provider=str(provider).strip() if isinstance(provider, str) and provider.strip() else None,
            workspace=str(workspace).strip() if isinstance(workspace, str) and workspace.strip() else None,
            doctrine_mode=doctrine_mode,
            doctrine_field_owners=doctrine_field_owners,
        )


def require_repo_root() -> Path:
    """Resolve the current project root or raise a user-facing error."""
    repo_root = locate_project_root(Path.cwd())
    if repo_root is None:
        raise TrackerConfigError(
            "Not inside a spec-kitty project. Run this command from a project with .kittify/."
        )
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
    config_path.parent.mkdir(parents=True, exist_ok=True)

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

    with config_path.open("w", encoding="utf-8") as handle:
        yaml.dump(payload, handle)


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
