# M3 Discovery / Research — code-truth against current `main` (2026-08-21)

**Audience:** the M3 implementer + reviewer (software-engineer persona).
**Method:** three independent code-truth verification passes over `pr/rc3-charter-gate-predicate-inversion` (== `upstream/main`, fresh cut), plus reading the source investigation (`docs/plans/investigations/friction-bugs-processing-charter-root-cause.md`) and the program sequencing doc (`docs/plans/initiatives/rc3-friction-burndown/rc3-friction-burndown-approach.md`). Every claim below is grounded in a re-verified file:line — not the pre-M0 spec's cited lines, which had drifted.

## 1. The one theme (root cause)

Five charter/runtime surfaces decide **delivery / tolerance / gating** by testing membership in a **coarse hardcoded set** instead of a predicate on the **entity actually declared**. Each starves shipped configuration or fails open:

| # | Surface | Coarse test | Declared entity it should consult |
|---|---------|-------------|-----------------------------------|
| #3596 | `src/charter/context.py:115,255,484` | `action in BOOTSTRAP_ACTIONS` (4-token frozenset) → compact | DRG node membership (`bundle.merged`) |
| #3598 | `src/charter/mission_type_profiles.py:766,1235` | `_project_has_doctrine_overrides(repo_root)` (project-wide) | per-type `governance-profile.yaml` id-match at any layer |
| fold | `src/charter/interview.py:34` | `action in _KNOWN_ACTIONS` (3rd copy) | one canonical vocabulary + declared nodes |
| #3599/#3597 | `analysis_report.py:33`, `runtime_bridge_io.py:841`, `mission_v1/guards.py`, `worktree.py:595-610` | hardcoded artifact filenames / dead guard registry | per-type artifact-name source + live per-type gate |
| #3407 | `runtime_bridge.py:796-798` | `mission_family="software-dev"` (unconditional) | resolved mission family → `_GUARD_TABLES[family]` |

## 2. Best-practice / brownfield context (what already changed under the spec)

The pre-M0 spec was written before M0 landed and before parts of M5/#3407 shipped. Discovery findings that reshape the implementation:

- **M0 landed** (`migrate backfill-mission-type` + fail-closed `doctor mission-type --fail-on`). The #3598 typo hard-fail is safe: real projects are already census-gated.
- **M5's canonical primitive landed** (`src/charter/mission_type_key.py:canonical_mission_type_key`). The delivery path **already** routes through it (`resolve_mission_type_key` → `_resolve_type_key` → `canonical_mission_type_key`): no legacy `mission` read, no `software-dev` default, `None`-degrades, never raises. The symbol the pre-M0 spec named — `read_mission_type()` — **does not exist**. Best practice: consume the landed primitive; do not build a parallel reader (NFR-002).
- **The `plan` guard table already exists** (`_evaluate_plan_guards` in `_GUARD_TABLES["plan"]`, `runtime_bridge_cores.py:680`). The #3407 fix is *routing* (resolve the family at `runtime_bridge.py:797`), not *building* a plan branch.
- **`mission_v1` guard cluster is dead in production** (zero `src/` callers outside tests; live FSM has no guard fields; the live runtime has its own `artifact_exists` at `engine.py:1445`). → design fork (d) = per-type data source, NOT revive-v1.
- **Two artifact vocabularies, no join:** step-contract short keys (`spec`/`plan`, via `MissionStepTemplateRef`) for NAMES; `expected-artifacts.yaml` dotted keys (`input.spec.main`) for gate SETS. `step.yaml` does not exist (the carrier is `*.step-contract.yaml`). Code lives under `src/doctrine/missions/` + `src/specify_cli/runtime/resolver.py`; data lives under `packs/built-in/missions/`.

## 3. Load-bearing hazards (for the implementer)

- **NFR-001 hot-path budget.** Resolving the bundle before the mode decision, or a stray second graph load, trips `tests/charter/test_charter_import_time_io.py` / the ~100 ms FSM path. Thread the already-loaded graph.
- **Red-by-design reversals must be reversed, not "fixed back":** `test_json_non_bootstrap_action_is_explicitly_ruled_out` (every_load_delivery.py:197), `test_project_with_overrides_does_not_hard_fail_for_unknown_type` (mission_type_profiles.py:260), any stray-`spec.md` presence assertion (AC-11), and keep the AC-2 green guard (context.py:228).
- **`_PRESENCE_FILE_TAGS` is 10 filenames, not 3** — the per-type conversion must preserve all 10 for built-ins (NFR-003).
- **C-001 charter ⊥ specify_cli** — the artifact-name charter slot stays `Mapping[str, Any]`; `ExpectedArtifactManifest` relocates from `src/specify_cli/dossier/manifest.py:168` to `src/doctrine/missions/`.
- **M4 same-file coordination** on `src/doctrine/missions/repository.py` (M4 owns `:316-317` fail-loud; M3 owns relocation + name reads).

## 4. Sources

- `docs/plans/investigations/friction-bugs-processing-charter-root-cause.md` (§2.2/§2.3/§10) — five-lens root cause.
- `docs/plans/initiatives/rc3-friction-burndown/rc3-friction-burndown-approach.md` — program sequencing, M0 gate, M3/M5 sign-offs.
- Live tree (re-verified 2026-08-21): all file:line citations in `spec.md` "Respec vs pre-M0 baseline".
- Issues #3596, #3598, #3599, #3597, #3407 (in scope); #3386, #3388 (CLOSED preconditions).
