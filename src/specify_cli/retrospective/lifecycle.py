"""Lifecycle terminus invocation. Filled out by WP06.

This module hosts the lifecycle terminus runner protocol that WP06 will
implement in ``src/specify_cli/next/_internal_runtime/retrospective_terminus.py``.
For now it provides the minimal type stubs and protocol definition that
gate.py and other callers need.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from specify_cli.retrospective.schema import ActorRef


class LifecycleStub(Protocol):
    """Type protocol for the lifecycle terminus runner. Implemented in WP06."""

    def run_terminus(
        self,
        *,
        mission_id: str,
        feature_dir: Path,
        repo_root: Path,
        actor: ActorRef,
    ) -> None:
        """Run the retrospective lifecycle terminus.

        Args:
            mission_id: Canonical ULID mission identity.
            feature_dir: Path to ``kitty-specs/<slug>/``.
            repo_root: Repository root (used for charter / mode resolution).
            actor: The actor initiating the terminus (human operator or runtime).
        """
        ...
