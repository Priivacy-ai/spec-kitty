---
work_package_id: WP04
title: Generator Script
lane: planned
dependencies:
- WP01
- WP02
- WP03
subtasks:
- T011
- T012
- T013
- T014
- T015
phase: Phase 3 - Synthesis
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-23T18:04:02Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Generator Script

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check `review_status`. If `has_feedback`, read **Review Feedback** below first.

---

## Review Feedback

*[Empty initially.]*

---

## Objectives & Success Criteria

Write and commit `handoff/generate.sh` — a minimal, self-contained Bash script that regenerates all handoff package files from source. Dry-run by default; `--write` activates file emission; `--force` allows overwriting.

**Done when**:
- [ ] `generate.sh` is executable (`chmod +x`)
- [ ] `generate.sh --help` prints usage without error
- [ ] `generate.sh` (dry-run) prints what would be written without creating files
- [ ] `generate.sh --write --output-dir /tmp/test-045` creates at minimum: `namespace.json`, `artifact-manifest.json`, `artifact-tree.json`, `events.jsonl`, and a `version-matrix.md` skeleton
- [ ] `SOURCE_COMMIT` variable in script equals `21ed0738f009ca35a2927528238a48778e41f1d4`
- [ ] Script exits 0 in dry-run mode from a clean 2.x checkout

**Implementation command** (depends on WP02 + WP03):
```bash
spec-kitty implement WP04 --base WP02
# Then: git merge 045-mission-handoff-package-version-matrix-WP03
```

---

## Context & Constraints

- **Feature dir**: `kitty-specs/045-mission-handoff-package-version-matrix/`
- **Output file**: `handoff/generate.sh`
- **Branch**: `2.x`
- **C-lite constraint**: Bash + Python 3.11+ stdlib inline invocations. No new Python modules. No new CLI subcommands.
- **Safety invariant**: Default mode MUST be dry-run. Files MUST NOT be created without `--write`.
- **No-overwrite invariant**: Existing files MUST abort unless `--force` is passed.
- **Supporting docs**: `data-model.md` §GeneratorCommand, `research.md` Decision 5, `quickstart.md`

---

## Subtasks & Detailed Guidance

### Subtask T011 – Write `generate.sh` Header: Shebang, Variables, Arg-Parsing, Dry-Run Default

**Purpose**: Establish the script's skeleton — safe Bash defaults, embedded constants, usage function, and flag-parsing.

**Steps**:
Write the following header content to `handoff/generate.sh`:

```bash
#!/usr/bin/env bash
# generate.sh — Regenerate the 045 handoff package from source
#
# Usage:
#   generate.sh [OPTIONS]
#
# Options:
#   --write            Emit files to OUTPUT_DIR (default: dry-run only)
#   --output-dir PATH  Output directory (default: directory containing this script)
#   --force            Overwrite existing files without aborting
#   --help             Show this usage text
#
# Default mode is dry-run: prints what would be written, creates nothing.
# NOTE: verification.md requires running pytest manually — see WP06 prompt.

set -euo pipefail

# ── Embedded constants (do not edit) ────────────────────────────────────────
SOURCE_COMMIT="21ed0738f009ca35a2927528238a48778e41f1d4"
SOURCE_BRANCH="2.x"
FEATURE_SLUG="045-mission-handoff-package-version-matrix"
MISSION_KEY="software-dev"
MANIFEST_VERSION="1"

# ── Defaults ────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}"
DRY_RUN=true
FORCE=false

# ── Usage ────────────────────────────────────────────────────────────────────
usage() {
  sed -n '2,15p' "${BASH_SOURCE[0]}" | sed 's/^# //' | sed 's/^#//'
  exit 0
}

# ── Arg parsing ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --write)       DRY_RUN=false ;;
    --output-dir)  OUTPUT_DIR="$2"; shift ;;
    --force)       FORCE=true ;;
    --help|-h)     usage ;;
    *)             echo "Unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done

# ── Helper: emit or dry-run ──────────────────────────────────────────────────
emit_file() {
  local path="$1"
  local content="$2"
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY-RUN] Would write: ${path} ($(echo "$content" | wc -c) bytes)"
  else
    if [[ -f "$path" && "$FORCE" == "false" ]]; then
      echo "ERROR: ${path} already exists. Use --force to overwrite." >&2
      exit 1
    fi
    mkdir -p "$(dirname "$path")"
    echo "$content" > "$path"
    echo "[WROTE] ${path}"
  fi
}
```

