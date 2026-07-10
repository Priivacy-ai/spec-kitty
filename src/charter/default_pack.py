"""Shared loader for the shipped default charter pack's activation ID lists.

Two ``specify_cli`` consumers both need the real built-in ``activated_<kind>``
id sets from ``src/charter/packs/default.yaml``, as the ``default_ids``
argument to :func:`charter.activation_engine.promote_activations` (the WP06
absent-key LAND-BLOCKER safety: promoting into a previously-absent
``activated_<kind>`` config key must materialize every built-in id first,
never write a bare restrictive list):

- :func:`specify_cli.doctrine.org_charter._promote_org_required_to_config`
  (org-required-artefact promotion)
- :class:`specify_cli.upgrade.migrations.m_unify_charter_activation.UnifyCharterActivationMigration`
  (answers-only-selection promotion)

Both landed in the same PR with independent, near-identical readers of the
same file (squad finding #2530). This module is the single canonical loader
both now import — the ``charter`` layer is the correct home because
``org_charter.py`` (specify_cli) and the migration (also specify_cli) are
peers with no dependency relationship to each other, and both are permitted
to import from ``charter`` (specify_cli sits above charter in the layer
chain: kernel <- doctrine <- charter <- glossary/runtime <- specify_cli).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

__all__ = ["load_default_pack_activation_ids"]


def _default_pack_yaml_path(charter_pkg_root: Path | None) -> Path:
    """Resolve the ``packs/default.yaml`` path under *charter_pkg_root*.

    Defaults to this module's own package directory (``src/charter``) —
    i.e. the shipped built-in pack — when *charter_pkg_root* is omitted.
    """
    root = charter_pkg_root if charter_pkg_root is not None else Path(__file__).resolve().parent
    return root / "packs" / "default.yaml"


def load_default_pack_activation_ids(
    charter_pkg_root: Path | None = None,
) -> dict[str, list[str]]:
    """Load the shipped default-pack's ``activated_<kind>`` id lists.

    Reads ``<charter_pkg_root>/packs/default.yaml`` (defaults to
    ``src/charter/packs/default.yaml``, the pack shipped with spec-kitty) and
    returns every top-level list-valued key verbatim — already in
    ``activated_<kind>`` form (``config.yaml``'s own key naming), so callers
    select only the keys they need via ``dict.get``.

    Returns ``{}`` when the file is absent, unreadable, empty, malformed
    YAML, or not a mapping — callers must treat an empty dict as "no real
    built-in default available" and must NOT silently synthesize one (see
    the WP06 absent-key LAND-BLOCKER note in
    :func:`charter.activation_engine.promote_activations`).

    Args:
        charter_pkg_root: Optional override for the ``charter`` package root
            (primarily for tests exercising a synthetic pack directory).
            Defaults to this module's own directory.
    """
    default_pack_path = _default_pack_yaml_path(charter_pkg_root)
    if not default_pack_path.exists():
        return {}
    yaml = YAML(typ="safe")
    try:
        raw: Any = yaml.load(default_pack_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — malformed YAML degrades to empty, caller decides
        return {}
    if not isinstance(raw, dict):
        return {}
    return {key: list(value) for key, value in raw.items() if isinstance(value, list)}
