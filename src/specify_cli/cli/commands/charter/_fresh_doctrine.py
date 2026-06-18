"""Fresh-project doctrine seed materialisation helpers (WP06 split).

Carved out of ``_synthesis.py`` so the synthesis helper module stays well
under 500 lines. Behaviour is unchanged — these helpers materialise the
minimal ``.kittify/doctrine/`` artifact set the runtime needs when no
LLM-authored YAMLs are present (see issue #839 / WP06 T031-T033).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

# T031 (#839 minimal artifact set): the runtime consumes ``.kittify/doctrine/``
# via ``DoctrineService(project_root=...)``. The candidate-list resolver in
# ``src/charter/_doctrine_paths.py::resolve_project_root`` treats project-root
# discovery as **directory-presence only** — an empty ``.kittify/doctrine/`` is
# a valid candidate, and the built-in layer (``src/doctrine/``) supplies content
# until the project layer is populated. The minimal artifact set
# ``charter synthesize`` must produce on a fresh project to unblock the runtime
# is therefore:
#
#   1. ``.kittify/doctrine/``                 — directory marker (REQUIRED)
#   2. ``.kittify/doctrine/PROVENANCE.md``    — human-readable provenance note
#                                                  describing the seed source
#                                                  (REQUIRED for auditability)
#   3. ``.kittify/charter/synthesis-manifest.yaml`` — machine-readable marker
#                                                  declaring built_in_only=true
#
# Project-layer DRG graph artifacts are produced ONLY when an LLM-authored
# corpus exists under ``.kittify/charter/generated/``. The fresh-seed manifest
# is the authoritative "built-in doctrine fallback is intended" marker used by
# charter freshness/preflight.
# See spec.md FR-015 / Spec Assumption A2 / GitHub issue #839.
_MINIMAL_FRESH_DOCTRINE_PROVENANCE_TEMPLATE = """\
# Spec Kitty Doctrine — Fresh Project Seed

This `.kittify/doctrine/` tree was materialized by `spec-kitty charter
synthesize` running against a **fresh project** (no LLM-authored YAML under
`.kittify/charter/generated/`). It exists so `DoctrineService` discovers a
project layer and the runtime can advance; it is intentionally empty.

The runtime falls back to the in-package built-in doctrine
(`src/doctrine/`) for all artifact lookups until the LLM harness writes
project-local artifacts under `.kittify/charter/generated/` and you re-run
`spec-kitty charter synthesize`.

References
----------
- GitHub issue: https://github.com/Priivacy-ai/spec-kitty/issues/839
- Spec assumption A2: public CLI synthesize works on a fresh project.
- Project-root resolution: `src/charter/_doctrine_paths.py`.
"""


def _fresh_seed_manifest_text() -> str:
    """Build the deterministic built-in-only synthesis manifest text."""
    from importlib.metadata import version as _pkg_version

    from charter.synthesizer.manifest import SynthesisManifest
    from charter.synthesizer.synthesize_pipeline import canonical_yaml

    try:
        synthesizer_version = _pkg_version("spec-kitty-cli")
    except Exception:
        synthesizer_version = "unknown"

    without_hash: dict[str, object] = {
        "schema_version": "2",
        "mission_id": None,
        "created_at": "1970-01-01T00:00:00+00:00",
        "run_id": "fresh-project-seed",
        "adapter_id": "fresh-seed",
        "adapter_version": synthesizer_version,
        "synthesizer_version": synthesizer_version,
        "artifacts": [],
        "built_in_only": True,
    }
    manifest_hash = hashlib.sha256(canonical_yaml(without_hash)).hexdigest()  # noqa: TID251 - production raw SHA-256 owner
    manifest = SynthesisManifest.model_validate(
        {**without_hash, "manifest_hash": manifest_hash}
    )
    return canonical_yaml(manifest.model_dump(mode="python")).decode("utf-8")


def _materialize_fresh_doctrine(repo_root: Path) -> list[str]:
    """Materialize the minimal ``.kittify/doctrine/`` artifact set.

    Used on a fresh project where ``.kittify/charter/generated/`` has no
    agent-authored YAML (T032 / #839). Sources the canonical seed text from
    this module's in-package constant — no external file I/O, no new
    dependency, no doctrine-subsystem changes.

    Idempotent: re-runs produce bytewise-identical output (T033). Returns the
    list of repo-relative paths written.
    """
    doctrine_dir = repo_root / ".kittify" / "doctrine"
    charter_dir = repo_root / ".kittify" / "charter"
    doctrine_dir.mkdir(parents=True, exist_ok=True)
    charter_dir.mkdir(parents=True, exist_ok=True)

    provenance_path = doctrine_dir / "PROVENANCE.md"
    # Idempotency: only write if content differs (avoids needless mtime churn,
    # though byte-stability is preserved either way).
    new_bytes = _MINIMAL_FRESH_DOCTRINE_PROVENANCE_TEMPLATE.encode("utf-8")
    if not provenance_path.exists() or provenance_path.read_bytes() != new_bytes:
        provenance_path.write_bytes(new_bytes)

    manifest_path = charter_dir / "synthesis-manifest.yaml"
    manifest_text = _fresh_seed_manifest_text()
    if not manifest_path.exists() or manifest_path.read_text(encoding="utf-8") != manifest_text:
        manifest_path.write_text(manifest_text, encoding="utf-8")

    # #1717 Fix A: the fresh-seed manifest declares built_in_only=true, so any
    # stale project-local graph.yaml the manifest disowns must be removed.
    # Mirrors the synthesizer's own post-condition (project_drg.
    # apply_post_condition, has_project_graph=False) for the path that bypasses
    # the synthesizer. FR-007: both sites route through the one shared helper.
    from charter.synthesizer.graph_residue import unlink_stale_project_graph  # noqa: PLC0415

    unlink_stale_project_graph(doctrine_dir)

    return [
        str(provenance_path.relative_to(repo_root)),
        str(manifest_path.relative_to(repo_root)),
    ]


def _planned_fresh_doctrine_paths(repo_root: Path) -> list[str]:
    """Return the repo-relative paths a fresh-project synthesize would write.

    Used by ``--dry-run`` on a fresh project (#839 follow-up): callers preview
    the materialization without touching the filesystem. Must mirror the write
    output of :func:`_materialize_fresh_doctrine` exactly.
    """
    doctrine_dir = repo_root / ".kittify" / "doctrine"
    charter_dir = repo_root / ".kittify" / "charter"
    return [
        str((doctrine_dir / "PROVENANCE.md").relative_to(repo_root)),
        str((charter_dir / "synthesis-manifest.yaml").relative_to(repo_root)),
    ]


def _planned_fresh_doctrine_deletes(repo_root: Path) -> list[str]:
    """Return repo-relative paths fresh-project synthesize would delete."""
    graph_path = repo_root / ".kittify" / "doctrine" / "graph.yaml"
    if not graph_path.exists():
        return []
    return [str(graph_path.relative_to(repo_root))]
