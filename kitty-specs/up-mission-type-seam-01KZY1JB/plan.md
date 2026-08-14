# Implementation Plan: Mission-Type Roster Layering & Resolution Seam

**Branch**: `pr/up-mission-type-seam` (mission coordination branch: `kitty/mission-up-mission-type-seam-01KZY1JB`) | **Date**: 2026-08-13 | **Spec**: `kitty-specs/up-mission-type-seam-01KZY1JB/spec.md`
**Input**: Mission specification from `kitty-specs/up-mission-type-seam-01KZY1JB/spec.md`

**Note**: All file:line citations below were re-verified against this checkout's live `src/`
and `tests/` trees during planning (not copied uncritically from `spec.md` or from the R&D spike
that informed this mission's scoping). Where a citation in this document differs from a citation
in `spec.md`, this document's citation is the one just re-checked and wins.

## Summary

The mission-type roster today resolves **built-in types only**: `MissionTypeRepository.default()`
(`src/doctrine/missions/mission_type_repository.py:48-50`) is a `@classmethod @functools.cache`
over the shipped `packs/built-in/missions/mission_types/` tree, and the two projection call
sites that feed a resolved mission's action sequence and template set —
`_resolve_action_slot` / `_resolve_template_set_slot`
(`src/charter/mission_type_profiles.py:762-807`, `841-884`) — are both built-in-only today, for two
structurally different reasons: `_resolve_template_set_slot` genuinely hardcodes `pack_context=None`
in its `MissionStepRepository.default().resolve_all_for_mission_type(...)` call (`:878`);
`_resolve_action_slot` has **no** `pack_context` parameter at all — its builtin-only-ness comes from
calling the zero-arg `MissionTypeRepository.default()` (`:793`), not from a hardcoded default.
An org-tier or project-tier doctrine pack can *activate* a non-built-in mission type
(`existing_mission_types()`, `mission_type_profiles.py:424-508`, returns any activated id without
intersecting the built-in catalog), but today that type cannot even resolve: `_resolve_action_slot`'s
`repo.get(mission_type)` call against the built-in-only repository returns `None`
(`mission_type_profiles.py:793-795`), so the function raises `UnknownMissionTypeError` at line 799 —
a **loud, immediate hard-fail**, not a silent degrade. The mission's dominant risk (CL-003) is
therefore prospective, not present-tense: only once this mission's own IC-01/IC-02 change lands does
`mission` become resolvable (non-`None`) for a non-built-in type via the new layered lookup — and
only then does `return list(mission.action_sequence or [])` at line 807 become the live,
silently-degrading path for a type whose YAML omits `action_sequence`. IC-05 below closes that
prospective gap with a named loud failure (`MissionTypeEmptyActionSequenceError`) landing in the
same PR that first makes the silent-degrade path reachable, so CL-003's "silent, planless success"
never actually reaches an operator.

This plan adds a **new, separate, module-level, pack-aware layered lookup** in
`src/doctrine/missions/mission_type_repository.py` — sibling to, never a replacement for,
`default()` — and threads the `PackContext` that `resolve_mission_type_context`
(`mission_type_profiles.py:516-618`) already constructs one call-frame down
(`existing_mission_types()` → `PackContext.from_config(repo_root)` at line 507) into the two
projection slots. It widens `charter activate mission-type`'s own availability scan
(`src/charter/pack_manager.py`) to see org/project mission-type files, fixes four CLI surfaces that
today tolerate-and-lie about non-built-in types, adds a named loud-fail for the empty-action-
sequence case, and deletes two pieces of confirmed dead code (`resolve_mission_steps` and the
shadowed `list_cmd` mission-type-list handler). The plan's first work package is an ADR — required
by spec CL-002 — that answers a real upstream sequencing risk before any code lands.

## Technical Context

**Language/Version**: Python 3.11+ (repo standard; `pyproject.toml`; this mission adds no new
runtime dependency).
**Primary Dependencies**: `ruamel.yaml` (mission-type YAML parsing, already used by
`MissionTypeRepository._load`), `pydantic` (the `MissionType` model, `src/doctrine/missions/models.py`),
stdlib `functools.cache`/`pathlib`. No new third-party dependency is introduced.
**Storage**: Filesystem only — YAML files under `packs/built-in/missions/mission_types/`
(built-in), `<org-pack-root>/mission_types/*.yaml` (org, new, CL-005), and
`.kittify/missions/mission_types/*.yaml` (project, new, CL-005). No database, no persisted cache
across process invocations (confirmed: `src/charter/{bundle,compiler,context}.py` never write or
read `action_sequence`, and no `.kittify` artifact stores a roster snapshot — every repository
loads at `__init__`, `src/doctrine/base.py:93-108` for the sibling `BaseDoctrineRepository`
pattern; `MissionTypeRepository` itself loads in its own `__init__`,
`mission_type_repository.py:40-42`).
**Testing**: `pytest`, repo-standard markers (`fast`/`integration`/`slow`/`architectural`). This
mission's new/changed tests land under `tests/doctrine/missions/`, `tests/charter/`, `tests/cli/`,
`tests/runtime/`, and one architectural-adjacent regression under `tests/architectural/` scope
notes (no new architectural gate is added or removed — see Gate Set below).
**Target Platform**: Same as the rest of the CLI — Linux/macOS/Windows 10+, Python 3.11+; no
platform-specific code in this seam.
**Project Type**: Single Python package (`src/`), not web/mobile. See Project Structure below.
**Performance Goals**: No new NFR beyond the existing ones this mission must not regress:
NFR-001's action-sequence hot path stays cache-warm (the new module-level `@functools.cache`
factory exists specifically so a second resolution of the same `(mission_types_dirs, pack_context)`
pair costs zero filesystem walks — same shape as the already-cache-warm
`_resolve_all_for_mission_type_cached`, `src/doctrine/missions/mission_step_repository.py:446-470`).
**Constraints**: NFR-003/C-008 — `doctrine.missions` gains no new import from `src/charter/`
(verified as a live constraint by `tests/architectural/test_layer_rules.py:279-302`,
`TestDoctrineIsolation.test_doctrine_does_not_import_charter`). NFR-004 — no `charter.*` module may
call the new factory or `MissionTypeRepository.default()` more than once combined at import time
(live gate: `tests/charter/test_charter_import_time_io.py:244-291`,
`TestHotModulesTriggerZeroImportTimeIo.test_import_charter_mission_type_profiles_and_pack_context_bounded_io`,
which spawns a subprocess, imports `charter.mission_type_profiles` / `charter.pack_context`, and
asserts a bounded-I/O subprocess probe exits 0). Zero new architectural-baseline edits is a design
goal (CL-001, verified below under "Producer-scan constraint").
**Scale/Scope**: Size class **L** per spec C-001 — this plan does not revise that estimate (see
"Sizing" below).

## The Seam

**Layer**: this change lands in the **doctrine layer**
(`src/doctrine/missions/mission_type_repository.py`), consumed one call-frame up by the
**charter layer** (`src/charter/mission_type_profiles.py`, `src/charter/pack_manager.py`), and
reached by the **CLI layer** (`src/specify_cli/cli/commands/{mission_type.py, doctrine.py,
charter/mission_type.py, charter/activate.py}`) only through the existing charter facade,
`src/charter/missions.py`. No kernel-layer code is touched.

**Concretely, new code in `src/doctrine/missions/mission_type_repository.py`:**

- A new **module-level** `@functools.cache`-decorated factory, keyed on
  `(mission_types_dirs, pack_context)` — a tuple of directories plus the existing structural
  `_PackContextLike` object — living beside (not inside) the `MissionTypeRepository` class, mirroring
  the sibling module's own already-live pattern:
  `_resolve_all_for_mission_type_cached` (`src/doctrine/missions/mission_step_repository.py:446-470`),
  a bare module-level `@functools.cache` function, **not** a classmethod cache. A `cache_clear()`
  static test seam is required (spec CL-001), mirroring
  `MissionStepRepository.cache_clear` (`mission_step_repository.py:323-333`, a `@staticmethod` that
  calls `.cache_clear()` on the module-level cached function).
- It imports the existing structural `_PackContextLike` `Protocol`
  (`mission_step_repository.py:41-61`, declaring `pack_roots: tuple[Path, ...]`,
  `repo_root: Path`, and an explicit `__hash__`) from its **sibling module in the same package**
  (`doctrine.missions`) — this is not a new cross-layer import; `doctrine` still never imports
  `charter`.
- `MissionTypeRepository.default()` (`mission_type_repository.py:48-85`) is **untouched**: still a
  `@classmethod @functools.cache` keyed on `cls` only, still built-in-only.

