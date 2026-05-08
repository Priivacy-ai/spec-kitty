# SHIM — removal_release: 3.2.0
# Owner: dashboard-services-domain-migration-01KR151P
# Canonical home: src/specify_cli/missions/project_state.py
# Do not add business logic here. Edit specify_cli/missions/project_state.py instead.
# This shim will be deleted in Phase C (after release 3.2.0).
from specify_cli.missions.project_state import ProjectStateService

__all__ = ["ProjectStateService"]
