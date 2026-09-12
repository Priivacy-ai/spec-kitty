# Approach Tracer — org-pack-authoring-diagnostics-01KZY463

Seeded at the plan phase per the mission-tracer-files procedure (Charter Standing Order #3).

## High-level approach

This mission is a set of **additive, CLI-layer-only diagnostics** wired into the existing
`pack_validate` / `validate_pack()` surface — no new runtime carrier, no new persisted state, no
new CLI command or flag. The whole diff lives inside `src/specify_cli/doctrine/` (plus one
call-site edit each in `pack_assembler.py` and `doctrine.py`, both in the CLI layer). It reads
from the doctrine-model layer (`src/doctrine/agent_profiles/repository.py`,
`src/doctrine/assets/repository.py`) to source or match existing runtime behaviour, but never
writes to that layer.

Three of the four FRs (FR-002, FR-003, FR-004) follow one shape: **make `pack validate` say
something about a shape that already fails silently at runtime**, using the existing
`ValidationIssue`/`ValidationResult` dataclasses and new `category` string values — never a new
top-level JSON key, never a schema change. The fourth (FR-001) was re-scoped by a binding
operator ruling mid-mission from a small code change to documentation-only, because the surface
it would have touched (`step_contracts.py` / `MissionStepContract`) is retired wholesale by an
Accepted ADR (`2026-08-13-1`) whose implementation just hasn't landed yet — investing further
code in a surface already decided-to-be-deleted was rejected.

The plan deliberately keeps `pack_validator.py`'s new logic in small, named, single-purpose
helper functions (`_check_profile_skipped_diagnostics`, `_check_drg_root_graph_missing`) called
once each from `validate_pack()`, mirroring the file's own established
`_validate_drg`/`_validate_asset_manifests` extraction pattern, rather than growing
`validate_pack()`'s own body — the file's docstring already records a prior extraction to stay
under ruff's complexity-15 ceiling, and this mission continues that discipline rather than
re-fighting it later.

## A concrete lesson from the spec phase: verify, don't trust, reported line numbers

The upstream issue (#3387) cited `snapshot.py:53-65` as the mechanism that "counts" a
mis-suffixed step-contract file via `endswith("contract.yaml")` semantics. During the spec phase,
this citation was checked directly against the live file rather than trusted: `_ARTIFACT_BUCKETS`
(`:53-65`) is indeed defined at that location, but `grep -rn "_ARTIFACT_BUCKETS" src/ tests/`
showed it is **never referenced anywhere else in the codebase** — it is dead code. The function
that actually populates `pack-manifest.yaml`'s `artifact_counts` is `_count_artifacts`
(`:195-212`), which counts by **directory membership** (`entry.rglob("*.yaml")`), not by the
`endswith` suffix check the issue described. The net *symptom* the issue reported (a mis-suffixed
contract file is counted but never loaded) still held — but through a different mechanism than
cited. This correction is preserved verbatim in `spec.md`'s "Verified Code Surfaces" table and is
recorded here as a general lesson for this mission's later phases (implement, review): a cited
file:line is a starting point for verification, not a substitute for reading the live code.

The same discipline was applied throughout this plan: every file:line reference above (the
`_load_layer` absent-directory guard at `repository.py:392-393`, the ADR file's actual absence on
this branch, the Typer JSON error gate's real scope, the `check_patch_targets.py` mechanics, the
contextive glossary's actual non-coverage of existing `category` values) was checked directly
against the live checkout during this plan phase, not assumed from the spec's or the task
brief's framing.
