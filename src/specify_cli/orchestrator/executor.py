"""Executor for spawning and managing agent processes.

This module handles:
    - Async process spawning with asyncio.create_subprocess_exec
    - Stdin piping for prompts
    - stdout/stderr capture to log files
    - Timeout enforcement with proper cleanup
    - Worktree creation integration

Implemented in WP06.
"""
