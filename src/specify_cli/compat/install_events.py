"""Post-upgrade installation verification event types (FR-012).

Public surface
--------------
VerificationConfidence      -- StrEnum with 3 confidence levels.
UvToolInstallationVerified  -- Frozen dataclass: post-upgrade verification event.

Security properties
-------------------
NFR-007: No PII. ``receipt_path`` is included for auditability but the event
consumer MUST NOT log or transmit it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


# ---------------------------------------------------------------------------
# VerificationConfidence enum
# ---------------------------------------------------------------------------


class VerificationConfidence(StrEnum):
    """Confidence level for post-upgrade installation verification.

    Confidence derivation:
    - HIGH:   exit_code == 0 AND entrypoint_match == True
    - MEDIUM: exit_code == 0 AND entrypoint_match == False
    - LOW:    exit_code != 0
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ---------------------------------------------------------------------------
# UvToolInstallationVerified event dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UvToolInstallationVerified:
    """Event emitted after a uv-tool upgrade attempt completes.

    Emitted by ``_default_upgrade_runner`` in ``upgrade_ux.py`` when
    ``install_method == UV_TOOL``, regardless of outcome.

    NFR-007: No PII. ``receipt_path`` is included for auditability
    but the event consumer MUST NOT log or transmit it.

    Confidence derivation:
    - HIGH:   exit_code == 0 AND entrypoint_match == True
    - MEDIUM: exit_code == 0 AND entrypoint_match == False
    - LOW:    exit_code != 0
    """

    receipt_path: Path | None         # path to uv-receipt.toml post-upgrade
    entrypoint_match: bool            # True if spec-kitty entrypoint is present post-upgrade
    package_binding: str              # package name + specifier from receipt, or "unknown"
    confidence: VerificationConfidence
