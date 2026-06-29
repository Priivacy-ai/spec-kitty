"""Delivery domain (WP04+): target registry, ledger, receiver, dispatcher seams.

A thin, side-effect-free public surface. The four ``typing.Protocol`` seams and
their exchanged value objects live in :mod:`specify_cli.delivery.interfaces`
(the IC-01 / C-001 abstraction); the concrete delivery-target registry lives in
:mod:`specify_cli.delivery.targets`. Importing this package never touches the
filesystem or a database.
"""
from __future__ import annotations

from specify_cli.delivery.interfaces import (
    DeliveryLedger,
    DeliveryReceiver,
    DeliveryTarget,
    DeliveryTargetRegistry,
    DeploymentMetadata,
    Dispatcher,
    ResetSignal,
    TargetIdentity,
)
from specify_cli.delivery.targets import (
    InvalidTargetUrlError,
    SqliteDeliveryTargetRegistry,
    canonicalize_url,
    compute_url_hash,
)

__all__ = [
    # Protocol seams (interfaces.py)
    "DeliveryTargetRegistry",
    "DeliveryLedger",
    "DeliveryReceiver",
    "Dispatcher",
    # Value objects (interfaces.py)
    "TargetIdentity",
    "DeliveryTarget",
    "ResetSignal",
    "DeploymentMetadata",
    # Concrete registry + pure helpers (targets.py)
    "SqliteDeliveryTargetRegistry",
    "canonicalize_url",
    "compute_url_hash",
    "InvalidTargetUrlError",
]