**Facade re-export decision (conditional on IC-01's still-open factory-shape choice — not yet a
settled fact).** `charter.missions`
(`src/charter/missions.py:24-42`) is the sanctioned door `specify_cli` reaches
`MissionTypeRepository`/`builtin_mission_type_ids` through today, and it is already
identity-checked by `tests/architectural/test_charter_facades_reexport_doctrine.py`'s
`_FACADE_TABLE["charter.missions"]` (lines 111-118 of that test file). Tracing every CLI consumer
this mission's FR-006/FR-007/FR-008 touch:

- `charter mission-type list` (`src/specify_cli/cli/commands/charter/mission_type.py:49-128`,
  `charter_mission_type_list`, with the "unknown"-layer tolerate branch at lines 74-83) needs a
  **per-id source layer** (`"built-in" | "org" | "project"`),
  not just an action sequence — `resolve_mission_type_context` gives an action sequence and a
  *governance* provenance, but the roster's own layer for a given id is a property of the new
  layered repository, not of the governance-profile resolver. This command therefore needs direct
  reach to the new factory (or a lookup method on the object it returns).
- `doctrine mission-type list` (`src/specify_cli/cli/commands/doctrine.py:1028-1044`,
  `_collect_built_in_mission_types`, called from `mission_type_list` at line 1067) must enumerate
  **all** ids across all layers regardless of
  activation — that is a roster-listing operation the new factory's returned object must support
  directly (e.g. its inherited `.load_all()` over the merged index), not something
  `resolve_mission_type_context` (which is activation-scoped) can answer.
- `mission-type show <type>` (`src/specify_cli/cli/commands/mission_type.py:1450-1520`,
  `show_mission_type`) already reaches `MissionTypeRepository` via `charter.missions` — its fix
  needs the layered lookup for the same reason as `charter mission-type list`.

All three surfaces need to construct/query the new layered lookup directly (not only via
`resolve_mission_type_context`) — **but whether that requires a new `charter.missions`
facade-table entry is conditional on IC-01's own still-open per-call-signature decision** (see
IC-01's Risks bullet below), not a settled fact:

- **If the new factory ships as a bare, module-level function** (mirroring the shape of
  `_resolve_all_for_mission_type_cached`, `mission_step_repository.py:446-470`) — it is a
  genuinely new symbol with no existing facade-table row, so a new entry naming it **is** needed.
- **If it instead ships as a new classmethod on `MissionTypeRepository`** (already present in
  `_FACADE_TABLE["charter.missions"]` by identity, `src/charter/missions.py:24-42`) — **no new
  facade-table entry is needed at all**, because the sibling module's own precedent shows this
  shape is sufficient: `mission_step_repository.py`'s analogous cache function,
  `_resolve_all_for_mission_type_cached`, is kept **private** — absent from that module's own
  `__all__` (`mission_step_repository.py:63-66`, which lists only `"StepKey"` and
  `"MissionStepRepository"`) — and every caller reaches it only through the already-exported
  `MissionStepRepository` class, never by importing the private function directly.
  `MissionTypeRepository` following the same shape would need nothing new here.

Concretely, **if** the tasks phase resolves IC-01's open question toward the bare-function shape
(so a new entry turns out to be needed):

1. Add the new symbol(s) to `charter.missions.__all__` and the module's `from
   doctrine.missions.mission_type_repository import (...)` block (`src/charter/missions.py:25-28`).
2. Add a `("<new-symbol>", "doctrine.missions.mission_type_repository")` row to
   `_FACADE_TABLE["charter.missions"]` in
   `tests/architectural/test_charter_facades_reexport_doctrine.py` (currently lines 111-118) — this
   is the **live, self-enforcing** contract (`test_facade_reexports_doctrine_symbol_by_identity`,
   `test_facade_all_lists_every_reexport`, and the inverse
   `test_facade_all_reexports_are_tabled`, lines 228-300 of that file all run against it).
3. The older, human-authored contract doc,
   `kitty-specs/charter-mediated-doctrine-selection-01KRTZCA/contracts/charter-facade-modules.md`,
   does **not** currently document `charter.missions` at all — that facade was added later, by
   mission `doctrine-public-api-surface-01KZPDSR` (WP07), whose own data-model doc
   (`kitty-specs/doctrine-public-api-surface-01KZPDSR/data-model.md:82-85`) is the closer
   precedent. Updating the stale `.md` contract doc is **not required by any enforced gate** — no
   test reads it — but this plan recommends a one-line addition to it for the next reader, scoped
   as boy-scout tidy-up inside the file this mission already touches conceptually, not a new
   file-set entry.

If the tasks phase instead resolves toward the classmethod shape, none of the three steps above
apply, and this section leaves no residual work item — the existing `MissionTypeRepository` facade
row already covers it by identity.

No other new facade door is needed regardless of which shape IC-01 picks:
`charter.mission_type_profiles` and `charter.pack_manager` are
themselves `charter.*` modules, so `specify_cli` reaching functions inside them
(`resolve_mission_type_context`, `existing_mission_types`) needs no additional facade — the
facade rule only gates `doctrine.*` symbols reached from outside `charter`.

## Generated vs Authored

**This mission touches no generated artifact.** Specifically:

- **Doctrine schemas** (`spec-kitty doctrine schema` output, checked by the "Verify generated
  doctrine schemas are up to date" CI step, `.github/workflows/ci-quality.yml:653`) are unaffected
  — this mission adds no new `MissionType` field and no new doctrine artifact kind; it changes
  *where* existing `MissionType` YAML is discovered and *how* its `action_sequence` is projected,
  not the schema shape.
- **Contextive glossary files** (`.github/workflows/ci-quality.yml:848`, "Check Contextive
  glossary files are up-to-date") are unaffected — no new canonical term is introduced. "Layer"
  ("built-in"/"org"/"project"), "mission type", and "action sequence" are all pre-existing terms.
- **Agent command copies** (`.claude/commands/`, `.agents/skills/`, etc., generated by
  `spec-kitty upgrade` from `src/doctrine/missions/mission-steps/`) are unaffected — this mission
  does not touch any `mission-steps/<type>/<step>/step.yaml` or `prompt.md` source template.

Everything this mission adds or edits is hand-authored `src/` and `tests/` Python plus one ADR
markdown file (WP01). No command in this repo needs to be re-run to regenerate anything this
mission changes.

## Contract Movement

**Mission-type roster surface (FR-006–FR-009) — status per surface:**

| Surface | Today | After this mission | Preserved or versioned? |
|---|---|---|---|
| `charter mission-type list` | Emits `source_layer: "unknown"` + `action_sequence: []` for any activated non-built-in id (`charter/mission_type.py:74-83`) | Emits the real layer + real action sequence | **Preserved output shape** (same columns/JSON keys), **corrected values** — not a schema version bump. The `"unknown"` sentinel string is retired as dead once every activated id resolves to a real layer; no other consumer of that literal string exists in `src/` (verified: `grep -rn '"unknown"' src/specify_cli/cli/commands/charter/mission_type.py` shows only this one site). |
| `mission-type show <type>` | Hard `typer.Exit(1)` for an activated non-built-in type (`mission_type.py:1487-1490`, `mt is None` branch) | Succeeds, displays resolved fields | **Preserved for every case that already worked** (built-in types keep behaving identically — User Story 3); the exit-1 case for a genuinely-unresolvable type is unchanged (still exit 1, still lists registered ids) — only the previously-mis-failing "activated org type" case is fixed. |
| `doctrine mission-type list` | Only ever calls `_collect_built_in_mission_types()` (`doctrine.py:1067`) despite its own docstring already promising built-in→org→project layering (`doctrine.py:1058-1059`) | Implements the layering its docstring already documents | **Preserved contract, corrected implementation** — the docstring is not changed because it already describes the target behavior; only the `rows` collection call changes. |
| `charter activate`'s step-removal warning (`_emit_step_removal_warnings`, `src/specify_cli/cli/commands/charter/activate.py:151-192`) | `current_seq`/`incoming_seq` both silently degrade to `[]` for a non-built-in type via the bare `except Exception: current_seq = []` at lines 180-181 and `MissionTypeRepository.default().get(artifact_id)` returning `None` at line 183 | Compares the type's real previous/incoming `action_sequence` for non-built-in types too | **Preserved warning semantics** (same warning text, same trigger condition — "a step was removed"); only the previously-blind non-built-in case now actually evaluates. |

**Does `spec-kitty-events` or the orchestrator-api surface move?** **No, confirmed by scope
inspection, not merely asserted.** `spec-kitty-events` owns event envelopes and payload schemas
(charter.md's "External Contract Packages" section) — this mission emits no new event and reads/writes
no event payload. The orchestrator-api surface
(`spec_kitty_orchestrator_api` docs / `docs/architecture/` orchestrator boundary) drives mission
*lifecycle* transitions (claim/status/review), not mission-*type* roster resolution; grepping this
mission's touched files (`mission_type_repository.py`, `mission_type_profiles.py`,
`pack_manager.py`, the four CLI command files, `resolver.py`, `activate.py`) against
`orchestrator_boundary` / `spec_kitty_events` import names returns no hits. Neither surface moves.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design — no violation found,
so Complexity Tracking below is empty.*

- **Single canonical authority** — the new layered lookup is the single new authority for
  "resolve a mission type across layers"; it does not duplicate `MissionStepRepository`'s existing
  layering logic, it reuses that module's `_PackContextLike` protocol by import. PASS.
- **Architectural alignment / module seams** — NFR-003/C-008 (`doctrine.missions` imports nothing
  from `charter`) is honored: the new factory lives in `doctrine.missions.mission_type_repository`
  and only ever *receives* a `_PackContextLike`-conforming object as a parameter; it never imports
  `charter.pack_context.PackContext` by name. PASS, mechanically enforced by
  `tests/architectural/test_layer_rules.py:279-302`.
- **Domain-driven splits / tiered rigour** — the dominant-risk path (CL-003's loud-fail) gets a
  named exception class and a red-first regression test (NFR-005); CLI glue gets ordinary
  coverage. PASS by design (see Gate Set below).
- **ATDD-first (C-011)** — every WP's red-first test is committed before its implementation commit;
  the CL-003 loud-fail is explicitly two ordered commits (NFR-005), not one combined commit.
- **Campsite cleaning (Standing Order #2)** — see "Campsite-Clean Opening Commit" below.
- **Mission tracer files (Standing Order #3)** — see "Tracer Files" below.
- **Terminology canon** — no `feature*` alias is introduced; spec.md's own Terminology Note
  confirms this and this plan introduces no new CLI flag or field name.

No charter violation requires a Complexity Tracking entry.

## Project Structure

### Documentation (this mission)

```
kitty-specs/up-mission-type-seam-01KZY1JB/
├── plan.md                       # This file
├── spec.md                       # Binding contract (already authored, reviewed, passed)
├── tracer-approach.md            # Seeded at specify phase; append-only from here
├── tracer-design-decisions.md    # Seeded at specify phase; append-only from here
├── tracer-tooling-friction.md    # Seeded at specify phase; append-only from here
└── tasks.md                      # Phase 2 output (/spec-kitty.tasks — NOT produced by this plan)
```

**No `research.md`, `data-model.md`, or `quickstart.md` for this mission** — see "Contracts"
below for why `data-model.md` and a `contracts/` directory are explicitly skipped rather than
silently omitted. `research.md` is skipped because Phase 0 research questions were already
answered exhaustively by the pre-spec R&D spike and re-verified first-hand during this planning
pass (every load-bearing claim above carries its own live `file:line` citation) — there is no
open unknown left to research before Phase 1 design. `quickstart.md` is skipped because this
mission has no new user-facing setup flow to walk through beyond the existing
`spec-kitty charter activate mission-type <id>` command, which is already documented.

### Source Code (repository root)

This is a **single Python package** mission (spec-kitty's own `src/` layout) — not a web or
mobile split. The concrete files touched, grouped by layer:

```
src/
├── doctrine/
│   └── missions/
│       └── mission_type_repository.py     # EXTEND (pre-existing, 238 lines): add
│                                           # module-level layered factory + cache_clear()
│                                           # seam (FR-001); pack_context param threaded into
│                                           # _inject_projected_fields (FR-002 support);
│                                           # corrected docstring (FR-011, CL-004) — preserve
│                                           # the existing MissionTypeRepository.default()
│                                           # classmethod and its cache untouched (see "The Seam")
├── charter/
│   ├── mission_type_profiles.py           # _resolve_action_slot / _resolve_template_set_slot
│   │                                       # gain pack_context threading (FR-002); new
│   │                                       # MissionTypeEmptyActionSequenceError + its raise
│   │                                       # site (FR-004, red-first per NFR-005)
│   ├── pack_manager.py                    # _scan_layout_for / _resolve_layer_candidate gain an
│   │                                       # org/project branch for kind=None (mission-type)
│   │                                       # (FR-003, FR-005)
│   ├── missions.py                        # possible new facade re-export entry, conditional
│   │                                       # on IC-01's still-open factory-shape choice — not
│   │                                       # a settled fact (see "The Seam" above)
│   └── resolver.py                        # DELETE resolve_mission_steps (FR-010, CL-004)
└── specify_cli/
    └── cli/
        └── commands/
            ├── mission_type.py            # DELETE list_cmd / _print_available_missions /
            │                               # discover_missions import (FR-013, CL-004a); FIX
            │                               # show_mission_type (FR-007)
            ├── doctrine.py                 # FIX _collect_built_in_mission_types /
            │                               # mission_type_list to layer-scan (FR-008)
            └── charter/
                ├── mission_type.py         # FIX charter_mission_type_list's "unknown" branch
                │                           # (FR-006)
                └── activate.py             # FIX _emit_step_removal_warnings for non-built-in
                                            # types (FR-009)

