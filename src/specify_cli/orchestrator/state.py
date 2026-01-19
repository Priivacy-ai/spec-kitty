"""State management for orchestration runs.

This module handles:
    - OrchestrationRun and WPExecution dataclasses
    - State persistence to .kittify/orchestration-state.json
    - State loading for resume capability
    - State updates during execution
    - Active orchestration detection

Implemented in WP04.
"""
