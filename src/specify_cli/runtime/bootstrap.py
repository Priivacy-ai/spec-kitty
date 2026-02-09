"""Runtime bootstrap: ensure_runtime() and related functions.

Provides version pin detection and warning for projects that set
``runtime.pin_version`` in their ``.kittify/config.yaml``.
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def check_version_pin(project_dir: Path) -> None:
    """Check for runtime.pin_version in project config and warn if present.

    Version pinning is not yet supported.  When a pin is detected the
    function emits both a ``logging.warning`` and a ``UserWarning`` so
    that CI pipelines and interactive users alike are notified.  The
    pinned version is **never** silently honored -- the latest global
    assets are always used.

    Args:
        project_dir: Project root containing ``.kittify/``.
    """
    config_path = project_dir / ".kittify" / "config.yaml"
    if not config_path.exists():
        return

    try:
        config = yaml.safe_load(config_path.read_text())
    except Exception:
        # Config parsing failure handled elsewhere
        return

    if not config or not isinstance(config, dict):
        return

    runtime = config.get("runtime", {})
    if not isinstance(runtime, dict):
        return

    if "pin_version" not in runtime:
        return

    pin = runtime["pin_version"]
    msg = (
        f"runtime.pin_version={pin} found in .kittify/config.yaml. "
        f"Version pinning is not yet supported. Using latest global assets. "
        f"The pin will NOT be silently honored."
    )
    logger.warning(msg)
    warnings.warn(msg, UserWarning, stacklevel=2)
