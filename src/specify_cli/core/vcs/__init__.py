"""
VCS Abstraction Package
=======================

This package provides a unified interface for Version Control System operations,
supporting both Git and Jujutsu (jj) backends.

Usage:
    from specify_cli.core.vcs import (
        VCSProtocol,
        VCSBackend,
        VCSCapabilities,
        GIT_CAPABILITIES,
        JJ_CAPABILITIES,
    )

The factory function `get_vcs()` and backend implementations (GitVCS, JujutsuVCS)
will be added in WP02-WP04.

See kitty-specs/015-first-class-jujutsu-vcs-integration/ for full documentation.
"""

from __future__ import annotations

# Enums
from .types import (
    ConflictType,
    SyncStatus,
    VCSBackend,
)

# Dataclasses
from .types import (
    ChangeInfo,
    ConflictInfo,
    FeatureVCSConfig,
    OperationInfo,
    ProjectVCSConfig,
    SyncResult,
    VCSCapabilities,
    WorkspaceCreateResult,
    WorkspaceInfo,
)

# Capability constants
from .types import (
    GIT_CAPABILITIES,
    JJ_CAPABILITIES,
)

# Protocol
from .protocol import VCSProtocol

# Exceptions
from .exceptions import (
    VCSBackendMismatchError,
    VCSCapabilityError,
    VCSConflictError,
    VCSError,
    VCSLockError,
    VCSNotFoundError,
    VCSSyncError,
)

__all__ = [
    # Enums
    "VCSBackend",
    "SyncStatus",
    "ConflictType",
    # Dataclasses
    "VCSCapabilities",
    "ChangeInfo",
    "ConflictInfo",
    "SyncResult",
    "WorkspaceInfo",
    "OperationInfo",
    "WorkspaceCreateResult",
    "ProjectVCSConfig",
    "FeatureVCSConfig",
    # Capability constants
    "GIT_CAPABILITIES",
    "JJ_CAPABILITIES",
    # Protocol
    "VCSProtocol",
    # Exceptions
    "VCSError",
    "VCSNotFoundError",
    "VCSCapabilityError",
    "VCSBackendMismatchError",
    "VCSLockError",
    "VCSConflictError",
    "VCSSyncError",
]
