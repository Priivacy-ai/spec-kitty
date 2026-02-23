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

MANIFEST_PATH="${OUTPUT_DIR}/artifact-manifest.json"
CAPTURED_AT="${GENERATED_AT}"

# Verify the source YAML exists at SOURCE_COMMIT (sanity check only).
# We do NOT read its content at runtime — the C-lite constraint requires a
# hardcoded Python dict (no PyYAML dependency).  The dict below was parsed
# once from expected-artifacts.yaml and embedded here.
YAML_REL="src/specify_cli/missions/software-dev/expected-artifacts.yaml"
if ! git show "${SOURCE_COMMIT}:${YAML_REL}" >/dev/null 2>&1; then
  echo "WARNING: ${YAML_REL} not found at SOURCE_COMMIT ${SOURCE_COMMIT}." >&2
  echo "         The embedded manifest may be stale." >&2
fi

MANIFEST_CONTENT="$(python3 - <<PYEOF
import json

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

TREE_PATH="${OUTPUT_DIR}/artifact-tree.json"

# Read committed state via git, not the working tree.
# The 045 feature dir was created after SOURCE_COMMIT, so we use HEAD.
TREE_COMMIT="$(git rev-parse HEAD)"
FEATURE_TREE_PREFIX="kitty-specs/${FEATURE_SLUG}"
HANDOFF_PREFIX="kitty-specs/${FEATURE_SLUG}/handoff/"

# git ls-tree gives us committed files; git show gives us committed content.
GIT_LS_TREE="$(git ls-tree -r --long "${TREE_COMMIT}" -- "${FEATURE_TREE_PREFIX}/")"

TREE_CONTENT="$(python3 - <<PYEOF
import hashlib, json, fnmatch, subprocess

feature_prefix = "${FEATURE_TREE_PREFIX}/"
handoff_prefix = "${HANDOFF_PREFIX}"
tree_commit = "${TREE_COMMIT}"

# Parse git ls-tree output: "<mode> <type> <hash> <size>\t<path>"
ls_lines = """${GIT_LS_TREE}""".strip().splitlines()

manifest = json.loads('''${MANIFEST_CONTENT}''')

present = []
for line in ls_lines:
    if not line.strip():
        continue
    meta, path = line.split("\t", 1)
    # Skip handoff/ directory files and __pycache__/.pyc
    if path.startswith(handoff_prefix):
        continue
    if "__pycache__" in path or path.endswith(".pyc"):
        continue
    parts = meta.split()
    size_bytes = int(parts[3]) if parts[3] != "-" else 0

    rel = path[len(feature_prefix):]

    # Hash committed content via git show
    blob = subprocess.run(
        ["git", "show", f"{tree_commit}:{path}"],
        capture_output=True, check=True,
    ).stdout
    sha256 = hashlib.sha256(blob).hexdigest()

    present.append({
        "path": rel,
        "sha256": sha256,
        "size_bytes": size_bytes,
        "status": "present",
    })

present.sort(key=lambda e: e["path"])
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
    "tree_commit": tree_commit,
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

# Read committed events via git show (not the working tree).
SOURCE_EVENTS_REL="kitty-specs/${FEATURE_SLUG}/status.events.jsonl"
EVENTS_PATH="${OUTPUT_DIR}/events.jsonl"

if git show "HEAD:${SOURCE_EVENTS_REL}" >/dev/null 2>&1; then
  EVENT_COUNT="$(git show "HEAD:${SOURCE_EVENTS_REL}" | wc -l | tr -d ' ')"
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY-RUN] Would extract: ${SOURCE_EVENTS_REL} from HEAD → ${EVENTS_PATH} (${EVENT_COUNT} events)"
  else
    if [[ -f "$EVENTS_PATH" && "$FORCE" == "false" ]]; then
      echo "ERROR: ${EVENTS_PATH} already exists. Use --force to overwrite." >&2
      exit 1
    fi
    git show "HEAD:${SOURCE_EVENTS_REL}" > "$EVENTS_PATH"
    echo "[WROTE] ${EVENTS_PATH} (${EVENT_COUNT} events)"
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
# SKELETON ONLY — by design (WP05).
#
# generate.sh emits a minimal version-matrix.md containing only the version
# pins that can be derived mechanically (package versions, source commit).
# The following sections require human judgement and are added manually after
# generation (see WP05 task prompt for the enrichment checklist):
#
#   1. Source Reference   — annotated links to key files at SOURCE_COMMIT
#   2. Replay Commands    — exact CLI invocations to reproduce the feature
#   3. Expected Artifact Classes — which artifact types the feature produces
#   4. Parity Verification — how to confirm regenerated output matches committed
#
# This separation keeps generate.sh fully deterministic while allowing the
# version matrix to carry context that only a human/reviewer can provide.
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

<!-- Skeleton generated by generate.sh.  Manual enrichment required:
  1. Source Reference   — annotated links to key files at SOURCE_COMMIT
  2. Replay Commands    — exact CLI invocations to reproduce the feature
  3. Expected Artifact Classes — which artifact types the feature produces
  4. Parity Verification — how to confirm regenerated output matches committed
  See tasks/WP05 for the full enrichment checklist. -->

NOTE: verification.md must be written manually after running pytest — see tasks/WP06 for instructions."

emit_file "${VERSION_MATRIX_PATH}" "${VERSION_MATRIX_CONTENT}"

echo ""
echo "Done. Files generated:"
if [[ "$DRY_RUN" == "true" ]]; then
  echo "  (dry-run — no files written; pass --write to emit)"
else
  ls -la "${OUTPUT_DIR}/"
fi
