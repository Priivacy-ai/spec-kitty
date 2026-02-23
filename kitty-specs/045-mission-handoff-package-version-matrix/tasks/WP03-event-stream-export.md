---
work_package_id: WP03
title: Event Stream Export
lane: "doing"
dependencies: [WP01]
base_branch: 2.x
base_commit: d9cacce44e9b10233e49d0f9fdd19a2f0f4a78da
created_at: '2026-02-23T20:07:13.558439+00:00'
subtasks:
- T008
- T009
- T010
phase: Phase 2 - Parallel Wave
assignee: ''
agent: "claude-opus"
shell_pid: "96811"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-23T18:04:02Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Event Stream Export

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check `review_status`. If `has_feedback`, read **Review Feedback** below first.

---

## Review Feedback

*[Empty initially.]*

---

## Objectives & Success Criteria

Export or synthesize the canonical event stream to `handoff/events.jsonl`. This gives downstream teams a deterministic, ordered record of the WP lifecycle for the 045 feature.

**Done when**:
- [ ] `handoff/events.jsonl` exists
- [ ] File is UTF-8 encoded
- [ ] Each line is a valid, independently parseable JSON object
- [ ] If source `status.events.jsonl` had content: `events.jsonl` line count matches
- [ ] If source was empty/absent: a single synthetic bootstrap event is present

**Implementation command** (depends on WP01, parallel with WP02):
```bash
spec-kitty implement WP03 --base WP01
```

---

## Context & Constraints

- **Feature dir**: `kitty-specs/045-mission-handoff-package-version-matrix/`
- **Source event log**: `kitty-specs/045-mission-handoff-package-version-matrix/status.events.jsonl` (may be empty or absent)
- **Output**: `kitty-specs/045-mission-handoff-package-version-matrix/handoff/events.jsonl`
- **Branch**: `2.x`
- **C-lite constraint**: stdlib only (json, shutil, uuid). No new modules.
- **Supporting docs**: `data-model.md` §EventStream, `research.md` Decision 2

---

## Subtasks & Detailed Guidance

### Subtask T008 – Check `status.events.jsonl` State

**Purpose**: Determine whether the feature has accumulated real status events during planning. This controls whether T009 copies verbatim or synthesizes a bootstrap event.

**Steps**:
1. Check if the file exists and has content:
   ```bash
   STATUS_EVENTS="kitty-specs/045-mission-handoff-package-version-matrix/status.events.jsonl"

   if [ -f "$STATUS_EVENTS" ] && [ -s "$STATUS_EVENTS" ]; then
     LINE_COUNT=$(wc -l < "$STATUS_EVENTS" | tr -d ' ')
     echo "EXISTS with ${LINE_COUNT} events — will copy verbatim"
   else
     echo "EMPTY or ABSENT — will synthesize bootstrap event"
   fi
   ```
2. Record your finding: either "copy" or "bootstrap" — this determines the T009 path.

**Files**: Read-only check, no output files.

**Notes**:
- The 045 feature was just specified and planned. It is expected that `status.events.jsonl` is either absent or contains only planning-phase status events. Either path is correct.
- Do NOT try to generate events by running spec-kitty commands — just observe the current state.

---

### Subtask T009 – Export Events or Write Synthetic Bootstrap Event

**Purpose**: Produce `handoff/events.jsonl` via the appropriate path determined in T008.

**Path A — Copy verbatim (if status.events.jsonl has content)**:
```python
python3 - <<'EOF'
import shutil
from pathlib import Path

src = Path("kitty-specs/045-mission-handoff-package-version-matrix/status.events.jsonl")
dst = Path("kitty-specs/045-mission-handoff-package-version-matrix/handoff/events.jsonl")

shutil.copy2(src, dst)
lines = dst.read_text(encoding="utf-8").splitlines()
print(f"Copied {len(lines)} events to {dst}")
EOF
```

