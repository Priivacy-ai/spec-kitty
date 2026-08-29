# Research: Accept path-convention portability (#3016)

Phase 0 decisions, consolidated from the pre-spec and post-spec adversarial squads (architect-alphonso,
debugger-debbie, reviewer-renata, randy-reducer, planner-priti — all profile-loaded, read-only) and
verified against `main` at `f43df85`/post-#3783.

## Decision 1 — Mechanism: config-side override, not doctrine edit, not advisory-by-default

- **Decision**: Introduce `project.path_conventions` in `.kittify/config.yaml`, resolved ahead of the
  mission-type `paths:` default. Value channel only.
- **Rationale**: A project's layout is project state, not shared doctrine (editing `mission.yaml` would
  break every other consumer). Advisory-by-default was rejected because it would revert the merged
  honesty mission #3783's blocking-by-default policy (#1892 lineage).
- **Alternatives considered**: (a) edit doctrine `mission.yaml` values — rejected (C-002); (b)
  advisory-by-default — rejected (reverts #3783, both architect and planner independently); (c) layout
  auto-detection from `manage.py`/`go.mod` — deferred to a separate ticket (larger, heuristic).

## Decision 2 — Seam & composition: single upstream merge before the per-key loop

- **Decision**: Merge the override into `declared`/`required_paths` inside `validate_mission_paths`
  (`src/specify_cli/validators/paths.py:~199`) **before** the per-key resolution loop and before the
  artifact-token membership check (`~:224`); read the override one level up in
  `evaluate_path_conventions` (`summary_core.py:~187`) where `repo_root` is in hand.
- **Rationale**: Mirrors the existing research `path_prefix` precedent; keeps artifact-token→`feature_dir`
  routing intact (C-008); avoids a third loop branch that would breach the ≤15 complexity gate
  (current complexity **12/15**, margin 3 — NFR-003). If margin is tight, extract
  `_resolve_required_paths(mission, override, path_prefix)`.
- **Alternatives considered**: merge into post-prefix `required_paths` — rejected (silently breaks
  artifact-token routing); a fourth loop `elif` — rejected (complexity breach).

## Decision 3 — Config reader: one new typed section reader

- **Decision**: Add `load_project_path_conventions(repo_root) -> dict[str,str]` as a new typed section
  reader modeled on `charter_runtime/preflight/config.py`.
- **Rationale**: `.kittify/config.yaml` has no single project-config loader — ~8 section-specific typed
  readers each load independently; the canonical pattern is a new typed section reader, not a raw inline
  `YAML()` load at the seam (C-004, Directive 044).

## Decision 4 — Key vocabulary: extract `valid_path_keys` first

- **Decision**: `valid_path_keys` is currently a function-local literal in
  `MissionConfig.model_post_init` (`mission.py:183`). Extract it to a shared module/class constant, then
  reuse it for override-key validation (C-005, FR-007).
- **Rationale**: A reusable authority can't be "reused" while it's an uncoverable local literal; reuse
  without extraction would re-declare it — the exact drift C-005 forbids.

## Decision 5 — #3785 fold: read `artifacts.optional`, guard `contracts/`

- **Decision**: `acceptance._missing_artifacts` reads `mission.config.artifacts.optional` (token→file/dir
  resolution) instead of the hardcoded `[quickstart, data-model, research, contracts]`. Fetch `mission`
  before the call; handle `mission is None`.
- **Rationale**: The hardcoded list omits software-dev's declared `checklists/` (verified in both
  `mission.yaml` trees) and is simply wrong for non-software-dev missions (it checks software-dev
  artifacts against research/plan/documentation missions). Guard: `contracts/` blocking-vs-warning
  severity is unchanged (C-003); this is a severable P3 WP with a split-tripwire.

## Decision 6 — Regression anchor & fixtures

- **Decision**: Anchor NFR-001/SC-002 beside
  `tests/cross_cutting/misc/test_acceptance_support.py::test_lenient_downgrades_path_conventions_to_warning`;
  build `apps/`/`internal/` fixtures via the existing `_MissionStub` (unit) and `feature_repo`
  (integration) — near-zero cost.
- **Rationale**: A real pre-mission behavior anchor already exists; NFR-001 pins the exact violation
  payload + full `format_errors()` string (not just "non-empty").

## Adversarial evidence disposition (plan/research contract)

Post-spec squad contested findings and their disposition:
- Fakeable SC-001 → **accepted** (added SC-006 negative discriminator).
- Missing single-merge-point boundary → **accepted** (added C-008).
- Unsatisfiable C-005 (`valid_path_keys` not importable) → **accepted** (reworded to extract-then-reuse).
- FR-006 complexity (call-site reorder, `None` fallback, token→file) → **accepted** (FR-006 reworded).
- `checklists/` "contradiction" (reviewer HIGH) → **rejected with evidence**: both `mission.yaml` trees
  declare `checklists/` in software-dev `artifacts.optional`; the hardcoded list omits it. SC-004 stands.
  Adjudicated at source (Paula's read + direct file inspection), not averaged.

No contested finding silently dropped (per `contracts/adversarial-evidence-contract.md`).

## Supply-chain (Directive 051)

No dependency added, upgraded, or removed. Supply-chain install-safety check is a documented **no-op**
for this mission.
