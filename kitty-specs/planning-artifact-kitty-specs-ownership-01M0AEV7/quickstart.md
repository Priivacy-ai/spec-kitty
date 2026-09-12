# Quickstart — verify planning-artifact kitty-specs ownership

## Reproduce the defect (pre-fix, RED)
Author a WP prompt (in a scratch mission) with:
```yaml
execution_mode: planning_artifact
owned_files:
  - kitty-specs/<slug>/disposition-matrix.md
create_intent:
  - kitty-specs/<slug>/disposition-matrix.md
```
Run:
```bash
spec-kitty agent mission finalize-tasks --validate-only --mission <slug> --json
```
Pre-fix observed: `{"error_code":"INVALID_WP_OWNED_FILES_KITTY_SPECS", ...}`.

## Expected (post-fix, GREEN)
- The command succeeds; the WP is placed in `lane-planning`.
- The same prompt with `execution_mode: code_change` is still rejected with
  `INVALID_WP_OWNED_FILES_KITTY_SPECS`.

## Automated verification
```bash
PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 .venv/bin/python -m pytest \
  tests/specify_cli/cli/commands/agent/test_mission_parsing.py \
  tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py \
  tests/tasks/test_finalize_tasks_owned_files_validation.py \
  tests/lanes/test_compute_planning_artifact.py \
  -q -p no:cacheprovider
.venv/bin/ruff check src/specify_cli/cli/commands/agent/mission_parsing.py
.venv/bin/mypy --strict src/specify_cli/cli/commands/agent/mission_parsing.py
```
