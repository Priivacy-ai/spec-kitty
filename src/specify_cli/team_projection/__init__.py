"""Team/public projection package (D1-T1).

Read-only, deterministic team-index / per-mission-snapshot / explicit-public
variants, serialized deterministically with exact-commit provenance and an
attestation manifest. See ``m1-contract-drafts/D1.md`` for the full contract.

This package introduces no server, no transport, no rendering, and no
provider call — see ``write.py`` for the sole file-writing entry point and
``provenance.py``/``attestation.py`` for the producer-only attestation story.
"""

from __future__ import annotations
