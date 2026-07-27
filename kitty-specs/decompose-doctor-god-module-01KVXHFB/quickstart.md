# Quickstart — Verifying the `doctor.py` Decomposition (#2059)

This mission is a behavior-preserving refactor. "Done" means the CLI surface is byte-identical, every function is ≤15 CC, each sibling is ≥90% covered, and the import graph stays one-way with a single `Console()`.

## 1. Golden CLI surface is byte-identical (FR-001, SC-001)

```bash
# Lands in WP01; re-run after EVERY extraction WP:
pytest tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py -q
```

Asserts: the 16 subcommand names (`command-files`, `skills`, `tool-surfaces`, `state-roots`, `workspaces`, `identity`, `topology`, `sparse-checkout`, `shim-registry`, `invocation-pairing`, `ops`, `orphan-daemons`, `restart-daemon`, `mission-state`, `doctrine`, `coordination`), each subcommand's flag/param set, per-subcommand `--help` snapshot, and the documented exit codes are unchanged. Manual spot-check:

```bash
spec-kitty doctor --help                       # 16 subcommands listed
spec-kitty doctor ops --threshold 5            # → BadParameter (needs --close-stale)
spec-kitty doctor skills --json; echo $?       # 0/1/2 contract
spec-kitty doctor restart-daemon --json; echo $?  # 0/1/2/3 contract
```

## 2. Complexity ceiling (NFR-001, SC-004)

```bash
ruff check --select C901 src/specify_cli/cli/commands/doctor.py \
  src/specify_cli/cli/commands/_doctor_shared.py \
  src/specify_cli/cli/commands/_doctrine_collect.py \
  src/specify_cli/cli/commands/_identity_audit.py \
  src/specify_cli/cli/commands/_command_surface_doctor.py \
  src/specify_cli/cli/commands/_mission_state_doctor.py \
  src/specify_cli/cli/commands/_coordination_doctor.py \
  src/specify_cli/cli/commands/_sparse_checkout_doctor.py \
  src/specify_cli/cli/commands/_workspace_husk_doctor.py \
  src/specify_cli/cli/commands/_daemon_doctor.py
```

Zero `C901` findings. The six named mega-functions (`skills` 20, `identity` 19, `sparse_checkout` 19, `_check_lane_sparse_checkout_drift` 19, `state_roots` 17, `_repair_command_skill_state` 16) must be decomposed, not relocated oversized.

## 3. Single `Console()` home (FR-007 / H1, SC-006)

```bash
# Exactly one Console() instance across the doctor surface (in _doctor_shared, or
# re-exported through it from _profile_health_render). No sibling instantiates its own.
git grep -n "Console()" src/specify_cli/cli/commands/_*doctor*.py \
  src/specify_cli/cli/commands/doctor.py src/specify_cli/cli/commands/_doctor_shared.py
```

## 4. No `doctor↔merge` cycle (FR-007 / H2, SC-006)

```bash
# path_is_under_worktrees must be imported INSIDE the function, never at module top:
git grep -n "path_is_under_worktrees" src/specify_cli/cli/commands/_coordination_doctor.py
python -c "import specify_cli.cli.commands.doctor"   # imports clean, no cycle
```

## 5. Test-facing re-exports resolve from `doctor` (FR-006, SC-005)

```bash
python -c "from specify_cli.cli.commands.doctor import (app, SlashCommandGap, \
  _load_slash_command_state, _repair_slash_command_state, _collect_profile_health, \
  _collect_org_layer_data, _build_pack_entries, _count_pack_artifacts, \
  _resolve_pack_version, _render_org_layer_section, _print_overdue_details)"
pytest tests/specify_cli/cli/commands/test_doctor_*.py tests/doctor/ \
  tests/cli_gate/test_doctor_modes.py tests/cli_gate/test_safe_commands.py -q
```

## 6. Per-sibling coverage ≥90% (NFR-002, SC-003)

```bash
pytest tests/specify_cli/cli/commands/test_doctrine_collect.py \
  --cov=specify_cli.cli.commands._doctrine_collect --cov-report=term-missing
# repeat per sibling; each ≥90%.
```

## 7. Pointer comment preserved (FR-002)

```bash
head -7 src/specify_cli/cli/commands/doctor.py   # still references #2059, no new responsibilities
```

## Definition of done (mission level)

- WP01 golden harness green at HEAD and after WP11.
- `doctor.py` ≤ ~400 LOC: `app` + 16 thin shells + re-export block + `_doctor_shared` import.
- 9 new siblings exist beside the 2 existing #1623 siblings; `_doctrine_collect` completes the doctrine MODEL/RENDER/COLLECT triad.
- `ruff` + `mypy --strict` clean, zero new suppressions; full doctor + cli_gate suites green.
