"""
VCS Abstraction Package
=======================

This package provides a unified interface for Version Control System operations,
supporting both Git and Jujutsu (jj) backends.

Usage:
    from specify_cli.core.vcs import (
        get_vcs,
        VCSProtocol,
        VCSBackend,
        VCSCapabilities,
        GIT_CAPABILITIES,
        JJ_CAPABILITIES,
        is_jj_available,
        is_git_available,
    )

    # Get appropriate VCS implementation
    vcs = get_vcs(feature_path)  # Auto-detect, prefers jj
    vcs = get_vcs(feature_path, backend=VCSBackend.GIT)  # Explicit git

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

# Detection and factory functions
from .detection import (
    detect_available_backends,
    get_git_version,
    get_jj_version,
    get_vcs,
    is_git_available,
    is_jj_available,
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
    # Detection and factory
    "get_vcs",
    "is_jj_available",
    "is_git_available",
    "get_jj_version",
    "get_git_version",
    "detect_available_backends",
]