**Files**:
- `handoff/generate.sh` (new, partial — header only at this stage)

**Notes**:
- `set -euo pipefail` ensures the script fails fast on any error, unset variable, or pipeline failure.
- `SCRIPT_DIR` resolution ensures the script works when called from any directory.
- `DRY_RUN=true` default is the safety constraint from the spec.

---

### Subtask T012 – Implement `namespace.json` Generation Step

**Purpose**: Add the step that generates `namespace.json` from embedded variables and live git metadata.

**Steps**:
Append to `generate.sh`:

```bash
# ── Step 1: namespace.json ───────────────────────────────────────────────────
echo "==> Step 1: namespace.json"

REPO_ROOT="$(git rev-parse --show-toplevel)"
PROJECT_SCOPE_ID="$(basename "$REPO_ROOT")"
GENERATED_AT="$(python3 -c "from datetime import datetime,timezone; print(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))")"
NAMESPACE_PATH="${OUTPUT_DIR}/namespace.json"

NAMESPACE_CONTENT="$(python3 - <<PYEOF
import json
print(json.dumps({
    "schema_version": "1",
    "project_scope_id": "${PROJECT_SCOPE_ID}",
    "feature_slug": "${FEATURE_SLUG}",
    "source_branch": "${SOURCE_BRANCH}",
    "source_commit": "${SOURCE_COMMIT}",
    "mission_key": "${MISSION_KEY}",
    "manifest_version": "${MANIFEST_VERSION}",
    "step_id": None,
    "generated_at": "${GENERATED_AT}",
}, indent=2))
PYEOF
)"

emit_file "${NAMESPACE_PATH}" "${NAMESPACE_CONTENT}"
```

**Files**: Appended to `handoff/generate.sh`

**Notes**:
- Shell variable expansion inside the Python heredoc provides the embedded constants.
- `None` in Python produces `null` in JSON — correct for `step_id`.

---

### Subtask T013 – Implement Manifest + Tree Generation Steps

**Purpose**: Add steps 2 and 3 — the YAML→JSON manifest export and the SHA-256 directory walk.

**Steps**:
Append to `generate.sh`:

