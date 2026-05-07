"""Public re-export surface for the dashboard HTML template helpers.

The canonical implementation lives in ``specify_cli.dashboard.templates``.
This module provides a clean import path for ``dashboard.api.routers.*``
that must not import from ``specify_cli.dashboard.*`` (FR-010 of mission
``dashboard-service-extraction-01KQMCA6``, preserved by mission
``frontend-api-fastapi-openapi-migration-01KQN2JA``).

removal_release: HTML template relocation outside ``specify_cli.dashboard``
(no mission scheduled yet — file a tracker issue if/when that work is
sequenced).
"""
# ruff: noqa: F401
from specify_cli.dashboard.templates import get_dashboard_html, get_dashboard_html_bytes
