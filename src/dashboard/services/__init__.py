"""Dashboard service objects.

The mission/WP registries below are the **single sanctioned reader** for
``kitty-specs/`` data on the transport side. Direct scanner imports from
transport modules (FastAPI routers, CLI command bodies, MCP tools) are
forbidden by the architectural test
``tests/architectural/test_transport_does_not_import_scanner.py``
(authored by WP05 of mission
``mission-registry-and-api-boundary-doctrine-01KQPDBB``).
"""
from dashboard.services.registry import (
    CacheEntry,
    LaneCounts,
    MissionRecord,
    MissionRegistry,
    WorkPackageRecord,
    WorkPackageRegistry,
)

__all__ = [
    "CacheEntry",
    "LaneCounts",
    "MissionRecord",
    "MissionRegistry",
    "WorkPackageRecord",
    "WorkPackageRegistry",
]