```bash
# ── Step 2: artifact-manifest.json ──────────────────────────────────────────
echo "==> Step 2: artifact-manifest.json"

YAML_SRC="${REPO_ROOT}/src/specify_cli/missions/software-dev/expected-artifacts.yaml"
MANIFEST_PATH="${OUTPUT_DIR}/artifact-manifest.json"
CAPTURED_AT="${GENERATED_AT}"

MANIFEST_CONTENT="$(python3 - <<PYEOF
import json, yaml
from pathlib import Path

data = yaml.safe_load(Path("${YAML_SRC}").read_text(encoding="utf-8"))
data["source_commit"] = "${SOURCE_COMMIT}"
data["captured_at"] = "${CAPTURED_AT}"
print(json.dumps(data, indent=2))
PYEOF
)"

emit_file "${MANIFEST_PATH}" "${MANIFEST_CONTENT}"

# ── Step 3: artifact-tree.json ───────────────────────────────────────────────
echo "==> Step 3: artifact-tree.json"

FEATURE_DIR_ABS="${REPO_ROOT}/kitty-specs/${FEATURE_SLUG}"
TREE_PATH="${OUTPUT_DIR}/artifact-tree.json"

TREE_CONTENT="$(python3 - <<PYEOF
import hashlib, json, fnmatch
from datetime import datetime, timezone
from pathlib import Path

feature_dir = Path("${FEATURE_DIR_ABS}")
handoff_dir = feature_dir / "handoff"
manifest = json.loads("""${MANIFEST_CONTENT}""")

present = []
for p in sorted(feature_dir.rglob("*")):
    if not p.is_file(): continue
    if handoff_dir in p.parents or p.parent == handoff_dir: continue
    if "__pycache__" in p.parts or p.suffix == ".pyc": continue
    rel = str(p.relative_to(feature_dir))
    sha256 = hashlib.sha256(p.read_bytes()).hexdigest()
    present.append({"path": rel, "sha256": sha256, "size_bytes": p.stat().st_size, "status": "present"})

present_paths = {e["path"] for e in present}
all_specs = list(manifest.get("required_always", []))
for specs in manifest.get("required_by_step", {}).values():
    all_specs.extend(specs)
all_specs.extend(manifest.get("optional_always", []))

absent = []
for spec in all_specs:
    pattern = spec["path_pattern"]
    if not any(fnmatch.fnmatch(p, pattern) for p in present_paths):
        absent.append({"path": pattern, "sha256": None, "size_bytes": None, "status": "absent"})

all_entries = present + absent
print(json.dumps({
    "schema_version": "1",
    "feature_slug": "${FEATURE_SLUG}",
    "root_path": "kitty-specs/${FEATURE_SLUG}",
    "source_commit": "${SOURCE_COMMIT}",
    "captured_at": "${CAPTURED_AT}",
    "entries": all_entries,
    "total_files": len(all_entries),
    "present_count": len(present),
    "absent_count": len(absent),
}, indent=2))
PYEOF
)"

emit_file "${TREE_PATH}" "${TREE_CONTENT}"
```

**Files**: Appended to `handoff/generate.sh`

**Notes**:
- The tree step embeds `$MANIFEST_CONTENT` to avoid re-reading the file (works for both dry-run and write modes).
- The Python heredoc inside a shell variable is a known pattern; `PYEOF` is the terminator and must not appear in the Python code.

---

### Subtask T014 – Implement `events.jsonl` Copy Step

**Purpose**: Add step 4 — copy or synthesize the event stream.

**Steps**:
Append to `generate.sh`:

```bash
# ── Step 4: events.jsonl ─────────────────────────────────────────────────────
echo "==> Step 4: events.jsonl"

SOURCE_EVENTS="${FEATURE_DIR_ABS}/status.events.jsonl"
EVENTS_PATH="${OUTPUT_DIR}/events.jsonl"

if [[ -f "$SOURCE_EVENTS" && -s "$SOURCE_EVENTS" ]]; then
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY-RUN] Would copy: ${SOURCE_EVENTS} → ${EVENTS_PATH} ($(wc -l < "$SOURCE_EVENTS") events)"
  else
    if [[ -f "$EVENTS_PATH" && "$FORCE" == "false" ]]; then
      echo "ERROR: ${EVENTS_PATH} already exists. Use --force to overwrite." >&2
      exit 1
    fi
    cp "$SOURCE_EVENTS" "$EVENTS_PATH"
    echo "[WROTE] ${EVENTS_PATH} ($(wc -l < "$EVENTS_PATH") events)"
  fi
else
  # Synthesize bootstrap event
  BOOTSTRAP_EVENT="$(python3 - <<PYEOF
import json, uuid
from datetime import datetime, timezone
print(json.dumps({
    "actor": "spec-kitty/045-generator",
    "at": "${GENERATED_AT}",
    "event_id": str(uuid.uuid4()),
    "event_type": "handoff_package_created",
    "feature_slug": "${FEATURE_SLUG}",
    "source_branch": "${SOURCE_BRANCH}",
    "source_commit": "${SOURCE_COMMIT}",
}, sort_keys=True))
PYEOF
)"
  emit_file "${EVENTS_PATH}" "${BOOTSTRAP_EVENT}"
fi
```

