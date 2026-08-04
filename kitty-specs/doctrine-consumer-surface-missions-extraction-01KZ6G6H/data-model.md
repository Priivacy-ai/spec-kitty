# Phase 1 Data Model: Missions/ Doctrine Tree Relocation & Gate Preconditions

This mission has no database/persistence entities. "Data model" here means the structural artifacts and invariants the plan introduces or changes — the reader-inventory record, the resolution primitive's contract, the gate-module split, and the synthetic-fixture shape.

## Entity: `MissionsReaderRecord` (FR-003)

One row per identified reader of `src/doctrine/missions/` content, forming the committed inventory artifact.

| Field | Type | Description |
|---|---|---|
| `file` | path | The reader file, e.g. `src/kernel/paths.py`. |
| `line` | int | Line of the reference (import, path construction, or content read). |
| `layer` | enum(`kernel`, `doctrine`, `charter`, `specify_cli`, `runtime`, `upgrade_migration`) | Which architectural layer this reader lives in — determines repoint order (kernel/doctrine first, since IC-04/IC-06 depend on the primitive existing there). |
| `current_path_assumption` | string | What path shape the reader currently assumes (e.g. `src/doctrine/missions/<type>/...`). |
| `decision` | enum(`move`, `stay`, `repoint`) | `move` = content itself relocates (only `src/doctrine/missions/` proper); `repoint` = reader's own reference updates to the new location; `stay` = reader is correct as-is (e.g. already resolves via a seam that doesn't hardcode the old path). |
| `rationale` | string | Why this decision, one sentence. |

