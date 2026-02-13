from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

VALID_PHASES = (0, 1, 2)
DEFAULT_PHASE = 1
DEFAULT_PHASE_SOURCE = "built-in default (Phase 1: dual-write)"
MAX_PHASE_01X = 2


def resolve_phase(repo_root: Path, feature_slug: str) -> tuple[int, str]:
    """Resolve active status phase. Precedence: meta.json > config.yaml > default.

    On 0.1x branch, caps at MAX_PHASE_01X. Returns (phase, source_description).
    """
    meta_phase = _read_meta_phase(repo_root, feature_slug)
    if meta_phase is not None:
        phase = meta_phase
        source = f"meta.json override for {feature_slug}"
    else:
        config_phase = _read_config_phase(repo_root)
        if config_phase is not None:
            phase = config_phase
            source = "global default from .kittify/config.yaml"
        else:
            phase = DEFAULT_PHASE
            source = DEFAULT_PHASE_SOURCE

    if is_01x_branch(repo_root) and phase > MAX_PHASE_01X:
        logger.info("Phase %d capped to %d on 0.1x branch", phase, MAX_PHASE_01X)
        phase = MAX_PHASE_01X
        source = f"{source} (capped to {MAX_PHASE_01X} on 0.1x)"

    return phase, source


def _read_meta_phase(repo_root: Path, feature_slug: str) -> int | None:
    """Read status_phase from feature meta.json. Returns None if not set or invalid."""
    meta_path = repo_root / "kitty-specs" / feature_slug / "meta.json"
    if not meta_path.exists():
        return None
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        raw = data.get("status_phase")
        if raw is None:
            return None
        phase = int(raw)
        if phase not in VALID_PHASES:
            logger.warning("Invalid status_phase %d in %s, ignoring", phase, meta_path)
            return None
        return phase
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Failed to read status_phase from %s: %s", meta_path, exc)
        return None


def _read_config_phase(repo_root: Path) -> int | None:
    """Read status.phase from .kittify/config.yaml. Returns None if not set."""
    config_path = repo_root / ".kittify" / "config.yaml"
    if not config_path.exists():
        return None
    try:
        from ruamel.yaml import YAML

        yaml = YAML()
        data = yaml.load(config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        status_section = data.get("status")
        if not isinstance(status_section, dict):
            return None
        raw = status_section.get("phase")
        if raw is None:
            return None
        phase = int(raw)
        if phase not in VALID_PHASES:
            logger.warning(
                "Invalid status.phase %d in %s, ignoring", phase, config_path
            )
            return None
        return phase
    except Exception as exc:
        logger.warning("Failed to read status.phase from %s: %s", config_path, exc)
        return None


def is_01x_branch(repo_root: Path) -> bool:
    """Check if current git branch is on the 0.1x line (main, release/*, etc.)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        if result.returncode != 0:
            return False
        branch = result.stdout.strip()
        if branch.startswith("2.") or branch == "2.x":
            return False
        if branch.startswith("034-"):
            return False
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return False