**Files**: Appended to `handoff/generate.sh`

---

### Subtask T015 – Version-Matrix Skeleton Step + `chmod +x` + Dry-Run Validation

**Purpose**: Add the final step (version-matrix.md skeleton), make the script executable, and validate dry-run mode works end-to-end.

**Steps**:
1. Append version-matrix step to `generate.sh`:

```bash
# ── Step 5: version-matrix.md ────────────────────────────────────────────────
echo "==> Step 5: version-matrix.md (skeleton)"

VERSION_MATRIX_PATH="${OUTPUT_DIR}/version-matrix.md"
VERSION_MATRIX_CONTENT="# Version Matrix: Mission Handoff Package & Version Matrix

## Version Pins

\`\`\`versions
spec-kitty=2.0.0
spec-kitty-events=2.3.1
spec-kitty-runtime=v0.2.0a0
source-commit=${SOURCE_COMMIT}
source-branch=${SOURCE_BRANCH}
\`\`\`

*Generated by generate.sh. Edit Replay Commands and Artifact Classes sections after generation.*

NOTE: verification.md must be written manually after running pytest — see tasks/WP06 for instructions.
"

emit_file "${VERSION_MATRIX_PATH}" "${VERSION_MATRIX_CONTENT}"

echo ""
echo "Done. Files generated:"
if [[ "$DRY_RUN" == "true" ]]; then
  echo "  (dry-run — no files written; pass --write to emit)"
else
  ls -la "${OUTPUT_DIR}/"
fi
```

2. Make the script executable:
   ```bash
   chmod +x kitty-specs/045-mission-handoff-package-version-matrix/handoff/generate.sh
   ```

3. Validate dry-run works:
   ```bash
   # From repo root
   bash kitty-specs/045-mission-handoff-package-version-matrix/handoff/generate.sh
   # Expected: prints [DRY-RUN] messages for each of the 5 files; exits 0; no files created
   ```

4. Validate write to temp dir:
   ```bash
   bash kitty-specs/045-mission-handoff-package-version-matrix/handoff/generate.sh --write --output-dir /tmp/test-045-handoff
   ls /tmp/test-045-handoff/
   # Expected: namespace.json, artifact-manifest.json, artifact-tree.json, events.jsonl, version-matrix.md
   ```

**Files**:
- `handoff/generate.sh` (complete — executable)

**Notes**:
- The version-matrix.md generated by the script is a skeleton — WP05 produces the full, human-authored version. The generator script only ensures version pins are correct for reproducibility.
- If the script fails with `yaml` import error, fall back to embedding the parsed YAML directly as a Python dict (the expected-artifacts.yaml content is stable and known).

---

## Risks & Mitigations

- **Shell variable expansion breaks Python heredoc**: Test with a simple `echo "$MANIFEST_CONTENT"` before using it inside Python to confirm the content is properly escaped.
- **`generate.sh` generates files different from committed ones**: This is expected if files are generated BEFORE all WPs are done. The final committed package is the authoritative reference; the script is for regeneration from a clean checkout.
- **`chmod +x` not preserved by git**: Git tracks the executable bit. After `chmod +x`, verify with `git ls-files --stage handoff/generate.sh` — should show `100755` (not `100644`). If not: `git update-index --chmod=+x handoff/generate.sh`.

---

## Review Guidance

Reviewers verify:
1. `git ls-files --stage handoff/generate.sh` shows mode `100755`
2. `generate.sh --help` exits 0 and prints usage
3. `generate.sh` (no flags) prints `[DRY-RUN]` lines for all 5 files, creates nothing
4. `SOURCE_COMMIT` in script == `21ed0738f009ca35a2927528238a48778e41f1d4` (grep to verify)
5. `generate.sh --write --output-dir /tmp/test` produces 5 files with valid content
6. `namespace.json` produced by generator matches the one committed in WP01 (except `generated_at`)

---

## Activity Log

- 2026-02-23T18:04:02Z – system – lane=planned – Prompt created.
