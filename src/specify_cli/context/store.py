"""Persistence layer for context token JSON files.

Context tokens are stored as individual JSON files in
``.kittify/runtime/contexts/<token>.json``. All writes are atomic
(write to temp file, then ``os.replace``).
"""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.context.errors import ContextCorruptedError, ContextNotFoundError
from specify_cli.context.models import ContextToken, MissionContext
from specify_cli.core.atomic import atomic_write


def _contexts_dir(repo_root: Path) -> Path:
    """Return the directory where context token files are stored."""
    return repo_root / ".kittify" / "runtime" / "contexts"


def save_context(context: MissionContext, repo_root: Path) -> ContextToken:
    """Persist a MissionContext to disk as a JSON file.

    Creates the ``.kittify/runtime/contexts/`` directory if it does not
    exist. Uses atomic writes so the file is never partially written.

    Args:
        context: The MissionContext to persist.
        repo_root: Repository root path.

    Returns:
        A ContextToken with the token string and the path to the file.
    """
    contexts_dir = _contexts_dir(repo_root)
    contexts_dir.mkdir(parents=True, exist_ok=True)

    context_path = contexts_dir / f"{context.token}.json"
    content = json.dumps(context.to_dict(), indent=2, sort_keys=True) + "\n"
    atomic_write(context_path, content)

    return ContextToken(token=context.token, context_path=context_path)


def load_context(token: str, repo_root: Path) -> MissionContext:
    """Load a MissionContext from a persisted JSON file.

    Args:
        token: The opaque context token string (e.g., "ctx-01HV...").
        repo_root: Repository root path.

    Returns:
        The deserialized MissionContext.

    Raises:
        ContextNotFoundError: If the token file does not exist.
        ContextCorruptedError: If the file contains invalid JSON.
    """
    context_path = _contexts_dir(repo_root) / f"{token}.json"

    if not context_path.exists():
        msg = (
            f"Context token '{token}' not found at {context_path}. "
            "Run `spec-kitty agent context resolve --wp <WP> --mission <slug>` "
            "to create a new context."
        )
        raise ContextNotFoundError(msg)

    try:
        data = json.loads(context_path.read_text(encoding="utf-8"))
        return MissionContext.from_dict(data)
    except (json.JSONDecodeError, TypeError) as exc:
        msg = f"Context token '{token}' is corrupted at {context_path}: {exc}"
        raise ContextCorruptedError(msg) from exc
    except KeyError as exc:
        msg = f"Context token '{token}' is missing required field: {exc}"
        raise ContextCorruptedError(msg) from exc


def list_contexts(repo_root: Path) -> list[ContextToken]:
    """List all persisted context tokens.

    Args:
        repo_root: Repository root path.

    Returns:
        A list of ContextToken objects for each ``.json`` file in the
        contexts directory. Returns an empty list if the directory does
        not exist.
    """
    contexts_dir = _contexts_dir(repo_root)
    if not contexts_dir.exists():
        return []

    tokens: list[ContextToken] = []
    for path in sorted(contexts_dir.glob("*.json")):
        tokens.append(ContextToken(token=path.stem, context_path=path))
    return tokens


def delete_context(token: str, repo_root: Path) -> None:
    """Delete a persisted context token file.

    No error is raised if the file does not exist.

    Args:
        token: The opaque context token string.
        repo_root: Repository root path.
    """
    context_path = _contexts_dir(repo_root) / f"{token}.json"
    if context_path.exists():
        context_path.unlink()
