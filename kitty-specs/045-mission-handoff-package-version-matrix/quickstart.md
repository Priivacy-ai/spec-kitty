# Quickstart: Mission Handoff Package & Version Matrix

**Feature**: 045-mission-handoff-package-version-matrix
**Branch**: 2.x

---

## What Is This?

This is the canonical handoff package for the **plan-context-bootstrap-fix wave** on spec-kitty `2.x`. It lets downstream teams (spec-kitty-saas, dashboard parity) replay the mission deterministically.

**Source commit anchor**: `21ed0738f009ca35a2927528238a48778e41f1d4`
(Merge WP05 from 041-enable-plan-mission-runtime-support, 2026-02-22)

---

## Where Are the Files?

After implementation is merged to `2.x`:

```
kitty-specs/045-mission-handoff-package-version-matrix/handoff/
├── namespace.json          ← start here: namespace tuple + source commit
├── artifact-manifest.json  ← expected artifacts for software-dev mission
├── artifact-tree.json      ← actual artifacts present + SHA-256 fingerprints
├── events.jsonl            ← status event stream (or bootstrap event)
├── version-matrix.md       ← version pins + replay commands
├── verification.md         ← test evidence (4 scenarios green)
└── generate.sh             ← regenerate the package from source
```

---

## Reading the Handoff Package

### 1. Identify the wave

```bash
cat kitty-specs/045-mission-handoff-package-version-matrix/handoff/namespace.json
```

Key fields: `source_commit`, `source_branch`, `mission_key`, `manifest_version`.

### 2. Check version pins

```bash
grep -A 10 '```versions' kitty-specs/045-mission-handoff-package-version-matrix/handoff/version-matrix.md
```

### 3. Replay the event sequence

```bash
# Read the event stream line-by-line
while IFS= read -r line; do
  echo "$line" | python3 -m json.tool --compact
done < kitty-specs/045-mission-handoff-package-version-matrix/handoff/events.jsonl
```

### 4. Check artifact completeness

```bash
python3 -c "
import json
tree = json.load(open('kitty-specs/045-mission-handoff-package-version-matrix/handoff/artifact-tree.json'))
absent = [e for e in tree['entries'] if e['status'] == 'absent']
print(f'{tree[\"present_count\"]} present, {tree[\"absent_count\"]} absent')
for e in absent:
    print(f'  ABSENT: {e[\"path\"]}')
"
```

---

## Regenerating the Package

If you want to verify or refresh the handoff package from source:

```bash
# Dry-run (default — prints what would be written, no files created)
bash kitty-specs/045-mission-handoff-package-version-matrix/handoff/generate.sh

# Write to a temporary directory for comparison
bash kitty-specs/045-mission-handoff-package-version-matrix/handoff/generate.sh \
  --write --output-dir /tmp/045-handoff-verify

# Compare against committed package (ignore timestamp fields)
diff kitty-specs/045-mission-handoff-package-version-matrix/handoff/namespace.json \
     /tmp/045-handoff-verify/namespace.json
```

---

## Re-running the Verification Tests

```bash
cd /path/to/spec-kitty  # must be on 2.x branch

pytest tests/integration/test_planning_workflow.py::TestSetupPlanCommand \
       tests/specify_cli/test_cli/test_agent_feature.py \
       -v --tb=short
```

Expected: all 4 setup-plan context scenarios pass.

---

## Version Compatibility

| Component | Version / Ref |
|-----------|--------------|
| spec-kitty | `2.0.0` |
| spec-kitty-events | `2.3.1` |
| spec-kitty-runtime | `v0.2.0a0` |
| Source branch | `2.x` |
| Source commit | `21ed0738f009ca35a2927528238a48778e41f1d4` |

---

## For Downstream Teams

The handoff package is designed to be consumed without access to the original developer environment. All you need:

1. A checkout of `spec-kitty` at `2.x` (any commit after the implementation merge)
2. Python 3.11+ installed
3. The `handoff/` directory — everything you need is there

No spec-kitty commands need to be run to read the package.
