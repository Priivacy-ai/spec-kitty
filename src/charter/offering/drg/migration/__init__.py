"""DRG migration -- extract inline refs from built-in doctrine into graph.yaml."""

from __future__ import annotations

from charter.offering.drg.migration.calibrator import calibrate_surfaces, measure_surface
from charter.offering.drg.migration.extractor import (
    extract_action_edges,
    extract_artifact_edges,
    generate_graph,
)
from charter.offering.drg.migration.id_normalizer import (
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
