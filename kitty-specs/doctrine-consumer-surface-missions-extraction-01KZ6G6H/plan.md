# Implementation Plan: Missions/ Doctrine Tree Relocation & Gate Preconditions

**Branch**: `research/doctrine-wheel-mission-types-public-api` | **Date**: 2026-08-04 | **Spec**: `kitty-specs/doctrine-consumer-surface-missions-extraction-01KZ6G6H/spec.md`
**Input**: Feature specification from `kitty-specs/doctrine-consumer-surface-missions-extraction-01KZ6G6H/spec.md`

## Summary

Relocate the `missions/` doctrine tree's **data content** from `src/doctrine/missions` to `packs/built-in/missions` (the `.py` logic modules stay put as an ordinary Python package, repointed to read data from the new external root), extracting a domain-agnostic, kernel-owned sibling-path-resolution primitive so `src/kernel/paths.py` no longer hardcodes doctrine/specify_cli vocabulary to find it. Converge three parallel resolvers onto that one primitive: `doctrine/pack_paths.py::_resolve_built_in` (per planning decision DM-01KZ6JH5) and `doctrine.missions.repository.MissionTemplateRepository.default_missions_root()` (the already-promoted authority a prior mission's WP06 explicitly deferred to this issue, #3091) — `doctrine_package_dir()` survives unmodified. Repoint the DRG extractor's separate `_missions_root()` resolver and regenerate its two dependent graph fragments, in the same atomically-reviewed change as the move itself (a post-plan squad found the original relocate/repoint split left a genuinely broken intermediate state). Before any of that, resolve two named CI-gate preconditions on `tests/architectural/test_no_dead_doctrine_paths.py`: split its four gates by actual scope (relocating shared scan helpers to a common module), and decouple its NFR-003 proof onto a planted synthetic fixture (per issue #3036's own recorded rejection of "loosen the assertion"). Fold in two small, independent fixes: `UnknownMissionTypeError`'s self-contradictory message (with a red-first reproduction test first), and two stale TIER-1 command-template overrides. The doctrine/charter public-API contract (originally bundled, issue #3179) is an explicit non-goal here — split into its own follow-on mission after a post-spec adversarial squad found the relocation piece alone was already more architecturally involved than scoped, and once-deferred territory.

## Technical Context