tests/
├── doctrine/
│   └── missions/
│       └── test_mission_type_repository.py   # EXTEND (pre-existing, 412 lines): add
│                                              # layered-lookup unit tests, cache-key
│                                              # correctness (NFR-001), cache_clear() seam —
│                                              # preserve the file's existing MissionType /
│                                              # MissionTypeRepository round-trip test classes,
│                                              # do not replace them
├── charter/
│   ├── test_mission_type_profiles.py          # EXTEND (pre-existing, 413 lines): add
│   │                                          # red-first empty-action-sequence test
│   │                                          # (CL-003/NFR-005, committed before its fix);
│   │                                          # pack_context-threading tests — preserve the
│   │                                          # file's existing MissionTypeProfile /
│   │                                          # resolve_mission_type_context test classes
│   │                                          # (including its "T034"/WP05 docstring
│   │                                          # reference), do not replace them
│   ├── test_resolver.py                       # DELETE resolve_mission_steps's test (FR-010)
│   └── test_charter_import_time_io.py         # EXTEND (not replace): assert the new factory
│                                              # also respects the ≤1-call-at-import bound
├── cli/
│   ├── test_charter_activate_warning.py       # EXTEND: non-built-in-type step-removal case
│   ├── test_charter_mission_type_commands.py  # EXTEND: charter mission-type list real-layer
│                                              # output for a non-built-in activated type
│                                              # (FR-006); assert list_mission_types is the
│                                              # sole "list" command registered on the app
│                                              # (no shadowed handler — CL-004a/IC-06)
│   └── test_doctrine_commands.py              # EXTEND: doctrine mission-type list layering
│                                              # (FR-008)
├── specify_cli/
│   └── cli/commands/
│       └── test_mission_type_template_set_cli.py  # EXTEND: show_mission_type output for a
│                                              # non-built-in activated type (FR-007).
│                                              # (Note: `tests/specify_cli/cli/commands/
│                                              # test_mission_type.py` does not exist — verified
│                                              # live; this pre-existing sibling file already
│                                              # exercises `show`'s output shape end-to-end.)
└── runtime/
    └── test_runtime_seam.py                   # EXTEND: golden parity check — all 4 built-in
                                              # types still resolve byte-identically
                                              # (User Story 3 / SC-003)
