# Contracts — relocate-saas-sync-flag-to-core-01KWQ3RV

This mission introduces **no new API/data contract**. It relocates a pure
env-flag reader within the import graph.

The mission does **update** an existing stability contract (FR-006):
`kitty-specs/082-stealth-gated-saas-sync-hardening/contracts/saas_rollout.md`
— to reflect the new canonical home (`core/saas_sync_config.py`) and the
retained `saas/rollout.py` shim, with a version bump. That file remains the
single authority the round-trip test (`tests/contract/test_example_round_trip.py`)
enforces; it is not duplicated here.

This directory exists to satisfy the software-dev mission's path convention.
