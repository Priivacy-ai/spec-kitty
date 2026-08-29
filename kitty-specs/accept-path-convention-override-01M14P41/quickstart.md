# Quickstart: Accept path-convention portability

## What changes for the operator
Declare your real layout once:
```yaml
# .kittify/config.yaml
project:
  path_conventions:
    workspace: apps/
    tests: tests/
```
Then `spec-kitty accept` honors it — no fabricated `src/`, no blanket `--lenient`.

## Requirement → test map (ATDD, red-first)

| Req | Test | Tier |
|-----|------|------|
| FR-001, FR-007, FR-008 | `tests/specify_cli/config/test_path_conventions_reader.py` — read key / absent→{} / bad key / malformed→fail-closed | Unit |
| FR-002 | `tests/agent/test_validators_unit.py` — `_MissionStub({workspace:src/})` + override `{workspace:apps/}` ⇒ `required_paths[workspace]==apps/` | Unit |
| FR-003, SC-001 | `test_acceptance_support.py` — `feature_repo` + `apps/` + override ⇒ `path_violations==[]`, clean tree, no `--lenient` | Integration |
| FR-004, SC-003 | `test_acceptance_cores.py::TestEvaluatePathConventions` — a non-software-dev mission honors override at the seam | Unit |
| FR-005 | `test_acceptance_support.py` — Go `internal/` layout accepts | Integration |
| FR-006, SC-004 | `test_missing_artifacts_from_config.py` — optional set from `artifacts.optional` incl. `checklists/`; `contracts/` severity unchanged; `mission is None` fallback; reads a real `mission.yaml` | Unit+Int |
| NFR-001, SC-002 | `test_acceptance_support.py::test_no_override_still_blocks_strict` (beside `:767`) — pins exact `path_violations` payload + full `format_errors()` string | Integration |
| NFR-004b | single-caller guard test — `validate_mission_paths` has exactly one production caller | Unit/arch |
| SC-005 | `ruff check --select C901 src/specify_cli/validators/paths.py` | Static |
| SC-006 | override `apps/` + `apps/` absent ⇒ strict still blocks | Unit/Int |
| C-009 | no existing #3783 lenient/blocking assertion deleted or weakened (diff review + additive coverage) | Review |

## Dev loop
```bash
# from the lane worktree (spec-kitty implement creates it):
PWHEADLESS=1 .venv/bin/python -m pytest tests/agent/test_validators_unit.py \
  tests/specify_cli/acceptance/ tests/specify_cli/config/ \
  tests/cross_cutting/misc/test_acceptance_support.py -q -p no:cacheprovider
ruff check src/specify_cli/validators/paths.py src/specify_cli/config/
mypy src/specify_cli/config/path_conventions.py
# terminology guard (touches acceptance prose):
pytest tests/architectural/test_no_legacy_terminology.py
```

## Definition of done
- All FR/NFR tests green; ruff + mypy --strict clean; complexity ≤15.
- No `mission.yaml` doctrine edit (C-002); ADR committed (C-006); arch-gate pins refreshed (C-007).
- `#3783` regression suite still green and unchanged in contract (C-009).