```

**Structure Decision**: single Python package, `src/{doctrine,charter,specify_cli}/` — the
existing three-layer split (kernel ← doctrine ← charter ← specify_cli) this repo already uses.
No new top-level directory, no new package. This mission is purely additive within the existing
layout.

## Contracts

This mission is not a REST/RPC API, so there is no OpenAPI/gRPC contract to author, and (per the
"Documentation" tree above) no `contracts/` directory is created. Two things that could plausibly
be mistaken for "the contract" here, addressed explicitly rather than left silent:

1. **`data-model.md` is explicitly skipped.** Spec.md's own "Key Entities" section (spec.md
   lines 328-352) already fully enumerates the four entities this mission touches
   (mission-type roster entry, `PackContext`, `_PackContextLike` Protocol, the new layered
   lookup) with their real field shapes and relationships; none of them is new data this
   mission invents — `PackContext` and `_PackContextLike` are reused as-is (spec CL-001), and
   the "roster entry" is the pre-existing `MissionType` Pydantic model
   (`src/doctrine/missions/models.py:220-282`), unchanged in shape by this mission. A dedicated
   `data-model.md` would either duplicate spec.md's Key Entities section verbatim or add nothing
   beyond it — this plan defers to spec.md as the single source for entity shape rather than
   forking a second copy that can drift.
2. **The four-CLI-surface table above ("Contract Movement") is this mission's real contract
   surface**, and it is a *behavior* contract (what each existing CLI command outputs), not a
   *schema* contract — hence a table in this document rather than a `contracts/*.yaml` file. Each
   row states explicitly whether the surface's contract is preserved or corrected; none is
   versioned (no `--json` schema field is added, renamed, or removed).

## Baseline

`main` carries known-red tests (issue #3284: 23 untracked test failures + 2 errors) and a shared
test-venv lock that can time out (#3283), per this checkout's `CLAUDE.md` § "Test-run baseline-red
gotcha". Concretely, before this mission's first commit, the implementer runs, against the
mission's own `planning_base_branch` (the merge-base commit this branch was cut from — this
mission's tracer-tooling-friction.md records that base as `main` @ `ab0a0b9b5`), the exact test
files this mission will touch or extend:

```
uv run pytest tests/doctrine/missions/test_mission_type_repository.py \
  tests/charter/test_mission_type_profiles.py tests/charter/test_resolver.py \
  tests/charter/test_charter_import_time_io.py tests/cli/test_charter_activate_warning.py \
  tests/cli/test_charter_mission_type_commands.py tests/cli/test_doctrine_commands.py \
  tests/specify_cli/cli/commands/test_mission_type_template_set_cli.py \
  tests/runtime/test_runtime_seam.py \
  tests/architectural/test_layer_rules.py tests/architectural/test_charter_facades_reexport_doctrine.py \
  tests/architectural/test_no_inert_schema_slots.py \
  -v --tb=short
```

against the merge-base commit (checked out read-only, or via `PYTHONPATH=<merge-base
worktree>/src` per CLAUDE.md's documented technique — never by mutating this mission's own
working tree). Any failure observed there is **pre-existing red**, attributable to #3284 or a
category-2/3 cause (CI-environment config, stale install) per CLAUDE.md's three-way
classification, and is recorded (not "fixed") before the mission's first functional commit. Only a
test that is **red on this mission's branch AND green on the merge-base** is this mission's own
regression to fix. The one test this mission deliberately makes RED-then-GREEN on purpose
(CL-003's empty-action-sequence regression test, NFR-005) is the sole intentional exception to
"red is bad" and is called out as such in its own commit message so a reviewer does not misfile it
as an unattributed baseline failure.

## Campsite-Clean Opening Commit

The mission's **first commit** is a distinct, behavior-preserving deletion pass — not a
grab-bag — folding exactly the two pieces of domain-matched debt spec.md already requires in this
mission's own touched surfaces:

1. **CL-004**: delete `resolve_mission_steps` (`src/charter/resolver.py:908-937` per live
   re-check — confirmed zero production callers via repo-wide grep, matching spec's own finding)
   and its single test in `tests/charter/test_resolver.py` (asserts only `isinstance(result, dict)`
   and non-empty length, never exercising the `pack_context` branch the function exists to expose).
2. **CL-004a**: delete `list_cmd` (`src/specify_cli/cli/commands/mission_type.py:150-151`),
   `_print_available_missions` (line 122), and — **only** the `discover_missions` name, not the
   whole import statement — from the multi-name import at lines 38-46. Verified live: `Mission`,
   `MissionError`, `MissionNotFoundError`, `get_mission_by_name`, `get_mission_for_feature`, and
   `list_available_missions` (the other six names imported in that same block) each have a live
   caller elsewhere in the file (`mission_type.py:75,244,247,268,269,271,277` etc.) — only
   `discover_missions` (used solely at line 124, inside the now-deleted
   `_print_available_missions`) becomes unused. Deleting the whole import block would be a
   different, larger, unauthorized diff; deleting the one now-dead name is the smallest-viable-diff
   application of Boy Scout cleanup inside this commit's own file set (charter's change-scope
   reconciliation order).

Both deletions are behavior-preserving (zero production callers today, confirmed above and in
spec.md's own CL-004/CL-004a citations) and are the exact domain-matched debt this mission's own
functional change touches (the file `list_cmd` shadows is the same file FR-006/FR-007/FR-008
modify; `resolve_mission_steps` sits in the same module, `resolver.py`, this mission's project-
layer scanning work is adjacent to). No unrelated tidy-up is folded into this commit.

## Tracer Files

`tracer-tooling-friction.md`, `tracer-approach.md`, and `tracer-design-decisions.md` are already
seeded (specify phase) and were re-read in full before this plan was authored. This plan **appends
no new entry to any of them** — no new tooling friction was hit while authoring this plan (the
`spec-kitty plan` scaffold command was not re-run per this task's own instruction; this document
was hand-edited directly onto the pre-existing scaffold). If a further tooling refusal surfaces
during implementation, the implementer appends a dated entry to `tracer-tooling-friction.md`
(never rewriting the existing SK-12 entries already there) and, if it is a genuinely new defect
class not already covered by `SPEC-KITTY-LEDGER.md`'s SK-12 entry, files a new ledger entry
separately (not as part of this plan).

## Complexity Tracking

*Empty — Charter Check above found no violation requiring justification.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Gate Set

Chosen from the hub's candidate gate table, grounded in the actual invocation of each gate (grepped
live from `Makefile`, `.github/workflows/ci-quality.yml`, and `pyproject.toml` — not invented):

**Included, and why:**

| Gate | Live invocation | Why included |
|---|---|---|
| `make lint` | `Makefile:13-14`, `uv run ruff check src/` | Advisory in CI (the `[ENFORCED]` `lint` job at `ci-quality.yml:613` runs the real ruff/mypy/commitlint/markdownlint sweep; `make lint` is the fast local pre-push discipline check) — run locally before every push per CLAUDE.md's Code Style section. |
| `fast-tests-doctrine` + `integration-tests-doctrine` | `ci-quality.yml:1138-1185` (`tests/doctrine/`, `--cov=doctrine --cov=charter`), `ci-quality.yml:2506-2540` | This mission's doctrine-layer change (`mission_type_repository.py`) is directly in the collected coverage scope and the collected test path. |
| `fast-tests-charter` + `integration-tests-charter` | `ci-quality.yml:2389-2441` (`tests/charter tests/specify_cli/charter_freshness tests/specify_cli/charter_lint tests/specify_cli/charter_preflight`, `--cov=charter --cov-fail-under=55`), `ci-quality.yml:2547-2593` | `mission_type_profiles.py`, `pack_manager.py`, `resolver.py`, and `missions.py` are all `src/charter/` — directly in scope, both the test path and the 55%-floor coverage collection. |
| `fast-tests-cli` + `integration-tests-cli` | `ci-quality.yml:1633-1687` (`tests/cli/ tests/specify_cli/cli/`, `--cov=src/specify_cli/cli`), `ci-quality.yml:3021-3049` | The four CLI-surface fixes (FR-006–FR-009) and the CL-004a deletion are all under `src/specify_cli/cli/`. |
| `arch-adversarial` (3-shard matrix) | `ci-quality.yml:2144-2177`, runs `tests/adversarial tests/architectural tests/architecture tests/lint` | This mission's own doctrine/charter changes must not regress `test_no_dead_symbols`, `test_layer_rules`, `test_no_inert_schema_slots`, or `test_charter_facades_reexport_doctrine` — all of which live under `tests/architectural/` and run in this shard; the last of those specifically guards the `charter.missions` facade table, which this mission may possibly touch, conditional on IC-01's still-open factory-shape choice (not yet a settled fact — see "The Seam"). |
| Doctrine schema freshness | `ci-quality.yml:653`, "[ENFORCED] Verify generated doctrine schemas are up to date" | Cheap, always-on in the same `lint` job; this mission adds no schema field but the gate is unconditional, so it runs regardless. |
| Contextive glossary | `ci-quality.yml:848` | Same — always-on in the `lint` job; no new term is introduced (see "Generated vs Authored" above) but the gate itself is unconditional. |
| TID251 banned-API | `ci-quality.yml:883` | Always-on in `lint`; this mission's new imports (`_PackContextLike` from a sibling module, and a possible new facade re-export conditional on IC-01's factory-shape choice — see "The Seam") are ordinary same-package/facade imports, not a banned pattern, but the gate runs regardless. |
| Typer 0.26 JSON error surface | `ci-quality.yml:896` | Always-on in `lint`; the four fixed CLI commands (`mission-type list/show`, `doctrine mission-type list`) all support `--json` today and must keep emitting the same JSON error shape on failure (e.g. `mission-type show` for a genuinely unknown id) — this gate is the mechanical check for that. |
| `patch()` target validation | `ci-quality.yml:940-941`, `scripts/check_patch_targets.py` | Always-on in `lint`; this mission's new tests will `patch()`/monkeypatch `MissionTypeRepository.default`, the new factory, and `_resolve_org_layer_dir`-adjacent helpers — this gate catches a stale/incorrect patch target string. |
| Bandit | `ci-quality.yml:914` | Always-on in `lint`; no new subprocess/eval/pickle surface is added by this mission, but the gate runs regardless. |
| pip-audit | `ci-quality.yml:929` | Always-on in `lint`; no new dependency is added, but the gate runs regardless of that fact. |
| commitlint | `ci-quality.yml:672-724` | Always-on in `lint` for any PR; this mission's campsite-clean-first commit sequencing (CL-004/CL-004a) and CL-003's two-ordered-commits requirement (NFR-005) both need conventional-commit-shaped messages that state which commit is the red-first test and which is the fix. |
| markdown lint | `ci-quality.yml:731` | Always-on in `lint`; this mission adds one new markdown file (the WP01 ADR) and edits none of the tracer `.md` files (append-only, per Tracer Files above) — the gate runs against the ADR. |
| architecture/docs consistency | `ci-quality.yml:795` | Always-on in `lint`, scoped to changed markdown; the WP01 ADR is new markdown under `docs/adr/3.x/` and must cross-reference the existing ADR it relates to (CL-002) correctly. |
| `uv lock --check` | `ci-quality.yml:4025-4043` (`uv-lock-check` job, a required `quality-gate` dependency at `ci-quality.yml:4364-4423`) | Always-on, required; this mission adds no dependency, so it is expected to pass trivially, but it is a blocking `quality-gate` member and cannot be skipped. |
| `diff-coverage` (critical-path, 90%) | `ci-quality.yml:3403-3406` (job comment + `diff-coverage:` header), `:3456-3517` (the `[ENFORCED]`-equivalent "diff-coverage (critical-path, enforced)" step; `critical_paths` array at `:3468-3477` includes `'src/doctrine/*'` at `:3470` and `'src/charter/*'` at `:3471`; the actual `diff-cover ... --fail-under=90` invocation at `:3514-3517`); required by `quality-gate`'s blocking `needs:` list (`- diff-coverage` at `:4343`, inside the `:4338-4394` block) | **[ENFORCED], PR-scoped, blocking — and directly targets this mission's own touched files.** This mission changes lines in both `src/doctrine/*` (`mission_type_repository.py`) and `src/charter/*` (`mission_type_profiles.py`, `pack_manager.py`, `resolver.py`, `missions.py`) — both are named in `critical_paths` — so every new branch/line in those five files must clear 90% diff coverage on changed lines, independent of and in addition to `fast-tests-charter`'s job-local 55% floor named above. This is the gate that actually enforces new-code coverage on this PR (see the Excluded table below for why SonarCloud's project-wide gate does not). |

**Excluded, and why (every enforced gate NOT included, with a stated reason):**

| Gate | Why excluded |
|---|---|
| **SonarCloud Quality Gate** (`ci-quality.yml:3568`, the `sonarcloud:` job header — the actual `[ENFORCED] SonarCloud Quality Gate` step is further down, at `:4011`) | **Provides zero enforcement on this PR — verified by reading the job's own `if:` condition, not assumed.** The job's `if:` (`ci-quality.yml:3625`) is `always() && (github.event_name == 'schedule' \|\| github.event_name == 'workflow_dispatch')` — it never runs on `pull_request` or `push`, so it never runs on this mission's own PR at all. It is also absent from `quality-gate`'s blocking `needs:` list (`:4338-4394`) — no `sonarcloud` entry there. The new-code-coverage concern this row would otherwise be cited for is fully covered by the `diff-coverage` row added to the Included table above (this document's own PLAN-VERIFY-001 remediation) — that gate, unlike this one, is `[ENFORCED]`, PR-scoped, and a real `quality-gate` dependency. |
| **Kernel coverage ≥90%** (`ci-quality.yml:1075-1128`, `--cov=src/kernel`, `kernel-tests` job) | **Does not apply — verified by directory scope, not assumed.** The coverage floor is computed only over `src/kernel/`. Neither of this mission's two named touch-points — `src/doctrine/missions/mission_type_repository.py` nor `src/charter/mission_type_profiles.py` — is under `src/kernel/`; `kernel-tests` runs unconditionally (`needs: [changes]`, `if: ... || github.event_name == 'push'`) but this mission adds zero lines to the scope its coverage assertion measures, so the floor is unaffected by construction. |
| **Mission-loader coverage ≥90%** (`ci-quality.yml:1517-1548`, `--cov=src/specify_cli/mission_loader`, `mission-loader-coverage` job) | **Does not apply — same reasoning.** The floor is scoped to `src/specify_cli/mission_loader/` and `tests/unit/mission_loader/` + `tests/integration/test_mission_run_command.py`. This mission touches `src/specify_cli/cli/commands/{mission_type.py,doctrine.py,charter/*}` — a sibling CLI-commands tree, not `mission_loader/` — and no file this mission edits lives under that path. The job still runs (it is `always()`-gated, not path-filtered by this mission's changes) but measures a directory tree this mission never writes to. |
| **`fast-tests-corpus`, `fast-tests-docs`, `fast-tests-missions`, `fast-tests-status`, `fast-tests-review`, `fast-tests-next`, `fast-tests-lanes`, `fast-tests-dashboard`, `fast-tests-upgrade`, `fast-tests-sync*`, `fast-tests-merge`, `fast-tests-post-merge`, `fast-tests-release`, `fast-tests-agent`, `fast-tests-core-misc`, `unit-contract-residual`, `slow-tests`, `e2e-cross-cutting`, `stress-tests-serial`, `timing-nfr-serial`, `restart-daemon-nfr-timing`, `regression-tests`, and their `integration-*` counterparts** | Every one of these is a distinct, dedicated `quality-gate` dependency (`ci-quality.yml:4338-4364`) scoped to a directory tree this mission does not touch (sync, merge, status, lanes, dashboard, upgrade, missions-lifecycle, docs, corpus, agent surface, etc.). They all run unconditionally in CI (most are `path-filter`-gated to their own tree via the `changes` job, and this mission's diff does not touch any of those trees, so they run in their already-green, unaffected state) — none is a gate this mission's *own* correctness depends on, so none is separately re-justified per row here beyond this one blanket entry. |
| **`build-wheel` / `clean-install-verification` / `consumer-compatibility`** | Package-build and cross-version-compatibility gates unrelated to a same-repo doctrine/charter/CLI seam change; this mission adds no new public wheel symbol beyond the facade re-export that may possibly be needed, conditional on IC-01's still-open factory-shape choice — not yet a settled fact (see "The Seam") — and even in that branch, the existing `charter.missions` door already satisfies it structurally. |
| **`docs-freshness.yml`, `docs-pages.yml`, `docs-build-pr.yml`** (separate workflow files) | This mission is not a documentation mission (spec.md's own scope is code, not docs); the WP01 ADR under `docs/adr/3.x/` is covered by the `lint` job's markdown/architecture-docs-consistency steps already listed above, not by the separate docs-build workflows, which build the rendered docs site. |
| **`orchestrator-boundary.yml`, `plugin-validate.yml`, `check-spec-kitty-events-alignment.yml`** | Confirmed not applicable under "Contract Movement" above — neither `spec-kitty-events` nor the orchestrator-api boundary moves in this mission, so these dedicated cross-package alignment workflows have nothing to check for this diff. |
| **`protect-main.yml`** | A branch-protection workflow, not a code-correctness gate; this mission follows the standard PR-branch flow (charter's Agent Push Authorization section) so it is never in a position to trip this workflow. |
| **`ui-e2e.yml`** | No dashboard/UI surface is touched by this mission (no `.tsx`/frontend file in the touched-file list above). |

**The two coverage floors named in this task's own instructions, addressed directly.** This
mission touches `src/doctrine/missions/mission_type_repository.py` and
`src/charter/mission_type_profiles.py`. Neither file is inside `src/kernel/` (the kernel-tests
floor's scope, `ci-quality.yml:1075` comment: "kernel is small, stable, and must be well-tested")
nor inside `src/specify_cli/mission_loader/` (the mission-loader floor's scope,
`ci-quality.yml:1517` comment: "NFR-003, mission #505 / WP07"). **Neither named 90% floor applies
to this mission by directory scope**, confirmed by reading both jobs' `--cov=` arguments directly
rather than assuming from the file names. What *does* apply, and is not optional: the
`fast-tests-charter` job's own `--cov-fail-under=55` floor over `src/charter/` (a lower, job-local
floor distinct from the two 90% floors), and — `[ENFORCED]`, PR-scoped, and blocking — the
`diff-coverage` gate's own 90% floor over `src/doctrine/*` and `src/charter/*` (see the Included
table's `diff-coverage` row above). CLAUDE.md's "Sonar Expectations" section ("Every new
branch/helper needs tests in the same PR") states the same discipline as engineering practice,
independent of whether the SonarCloud CI job itself runs on this PR — it does not (see the
Excluded table's SonarCloud row above); `diff-coverage` is the mechanism that actually enforces it
here. This plan's Implementation Concern Map below assigns a directly-testing unit
test to every new branch this mission introduces (the layered factory's cache-hit/cache-miss
paths, the new loud-fail's raise site, each of the four CLI-surface fixes' new/changed branch),
which is how this plan holds that gate — not by asserting "we'll run the tests."

## Producer-scan constraint (verified, not merely cited)

CL-001's rejected option (b) — moving the `action_sequence` projection out of
`src/doctrine/missions/mission_type_repository.py` into `charter` — was checked against the live
architectural gate, not just cited from the spike. `tests/architectural/test_no_inert_schema_slots.py`
(`test_live_tree_has_no_new_inert_slots`, lines 62-75) asserts `ratchet(...)` returns an empty
`new` list; `tests/architectural/_inert_slots.py`'s `_code_producers` walk
(`find_inert_slots`, lines 360-368) only scans `src/doctrine/` + `packs/built-in/` for a slot's
producer — confirmed by reading `find_inert_slots`'s docstring and call graph directly. The
baseline file's `code_only_suppressions` row for `action_sequence`
(`tests/architectural/_inert_slots_baseline.yaml:437-444` per the spike's citation, not
independently re-walked line-by-line in this pass since the row's *existence* and the scan's
*scope* are what matter, both confirmed above) names
`src/doctrine/missions/mission_type_repository.py` as the sole producer. **This is why
`payload["action_sequence"] = ...` (`mission_type_repository.py:209`, inside
`_inject_projected_fields`) stays exactly where it is**: moving it to `src/charter/` would put the
only producer of that schema slot outside the tree `_code_producers` walks, which reds
`test_live_tree_has_no_new_inert_slots`'s `assert new == []` (a "new" unaccounted-for inert slot)
and — independently — `code_only_drift` (`_inert_slots.py:766-780`) would flag the baseline row as
"stale" (a producer citation with nothing left to verify against). Both are live, enforced
assertions; this design change costs **zero** `_inert_slots_baseline.yaml` edits, matching spec
CL-001's own framing and the sizing note in spec C-001.

## Sizing

This plan does **not** revise spec C-001's **L** estimate (~150–190 `src/` LOC, ~260 test LOC,
plus the WP01 ADR, not counted in the LOC estimate). The per-file touch list under "Project
Structure" above is consistent with that range: one new factory + `cache_clear()` seam +
docstring fix in `mission_type_repository.py` (~40-50 LOC), `pack_context` threading + the new
named exception + its raise site in `mission_type_profiles.py` (~40-50 LOC), the org/project
branch in `pack_manager.py` (~15-20 LOC), the possible facade re-export if IC-01 resolves toward
the bare-function shape (~4-6 LOC, ~0 LOC if the classmethod shape is chosen instead — see "The
Seam"), the four CLI-surface
fixes (~40-50 LOC combined), minus the two deletions (`resolve_mission_steps` ~-30 LOC, `list_cmd`
cluster ~-30 LOC). No part of this plan's design adds scope beyond what spec.md already bounds.

## Implementation Concern Map

**WP01 = author the ADR.** Per spec CL-002/FR-012, the plan/tasks phase's first work package is
authoring a new ADR under `docs/adr/3.x/` (the actual document is written in tasks/implement, not
here — this plan states only what it must contain and why it comes first). It must state,
verifiably and in these terms:

(a) **No `ArtifactKind` promotion.** This mission does not promote mission-type to a first-class
`ArtifactKind` member (confirmed: `src/doctrine/artifact_kinds.py`'s `ArtifactKind` enum has no
`MISSION_TYPE` member today, and `src/charter/kind_vocabulary.py`'s
`MissionTypeNotAnArtifactKind` exception exists specifically to keep `"mission-type"` out of the
charter-activatable `ArtifactKind` vocabulary while still being a `CHARTER_KIND_TOKENS` member).
That promotion is a separate, larger, currently-unstarted upstream effort (issue #2468, blocked on
keystone issue #2467).

(b) **Relation to `docs/adr/3.x/2026-08-05-1-mission-type-availability-before-kind-promotion.md`'s
"no silent contract reversal" driver.** That ADR names `#2468`'s promotion as reversing a
deliberate, tested "no silent fallback" contract (pinned by
`tests/doctrine/test_org_pack_augmentation.py`) and requires it carry its own decision record
rather than being smuggled into an availability slice. This mission's WP01 ADR must state plainly
that this mission **is** the availability/resolution slice that ADR anticipates, and is
**explicitly not** the contract-reversing type-promotion slice, so a future reader auditing either
ADR cannot conflate the two.

(c) **The flat org-pack layout decision (CL-005) as its own short decision record.** The referenced
ADR explicitly leaves "nested-vs-flat mission-type path" as an undecided open sub-decision it
deliberately parks for the `#2468` promotion slice ("This ADR does not bind it"). This mission's
WP01 ADR must record, as a self-contained decision distinct from (a)/(b) above: the org layer is
flat (`<pack>/mission_types/*.yaml`, matching the sibling `mission-steps/` convention already used
at the org/project pack tier — confirmed live at
`src/doctrine/missions/mission_step_repository.py:411`,
`{pack_root}/mission-steps/{mission_type_id}/{step_id}/step.yaml`), and the project layer is
`.kittify/missions/mission_types/*.yaml`, scanned **non-recursively** — deliberately not
`.kittify/doctrine/mission_types/`, which this plan confirms (see IC-03 below) is a real trap in
the live scanning code, not a hypothetical one.

**Zero architectural-baseline edits (CL-001) is a design goal for this mission**, verified above
under "Producer-scan constraint" — restated here because it is the property every IC below is
designed to preserve, not merely a WP01 ADR talking point.

### IC-01 — Layered mission-type lookup + module-level cache

- **Purpose**: Add the new, separate, pack-aware layered lookup in
  `doctrine.missions.mission_type_repository`, keyed on `(mission_types_dirs, pack_context)`,
  without touching `MissionTypeRepository.default()`'s existing built-in-only semantics.
- **Relevant requirements**: FR-001, NFR-001, NFR-002, NFR-003/C-008.
- **Affected surfaces**: `src/doctrine/missions/mission_type_repository.py` (new module-level
  cached factory + `cache_clear()` static seam); imports `_PackContextLike` from
  `mission_step_repository.py:41-61` (sibling module, no new cross-layer edge).
- **Malformed-YAML handling (spec.md Edge Cases, CL-006/NFR-002)**: the new factory's org/project-
  layer parse call MUST wrap and re-raise a `ruamel.yaml` parse failure with the offending file's
  path named in the error message — it must not silently skip the file and resolve as though it
  did not exist. Verified live against the exact call shape this factory is most likely to
  mirror/extend: `MissionTypeRepository._load` (`mission_type_repository.py:130-163`) calls
  `_yaml.load(yaml_file.read_text(encoding="utf-8"))` (`:147`) — parsing a bare `str`, not a named
  stream — so a `ruamel.yaml.YAMLError` raised there carries no file identity of its own unless the
  caller wraps it; naively reusing this exact call shape unmodified for org/project scanning would
  satisfy "fail loudly" but not spec.md's "naming the offending file" half of the requirement. This
  is distinct from, and does not require changing, `charter/pack_manager.py`'s unrelated
  `_declared_id` helper (`pack_manager.py:339-355`), which already catches `YAMLError` and returns
  `None` for a malformed file during IC-03's *availability* scan — that helper is shared, generic,
  kind-agnostic machinery serving every charter-activatable artifact kind, not mission-type-
  specific, so changing its silent-skip-to-loud-fail behavior would be a materially larger,
  unrelated-blast-radius change outside this mission's scope (the same smallest-viable-diff
  discipline IC-03's own Risks bullet already applies to the `rglob`-vs-`glob` trap). The binding
  "fail loudly, naming the file" requirement is satisfied at the point this mission actually
  resolves a roster entry's fields (this IC's layered lookup), not at the earlier, separate
  availability-listing step IC-03 owns.
- **Sequencing/depends-on**: none (IC-02 depends on this; IC-03 and IC-06 are independently
  sequenced — see their own bullets, and IC-06 in particular precedes IC-01 as the mission's first
  commit).
- **Risks**: the factory must never be called at module scope in any `charter.*` module (NFR-004)
  — a naive "warm the cache at import" optimization would trip
  `tests/charter/test_charter_import_time_io.py:263-291`. The factory's exact per-call signature
  (whether it mirrors `MissionStepRepository`'s per-call `pack_context` parameter shape, or
  `MissionTypeRepository` instead gains org/project directories baked into its own `__init__` at
  construction time) is a tasks-phase implementation choice this plan deliberately leaves open —
  both shapes satisfy FR-001's stated cache-key contract; the tasks phase should pick whichever
  keeps `_inject_projected_fields`'s existing signature (`mission_type_repository.py:171`) least
  disturbed, since that function's producer-scan position is the one CL-001 protects (see
  "Producer-scan constraint" above).
- **Test surface**: `tests/doctrine/missions/test_mission_type_repository.py` — cache-hit vs
  cache-miss for the same `(dirs, pack_context)` pair; two distinct `pack_context`s (same-process,
  two-project regression per NFR-001) return distinct, correct results; `cache_clear()` actually
  clears; `default()`'s own cache key and returned roster are unaffected by any activity on the new
  factory (User Story 3 AC2); a red-first-or-otherwise regression test constructing a scratch
  org/project mission-type pack whose single `*.yaml` file is syntactically invalid YAML, asserting
  the new factory's resolution raises an error whose message contains that file's path (spec.md
  Edge Cases: malformed/unparsable YAML, CL-006).

### IC-02 — Thread `PackContext` into action-sequence/template-set projection

- **Purpose**: `resolve_mission_type_context` already constructs a `PackContext` one frame down
  (`existing_mission_types()` → `PackContext.from_config(repo_root)`,
  `mission_type_profiles.py:507`) — keep that object and thread it into both projection slots, by
  two structurally different edits: `_resolve_template_set_slot` (`:841-884`) genuinely hardcodes
  `pack_context=None` in its `MissionStepRepository` call (`:878`) and needs that argument replaced
  with the real `PackContext`; `_resolve_action_slot` (`:762-807`) has **no** `pack_context`
  parameter at all today — its fix is a repository-call swap (from `MissionTypeRepository.default()`
  at `:793` to IC-01's new layered factory), not argument-threading.
- **Relevant requirements**: FR-002.
- **Affected surfaces**: `src/charter/mission_type_profiles.py` — `resolve_mission_type_context`
  (`:516-618`), `_resolve_action_slot`, `_resolve_template_set_slot`; both slot functions gain a
  `pack_context` parameter and call IC-01's new factory instead of
  `MissionTypeRepository.default()` when a non-built-in type is in play.
- **Sequencing/depends-on**: IC-01 (needs the new factory to exist first).
- **Risks**: the edge case in spec.md ("project overrides org overrides built-in, via full
  per-compound-key replacement — deliberately NOT the field-level merge
  `docs/adr/3.x/2026-05-16-1-doctrine-layer-merge-semantics.md` mandates") must be implemented as
  full-replace, not accidentally imported by analogy from that unrelated ADR — confirmed as a
  live risk because `MissionTypeRepository` deliberately does **not** inherit
  `BaseDoctrineRepository` (`src/doctrine/base.py`), which is where that ADR's field-merge helpers
  (`_apply_org_overrides`/`_apply_project_overrides`) actually live.
- **Test surface**: `tests/charter/test_mission_type_profiles.py` — an org-pack type with a
  populated `action_sequence` projects real, non-empty fields (User Story 1 AC2); a project-layer
  override that omits `action_sequence` trips IC-05's loud-fail exactly as an org-layer omission
  would (full-replace, not silent inherit); `tests/runtime/test_runtime_seam.py`'s existing golden
  parity check for all 4 built-ins must keep passing byte-identically (User Story 3 AC1).

### IC-03 — `charter activate mission-type` scans org and project layers

- **Purpose**: `_scan_layout_for(None)` (`src/charter/pack_manager.py:227-229`) returns
  `("missions/mission_types", "*.yaml", False)` — `layered=False` — and `_resolve_layer_candidate`
  (`:256-317`) only resolves a directory for `layer == "built-in"` when `layered=False`; org and
  project layers fall through to `return None` (line 317), so `charter activate mission-type qa`
  can never find a non-built-in `qa` today, confirmed live (not merely per the R&D spike) by
  reading both functions' full bodies.
- **Relevant requirements**: FR-003, FR-005 (project-layer location = CL-005's flat, non-recursive
  path).
- **Affected surfaces**: `src/charter/pack_manager.py` — add an explicit `kind is None`
  (mission-type) branch to `_resolve_layer_candidate` for `layer in ("org", "project")`, resolving
  to `<pack_root>/mission_types` (org) and `<repo_root>/.kittify/missions/mission_types` (project)
  respectively. `resolve_layer_roots` (`src/specify_cli/cli/commands/charter/_layer_roots.py:10-36`)
  and `activate_cmd` (`src/specify_cli/cli/commands/charter/activate.py:387,433,446`) already resolve
  and pass `layer_roots` generically for every kind including `"mission-type"` — **no change is
  needed in either of those two files**; this IC is scoped entirely to `pack_manager.py`.
- **Sequencing/depends-on**: none functionally (independent of IC-01/IC-02 per spec's own Q5
  independence finding — `CharterPackManager.activate` validates purely against `available_ids`,
  no roster read), but ships in the same PR as IC-01/IC-02 per CL-003's atomicity requirement, and
  should share IC-04's flat-layout constant so activation-availability and roster-resolution never
  diverge on "what counts as an available mission type."
- **Risks**: the `rglob`-vs-`glob` trap the spike flags (`list_available_detailed`,
  `pack_manager.py:808-809`, uses `scan_dir.rglob(glob)` universally) is **structurally
  neutralized, not fixed in code**, by CL-005's own directory choice: `.kittify/missions/mission_types/`
  contains only flat `*.yaml` files with no per-type subdirectory (unlike the rejected
  `.kittify/doctrine/mission_types/<type>/governance-profile.yaml` shape), so `rglob("*.yaml")`
  and `glob("*.yaml")` are behaviorally identical there. This plan does **not** propose changing
  `rglob` to `glob` in `list_available_detailed` — that would be an unrelated, broader-blast-radius
  change (it affects every other charter-activatable kind) outside this mission's scope. A
  regression test proves the non-collision explicitly rather than relying on this being "obviously
  fine."
- **Test surface**: a new `tests/charter/test_pack_manager.py`-adjacent (or extended existing)
  test constructing a scratch org pack with `mission_types/qa.yaml` and confirming
  `CharterPackManager.list_available(ctx, "mission-type", layer_roots=...)` includes `"qa"`
  post-fix and excludes it pre-fix (i.e., the test is written to fail against the current
  `_resolve_layer_candidate` body first).

### IC-04 — CL-005 project-layer roster location

- **Purpose**: pin the project-layer mission-type roster at
  `.kittify/missions/mission_types/*.yaml`, scanned non-recursively, and confirm — not merely
  assert — that this location has no live collision with the pre-existing `.kittify/missions/<mission_name>/`
  per-mission-instance directory convention (`src/specify_cli/mission.py:79,463,473,476,502,829`).
- **Relevant requirements**: FR-005.
- **Affected surfaces**: `src/charter/pack_manager.py` (same edit as IC-03 — this IC states the
  *location choice*, IC-03 states the *scan-branch mechanism*; they are one code change,
  split here only for requirements traceability).
- **Sequencing/depends-on**: same commit as IC-03.
- **Risks**: **the real protection against this collision is pre-existing and structural, not a
  byproduct of this mission's own deletions.** `_mission_dir_if_valid`
  (`src/specify_cli/mission.py:74-75`) only recognizes a subdirectory as a mission instance when it
  contains a file literally named `mission.yaml` — a roster directory of flat `*.yaml` files named
  after mission-type ids (CL-005's shape) never satisfies that check, regardless of whether
  `discover_missions()`/`list_cmd` exist to call it. `discover_missions()`
  (`src/specify_cli/mission.py:806-841`) — the scanner `list_cmd`/`_print_available_missions` call
  — does treat every subdirectory of `.kittify/missions/` as a *candidate*, but it still routes
  every candidate through `_mission_dir_if_valid` (line 834) before accepting it, so even with that
  dead code left live, a `.kittify/missions/mission_types/` directory containing only flat YAML
  files (no `mission_types/mission.yaml`) would never have been misinterpreted as a mission
  instance. This mission's own CL-004a deletion (IC-06) is still good hygiene — it removes a
  shadowed, confirmed-dead second scanner from the exact file FR-006/FR-007/FR-008 modify — but it
  is not the operative safeguard against this particular collision; `_mission_dir_if_valid`'s
  `mission.yaml`-presence check is, and it would hold even had IC-06 never run.
- **Test surface**: covered by IC-03's test (same fixture); no separate test file needed beyond
  confirming a scratch `.kittify/missions/mission_types/qa.yaml` resolves as a mission-type roster
  entry, not as a mission instance (i.e., `discover_missions`, if it still existed, would not have
  seen it — moot post-IC-06, but worth one assertion that nothing in the surviving code path
  treats it as a mission instance).

### IC-05 — Loud failure for empty action sequence (dominant risk, red-first)

- **Purpose**: raise a named, specific exception — `MissionTypeEmptyActionSequenceError` (or
  equivalent name decided in tasks phase) — when a non-built-in-layer mission type resolves with
  no `action_sequence`, instead of silently degrading to `[]`. This is the mission's own stated
  reason for existing (CL-003).
- **Relevant requirements**: FR-004, NFR-005 (red-first ordering), NFR-002 (no silent success).
- **Affected surfaces**: `src/charter/mission_type_profiles.py` — new exception class following
  the existing `UnknownMissionTypeError` pattern (class definition at `:193-229`, raised at
  `:738` and `:799` for the two existing hard-fail branches); the new raise site sits inside
  `_resolve_action_slot` (`:762-807`), specifically the branch that currently returns
  `list(mission.action_sequence or [])` (`:807`) when `mission.action_sequence` is `None`/empty
  for a non-built-in-layer resolution.
- **Sequencing/depends-on**: IC-01/IC-02 (needs the layered lookup and pack_context threading to
  exist so a non-built-in type can be resolved at all before this raise site can fire on it).
- **Risks**: NFR-005's verification bar is explicit — "reviewers identify the commit SHA that
  introduces the CL-003 regression test, check it out in isolation (without the fix commit), and
  confirm the test fails there." This IC's own commit sequencing must literally produce two commits
  in that order (test first, RED; fix second, GREEN), not one combined commit — this plan states
  that as a process requirement for whichever WP implements this IC, not merely a testing detail.
- **Test surface**: `tests/charter/test_mission_type_profiles.py` — the red-first commit adds a
  test asserting the silent `[]` degradation that becomes live only once IC-01/IC-02 land (per
  Summary) is now expected to raise `MissionTypeEmptyActionSequenceError` (this test is RED
  against the pre-fix code, by construction); the fix commit makes it GREEN. A second test
  confirms `mission create` against
  the same misconfigured type propagates the same exception *type* (User Story 2 AC2 — asserted
  on `isinstance`, never message substring).

### IC-06 — Delete dead code (`resolve_mission_steps`; `list_cmd` cluster) + docstring fix

- **Purpose**: the campsite-clean opening commit's content (see "Campsite-Clean Opening Commit"
  above) plus the stale-docstring correction (FR-011, CL-004) that would otherwise misdirect the
  next reader toward a seam ("WP06") that is not an org/project seam at all.
- **Relevant requirements**: FR-010, FR-011, FR-013.
- **Affected surfaces**: `src/charter/resolver.py` (delete `resolve_mission_steps`,
  lines 908-937), `tests/charter/test_resolver.py` (delete its one test),
  `src/specify_cli/cli/commands/mission_type.py` (delete `list_cmd` lines 150-151,
  `_print_available_missions` line 122 through its body, and the `discover_missions` name only
  from the import block at lines 38-46), `src/doctrine/missions/mission_type_repository.py`
  (correct the docstring at line 177, which currently reads "those apply through the separate
  runtime consumer switch, WP06" — replace with an accurate statement that org/project overrides
  are handled by the new layered lookup this mission adds, per IC-01/IC-02, not by any WP06
  consumer switch).
- **Sequencing/depends-on**: none — this is the mission's first commit (see "Campsite-Clean
  Opening Commit"), landing before IC-01 begins.
- **Risks**: none identified beyond the import-pruning precision already called out in
  "Campsite-Clean Opening Commit" (delete only the one now-dead name from the multi-name import,
  not the whole block).
- **Test surface**: no new test needed for the deletions themselves beyond confirming the test
  suite still collects/passes without the deleted tests (i.e., their removal is itself validated
  by the suite no longer referencing them); `tests/cli/test_charter_mission_type_commands.py`
  (verified live: no `tests/specify_cli/cli/commands/test_mission_type.py` exists — this
  pre-existing file already exercises the app's command routes end-to-end and is the real home
  for this assertion) gains one assertion that `list_mission_types` (`mission_type.py:1429-1450`)
  is the sole `"list"` command registered on the app (CL-004a / SC-006's grep-verifiable claim,
  made executable as a test rather than left as a manual grep).

### IC-07 — Four CLI-surface fixes (FR-006–FR-009)

- **Purpose**: stop each of the four consumer surfaces from tolerating-and-lying about a
  non-built-in mission type, using IC-01's layered lookup and IC-02's real projected fields.
- **Relevant requirements**: FR-006, FR-007, FR-008, FR-009.
- **Affected surfaces**: `src/specify_cli/cli/commands/charter/mission_type.py`
  (`charter_mission_type_list`, `:49-84` — replace the `source_layer: "unknown"` branch with a
  real per-id layer lookup); `src/specify_cli/cli/commands/mission_type.py`
  (`show_mission_type`, `:1450-1520` — three problem sites in this one function, each independently
  re-verified live: (1) the `mt is None` → `typer.Exit(1)` branch at lines 1487-1490, which wrongly
  hard-fails for a genuinely-activated-but-non-built-in type because it queries the built-in-only
  `MissionTypeRepository.default()` (line 1485) instead of the layered lookup; (2) the JSON-output
  branch's hardcoded `"source_layer": "built-in"` literal at line 1531; (3) the human-readable
  Panel branch's own, independently-hardcoded `"[cyan]Source Layer:[/cyan] built-in"` literal at
  line 1543 — the default, non-`--json` output path that User Story 1 AC3 exercises. (2) and (3)
  are two separate lying sites, not one, because the JSON branch and the Panel branch each build
  their output list from scratch rather than sharing one already-computed `source_layer` value —
  fixing (2) alone leaves (3) unfixed); `src/specify_cli/cli/commands/doctrine.py`
  (`_collect_built_in_mission_types` / `mission_type_list`, `:1028-1069` — extend `rows` (assigned
  at line 1067) to include org/project entries, matching the command's own pre-existing docstring
  promise at `:1058-1059`); `src/specify_cli/cli/commands/charter/activate.py`
  (`_emit_step_removal_warnings`, `:151-192` — replace with layer-aware resolution the bare
  `except Exception: current_seq = []` at lines 180-181 and the
  `MissionTypeRepository.default().get(artifact_id)` call at line 183, per spec's Edge Cases note
  that a resolution failure must surface, not be silently treated as "no steps were removed").
- **Sequencing/depends-on**: IC-01, IC-02 (needs real layer/projection data to report); IC-03
  (activation must actually succeed for a non-built-in type before these display surfaces have
  anything real to show); ships after IC-06's deletion in the same PR (CL-004a explicitly requires
  this — "the same PR as the FR-006/FR-007/FR-008 work").
- **Risks**: the `mission-type show`/`charter mission-type list` JSON output shape must not change
  field names or types (Contract Movement table above) — only values change from placeholder to
  real.
- **Test surface**: `tests/cli/test_charter_mission_type_commands.py` (FR-006's `charter
  mission-type list`), `tests/specify_cli/cli/commands/test_mission_type_template_set_cli.py`
  (FR-007's `show_mission_type` — must assert the correct resolved layer is shown on **both** the
  `--json` output (site 2 above, line 1531) **and** the default, non-`--json` Panel output (site 3
  above, line 1543) for the same activated non-built-in type; a fix that threads the real layer
  through the JSON branch only, leaving the Panel branch's `"built-in"` literal in place, must fail
  this test), `tests/cli/test_doctrine_commands.py` (FR-008's `doctrine
  mission-type list`), and `tests/cli/test_charter_activate_warning.py` (FR-009) — one test per
  surface exercising an activated non-built-in type end-to-end (User Story 1 AC1/AC3);
  `tests/cli/test_charter_activate_warning.py` specifically extended for the "resolution failure
  surfaces, not silently treated as no removed steps" edge case from spec.md's Edge Cases section.
  (`tests/specify_cli/cli/commands/test_mission_type.py` does not exist — verified live; the four
  files above are the real, pre-existing homes for these four surfaces' tests.)
