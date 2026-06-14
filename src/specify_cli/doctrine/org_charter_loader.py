"""Helpers for assembling the ``org_charter`` JSON block surfaced by ``charter context --json``.

This module lives in ``specify_cli`` (the highest layer) and is responsible
for materialising the data structure that :func:`charter.context.build_charter_context_json`
embeds under the ``org_charter`` key.

Architectural note
------------------
The charter layer is forbidden from importing ``specify_cli`` (ADR
2026-03-27-1).  All org-layer policy reads therefore happen here; the result
is passed *as data* into the charter layer.

WP09 owns ``specify_cli.doctrine.org_charter`` (the policy schema + loader).
This module imports that loader lazily so WP07 ships independently — when
WP09 is not yet installed, the org-charter block degrades to
``{"present": false, "packs": []}``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


_EMPTY_BLOCK: dict[str, Any] = {"present": False, "packs": []}


def load_org_charter_json_block(org_roots: list[Path] | None) -> dict[str, Any]:
    """Return the ``org_charter`` JSON block for the configured org snapshots.

    Walks every supplied org snapshot path looking for an ``org-charter.yaml``
    file and merges the resulting policy summaries into a single block.
    The block shape is::

        {
            "present": bool,
            "packs": [
                {
                    "pack_name": str,
                    "governance_policies": [{..., "source": "org"}, ...],
                    "required_directives": [str, ...]
                },
                ...
            ]
        }

    Returns the empty block (``present=False``, ``packs=[]``) when:

    * ``org_roots`` is empty or ``None``;
    * the optional WP09 module ``specify_cli.doctrine.org_charter`` is not
      installed;
    * none of the configured packs ship an ``org-charter.yaml``.
    """
    if not org_roots:
        return dict(_EMPTY_BLOCK)

    try:
        from specify_cli.doctrine.org_charter import (
            load_org_charter_policy,
        )
    except ImportError:
        return dict(_EMPTY_BLOCK)

    pack_entries: list[dict[str, Any]] = []
    for org_root in org_roots:
        if not org_root.exists():
            continue
        charter_path = org_root / "org-charter.yaml"
        if not charter_path.exists():
            continue
        try:
            policy = load_org_charter_policy(org_root)
        except Exception:  # noqa: BLE001, S112 — best-effort summary; continue with next pack
            continue
        if policy is None:
            continue

        governance_policies: list[dict[str, Any]] = []
        for gp in getattr(policy, "governance_policies", []) or []:
            try:
                entry = gp.model_dump() if hasattr(gp, "model_dump") else dict(gp)
            except Exception:  # noqa: BLE001, S112 — best-effort summary; skip malformed entry
                continue
            entry["source"] = "org"
            governance_policies.append(entry)

        pack_entries.append(
            {
                "pack_name": getattr(policy, "org_name", None) or org_root.name,
                "governance_policies": governance_policies,
                "required_directives": list(
                    getattr(policy, "required_directives", []) or []
                ),
            }
        )

    return {"present": bool(pack_entries), "packs": pack_entries}


__all__ = ["load_org_charter_json_block"]
