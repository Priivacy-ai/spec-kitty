---
work_package_id: WP05
title: Version Matrix Note
lane: "doing"
dependencies: [WP01]
base_branch: 2.x
base_commit: c68d22f347a00d33225c7ccf1f2a4dd1b7ba068a
created_at: '2026-02-23T20:29:57.904796+00:00'
subtasks:
- T016
- T017
- T018
phase: Phase 2 - Parallel Wave
assignee: ''
agent: "claude-opus"
shell_pid: "27166"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-23T18:04:02Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 – Version Matrix Note

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check `review_status`. If `has_feedback`, read **Review Feedback** below first.

---

## Review Feedback

*[Empty initially.]*

---

## Objectives & Success Criteria

Write and commit `handoff/version-matrix.md` — the human-readable version pin document and replay guide for downstream teams. This is the full, authoritative version (not the script-generated skeleton from WP04).

**Done when**:
- [ ] `handoff/version-matrix.md` is committed
- [ ] A `versions` fenced code block exists with all 5 required key=value pairs
- [ ] The source reference section names the exact commit SHA and its description
- [ ] At least one executable replay command uses the concrete `045-mission-handoff-package-version-matrix` slug
- [ ] All 6 artifact classes (input, workflow, output, evidence, policy, runtime) are listed with at least one canonical path pattern each

**Implementation command** (depends on WP01, parallel with WP02 + WP03):
```bash
spec-kitty implement WP05 --base WP01
```

---

## Context & Constraints

- **Output file**: `kitty-specs/045-mission-handoff-package-version-matrix/handoff/version-matrix.md`
- **Branch**: `2.x`
- **Version pins** (from `pyproject.toml` on 2.x):
  - `spec-kitty=2.0.0`
  - `spec-kitty-events=2.3.1`
  - `spec-kitty-runtime=v0.2.0a0`
  - `source-commit=21ed0738f009ca35a2927528238a48778e41f1d4`
  - `source-branch=2.x`
- **Machine-scan convention**: The `versions` fenced block must use `key=value` format, one per line. CI tooling scans this block.
- **Artifact class taxonomy**: From PRD §6 (Ubiquitous Language): `input`, `workflow`, `output`, `evidence`, `policy`, `runtime`
- **Supporting docs**: `data-model.md` §VersionMatrix, `research.md` Decision 6, `quickstart.md`

---

## Subtasks & Detailed Guidance

### Subtask T016 – Write Version Pins Section

**Purpose**: Provide the machine-scannable version anchor that CI tooling and downstream repos read to determine compatibility.

**Content to write** (file header + version pins section):

```markdown
# Version Matrix: Mission Handoff Package & Version Matrix

**Wave**: plan-context-bootstrap-fix (feature 041-enable-plan-mission-runtime-support)
**Handoff feature**: 045-mission-handoff-package-version-matrix
**Date**: 2026-02-23
**Branch**: `2.x`

---

## Version Pins

The following version pins define the exact component versions used for this wave. CI tooling can extract versions by reading the `versions` code block below.

```versions
spec-kitty=2.0.0
spec-kitty-events=2.3.1
spec-kitty-runtime=v0.2.0a0
source-commit=21ed0738f009ca35a2927528238a48778e41f1d4
source-branch=2.x
```

**Verify current pins against `pyproject.toml`**:
```bash
grep -E "spec-kitty|spec-kitty-events|spec-kitty-runtime" pyproject.toml
```
```

**Files**:
- `handoff/version-matrix.md` (new, partial after this subtask)

**Notes**:
- The fenced block language hint is literally `versions` (not `bash`, not `yaml`).
- Key names use hyphens (not underscores) for readability in CI grep patterns.
- `source-commit` and `source-branch` are included in the block because CI tooling may need to pin to the exact git ref.

---

### Subtask T017 – Write Source Reference + Replay Commands Sections

**Purpose**: Give downstream teams the precise wave context and executable commands to replay or regenerate the handoff.

**Content to append**:

```markdown
---

## Source Reference

| Field | Value |
|-------|-------|
| Branch | `2.x` |
| Source commit | `21ed0738f009ca35a2927528238a48778e41f1d4` |
| Commit description | Merge WP05 from 041-enable-plan-mission-runtime-support |
| Commit date | 2026-02-22T09:47:49+01:00 |
| Wave | plan-context-bootstrap-fix |

**Significance**: This commit is the completion point of the plan-context-bootstrap-fix wave on `2.x`. It introduced:
- `mission-runtime.yaml` schema for the plan mission
- Four command templates for plan workflow
- Explicit `--feature <slug>` binding in `setup-plan`
- Test coverage for context bootstrap scenarios

---

## Replay Commands

### Regenerate the handoff package from source

```bash
# From a clean checkout of spec-kitty at branch 2.x:
git checkout 2.x
bash kitty-specs/045-mission-handoff-package-version-matrix/handoff/generate.sh

# Write to temporary directory for comparison:
bash kitty-specs/045-mission-handoff-package-version-matrix/handoff/generate.sh \
  --write \
  --output-dir /tmp/045-handoff-verify

# Compare against committed package (timestamps differ by design):
diff kitty-specs/045-mission-handoff-package-version-matrix/handoff/namespace.json \
     /tmp/045-handoff-verify/namespace.json
