---
description: "Work package task list template for feature implementation"
---

# Work Packages: Mission Handoff Package & Version Matrix

**Inputs**: Design documents from `/kitty-specs/045-mission-handoff-package-version-matrix/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓

**Tests**: Verification note WP (WP06) runs the 4 setup-plan context scenarios that already exist in the test suite. No new tests are written for this feature.

**Organization**: 22 fine-grained subtasks (T001–T022) roll up into 6 work packages (WP01–WP06). All output files committed to `kitty-specs/045-mission-handoff-package-version-matrix/handoff/` on branch `2.x`.

**Source commit anchor**: `21ed0738f009ca35a2927528238a48778e41f1d4` (Merge WP05 from 041, 2026-02-22)

---

## Work Package WP01: Handoff Directory Scaffold + Namespace Tuple (Priority: P0) 🎯 Foundation

**Goal**: Create the `handoff/` output directory and commit the canonical `namespace.json` identity anchor for this wave.
**Independent Test**: `namespace.json` exists, is valid JSON, passes all 6 invariant checks from data-model.md (source_commit is 40-char hex, step_id is null, schema_version is "1", etc.).
**Prompt**: `tasks/WP01-handoff-scaffold-namespace-tuple.md`

### Included Subtasks
- [ ] T001 Create `kitty-specs/045-.../handoff/` directory
- [ ] T002 Write `handoff/namespace.json` with all 9 required fields
- [ ] T003 Validate namespace.json against all 4 invariants from data-model.md

### Implementation Notes
- `handoff/` is a new subdirectory inside the existing feature dir — use a README or .gitkeep so git tracks it before files land
- `project_scope_id`: derive from `basename $(git rev-parse --show-toplevel)` — will be `spec-kitty`
- `source_commit` is hardcoded: `21ed0738f009ca35a2927528238a48778e41f1d4`
- `generated_at`: current UTC time in ISO 8601 format
- Do not auto-commit in this WP — finalize-tasks handles git

### Parallel Opportunities
- None; WP01 is the foundation that all other WPs depend on.

### Dependencies
- None (starting package).

### Risks & Mitigations
- Wrong source_commit → validate the SHA against `git log --oneline` before hardcoding.
- `generated_at` format drift → use `date -u +"%Y-%m-%dT%H:%M:%SZ"` or Python `datetime.utcnow().strftime(...)`.

---

## Work Package WP02: Artifact Manifest Snapshot + Tree Snapshot (Priority: P1)

**Goal**: Generate and commit `artifact-manifest.json` (expected artifact contract at source_commit) and `artifact-tree.json` (actual directory state with SHA-256 fingerprints and present/absent status).
**Independent Test**: Manifest snapshot matches the content of `expected-artifacts.yaml`; tree snapshot lists all files in `kitty-specs/045-.../` with correct fingerprints; absent expected artifacts are explicitly flagged.
**Prompt**: `tasks/WP02-artifact-manifest-and-tree.md`
**Estimated size**: ~320 lines

### Included Subtasks
- [ ] T004 [P] Export `src/specify_cli/missions/software-dev/expected-artifacts.yaml` → `handoff/artifact-manifest.json`
- [ ] T005 [P] Walk `kitty-specs/045-.../` recursively, compute SHA-256 for each file
- [ ] T006 Cross-reference walked entries against manifest to identify expected-but-absent artifacts
- [ ] T007 Write `handoff/artifact-tree.json` with combined present + absent entries and summary counts

### Implementation Notes
- YAML → JSON: `python3 -c "import yaml,json,sys; print(json.dumps(yaml.safe_load(open(sys.argv[1]).read()), indent=2))" path/to/expected-artifacts.yaml`
- Add extra fields to manifest snapshot: `source_commit`, `captured_at`
- Exclude `handoff/` from tree walk (prevents self-referential entries)
- Absent detection: cross-reference `required_always` + `required_by_step["specify"]` path_patterns against walked paths
- Glob patterns in path_pattern (e.g., `tasks/*.md`) must be expanded to check if any match exists

### Parallel Opportunities
- T004 and T005 can run in parallel (different operations on different file sets).

### Dependencies
- Depends on WP01 (handoff/ directory must exist before writing output files).

### Risks & Mitigations
- YAML parsing failure → ensure PyYAML or ruamel.yaml is available in venv; both are spec-kitty deps.
- `handoff/` included in own tree → test the exclusion logic with an assertion before committing.

---

## Work Package WP03: Event Stream Export (Priority: P1)

**Goal**: Export or synthesize the canonical event stream to `handoff/events.jsonl`, preserving insertion order and ensuring UTF-8 / valid JSONL integrity.
**Independent Test**: `events.jsonl` exists; each line is valid JSON with sorted keys; if `status.events.jsonl` was non-empty, line counts match.
**Prompt**: `tasks/WP03-event-stream-export.md`
**Estimated size**: ~220 lines

### Included Subtasks
- [ ] T008 Check `kitty-specs/045-.../status.events.jsonl` — determine if it exists and has content
- [ ] T009 Export events verbatim OR write single synthetic bootstrap event if log is empty
- [ ] T010 Verify `handoff/events.jsonl` integrity: UTF-8 decoding, one JSON object per line, sorted keys

### Implementation Notes
- Verbatim copy: `cp status.events.jsonl handoff/events.jsonl` is sufficient if file has content
- Synthetic bootstrap event (if empty): JSON object with fields: `event_id` (ULID or UUID), `event_type=handoff_package_created`, `feature_slug`, `source_commit`, `source_branch`, `at`, `actor=spec-kitty/045-generator`
- Sorted keys verification: `python3 -c "import json; [json.loads(l) for l in open('events.jsonl')]"` — loads each line
- Do NOT re-sort events from a real event log; insertion order is the invariant

### Parallel Opportunities
- T008 can run in parallel with WP02's T004/T005 (independent read operation).

### Dependencies
- Depends on WP01 (handoff/ directory must exist).

### Risks & Mitigations
- Status events may not yet exist (feature is in spec phase) → the bootstrap event path is expected and not a failure.
- Encoding issues → always open with `encoding="utf-8"` in Python; spec-kitty codec ensures events are already UTF-8.

---

## Work Package WP04: Generator Script (Priority: P1)

**Goal**: Write and commit `handoff/generate.sh` — a minimal, self-contained shell script that regenerates the handoff package from source. Dry-run by default; `--write` activates file emission; `--force` allows overwriting.
**Independent Test**: `generate.sh --help` prints usage; `generate.sh` (dry-run) prints what would be written without creating files; `generate.sh --write --output-dir /tmp/test-handoff` creates all 5 package files (namespace, manifest, tree, events, version-matrix) with correct content; SOURCE_COMMIT in script matches `namespace.json`.
**Prompt**: `tasks/WP04-generator-script.md`
**Estimated size**: ~380 lines

### Included Subtasks
- [ ] T011 Write `generate.sh` header: shebang, set -euo pipefail, embedded SOURCE_COMMIT/SOURCE_BRANCH vars, usage function, arg-parsing, DRY_RUN default
- [ ] T012 Implement `namespace.json` generation step (Python inline, reads git metadata, writes JSON)
- [ ] T013 Implement `artifact-manifest.json` + `artifact-tree.json` generation steps (Python inline for YAML→JSON + SHA-256 walk)
- [ ] T014 Implement `events.jsonl` copy step (cp from status.events.jsonl or synthesize bootstrap event)
- [ ] T015 Implement `version-matrix.md` skeleton step + `chmod +x generate.sh` + dry-run output validation

### Implementation Notes
- Shell structure: `parse_args → check_prereqs → generate_namespace → generate_manifest → generate_tree → export_events → generate_version_matrix → done`
- Dry-run: print each file's target path and byte count estimate, but do NOT write
- `--write`: activate actual file emission
- `--output-dir <path>`: override destination (default: script's own parent directory = `handoff/`)
- `--force`: overwrite existing files without aborting
- All Python invocations: use `python3 -c "..."` with stdlib only (json, hashlib, yaml/ruamel.yaml, datetime, pathlib)
- The version-matrix.md step in the generator produces a skeleton with correct version pins but NOTE: `verification.md` is NOT generated by the script (it requires a manual test run)
- Comment in script: `# NOTE: verification.md requires running pytest manually — see WP06`

### Parallel Opportunities
- None; generator must accurately reflect the actual content of WP01-WP03 output files.

### Dependencies
- Depends on WP01, WP02, WP03 (generator must match what those WPs actually wrote).

### Risks & Mitigations
- Script generates different content than committed files → include a self-check comment pointing to the diff command in quickstart.md.
- YAML library unavailability in fresh env → fallback: use `python3 -c "import json; ..."` with pre-known YAML content (the expected-artifacts.yaml content is stable).

---

## Work Package WP05: Version Matrix Note (Priority: P1)

**Goal**: Write and commit `handoff/version-matrix.md` — a human-readable document with machine-scannable version pins and complete replay instructions for downstream teams.
**Independent Test**: The `versions` code block is present and contains all 5 required key=value pairs; the replay command section has at least one executable example using the `045-mission-handoff-package-version-matrix` slug; all 6 artifact classes are listed with path patterns.
**Prompt**: `tasks/WP05-version-matrix-note.md`
**Estimated size**: ~220 lines

### Included Subtasks
- [ ] T016 [P] Write version pins section with `versions` fenced code block (5 key=value pairs)
- [ ] T017 [P] Write source reference + wave description + replay commands sections
- [ ] T018 [P] Write expected artifact classes section (all 6 classes: input, workflow, output, evidence, policy, runtime)

### Implementation Notes
- File location: `handoff/version-matrix.md`
- Machine-scan convention: `versions` fenced block with these exact keys: `spec-kitty`, `spec-kitty-events`, `spec-kitty-runtime`, `source-commit`, `source-branch`
- Version values: `spec-kitty=2.0.0`, `spec-kitty-events=2.3.1`, `spec-kitty-runtime=v0.2.0a0`, `source-commit=21ed0738f009ca35a2927528238a48778e41f1d4`, `source-branch=2.x`
- Replay commands: include the `generate.sh --write` invocation AND the `pytest` re-run command from quickstart.md
- All 6 artifact classes per the PRD taxonomy: `input`, `workflow`, `output`, `evidence`, `policy`, `runtime`; for each class include at least one example path pattern from the 045 feature dir
- Section: Parity checks — reference the `generate.sh` diff verification from quickstart.md

### Parallel Opportunities
- T016, T017, T018 are logically sequential sections of one file but can be drafted in any order.

### Dependencies
- Depends on WP01 (needs namespace.json values; output dir must exist).

### Risks & Mitigations
- Version pins stale if pyproject.toml changes → embed a verification note: "Check `pyproject.toml` to confirm these pins before publishing."
- Missing artifact classes → the spec requires all 6; verify against PRD §6 Ubiquitous Language.

---

## Work Package WP06: Test Run + Verification Note (Priority: P3) 🏁 Evidence Gate

**Goal**: Run the 4 setup-plan context test scenarios on 2.x at the source commit, confirm all pass, and commit `handoff/verification.md` as the evidence gate for this handoff.
**Independent Test**: `verification.md` is readable standalone: contains all 4 scenario rows, pass/fail counts, branch name, commit SHA, run date, and re-run command. All 4 scenarios show PASS.
**Prompt**: `tasks/WP06-test-verification-note.md`
**Estimated size**: ~280 lines

### Included Subtasks
- [ ] T019 Run the 4 setup-plan context scenarios via pytest and capture output
- [ ] T020 Confirm all 4 scenarios pass — fail hard (do not write verification.md) if any fail
- [ ] T021 Write `handoff/verification.md` with the scenario table, pass/fail counts, branch, commit SHA, run date
- [ ] T022 Add re-run command to verification.md and perform completeness self-check

### Implementation Notes
- Pytest invocation (run from repo root on branch 2.x):
  ```bash
  pytest tests/integration/test_planning_workflow.py::TestSetupPlanCommand \
         tests/specify_cli/test_cli/test_agent_feature.py \
         -v --tb=short 2>&1 | tee /tmp/verification-run.txt
  ```
- 4 required scenarios (all must be PASS):
  1. `test_setup_plan_ambiguous_context_returns_candidates` → scenario (a) multiple features → ambiguity error
  2. `test_setup_plan_explicit_feature_reports_spec_path` → scenario (b) explicit --feature → success
  3. `test_setup_plan_missing_spec_reports_absolute_path` → scenario (c) missing spec.md → hard error
  4. Test for invalid feature slug (in `test_agent_feature.py`) → scenario (d) validation error
- If any test FAILS: do not write verification.md. Instead, file a bug against 2.x and block WP06 completion.
- verification.md must include: `git rev-parse --abbrev-ref HEAD` (branch), `git rev-parse HEAD` (commit SHA), current UTC date
- Re-run command must be copy-pasteable from a clean 2.x checkout

### Parallel Opportunities
- T019 can run while WP04/WP05 are in progress (test execution is independent of generate.sh).

### Dependencies
- Depends on WP02, WP03, WP04, WP05 — verification is the evidence gate and should be the last thing committed.

### Risks & Mitigations
- Test failure on 2.x → this is a BLOCKING signal; the plan-context-bootstrap-fix wave is not actually validated. Escalate before completing this WP.
- Pytest class/function name changes → verify test names exist before running: `pytest --collect-only -q tests/integration/test_planning_workflow.py | grep setup_plan`.

---

## Dependency & Execution Summary

```
WP01 (scaffold + namespace)
  ├── WP02 (manifest + tree)  ─┐
  ├── WP03 (event stream)     ─┤─→ WP04 (generator script)
  └── WP05 (version matrix)  ─┘
                                       │
                                       └─→ WP06 (test + verification)
```

**Wave 1** (foundation): WP01 → must complete first
**Wave 2** (parallel): WP02, WP03, WP05 → can run simultaneously once WP01 is done
**Wave 3** (synthesis): WP04 → after WP02 + WP03 complete (generator must match actual files)
**Wave 4** (evidence): WP06 → after all previous WPs complete

**Parallelization**: 3 agents can work in parallel in Wave 2 (WP02, WP03, WP05). Total critical path: WP01 → WP02 → WP04 → WP06 (4 hops vs 6 sequential).

**MVP Scope**: WP01 + WP02 + WP03 delivers the deterministic replay baseline (namespace + manifest + tree + events). WP05 and WP06 are required for downstream team consumption and evidence gate.

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Create `handoff/` directory | WP01 | P0 | No |
| T002 | Write `namespace.json` | WP01 | P0 | No |
| T003 | Validate namespace invariants | WP01 | P0 | No |
| T004 | Export expected-artifacts.yaml → manifest JSON | WP02 | P1 | Yes |
| T005 | Walk feature dir, compute SHA-256 | WP02 | P1 | Yes |
| T006 | Cross-reference tree vs manifest, flag absent | WP02 | P1 | No |
| T007 | Write artifact-tree.json | WP02 | P1 | No |
| T008 | Check status.events.jsonl state | WP03 | P1 | Yes |
| T009 | Export events or write bootstrap event | WP03 | P1 | No |
| T010 | Verify events.jsonl integrity | WP03 | P1 | No |
| T011 | Write generate.sh header + arg-parsing | WP04 | P1 | No |
| T012 | Implement namespace.json generation step | WP04 | P1 | No |
| T013 | Implement manifest + tree generation steps | WP04 | P1 | No |
| T014 | Implement events.jsonl copy step | WP04 | P1 | No |
| T015 | Implement version-matrix step + chmod +x | WP04 | P1 | No |
| T016 | Write version pins section (versions block) | WP05 | P1 | Yes |
| T017 | Write source ref + replay commands | WP05 | P1 | Yes |
| T018 | Write expected artifact classes section | WP05 | P1 | Yes |
| T019 | Run 4 setup-plan context tests via pytest | WP06 | P3 | Yes |
| T020 | Confirm all 4 scenarios pass | WP06 | P3 | No |
| T021 | Write verification.md with scenario table | WP06 | P3 | No |
| T022 | Add re-run command + completeness check | WP06 | P3 | No |