**Path B — Synthesize bootstrap event (if status.events.jsonl is empty or absent)**:
```python
python3 - <<'EOF'
import json, uuid
from datetime import datetime, timezone
from pathlib import Path

out_path = Path("kitty-specs/045-mission-handoff-package-version-matrix/handoff/events.jsonl")

bootstrap_event = {
    "actor": "spec-kitty/045-generator",
    "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "event_id": str(uuid.uuid4()),
    "event_type": "handoff_package_created",
    "feature_slug": "045-mission-handoff-package-version-matrix",
    "source_branch": "2.x",
    "source_commit": "21ed0738f009ca35a2927528238a48778e41f1d4",
}

# Sort keys for determinism
line = json.dumps(bootstrap_event, sort_keys=True)
out_path.write_text(line + "\n", encoding="utf-8")
print(f"Written bootstrap event to {out_path}")
EOF
```

**Files**:
- `handoff/events.jsonl` (new)

**Notes**:
- Path B produces exactly 1 line. This is valid — the handoff spec says "one synthetic bootstrap event" when the log is empty.
- Do NOT re-sort or reorder events from Path A. Insertion order is the invariant.
- JSONL format: each event is one complete JSON object on its own line, terminated by `\n`. The file ends with a newline.

---

### Subtask T010 – Verify `events.jsonl` Integrity

**Purpose**: Confirm the output file satisfies all format requirements before committing.

**Steps**:
1. Run integrity check:
   ```python
   python3 - <<'EOF'
   import json, sys
   from pathlib import Path

   f = Path("kitty-specs/045-mission-handoff-package-version-matrix/handoff/events.jsonl")
   errors = []

   if not f.exists():
       print("FAIL: events.jsonl does not exist")
       sys.exit(1)

   lines = f.read_text(encoding="utf-8").splitlines()
   if not lines:
       errors.append("File is empty — expected at least 1 event")

   for i, line in enumerate(lines, 1):
       try:
           obj = json.loads(line)
           if not isinstance(obj, dict):
               errors.append(f"Line {i}: not a JSON object")
       except json.JSONDecodeError as e:
           errors.append(f"Line {i}: invalid JSON — {e}")

   if errors:
       print("INTEGRITY FAILED:")
       for e in errors: print(f"  - {e}")
       sys.exit(1)
   else:
       print(f"events.jsonl: PASS — {len(lines)} event(s), all valid JSON objects")
   EOF
   ```
2. Fix any failures before proceeding.

**Files**: Read-only check.

**Notes**:
- Sorted keys are not strictly required for the integrity check (events from Path A may not have sorted keys). The integrity check only validates parseable JSON objects.
- If you want to enforce sorted keys on the bootstrap event, the Path B script already does `sort_keys=True`.

---

## Risks & Mitigations

- **Encoding issue in source events**: If the spec-kitty codec was active during event writing, source events are UTF-8. The integrity check catches any non-UTF-8 content.
- **Bootstrap event UUID format**: `uuid.uuid4()` produces a random UUID (not a ULID). This is acceptable for a synthetic event; real status events use ULIDs but the bootstrap event is not a `StatusEvent` instance.
- **File ends without newline**: `write_text(line + "\n", ...)` ensures the final newline. JSONL convention requires each line to end with `\n`.

---

## Review Guidance

Reviewers verify:
1. `handoff/events.jsonl` exists and is non-empty
2. Each line independently parses as a JSON object (`python3 -c "[json.loads(l) for l in open('events.jsonl')]"`)
3. If bootstrap path was used: exactly 1 line; `event_type=handoff_package_created`; `source_commit` matches namespace.json
4. If verbatim copy path was used: line count matches source `status.events.jsonl`
5. File is UTF-8 (no BOM, no encoding errors)

---

## Activity Log

- 2026-02-23T18:04:02Z – system – lane=planned – Prompt created.
- 2026-02-23T20:07:13Z – claude-opus – shell_pid=94220 – lane=doing – Assigned agent via workflow command
- 2026-02-23T20:09:11Z – claude-opus – shell_pid=94220 – lane=for_review – Ready for review: handoff/events.jsonl contains verbatim copy of 10 status events from status.events.jsonl. UTF-8, no BOM, each line valid JSON, line count matches source. All 3 subtasks (T008-T010) complete.
- 2026-02-23T20:10:41Z – claude-opus – shell_pid=96811 – lane=doing – Started review via workflow command
