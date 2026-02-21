---
work_package_id: WP04
title: Phase Configuration
lane: "done"
dependencies:
- WP01
base_branch: 2.x
base_commit: 1b37d3a7c2a626005000cff7b1dd2e76a87de203
created_at: '2026-02-08T14:31:46.056310+00:00'
subtasks:
- T017
- T018
- T019
- T020
- T021
phase: Phase 0 - Foundation
assignee: ''
agent: "claude-wp04"
shell_pid: "42771"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-02-08T14:07:18Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 -- Phase Configuration

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP04 --base WP01
```

This WP depends on WP01 (uses Lane enum for phase validation context). Branch from WP01's branch. WP04 can be implemented in parallel with WP02 and WP05.

---

## Objectives & Success Criteria

Create the three-tier phase resolution system that controls how the status model behaves throughout the application. The phase determines whether the system runs in hardening mode, dual-write mode, or read-cutover mode. This WP delivers:

1. `resolve_phase()` function with three-tier precedence: meta.json > config.yaml > built-in default
2. Support for the `status.phase` key in `.kittify/config.yaml`
3. Support for the `status_phase` field in feature `meta.json`
4. 0.1x branch cap enforcement (max phase 2)
5. Source description tracking (tells the caller where the phase value came from)
6. Comprehensive unit tests

**Success**: `resolve_phase()` returns the correct phase number and source description for each precedence level. meta.json overrides config.yaml, config.yaml overrides the built-in default. The 0.1x branch cap prevents phase values beyond 2.

---

## Context & Constraints

- **Spec**: `kitty-specs/034-feature-status-state-model-remediation/spec.md` -- FR-026 (phase configuration mechanism)
- **Plan**: `kitty-specs/034-feature-status-state-model-remediation/plan.md` -- AD-5 (Phase Configuration), Phase behaviors (0=hardening, 1=dual-write, 2=read-cutover), 0.1x cap
- **Data Model**: `kitty-specs/034-feature-status-state-model-remediation/data-model.md` -- Phase Configuration section, Resolution Logic pseudocode

**Key constraints**:

- Phase values: 0 (hardening), 1 (dual-write), 2 (read-cutover)
- Built-in default: Phase 1 (dual-write)
- Resolution order: `meta.json.status_phase` > `config.yaml.status.phase` > built-in default (1)
- On 0.1x branch line: phase capped at 2 maximum
- Do NOT modify existing config loader or meta.json loader -- read the new keys independently
- Use existing loading patterns from the codebase (json.loads for meta.json, YAML for config.yaml)
- Phase must be an integer (0, 1, or 2) -- reject non-integer values

**Existing code references**:

- Config loading pattern: see `src/specify_cli/agent_config.py` for how `.kittify/config.yaml` is read
- Meta.json loading: see `src/specify_cli/core/feature_detection.py` for how `meta.json` is read
- Git branch detection: `subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], ...)`

---

## Subtasks & Detailed Guidance

### Subtask T017 -- Create `src/specify_cli/status/phase.py`

**Purpose**: Main module for phase resolution with the three-tier precedence chain.

**Steps**:

1. Create `src/specify_cli/status/phase.py` with imports:

   ```python
   from __future__ import annotations

   import json
   import logging
   import subprocess
   from pathlib import Path

   logger = logging.getLogger(__name__)
   ```

2. Define constants:

   ```python
   VALID_PHASES = (0, 1, 2)
   DEFAULT_PHASE = 1
   DEFAULT_PHASE_SOURCE = "built-in default (Phase 1: dual-write)"
   MAX_PHASE_01X = 2
   ```

3. Implement `resolve_phase()`:

   ```python
   def resolve_phase(repo_root: Path, feature_slug: str) -> tuple[int, str]:
       """Resolve the active status phase.

       Precedence (highest to lowest):
       1. meta.json status_phase (per-feature override)
       2. config.yaml status.phase (global default)
       3. Built-in default: 1 (dual-write)

       On 0.1x branch line, phase is capped at MAX_PHASE_01X.

       Returns:
           Tuple of (phase_number, source_description)
       """
       # 1. Check per-feature override in meta.json
       meta_phase = _read_meta_phase(repo_root, feature_slug)
       if meta_phase is not None:
           phase = meta_phase
           source = f"meta.json override for {feature_slug}"
       else:
           # 2. Check global config
           config_phase = _read_config_phase(repo_root)
           if config_phase is not None:
               phase = config_phase
               source = "global default from .kittify/config.yaml"
           else:
               # 3. Built-in default
               phase = DEFAULT_PHASE
               source = DEFAULT_PHASE_SOURCE

       # Apply 0.1x cap
       if is_01x_branch(repo_root) and phase > MAX_PHASE_01X:
           logger.info(
               "Phase %d capped to %d on 0.1x branch",
               phase, MAX_PHASE_01X,
           )
           phase = MAX_PHASE_01X
           source = f"{source} (capped to {MAX_PHASE_01X} on 0.1x)"

       return phase, source
   ```

4. Implement private helper `_read_meta_phase()`:

   ```python
   def _read_meta_phase(repo_root: Path, feature_slug: str) -> int | None:
       """Read status_phase from feature's meta.json. Returns None if not set."""
       meta_path = repo_root / "kitty-specs" / feature_slug / "meta.json"
       if not meta_path.exists():
           return None
       try:
           data = json.loads(meta_path.read_text(encoding="utf-8"))
           raw = data.get("status_phase")
           if raw is None:
               return None
           phase = int(raw)
           if phase not in VALID_PHASES:
               logger.warning(
                   "Invalid status_phase %d in %s (expected %s), ignoring",
                   phase, meta_path, VALID_PHASES,
               )
               return None
           return phase
       except (json.JSONDecodeError, ValueError, TypeError) as exc:
           logger.warning("Failed to read status_phase from %s: %s", meta_path, exc)
           return None
   ```

5. Implement private helper `_read_config_phase()`:

   ```python
   def _read_config_phase(repo_root: Path) -> int | None:
       """Read status.phase from .kittify/config.yaml. Returns None if not set."""
       config_path = repo_root / ".kittify" / "config.yaml"
       if not config_path.exists():
           return None
       try:
           from ruamel.yaml import YAML
           yaml = YAML()
           data = yaml.load(config_path.read_text(encoding="utf-8"))
           if not isinstance(data, dict):
               return None
           status_section = data.get("status")
           if not isinstance(status_section, dict):
               return None
           raw = status_section.get("phase")
           if raw is None:
               return None
           phase = int(raw)
           if phase not in VALID_PHASES:
               logger.warning(
                   "Invalid status.phase %d in %s (expected %s), ignoring",
                   phase, config_path, VALID_PHASES,
               )
               return None
           return phase
       except Exception as exc:
           logger.warning("Failed to read status.phase from %s: %s", config_path, exc)
           return None
   ```

**Files**: `src/specify_cli/status/phase.py` (new file)

**Validation**:

- With meta.json containing `status_phase: 2` and config.yaml containing `status.phase: 1`, `resolve_phase()` returns `(2, "meta.json override for ...")`
- With no meta.json override and config.yaml containing `status.phase: 0`, returns `(0, "global default from .kittify/config.yaml")`
- With neither set, returns `(1, "built-in default (Phase 1: dual-write)")`

**Edge Cases**:

- meta.json does not exist: skip to config.yaml
- config.yaml does not exist: skip to default
- meta.json has `status_phase: "invalid"`: log warning, skip to config.yaml
- config.yaml has `status: null`: skip to default
- config.yaml has `status.phase: 5` (out of range): log warning, skip to default

---

### Subtask T018 -- Add `status.phase` key to config.yaml loading

**Purpose**: Ensure the `status.phase` key is recognized in `.kittify/config.yaml`.

**Steps**:

1. This is already handled within `_read_config_phase()` in T017 -- the function reads the key independently without modifying the existing config loader
2. Verify that adding `status:\n  phase: 1` to an existing config.yaml does not break other config loading
3. The `status` key is a new top-level section in config.yaml, sitting alongside existing sections like `agents`

**Expected config.yaml format**:

```yaml
# Existing keys...
agents:
  available:
    - opencode
    - claude