**Language/Version**: Python 3.11+ (matches repository-wide `requires-python`)
**Primary Dependencies**: None new. Stdlib only for the primitive (`importlib.resources`, `pathlib`, `os`); `pytestarch` (already a dev dependency, used by `test_layer_rules.py`) plus a hand-rolled `ast`-walk (matching `test_charter_no_specify_cli_import.py`'s own idiom) for the new kernel-scoped gate — pytestarch's import-edge analysis cannot see a string-literal `importlib.resources.files(...)` call, so an AST walk is required for this specific shape, same reasoning as the charter gate's own precedent.
**Storage**: N/A (filesystem content relocation only; no database/schema involved)
**Testing**: pytest, run via `PYTHONPATH=src python -m pytest ...` per this repo's convention. New/changed test surfaces: a split of `tests/architectural/test_no_dead_doctrine_paths.py` into scope-appropriate modules, a new kernel-scoped architectural test (name TBD by implementer, e.g. `tests/architectural/test_kernel_no_doctrine_import.py`), a planted synthetic fixture for the NFR-003-style proof (mirrors this repo's existing `tmp_path`-based planted-violation test idiom already used elsewhere in the same file, e.g. `test_gate_a_rejects_a_planted_violation`), and existing `tests/doctrine/`, `tests/charter/`, `tests/kernel/` (if present) suites re-run for regression.
**Target Platform**: Cross-platform CLI (Linux/macOS/Windows dev + CI) — no platform-specific behavior introduced; the resolution primitive must continue to resolve identically across an editable checkout and an installed wheel (both already-exercised resolution modes).
**Project Type**: Single project (existing monorepo Python CLI; no frontend/mobile surface touched)
**Performance Goals**: Not a hot-path change — path resolution runs once per CLI invocation (init, mission-type enumeration), not in a loop. No explicit throughput target; NFR bar is "no user-observable slowdown," not a numeric threshold.
**Constraints**: Per spec C-001–C-003 — no wheel publish in this mission (`src/kernel`/`src/doctrine`/`src/charter` remain bundled in the root wheel); `change_mode: bulk_edit` governs the relocation (occurrence map + `moves:` block required before implementation); named issues #3179/#2986/#3022/#2468/#2652 explicitly out of scope.
**Scale/Scope**: Cross-layer but bounded — touches `src/kernel/paths.py`, `src/doctrine/pack_paths.py`, `src/doctrine/missions/**` (data subdirectories relocated; `.py` logic modules stay), `packs/built-in/missions/**` (new), `packs/built-in/agent_profiles/doctrine-daphne.agent.yaml` (current path, post `relocate-builtin-doctrine-packs-01KYT87F`), `src/charter/mission_type_profiles.py`, `src/doctrine/drg/migration/extractor.py` (`_missions_root()`), `packs/built-in/mission_type.graph.yaml`/`mission_step_contract.graph.yaml` (regenerated), `.kittify/overrides/missions/software-dev/command-templates/{implement,review}.md`, `tests/architectural/test_no_dead_doctrine_paths.py` (split), plus every identified reader of `missions/` content across `specify_cli`/`runtime`/upgrade migrations (exact set is FR-003's own deliverable — this plan does not presuppose the count).

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Relevant charter sections consulted: "Architecture: Shared Package Boundaries" (`.kittify/charter/charter.md:193-225`), "Quality & Tech-Debt Standing Orders" (complexity ceiling, repeated-literal-to-constant, no empty exception handlers), "Code Quality" / "Quality Gates".

- **External Contract Packages / Internal Runtime Boundary** — **PASS, not applicable.** This mission does not touch `spec-kitty-events` or `spec-kitty-tracker`, and does not publish any new external package (C-001 explicitly keeps kernel/doctrine/charter in the root wheel). The charter's boundary rules govern *external* package contracts; this mission's kernel-primitive extraction is an *internal* layer-direction fix within the existing monolith, not a new shared-package boundary — no charter violation.
- **Complexity ceiling (≤15, ruff C901/Sonar S3776)** — **Watch, not a known violation yet.** No existing function this mission touches is known to be near the ceiling; the new resolution primitive and the new gate module are both greenfield, small, single-purpose functions by design. Flag if `finalize-tasks`/implementation reveals otherwise.
- **`__all__` Declaration Convention (binding, charter.md:496)** — **Applies directly to FR-004/WP04.** "Every module under `src/charter/` and `src/kernel/` MUST declare `__all__`." The new resolution primitive lands in `src/kernel/` — it must be added to `paths.py`'s existing `__all__` (or, if implemented as a new sibling module, that module needs its own `__all__`). Found missing from this Charter Check during `/spec-kitty.analyze`'s review; no violation exists yet since no code has been written, but WP04's implementer must not miss this.
- **Repeated literals → constants (≥3 occurrences)** — **Applies directly.** The relocation touches multiple readers of the string `"missions"` / the `src/doctrine/missions` path shape; the WP-level implementation must hoist any newly-repeated literal per this standing order rather than duplicating it across the repointed call sites.
- **No empty/effect-free exception handlers** — **Applies to FR-004.** The kernel primitive's fail-closed behavior (mirroring `pack_paths.PackRootNotFound`) must raise a named, informative exception, not swallow a lookup failure silently.
- **ATDD-first discipline (C-011)** — **Applies to FR-002/FR-004/FR-006.** The gate-fixture decoupling, the new kernel gate, and the error-message fix should each land red-first against the defect they close (an injected violation for the gates; a new reproduction of the actual activated-but-unresolvable case for FR-006, since the existing test doesn't cover it) before the fix, per this repo's own directive.

No charter violations found requiring a Complexity Tracking justification entry.

## Project Structure

### Documentation (this mission)

```
kitty-specs/doctrine-consumer-surface-missions-extraction-01KZ6G6H/
├── spec.md               # Mission specification (committed)
├── plan.md               # This file
├── research.md           # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/            # Phase 1 output
│   ├── kernel-resolution-primitive.md
│   └── architectural-gates.md
├── decisions/            # Decision Moment records (DM-01KZ6JH5...)
├── checklists/requirements.md
└── tasks.md              # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/
├── kernel/
│   └── paths.py                       # FR-004: get_package_asset_root() and its
│                                       #   _looks_like_missions_root/_resolve_env_root
│                                       #   helpers replaced by the new primitive
├── doctrine/
│   ├── pack_paths.py                   # FR-004: _resolve_built_in() converges onto
│   │                                   #   the kernel primitive; doctrine_package_dir()
│   │                                   #   unchanged; exception translated to
│   │                                   #   PackRootNotFound at this boundary
│   ├── missions/                       # FR-005: DATA subdirectories (mission_types/,
│   │                                   #   built_in_step_contracts/, mission-steps/,
│   │                                   #   per-type templates/actions/) relocate out;
│   │                                   #   the 11 .py logic modules (repository.py,
│   │                                   #   mission_type_repository.py, step_contracts.py,
│   │                                   #   etc.) STAY as an ordinary Python package,
│   │                                   #   repointed to read the new external root —
│   │                                   #   including repository.py's own
│   │                                   #   default_missions_root(), which converges
│   │                                   #   onto the FR-004 primitive
│   └── drg/migration/extractor.py      # FR-005: _missions_root() repointed; its
│                                       #   "missions were not relocated" docstring
│                                       #   assumption is exactly what this mission
│                                       #   falsifies
├── charter/
│   └── mission_type_profiles.py        # FR-006: UnknownMissionTypeError message fix
│                                       #   (red-first reproduction test added first)
└── specify_cli/, runtime/, upgrade/migrations/
                                        # FR-003/FR-005: readers identified by the
                                        #   inventory, repointed onto the new location

packs/built-in/
├── missions/                          # FR-005: new home for the relocated DATA
│                                       #   content, alongside agent_profiles/,
│                                       #   directives/, tactics/, styleguides/,
│                                       #   toolguides/, paradigms/, procedures/,
│                                       #   glossary_packs/
├── agent_profiles/
│   └── doctrine-daphne.agent.yaml      # FR-002: repo-local avoidance-boundary mention
│                                       #   removed (the "daphne cleanup") — current
│                                       #   path, post relocate-builtin-doctrine-packs
├── mission_type.graph.yaml             # FR-005: regenerated + diffed against
└── mission_step_contract.graph.yaml    #   committed state after extractor repoint

.kittify/overrides/missions/software-dev/command-templates/
├── implement.md                       # FR-007: canonical construction pattern,
└── review.md                          #   no reference to retired `constitution context`

tests/architectural/
└── test_no_dead_doctrine_paths.py     # FR-001: split by actual scope (A+B / C / D)
                                        #   into new, explicitly-scoped modules, with
                                        #   shared scan helpers (Site, _rel, _read_lines,
                                        #   _text_files, root constants) extracted to
                                        #   one common module; exact module names/count
                                        #   are a Phase-0/implementation decision, not
                                        #   fixed here
```

**Structure Decision**: Single-project layout (repository root, existing monorepo). No new top-level source directories beyond the already-planned `packs/built-in/missions/`. Gate-split module names are intentionally left to the implementer within FR-001's scope constraint (group by actual current scope, name explicitly) rather than pre-decided in this plan, since the "right" split shape is itself part of what FR-001 delivers. `src/doctrine/missions/` is **not** deleted — only its data subdirectories relocate; its `.py` package structure remains, importable exactly as before.

## Complexity Tracking

*No Charter Check violations require justification — table intentionally empty.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Gate-file scope split + shared-helper extraction

- **Purpose**: Split `test_no_dead_doctrine_paths.py`'s four gates (A `scan_graph_monolith_paths`/`_shipped`, B `scan_shipped_pack_paths`/`_shipped`, C `scan_doctrine_cross_links`/`_shipped`, D `test_no_live_doc_names_a_pre_move_builtin_path`) into modules grouped by actual scope, preserving the NFR-002 discriminator-proof discipline unchanged; extract the shared scan helpers (`Site`, `_rel`, `_read_lines`, `_text_files`, root constants — used by Gates A, B, and C today) into one common module both post-split modules import.
- **Relevant requirements**: FR-001, NFR-003.
- **Affected surfaces**: `tests/architectural/test_no_dead_doctrine_paths.py` → new modules (names TBD, e.g. `test_no_dead_cli_paths.py` for A+B, `test_no_dead_doctrine_paths.py` retained/narrowed for C, a named home for D) + a new shared helper module (e.g. `_dead_path_scan.py`, matching this directory's `_gate_coverage.py`/`_sole_door_scan.py` naming convention).
- **Sequencing/depends-on**: none.
- **Risks**: Narrowing Gate B's scan root to `_DOCTRINE_ROOT` as a side effect of the split would silently drop its real `src/`-wide coverage (it is not doctrine-scoped today) — the exact regression NFR-003 forbids. Gate D's landing spot must be decided explicitly, not left as an afterthought. If this IC and IC-04 land in parallel lanes, both touch the shared `_gate_coverage_baseline.json` ratchet — whichever merges second must regenerate it (NFR-004).

### IC-02 — Synthetic-fixture decoupling + daphne cleanup

- **Purpose**: Redrive `test_forbidding_mention_would_false_red_without_its_discriminator` (and Gate C's analogous on-disk-cross-link case) from a planted synthetic fixture instead of the live shipped artifact, per issue #3036's own recorded design; then perform the "daphne cleanup" the decoupling enables (remove the repo-local `src/doctrine/graph.yaml` mention, at line 136, from `doctrine-daphne.agent.yaml`'s `avoidance-boundary`).
- **Relevant requirements**: FR-002, SC-006.
- **Affected surfaces**: `tests/architectural/test_no_dead_doctrine_paths.py` (post-IC-01 module), `packs/built-in/agent_profiles/doctrine-daphne.agent.yaml` (current path — this file was already relocated by a prior mission).
- **Sequencing/depends-on**: IC-01 (module split lands first, per FR-002's own blocking-dependency note).
- **Risks**: The literal-compliance failure mode named in the spec (deleting the proof test entirely rather than redesigning it) — the fixture-based proof must still demonstrably catch a planted violation, not merely stop failing.

### IC-03 — Cross-layer `missions/` reader inventory

- **Purpose**: Enumerate every reader of `src/doctrine/missions/` content across doctrine, kernel, charter, `specify_cli`, and upgrade migrations, by tracing `doctrine.missions.*` symbol usage (not path-literal grepping alone — grepping missed a load-bearing call site during this mission's own post-plan review), with an explicit move/stay/repoint decision per reader, committed as a reviewable artifact. Must explicitly include `MissionTemplateRepository.default_missions_root()` and the DRG extractor's `_missions_root()` (both already identified — this IC formalizes and completes the inventory, not discovers these two from scratch), plus the `.py`-vs-data-content split within `src/doctrine/missions/` itself.
- **Relevant requirements**: FR-003, SC-007.
- **Affected surfaces**: research/analysis only at this stage — output is a committed table at `docs/plans/doctrine/missions-reader-inventory-01KZ6G6H.md` (outside `kitty-specs/`, per issue #2643's `finalize-tasks` ownership gap), not a code change.
- **Sequencing/depends-on**: IC-01, IC-02 (per the spec's binding sequencing note — gates land before relocation work begins, and the inventory is the first relocation-adjacent step).
- **Risks**: A shallow inventory (e.g. skipping upgrade migrations, or the DRG extractor) silently under-scopes IC-05.

### IC-04 — Kernel-owned resolution primitive + three-way convergence

- **Purpose**: Extract a domain-agnostic sibling-path-resolution primitive into `src/kernel/`, replacing `get_package_asset_root()`'s `files("doctrine")` call and its `_looks_like_missions_root`/`_resolve_env_root` helpers; converge **both** `doctrine/pack_paths.py::_resolve_built_in` (decided during planning, DM-01KZ6JH5) **and** `doctrine.missions.repository.MissionTemplateRepository.default_missions_root()` (per IC-03's finding — the authority a prior mission's WP06 explicitly deferred convergence of, to this issue) onto the same primitive; prove the result with a new kernel-scoped architectural test. `doctrine_package_dir()` stays unmodified as its own public, test-pinned symbol. `pack_paths.py`'s call site translates the primitive's own exception type back to `PackRootNotFound` so existing `except (PackRootNotFound, ...)` consumers (e.g. `pack_validator.py`) are not silently broken.
- **Relevant requirements**: FR-004, NFR-002.
- **Affected surfaces**: `src/kernel/paths.py` (or a new sibling module within `src/kernel/`), `src/doctrine/pack_paths.py`, `src/doctrine/missions/repository.py`, a new `tests/architectural/test_kernel_*.py` gate.
- **Sequencing/depends-on**: none upstream (independent of IC-01–IC-03); feeds IC-05.
- **Risks**: The interim-state trap the post-spec squad flagged — any code path holding a doctrine-identifying string at any point (even transiently, even as a runtime argument rather than an import) reproduces the violation in spirit. The primitive's own anchor must be the *calling* package's `__file__`, not a passed-in package name string. If this IC and IC-01 land in parallel lanes, both touch `_gate_coverage_baseline.json` — see IC-01's note (NFR-004).

### IC-05 — `missions/` data relocation + reader repoint — one atomic change

- **Purpose**: Physically move `src/doctrine/missions/`'s **data subdirectories only** (`mission_types/`, `built_in_step_contracts/`, `mission-steps/`, per-type `templates/`/`actions/`) to `packs/built-in/missions/` — the `.py` logic modules stay in place — and repoint every reader IC-03 identified (the `.py` modules themselves, kernel via IC-04's primitive, charter, `specify_cli`, upgrade migrations, and `src/doctrine/drg/migration/extractor.py::_missions_root()`) onto the new location, **landed as one atomically-reviewed change, not split across separate WPs**: a move-without-repoint intermediate state is a genuinely broken build (NFR-001), and the bulk-edit `occurrence_map.yaml`'s own `moves:` block already treats this as one diff. Includes regenerating `packs/built-in/mission_type.graph.yaml`/`mission_step_contract.graph.yaml` and diffing against committed state (`tests/doctrine/drg/test_regen_roundtrip.py` is the backstop, but the regeneration step itself must be a stated task, not a surprise test failure).
- **Relevant requirements**: FR-005, SC-001, SC-007, SC-008, NFR-001.
- **Affected surfaces**: `src/doctrine/missions/**` (data subdirectories moved; `.py` modules repointed, not deleted), `packs/built-in/missions/**` (new), `src/doctrine/drg/migration/extractor.py`, `packs/built-in/mission_type.graph.yaml`, `packs/built-in/mission_step_contract.graph.yaml`, whichever `specify_cli`/`runtime`/upgrade-migration files IC-03's inventory names.
- **Sequencing/depends-on**: IC-03 (inventory complete) **and** IC-04 (primitive ready) — a fork/join, both required; do not model as a strict chain when authoring `tasks.md`.
- **Risks**: Governed by the bulk-edit `moves:` block (C-003) — must be reviewed/approved before this IC's WP claims any file. A reader silently left on the old path fails closed once the data subdirectories move — NFR-001's full-suite-green requirement (including the DRG regen-roundtrip tests) is the backstop that catches this.

### IC-06 — Mission-type error message fix

- **Purpose**: Add a red-first reproduction test for the actual activated-but-unresolvable-profile scenario (the existing test doesn't cover it), then fix `UnknownMissionTypeError`'s self-contradictory message.
- **Relevant requirements**: FR-006, SC-003.
- **Affected surfaces**: `src/charter/mission_type_profiles.py`, `tests/charter/test_mission_type_profiles.py` (new reproduction test).
- **Sequencing/depends-on**: none — fully independent of every other IC.
- **Risks**: Low; a docstring already documents the exact reproduction (per debugger-debbie's squad finding), reducing this to a small, well-understood fix.

### IC-07 — TIER-1 override template refresh

- **Purpose**: Refresh `.kittify/overrides/missions/software-dev/command-templates/{implement,review}.md` onto the canonical construction pattern; remove the retired `constitution context` reference.
- **Relevant requirements**: FR-007, SC-004.
- **Affected surfaces**: the two named override files.
- **Sequencing/depends-on**: none — fully independent of every other IC.
- **Risks**: Low; campsite-scoped, two files.
