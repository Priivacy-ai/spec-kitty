"""Internal DRG loading helper for charter_lint.

Wraps the doctrine DRG package behind a thin, exception-safe façade.
Callers receive a duck-typed DRG object or ``None`` when the DRG is
unavailable (package not installed, file missing, etc.).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def load_merged_drg(repo_root: Path) -> Any | None:
    """Load the merged DRG from ``.kittify/doctrine/``.

    Returns a ``DRGGraph`` instance, or ``None`` when:

    - the ``doctrine`` package is not importable, or
    - no recognised graph file exists under ``.kittify/doctrine/``, or
    - any other error occurs during loading.

    The search order matches the one used by ``entity_pages.py``::

        graph.yaml > merged_drg.json > drg.json > compiled_drg.json
    """
    try:
        from doctrine.drg.models import DRGGraph  # type: ignore[import]
        from ruamel.yaml import YAML  # type: ignore[import]

        drg_dir = repo_root / ".kittify" / "doctrine"
        candidates = ["graph.yaml", "merged_drg.json", "drg.json", "compiled_drg.json"]
        for name in candidates:
            p = drg_dir / name
            if p.exists():
                text = p.read_text(encoding="utf-8")
                if name.endswith((".yaml", ".yml")):
                    yaml = YAML()
                    raw = yaml.load(text)
                else:
                    raw = json.loads(text)
                return DRGGraph.model_validate(raw)
        return None
    except Exception:  # noqa: BLE001
        logger.debug("charter_lint._drg: DRG not available", exc_info=True)
        return None


def get_nodes_by_kind(drg: Any, kind_str: str) -> list[Any]:
    """Return all nodes whose ``kind`` value equals *kind_str*.

    Works with both enum-valued and string-valued ``kind`` attributes.
    Returns ``[]`` when *drg* is ``None`` or has no ``nodes`` attribute.
    """
    if drg is None:
        return []
    result: list[Any] = []
    for node in getattr(drg, "nodes", []):
        kind = getattr(node, "kind", None)
        kind_val = kind.value if hasattr(kind, "value") else str(kind) if kind else ""
        if kind_val == kind_str:
            result.append(node)
    return result


def get_incoming_edges(drg: Any, node_urn: str, relation_strs: set[str]) -> list[Any]:
    """Return edges that point *to* ``node_urn`` with a relation in ``relation_strs``.

    Uses ``edge.relation`` (not ``edge.type``) to match the doctrine DRGEdge schema.
    Returns ``[]`` when *drg* is ``None`` or has no ``edges`` attribute.
    """
    if drg is None:
        return []
    result: list[Any] = []
    for edge in getattr(drg, "edges", []):
        target = getattr(edge, "target", None)
        if target != node_urn:
            continue
        relation = getattr(edge, "relation", None)
        relation_val = (
            relation.value if hasattr(relation, "value") else str(relation) if relation else ""
        )
        if relation_val in relation_strs:
            result.append(edge)
    return result