# New key added by this feature
status:
  phase: 1  # 0=hardening, 1=dual-write, 2=read-cutover
```

**Files**: `src/specify_cli/status/phase.py` (same file -- reading logic is self-contained)

**Validation**:

- Load a config.yaml with both `agents` and `status.phase` sections -- both are read correctly by their respective loaders
- Load a config.yaml WITHOUT the `status` section -- existing behavior unchanged

**Edge Cases**:

- `status` key exists but is not a dict (e.g., `status: "enabled"`) -- treated as phase not set
- `status.phase` is a float (e.g., `1.5`) -- `int()` conversion truncates, but validation rejects if not in VALID_PHASES

---

### Subtask T019 -- Add `status_phase` field to meta.json loading

**Purpose**: Ensure the `status_phase` field is recognized in feature `meta.json`.

**Steps**:

1. This is already handled within `_read_meta_phase()` in T017 -- the function reads the key independently without modifying the existing meta.json loader
2. Verify that adding `"status_phase": 2` to an existing meta.json does not break other meta.json loading
3. The `status_phase` key is a new top-level field in meta.json, sitting alongside existing fields

**Expected meta.json format**:

```json
{
  "feature_slug": "034-feature-status-state-model-remediation",
  "created_at": "2026-02-08",
  "status_phase": 2
}
```

**Files**: `src/specify_cli/status/phase.py` (same file -- reading logic is self-contained)

**Validation**:

- Load a meta.json with and without `status_phase` -- both work correctly
- Existing code that reads meta.json for other fields is unaffected

**Edge Cases**:

- meta.json is valid JSON but not a dict (e.g., `["array"]`) -- handled by `data.get("status_phase")` failing gracefully
- meta.json has `"status_phase": null` -- treated as not set (returns None)

---

### Subtask T020 -- 0.1x branch cap enforcement

**Purpose**: When running on a 0.1x branch line (e.g., `main`, `release/0.13.x`), cap the maximum phase at 2.

**Steps**:

1. Implement `is_01x_branch()`:

   ```python
   def is_01x_branch(repo_root: Path) -> bool:
       """Check if the current git branch is on the 0.1x line.

       The 0.1x line includes:
       - main branch
       - release/0.1x.y branches (e.g., release/0.13.0)
       - Any branch matching 0.1x patterns

       The 2.x line includes:
       - 2.x branch
       - Branches starting with "2." or "034-" (feature branches on 2.x)

       Returns False if git is unavailable or branch cannot be determined.
       """
       try:
           result = subprocess.run(
               ["git", "rev-parse", "--abbrev-ref", "HEAD"],
               cwd=repo_root,
               capture_output=True,
               text=True,
               timeout=5,
           )
           if result.returncode != 0:
               return False
           branch = result.stdout.strip()

           # 2.x line branches are NOT 0.1x
           if branch.startswith("2.") or branch == "2.x":
               return False

           # Feature branches on 2.x
           if branch.startswith("034-"):
               return False

           # Everything else is 0.1x (main, release/*, etc.)
           return True
       except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
           return False
   ```

2. The cap is applied in `resolve_phase()` (already implemented in T017) after the phase value is determined but before returning.

3. When the cap is applied, the source description is amended with `"(capped to 2 on 0.1x)"` to make the override visible.

**Files**: `src/specify_cli/status/phase.py` (same file)

**Validation**:

- On a 2.x branch with phase=3 (hypothetical): no cap applied, returns 3 (but validation elsewhere rejects)
- On main branch with meta.json phase=3 (hypothetical): capped to 2 with amended source
- On main branch with default phase=1: no cap needed, returns 1 unchanged

**Edge Cases**:

- Detached HEAD (`branch == "HEAD"`): not matched as 2.x, so treated as 0.1x (cap applied) -- conservative default
- Git not available (no git installed): `is_01x_branch()` returns False (no cap) -- fails open
- Branch name contains "2." but is not 2.x line (e.g., "feature-v2.0-compat"): starts with "feature", not "2.", so treated as 0.1x

---

### Subtask T021 -- Unit tests for phase resolution

**Purpose**: Verify the complete precedence chain, cap enforcement, and source descriptions.

**Steps**:

1. Create `tests/specify_cli/status/test_phase.py`
2. Use `tmp_path` fixture to create test config files
3. Mock `subprocess.run` for git branch detection in cap tests
4. Test cases:

   - `test_default_phase_when_no_config` -- no meta.json, no config.yaml: returns `(1, "built-in default (Phase 1: dual-write)")`
   - `test_config_yaml_overrides_default` -- config.yaml has `status.phase: 0`, no meta.json override: returns `(0, "global default from .kittify/config.yaml")`
   - `test_meta_json_overrides_config_yaml` -- meta.json has `status_phase: 2`, config.yaml has `status.phase: 1`: returns `(2, "meta.json override for ...")`
   - `test_meta_json_overrides_default` -- meta.json has `status_phase: 0`, no config.yaml: returns `(0, "meta.json override for ...")`
   - `test_invalid_meta_json_phase_ignored` -- meta.json has `status_phase: 99`: falls through to config or default
   - `test_invalid_config_phase_ignored` -- config.yaml has `status.phase: -1`: falls through to default
   - `test_non_integer_phase_ignored` -- meta.json has `status_phase: "two"`: falls through
   - `test_01x_cap_enforcement` -- on main branch with phase=3 (hypothetical extended range): capped to 2
   - `test_01x_cap_not_applied_on_2x` -- on 2.x branch: no cap applied
   - `test_source_description_accuracy` -- verify each source string is descriptive and unique
   - `test_missing_meta_json_file` -- meta.json does not exist: gracefully skips to config
   - `test_missing_config_yaml_file` -- config.yaml does not exist: gracefully skips to default
   - `test_config_yaml_no_status_section` -- config.yaml exists but has no `status` key: returns default
   - `test_config_yaml_status_not_dict` -- config.yaml has `status: true`: treated as not set
   - `test_is_01x_branch_main` -- `is_01x_branch()` returns True for "main"
   - `test_is_01x_branch_2x` -- `is_01x_branch()` returns False for "2.x"
   - `test_is_01x_branch_feature` -- `is_01x_branch()` returns False for "034-feature-name"

**Files**: `tests/specify_cli/status/test_phase.py` (new file)

**Validation**: `python -m pytest tests/specify_cli/status/test_phase.py -v` -- all pass

**Edge Cases**:

- Test with corrupted meta.json (invalid JSON): warning logged, falls through to config
- Test with empty config.yaml file: parsed as None, falls through to default
- Test the amended source description when cap is applied

---

## Test Strategy

**Required per user requirements**: Unit tests covering phase resolution precedence and cap.

- **Coverage target**: 100% of phase.py
- **Test runner**: `python -m pytest tests/specify_cli/status/test_phase.py -v`
- **Mocking**: Mock `subprocess.run` for `is_01x_branch()` tests to control branch name
- **File-based tests**: Use `tmp_path` to create real config.yaml and meta.json files
- **Precedence tests**: Each level of the precedence chain must be tested in isolation and in combination
- **Negative tests**: Invalid values, missing files, corrupted files must all be tested

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Config.yaml schema change | Breaks existing projects | Additive key only -- existing configs without `status` section unaffected |
| meta.json schema change | Breaks existing features | Additive field only -- existing meta.json without `status_phase` unaffected |
| Git subprocess failure | Cannot detect branch for cap | `is_01x_branch()` returns False on failure (fails open -- no cap applied) |
| Future phase values beyond 2 | Need to extend VALID_PHASES | VALID_PHASES is a constant, easy to extend later |
| ruamel.yaml import in phase.py | Import overhead | Local import inside `_read_config_phase()` to minimize import cost when config is not read |

---

## Review Guidance

- **Check precedence order**: meta.json > config.yaml > built-in default. Verify with all three set, then with each removed
- **Check validation**: Only 0, 1, 2 accepted. Invalid values logged and skipped, not error
- **Check cap enforcement**: `is_01x_branch()` correctly identifies 0.1x vs 2.x branches
- **Check source descriptions**: Each return path has a unique, descriptive source string
- **Check graceful handling**: Missing files, invalid JSON, wrong types all handled without crashing
- **No fallback mechanisms**: Invalid phase values cause the tier to be skipped, falling through to the next tier. This is precedence chain logic, not a fallback mechanism. If all tiers fail, the built-in default is used.

---

## Activity Log

- 2026-02-08T14:07:18Z -- system -- lane=planned -- Prompt created.
- 2026-02-08T14:31:47Z – claude-wp04 – shell_pid=42771 – lane=doing – Assigned agent via workflow command
- 2026-02-08T14:46:43Z – claude-wp04 – shell_pid=42771 – lane=for_review – Moved to for_review
- 2026-02-08T14:46:57Z – claude-wp04 – shell_pid=42771 – lane=done – Moved to done
