"""SHA-256 hasher for constitution content."""

import hashlib
from pathlib import Path

from ruamel.yaml import YAML


def hash_content(content: str) -> str:
    """Generate SHA-256 hash of constitution content.

    Args:
        content: Constitution markdown text

    Returns:
        Hash string in format "sha256:hexdigest"
    """
    # Normalize whitespace (strip trailing newlines)
    normalized = content.strip()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def hash_constitution(constitution_path: Path) -> str:
    """Compute SHA-256 hash of constitution file.

    Args:
        constitution_path: Path to constitution.md file

    Returns:
        Hash string in format "sha256:hexdigest"
    """
    content = constitution_path.read_text("utf-8")
    return hash_content(content)


def is_stale(constitution_path: Path | None, metadata_path: Path, content: str | None = None) -> tuple[bool, str, str]:
    """Check if constitution has changed since last sync.

    Args:
        constitution_path: Path to constitution.md (None if using content directly)
        metadata_path: Path to metadata.yaml
        content: Optional pre-read content (avoids TOCTOU race condition)

    Returns:
        Tuple of (is_stale, current_hash, stored_hash)
        - is_stale: True if constitution needs re-extraction
        - current_hash: Hash of current constitution content
        - stored_hash: Hash from metadata.yaml (empty string if no metadata)
    """
    if content is not None:
        current_hash = hash_content(content)
    elif constitution_path is not None:
        current_hash = hash_constitution(constitution_path)
    else:
        raise ValueError("Either constitution_path or content must be provided")

    if not metadata_path.exists():
        return True, current_hash, ""

    yaml = YAML()
    metadata = yaml.load(metadata_path)
    stored_hash = metadata.get("constitution_hash", "") if metadata else ""

    return current_hash != stored_hash, current_hash, stored_hash
