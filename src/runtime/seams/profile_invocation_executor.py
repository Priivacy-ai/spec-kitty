"""ProfileInvocationExecutor — canonical boundary reference (FR-009).

Phase 4 of #461 shipped ProfileInvocationExecutor at:
    specify_cli.invocation.executor.ProfileInvocationExecutor

Runtime code that needs to call into profile-governed invocations
imports from this module so the dependency is documented here.

Do NOT move or re-implement the executor — it lives in invocation/.
"""
from __future__ import annotations

from specify_cli.invocation.executor import ProfileInvocationExecutor

__all__ = ["ProfileInvocationExecutor"]
