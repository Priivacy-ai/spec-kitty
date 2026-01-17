"""
VCS Exceptions Module
=====================

This module defines the exception hierarchy for VCS operations.
All VCS-related exceptions inherit from VCSError.
"""

from __future__ import annotations


class VCSError(Exception):
    """
    Base exception for VCS operations.

    All VCS-related exceptions inherit from this class.
    """

    pass


class VCSNotFoundError(VCSError):
    """
    Neither jj nor git is available.

    Raised when attempting VCS operations but no supported
    VCS tool is installed or accessible.
    """

    pass


class VCSCapabilityError(VCSError):
    """
    Operation not supported by this backend.

    Raised when attempting an operation that the current
    VCS backend does not support (e.g., jj undo on git).
    """

    pass


class VCSBackendMismatchError(VCSError):
    """
    Requested backend doesn't match feature's locked VCS.

    Raised when explicitly requesting a backend that differs
    from the VCS locked in the feature's meta.json.
    """

    pass


class VCSLockError(VCSError):
    """
    Attempted to change VCS for a feature after it was locked.

    Once a feature has its VCS set (on first workspace creation),
    it cannot be changed. This exception is raised on such attempts.
    """

    pass


class VCSConflictError(VCSError):
    """
    Operation blocked due to unresolved conflicts.

    Raised when an operation cannot proceed because the
    workspace has unresolved conflicts that must be addressed first.
    """

    pass


class VCSSyncError(VCSError):
    """
    Sync operation failed.

    Raised when workspace synchronization fails due to
    network issues, permissions, or other errors.
    """

    pass
