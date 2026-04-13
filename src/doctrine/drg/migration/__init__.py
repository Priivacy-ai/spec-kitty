"""DRG migration -- extract inline refs from shipped doctrine into graph.yaml."""

from __future__ import annotations

from doctrine.drg.migration.calibrator import calibrate_surfaces, measure_surface
from doctrine.drg.migration.extractor import (
    extract_action_edges,
    extract_artifact_edges,
    generate_graph,
)
from doctrine.drg.migration.id_normalizer import (
    artifact_to_urn,
    directive_to_urn,
    normalize_directive_id,
)

__all__ = [
    "artifact_to_urn",
    "calibrate_surfaces",
    "directive_to_urn",
    "extract_action_edges",
    "extract_artifact_edges",
    "generate_graph",
    "measure_surface",
    "normalize_directive_id",
]
