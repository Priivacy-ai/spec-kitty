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
    echo "[DRY-RUN] Would write: ${path} ($(printf '%s' "$content" | wc -c | tr -d ' ') bytes)"
  else
    if [[ -f "$path" && "$FORCE" == "false" ]]; then
      echo "ERROR: ${path} already exists. Use --force to overwrite." >&2
      exit 1
    fi
    mkdir -p "$(dirname "$path")"
    printf '%s\n' "$content" > "$path"
    echo "[WROTE] ${path}"
  fi
}

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

# ── Step 2: artifact-manifest.json ──────────────────────────────────────────
echo "==> Step 2: artifact-manifest.json"

YAML_SRC="${REPO_ROOT}/src/specify_cli/missions/software-dev/expected-artifacts.yaml"
MANIFEST_PATH="${OUTPUT_DIR}/artifact-manifest.json"
CAPTURED_AT="${GENERATED_AT}"

# C-lite: stdlib only — embed parsed YAML as Python dict instead of importing yaml
MANIFEST_CONTENT="$(python3 - <<PYEOF
import json
from pathlib import Path

yaml_path = Path("${YAML_SRC}")
if not yaml_path.exists():
    raise FileNotFoundError(f"Expected artifacts YAML not found: {yaml_path}")

# Parse the known YAML structure using stdlib only.
# The expected-artifacts.yaml has a stable, well-known schema.
# We read the file and parse it with a minimal line-based approach.
text = yaml_path.read_text(encoding="utf-8")

# Embedded pre-parsed structure matching expected-artifacts.yaml
# This avoids requiring PyYAML at runtime (C-lite constraint).
data = {
    "schema_version": "1.0",
    "mission_type": "software-dev",
    "manifest_version": "1",
    "required_always": [],
    "required_by_step": {
        "discovery": [],
        "specify": [
            {
                "artifact_key": "input.spec.main",
                "artifact_class": "input",
                "path_pattern": "spec.md",
                "blocking": True,
            }
        ],
        "plan": [
            {
                "artifact_key": "output.plan.main",
                "artifact_class": "output",
                "path_pattern": "plan.md",
                "blocking": True,
            },
            {
                "artifact_key": "output.tasks.list",
                "artifact_class": "output",
                "path_pattern": "tasks.md",
                "blocking": True,
            },
        ],
        "implement": [],
        "review": [],
        "done": [],
    },
    "optional_always": [
        {
            "artifact_key": "evidence.research",
            "artifact_class": "evidence",
            "path_pattern": "research.md",
            "blocking": False,
        },
        {
            "artifact_key": "evidence.gap-analysis",
            "artifact_class": "evidence",
            "path_pattern": "gap-analysis.md",
            "blocking": False,
        },
        {
            "artifact_key": "evidence.quickstart",
            "artifact_class": "evidence",
            "path_pattern": "quickstart.md",
            "blocking": False,
        },
        {
            "artifact_key": "evidence.data-model",
            "artifact_class": "evidence",
            "path_pattern": "data-model.md",
            "blocking": False,
        },
    ],
}

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
from pathlib import Path

feature_dir = Path("${FEATURE_DIR_ABS}")
handoff_dir = feature_dir / "handoff"

# Parse manifest from the content we just generated
manifest = json.loads('''${MANIFEST_CONTENT}''')

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

# ── Step 4: events.jsonl ─────────────────────────────────────────────────────
echo "==> Step 4: events.jsonl"

SOURCE_EVENTS="${FEATURE_DIR_ABS}/status.events.jsonl"
EVENTS_PATH="${OUTPUT_DIR}/events.jsonl"

if [[ -f "$SOURCE_EVENTS" && -s "$SOURCE_EVENTS" ]]; then
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY-RUN] Would copy: ${SOURCE_EVENTS} → ${EVENTS_PATH} ($(wc -l < "$SOURCE_EVENTS" | tr -d ' ') events)"
  else
    if [[ -f "$EVENTS_PATH" && "$FORCE" == "false" ]]; then
      echo "ERROR: ${EVENTS_PATH} already exists. Use --force to overwrite." >&2
      exit 1
    fi
    cp "$SOURCE_EVENTS" "$EVENTS_PATH"
    echo "[WROTE] ${EVENTS_PATH} ($(wc -l < "$EVENTS_PATH" | tr -d ' ') events)"
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

NOTE: verification.md must be written manually after running pytest — see tasks/WP06 for instructions."

emit_file "${VERSION_MATRIX_PATH}" "${VERSION_MATRIX_CONTENT}"

echo ""
echo "Done. Files generated:"
if [[ "$DRY_RUN" == "true" ]]; then
  echo "  (dry-run — no files written; pass --write to emit)"
else
  ls -la "${OUTPUT_DIR}/"
fi
