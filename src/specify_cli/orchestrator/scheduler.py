"""Scheduler for orchestrating work package execution.

This module handles:
    - Dependency graph reading from WP frontmatter
    - Ready WP detection (dependencies satisfied)
    - Agent selection by role and priority
    - Concurrency management via semaphores
    - Single-agent mode handling

Implemented in WP05.
"""
