# Work Packages: Stop the literal-`${…}`-filename test leak and guard it

**Mission**: `cmd-output-file-leak-guard-01KWVZX7` | **Issue**: #2169 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Subtask Format: `[Txxx] Description (WP)`

## Path Conventions
Repo-root-relative. Single coherent unit: fix the one leaking fake + add the class-closing filename guard, registered in the sharded arch pole. One work package.

| Subtask | Description | WP | Requirement |
| --- | --- | --- | --- |
| T001 | Fix BOTH `--output=` parsers (wired `fake_run_with_xml` + dead twin `fake_run`) → env path / `tmp_path` cwd, or delete the twin; no `Path(m.group)` residue | WP01 | FR-001, FR-002 |
| T002 | New `tests/architectural/test_no_invalid_windows_filenames.py` — two named sets (Windows-illegal + shell-telltale) tracked-filename guard | WP01 | FR-003 |
| T003 | Register the guard in `tests/_arch_shard_map.py` (`_ARCH_SHARD_N_FILES`) so it earns an `arch_shard_N` marker (#2397) | WP01 | NFR-001 |
| T004 | Non-vacuous proof: leak RED@scratch-cwd (env-independent)→GREEN; guard RED on a genuinely-Windows-illegal file (`a"b.txt`) AND a `${}` file; completeness gate + per-shard selector green | WP01 | FR-004, SC-001..003 |

---

## Work Package WP01: Fix the leaking fake + add the registered filename guard (Priority: P1)

**Prompt**: `/tasks/WP01-leak-fix-and-guard.md`

**Goal**: The one leaking test double stops writing a `"${…}"` file into cwd (env-independent), and a new architectural guard — **registered in the sharded arch pole** — fails any PR whose tracked tree contains a Windows-illegal filename, so this can never reach Windows CI again.

**Independent test**: `test_capture_baseline_custom_test_runner_label` run from a scratch cwd leaves it clean (var set or unset); the new guard goes RED on a forbidden-char-named tracked file and is selected by `-m 'arch_shard_<N> and not windows_ci and (git_repo or integration or architectural)'`; `test_arch_shard_marker_completeness.py` green.

### Included Subtasks
- [ ] T001 Fix `fake_run_with_xml` to write to the env path / tmp cwd (WP01)
- [ ] T002 New forbidden-char tracked-filename guard (WP01)
- [ ] T003 Register the guard in `tests/_arch_shard_map.py` (WP01)
- [ ] T004 Non-vacuous proof + all-green (WP01)

### Implementation Notes
Mirror the safe sibling fakes at `test_baseline.py:~253/294/338` (`Path(kwargs["env"]["SPEC_KITTY_CMD_OUTPUT_FILE"]).write_text(...)`). The product (`configured_command.py`) is correct — do not touch it. The guard + its shard-map registration MUST land together (an unregistered `tests/architectural/` file breaks `test_arch_shard_marker_completeness.py`).

### Parallel Opportunities
None — single WP; the guard and its registration are coupled.

### Dependencies
None.

### Risks & Mitigations
- **Shard deselection / RED completeness gate**: an unregistered guard is silently deselected AND reds the completeness test. — Register in `_ARCH_SHARD_N_FILES` in the same change; verify under the per-shard selector.
- **Vacuous guard**: — mutation-check (add a forbidden-char tracked file → RED).
- **Preserve the test's assertion**: `test_capture_baseline_custom_test_runner_label` keeps asserting the custom-runner-label behavior; only redirect the write.
