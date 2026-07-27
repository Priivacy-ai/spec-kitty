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