```

### Verify test scenarios (setup-plan context bootstrap)

```bash
# Run from repo root on branch 2.x:
pytest tests/integration/test_planning_workflow.py::TestSetupPlanCommand \
       tests/specify_cli/test_cli/test_agent_feature.py \
       -v --tb=short
```

### Read the event stream

```bash
# Print each event, pretty-printed:
while IFS= read -r line; do
  echo "$line" | python3 -m json.tool --compact
done < kitty-specs/045-mission-handoff-package-version-matrix/handoff/events.jsonl
```

### Inspect artifact completeness

```bash
python3 -c "
import json
tree = json.load(open('kitty-specs/045-mission-handoff-package-version-matrix/handoff/artifact-tree.json'))
print(f'{tree[\"present_count\"]} present, {tree[\"absent_count\"]} absent')
for e in tree['entries']:
    if e['status'] == 'absent':
        print(f'  ABSENT: {e[\"path\"]}')
"
```
```

**Files**: Appended to `handoff/version-matrix.md`

---

### Subtask T018 – Write Expected Artifact Classes Section

**Purpose**: Enumerate all 6 artifact classes with canonical path patterns so downstream teams know what to expect in the handoff directory and in a fully-implemented feature.

**Content to append**:

```markdown
---

## Expected Artifact Classes and Paths

All 6 artifact classes from the Mission Dossier taxonomy are present in this wave. Each class lists at least one canonical path pattern relative to the feature directory (`kitty-specs/045-.../`).

### `input` — User or external source artifacts

| Artifact | Path Pattern | Required? |
|----------|-------------|-----------|
| Feature specification | `spec.md` | Yes (blocking) |

### `workflow` — Process artifacts produced during mission execution

| Artifact | Path Pattern | Required? |
|----------|-------------|-----------|
| Implementation plan | `plan.md` | Yes (blocking, at plan step) |
| Task package | `tasks.md` | Yes (blocking, at plan step) |
| Work package prompts | `tasks/WP*.md` | No (optional) |

### `output` — Deliverables produced for downstream consumption

| Artifact | Path Pattern | Required? |
|----------|-------------|-----------|
| Handoff package | `handoff/*.json` | Yes (this feature's primary output) |
| Generator script | `handoff/generate.sh` | Yes |
| Version matrix | `handoff/version-matrix.md` | Yes |

### `evidence` — Supporting evidence and research

| Artifact | Path Pattern | Required? |
|----------|-------------|-----------|
| Research decisions | `research.md` | No (optional) |
| Data model | `data-model.md` | No (optional) |
| Quickstart guide | `quickstart.md` | No (optional) |
| Test verification | `handoff/verification.md` | Yes (evidence gate) |
| Specification checklist | `checklists/requirements.md` | No (optional) |

### `policy` — Governance and architectural decisions

| Artifact | Path Pattern | Required? |
|----------|-------------|-----------|
| Constitution | `.kittify/memory/constitution.md` | At project level (not per-feature) |

### `runtime` — Generated at runtime (not committed)

| Artifact | Path Pattern | Notes |
|----------|-------------|-------|
| Status event log | `status.events.jsonl` | Accumulated during WP lifecycle |
| Status snapshot | `status.json` | Materialized from event log |

---

## Parity Verification

To confirm the committed package matches the current source state, run the diff verification from `quickstart.md`:

```bash
bash handoff/generate.sh --write --output-dir /tmp/045-verify
diff handoff/namespace.json /tmp/045-verify/namespace.json
# Only generated_at and captured_at timestamps should differ
```

Any non-timestamp diff indicates the committed package is stale.
```

**Files**: Final append to `handoff/version-matrix.md` (file complete after this subtask)

---

## Risks & Mitigations

- **`versions` block language hint wrong**: Verify by running `grep -A 8 '^\`\`\`versions' version-matrix.md` — if no match, the CI scan will fail. The hint is exactly `versions` (lowercase, no spaces).
- **Artifact classes incomplete**: The PRD §6 defines exactly 6 classes: input, workflow, output, evidence, policy, runtime. Verify all 6 have a section in the document.
- **Replay commands untested**: Run the `generate.sh --write` command and the `pytest` command before committing — verify they produce the expected outputs.

---

## Review Guidance

Reviewers verify:
1. `versions` fenced block present with all 5 key=value pairs
2. All version values match `pyproject.toml` on 2.x: `grep -E "spec-kitty" pyproject.toml`
3. Source commit SHA matches `namespace.json::source_commit`
4. All 6 artifact classes present (input / workflow / output / evidence / policy / runtime)
5. At least one replay command uses the slug `045-mission-handoff-package-version-matrix`
6. Document is readable and self-contained (no broken references or placeholder text)

---

## Activity Log

- 2026-02-23T18:04:02Z – system – lane=planned – Prompt created.
- 2026-02-23T20:29:58Z – claude-opus – shell_pid=23713 – lane=doing – Assigned agent via workflow command
- 2026-02-23T20:32:07Z – claude-opus – shell_pid=23713 – lane=for_review – Ready for review: version-matrix.md (160 lines) with all 5 version pins in versions block, source reference with exact commit SHA, 4 executable replay commands using concrete slug, all 6 artifact classes (input/workflow/output/evidence/policy/runtime). All 3 subtasks (T016-T018) complete.
- 2026-02-23T20:32:45Z – claude-opus – shell_pid=27166 – lane=doing – Started review via workflow command
