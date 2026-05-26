"""Fresh-project doctrine seed materialisation helpers (WP06 split).

Carved out of ``_synthesis.py`` so the synthesis helper module stays well
under 500 lines. Behaviour is unchanged — these helpers materialise the
minimal ``.kittify/doctrine/`` artifact set the runtime needs when no
LLM-authored YAMLs are present (see issue #839 / WP06 T031-T033).
"""
from __future__ import annotations

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
#
# Anything beyond this set (per-directive YAML, project-layer DRG graph,
# provenance sidecars, synthesis manifest) is produced ONLY when an LLM-authored
# corpus exists under ``.kittify/charter/generated/`` and is out of WP06 scope.
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
    doctrine_dir.mkdir(parents=True, exist_ok=True)

    provenance_path = doctrine_dir / "PROVENANCE.md"
    # Idempotency: only write if content differs (avoids needless mtime churn,
    # though byte-stability is preserved either way).
    new_bytes = _MINIMAL_FRESH_DOCTRINE_PROVENANCE_TEMPLATE.encode("utf-8")
    if not provenance_path.exists() or provenance_path.read_bytes() != new_bytes:
        provenance_path.write_bytes(new_bytes)

    return [
        str(provenance_path.relative_to(repo_root)),
    ]


def _planned_fresh_doctrine_paths(repo_root: Path) -> list[str]:
    """Return the repo-relative paths a fresh-project synthesize would write.

    Used by ``--dry-run`` on a fresh project (#839 follow-up): callers preview
    the materialization without touching the filesystem. Must mirror the
    output of :func:`_materialize_fresh_doctrine` exactly.
    """
    doctrine_dir = repo_root / ".kittify" / "doctrine"
    return [
        str((doctrine_dir / "PROVENANCE.md").relative_to(repo_root)),
    ]
