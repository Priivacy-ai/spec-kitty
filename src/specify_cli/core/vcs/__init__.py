"""
VCS Abstraction Package
=======================

This package provides a unified interface for Version Control System operations,
supporting Git as the backend.

Usage:
    from specify_cli.core.vcs import (
        get_vcs,
        VCSProtocol,
        VCSBackend,
        VCSCapabilities,
        GIT_CAPABILITIES,
        is_git_available,
    )

    # Get appropriate VCS implementation
    vcs = get_vcs(feature_path)  # Auto-detect
    vcs = get_vcs(feature_path, backend=VCSBackend.GIT)  # Explicit git
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

# Detection and factory functions
from .detection import (
    detect_available_backends,
    get_git_version,
    get_vcs,
    is_git_available,
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
    # Detection and factory
    "get_vcs",
    "is_git_available",
    "get_git_version",
    "detect_available_backends",
]
