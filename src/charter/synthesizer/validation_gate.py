"""Pre-synthesis validation gate (FR-008 / NFR-004 / US-5).

Public API: ``validate(staging_dir, shipped_drg) -> None``

Flow:
1. Load the staged project overlay from ``staging_dir/doctrine/graph.yaml``.
2. Merge with *shipped_drg* via ``merge_layers()`` (additive semantics).
3. Call ``validate_graph(merged)`` — dangling refs, duplicate edges, cycles.
4. If any errors: raise ``ProjectDRGValidationError`` with structured fields
   that carry enough information for a ``rich``-rendered CLI panel (US-5).

NFR-004: fail-closed within 5s.  The validator runs entirely in-process on
in-memory data structures — 5s is orders of magnitude above actual latency.
``test_validation_gate.py`` includes a timing assertion to lock this in.

WP03 integration: ``write_pipeline.promote(validation_callback=validate)``
calls this gate before any ``os.replace`` writes land in ``.kittify/``.  On
``ProjectDRGValidationError`` the orchestrator routes the staging dir to
``.failed/`` and surfaces the structured error.

See data-model.md §E-5 for overlay discipline.
"""

from __future__ import annotations

from pathlib import Path

from doctrine.drg.loader import DRGLoadError, load_graph, merge_layers
from doctrine.drg.models import DRGGraph
from doctrine.drg.validator import validate_graph

from .errors import ProjectDRGValidationError


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate(
    staging_dir: Path,
    shipped_drg: DRGGraph,
) -> None:
    """Validate the staged project DRG overlay against *shipped_drg*.

    Args:
        staging_dir: Root of the staging area produced by the current run.
            The overlay is expected at ``staging_dir/doctrine/graph.yaml``.
        shipped_drg: The shipped-layer ``DRGGraph``.  Used as the lower layer
            in the ``merge_layers`` call.

    Raises:
        ProjectDRGValidationError: When validation fails for any reason:
            * The staged overlay file is missing or malformed.
            * ``validate_graph`` returns ≥ 1 errors (dangling refs, duplicate
              edges, cycles).
        The error carries ``errors`` and ``merged_graph_summary`` fields rich
        enough for a CLI panel that names the dangling URN, the offending
        artifact, and the source reference that triggered it (US-5).
    """
    overlay_path = staging_dir / "doctrine" / "graph.yaml"

    # --- Step 1: Load the staged overlay -----------------------------------
    try:
        project_overlay = load_graph(overlay_path)
    except DRGLoadError as exc:
        raise ProjectDRGValidationError(
            errors=(
                f"Could not load staged project overlay from "
                f"{overlay_path}: {exc}",
            ),
            merged_graph_summary=(
                f"staging_dir={staging_dir}, "
                f"shipped_nodes={len(shipped_drg.nodes)}"
            ),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise ProjectDRGValidationError(
            errors=(f"Unexpected error loading overlay {overlay_path}: {exc}",),
            merged_graph_summary=(
                f"staging_dir={staging_dir}"
            ),
        ) from exc

    # --- Step 2: Merge layers (additive) -----------------------------------
    merged = merge_layers(shipped_drg, project_overlay)

    # --- Step 3: Validate merged graph -------------------------------------
    errors = validate_graph(merged)
    if not errors:
        return  # all good — no raise

    # --- Step 4: Surface structured error ----------------------------------
    # Build a human-readable summary that names specific problem artifacts.
    project_urns = frozenset(n.urn for n in project_overlay.nodes)
    summary = (
        f"shipped_nodes={len(shipped_drg.nodes)}, "
        f"project_nodes={len(project_overlay.nodes)}, "
        f"merged_nodes={len(merged.nodes)}, "
        f"merged_edges={len(merged.edges)}, "
        f"project_urns=[{', '.join(sorted(project_urns))}]"
    )

    raise ProjectDRGValidationError(
        errors=tuple(errors),
        merged_graph_summary=summary,
    )


__all__ = ["validate"]