**Invariant**: every row has a non-empty `decision` and `rationale` — an inventory row with `decision` empty is not a completed inventory (this is what SC-007 checks). The inventory must include, at minimum, the two sites already identified during post-plan review (`MissionTemplateRepository.default_missions_root()` — decision: `repoint` onto the FR-004 primitive; `drg/migration/extractor.py::_missions_root()` — decision: `repoint`, plus the DRG fragment regeneration) — a review that finds these two rows absent should treat the inventory as incomplete, not merely under-detailed. Rows for the 11 `.py` logic modules under `src/doctrine/missions/` should each carry `decision: stay` (the package itself doesn't move) unless a specific module's own internal path assumptions need `repoint`.

## Entity: `SiblingPathResolutionPrimitive` (FR-004)

The kernel-owned function both `kernel.paths.get_package_asset_root()` and `doctrine.pack_paths._resolve_built_in()` converge onto (per DM-01KZ6JH5).

Conceptual signature (exact name/module left to the implementer within FR-004's constraint):

```python
def resolve_installed_sibling(
    *,
    anchor_file: Path,       # the CALLING module's own __file__ (self-referential, never a hard-coded package-name string)
    env_override: str | None,  # e.g. os.environ.get("SPEC_KITTY_PACKS_ROOT") — caller-supplied, primitive does not know env var names
    sibling_relative_path: PurePosixPath,  # e.g. "packs/built-in" or "packs/built-in/missions"
) -> Path:
    """4-step resolution: env override -> editable-checkout ancestor walk from
    anchor_file -> installed-wheel sibling of anchor_file's own package -> fail-closed.
    Raises a named exception (mirrors PackRootNotFound) on failure; never returns
    a path inside anchor_file's own source tree, never falls open to an arbitrary tree.
    """
```

**Invariants**:
- The primitive itself contains no string identifying `"doctrine"`, `"specify_cli"`, `"kernel"`, or any mission-type name — those are supplied by each caller as `anchor_file`/`sibling_relative_path` arguments.
- **Three** call sites converge onto it — `kernel.paths.get_package_asset_root()`, `doctrine.pack_paths._resolve_built_in()`, **and** `doctrine.missions.repository.MissionTemplateRepository.default_missions_root()` (the authority a prior mission's WP06 already promoted and explicitly deferred converging to this issue, #3091) — each producing identical resolution behavior to what they do today, for every existing passing test (NFR-001).
- `doctrine.pack_paths.doctrine_package_dir()` is a **separate, unmodified** public symbol (identity-pinned by `tests/doctrine/test_built_in_location_authority.py`, and independently consumed by `drg/migration/extractor.py`) — this primitive replaces `_resolve_built_in()`'s internal *call* to it, not the symbol itself.
- Fails closed: never returns a nonexistent path, never falls back to an arbitrary tree. Since the primitive lives in `kernel` and cannot import `doctrine.pack_paths.PackRootNotFound`, it raises its own exception type; `pack_paths._resolve_built_in()` catches and re-raises as `PackRootNotFound` so existing consumers (e.g. `specify_cli/doctrine/pack_validator.py`'s `except (PackRootNotFound, BuiltInContentDirNotAvailable)`) are unaffected.

## Entity: `ArchitecturalGateModule` (FR-001)

The post-split shape of `test_no_dead_doctrine_paths.py`.

| Module (name TBD) | Scans | Scope root | Contains |
|---|---|---|---|
| CLI-wide gate module | Gate A + Gate B | `_SRC_ROOT` (`src/`) | `scan_graph_monolith_paths`/`_shipped`, `scan_shipped_pack_paths`/`_shipped`, their discriminator-proof tests, their planted-violation tests |
| Doctrine-content gate module | Gate C | `_DOCTRINE_ROOT` (`src/doctrine/`) | `scan_doctrine_cross_links`/`_shipped`, its discriminator-proof tests, planted-violation test, the FR-002 synthetic-fixture decoupling |
| Docs gate module | Gate D | `docs/` | `test_no_live_doc_names_a_pre_move_builtin_path` |

**Invariant**: the union of all three modules' assertions equals the current file's assertions exactly — no assertion silently dropped or narrowed (NFR-003's own requirement). The shared scan helpers (`Site` dataclass, `_rel`, `_read_lines`, `_text_files`, and the `_REPO_ROOT`/`_SRC_ROOT`/`_DOCTRINE_ROOT`/`_PACKS_ROOT`/`_TEXT_SUFFIXES` constants — used by Gates A, B, and C today) land in one shared helper module both post-split modules import; they are not duplicated.

## Entity: `MissionsDataContent` vs. `MissionsPythonPackage` (FR-005, FR-003)

The split within `src/doctrine/missions/` that this mission's relocation must not conflate:

| | Contents | Destination |
|---|---|---|
| `MissionsDataContent` | `mission_types/`, `built_in_step_contracts/`, `mission-steps/`, per-type `templates/`/`actions/` | `packs/built-in/missions/` |
| `MissionsPythonPackage` | `repository.py`, `mission_type_repository.py`, `mission_step_repository.py`, `step_projection.py`, `models.py`, `action_index.py`, `primitives.py`, `step_contracts.py`, `step_offer_seam.py`, `glossary_hook.py`, `__init__.py` | Stays in `src/doctrine/missions/` (repointed to read `MissionsDataContent` from its new location) |

**Invariant**: every existing `from doctrine.missions.<module> import ...` call site continues to resolve — the package itself does not move, only the data it reads does.

## Entity: DRG-generated `missions/`-derived fragments (FR-005)

`packs/built-in/mission_type.graph.yaml` and `packs/built-in/mission_step_contract.graph.yaml`, produced by `doctrine/drg/migration/extractor.py`'s `_missions_root()` resolver via `extract_artifact_edges`/`generate_graph`.

**Invariant**: after `_missions_root()` is repointed to the relocated `MissionsDataContent`, regenerating both fragments produces output byte-identical to their committed state (`tests/doctrine/drg/test_regen_roundtrip.py`'s existing assertions are the proof, not a new test).

## Entity: `SyntheticForbiddingMentionFixture` (FR-002)

A `tmp_path`-constructed fixture (mirroring the existing `test_gate_a_rejects_a_planted_violation`/`test_gate_b_rejects_a_planted_violation` idiom in the same file) carrying a planted forbidding-mention string, used in place of the live `doctrine-daphne.agent.yaml` as the NFR-002 discriminator-proof's subject.

**Invariants**:
- The discriminator's effect-set pin still runs against this fixture — an unexpected new exclusion in the fixture is still a visible diff (the anti-widening property SC-006 requires).
- The live `doctrine-daphne.agent.yaml` is free to drop its repo-local `src/doctrine/graph.yaml` mention once this fixture exists, without turning the gate red.

## State transition: `UnknownMissionTypeError` message (FR-007)

Before → after, no new state, a pure message-content fix:

- **Before**: `"Unknown mission type '{id}'. Registered types: {id}."` (self-contradictory when `{id}` is activated but has no loadable profile).
- **After**: two distinct facts stated separately, e.g. `"Mission type '{id}' is activated but has no loadable profile."` — never claims both "unknown" and "registered" of the same id in one sentence.

## No entities for FR-008

The TIER-1 override-template refresh is a content fix (Markdown prose), not a data/schema change — governed entirely by SC-004's textual requirement (no reference to raw construction or the retired `constitution context` command).
