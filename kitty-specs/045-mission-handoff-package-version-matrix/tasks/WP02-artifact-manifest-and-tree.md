---
work_package_id: WP02
title: Artifact Manifest Snapshot + Tree Snapshot
lane: "doing"
dependencies: [WP01]
base_branch: 2.x
base_commit: daad18d1a6cc861106e5879e1875fda34517d0a2
created_at: '2026-02-23T19:43:18.822060+00:00'
subtasks:
- T004
- T005
- T006
- T007
phase: Phase 2 - Parallel Wave
assignee: ''
agent: ''
shell_pid: "36909"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-23T18:04:02Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Artifact Manifest Snapshot + Tree Snapshot

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check `review_status`. If `has_feedback`, read **Review Feedback** below first.
- Address all feedback before completing this WP.

---

## Review Feedback

*[Empty initially. Populated by `/spec-kitty.review` if changes are requested.]*

---

## Objectives & Success Criteria

Generate and commit two JSON snapshots that together form the completeness record for this handoff wave:
1. `artifact-manifest.json` — the expected artifact contract for the software-dev mission at `source_commit`
2. `artifact-tree.json` — the actual state of the 045 feature directory with SHA-256 fingerprints and explicit absent-artifact entries

**Done when**:
- [ ] `handoff/artifact-manifest.json` is valid JSON matching the YAML source plus `source_commit` and `captured_at` fields
- [ ] `handoff/artifact-tree.json` has `entries[]` for every file in the feature dir (excluding `handoff/`) plus absent entries for any expected artifacts not found
- [ ] Tree snapshot includes `total_files`, `present_count`, `absent_count` summary fields
- [ ] No file from `handoff/` appears in the tree entries

**Implementation command** (depends on WP01):
```bash
spec-kitty implement WP02 --base WP01
```

---

## Context & Constraints

- **Feature dir**: `kitty-specs/045-mission-handoff-package-version-matrix/`
- **Output dir**: `kitty-specs/045-mission-handoff-package-version-matrix/handoff/` (created in WP01)
- **Branch**: `2.x`
- **Source commit**: `21ed0738f009ca35a2927528238a48778e41f1d4`
- **YAML source**: `src/specify_cli/missions/software-dev/expected-artifacts.yaml` (read this at HEAD — it reflects the software-dev mission contract at source_commit)
- **Supporting docs**: `data-model.md` §§ ArtifactManifestSnapshot, ArtifactTreeSnapshot
- **C-lite**: Python stdlib + existing deps (json, hashlib, pathlib, yaml). No new modules.

---

## Subtasks & Detailed Guidance

### Subtask T004 – Export `expected-artifacts.yaml` → `artifact-manifest.json`

**Purpose**: Capture a point-in-time JSON snapshot of the expected artifact manifest so downstream teams don't need to read the YAML source.

**Steps**:
1. Confirm the YAML file exists:
   ```bash
   ls src/specify_cli/missions/software-dev/expected-artifacts.yaml
   ```
2. Convert to JSON and add provenance fields:
   ```python
   python3 - <<'EOF'
   import json, yaml, sys
   from datetime import datetime, timezone
   from pathlib import Path

   yaml_path = Path("src/specify_cli/missions/software-dev/expected-artifacts.yaml")
   out_path = Path("kitty-specs/045-mission-handoff-package-version-matrix/handoff/artifact-manifest.json")

   data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
   data["source_commit"] = "21ed0738f009ca35a2927528238a48778e41f1d4"
   data["captured_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

   out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
   print(f"Written: {out_path} ({out_path.stat().st_size} bytes)")
   EOF
   ```
3. Verify the output contains the expected top-level keys:
   ```bash
   python3 -c "import json; d=json.load(open('kitty-specs/045-mission-handoff-package-version-matrix/handoff/artifact-manifest.json')); print(list(d.keys()))"
   # Expected: ['schema_version', 'mission_type', 'manifest_version', 'required_always', 'required_by_step', 'optional_always', 'source_commit', 'captured_at']
   ```

**Files**:
- `handoff/artifact-manifest.json` (new, ~50 lines)

**Notes**:
- If `ruamel.yaml` is preferred over `PyYAML`, both are available in the spec-kitty venv. Use `yaml.safe_load` (PyYAML) or `ruamel.yaml.YAML().load()` — either works.
- `source_commit` and `captured_at` are added AFTER loading from YAML (not in the YAML file itself).

---

### Subtask T005 – Walk Feature Directory, Compute SHA-256

**Purpose**: Build the raw inventory of files present in the feature directory.

**Steps**:
1. Write a Python script that walks the feature directory, excluding `handoff/`:
   ```python
   python3 - <<'EOF'
   import hashlib, json
   from pathlib import Path

   feature_dir = Path("kitty-specs/045-mission-handoff-package-version-matrix")
   handoff_dir = feature_dir / "handoff"

   entries = []
   for p in sorted(feature_dir.rglob("*")):
       if not p.is_file():
           continue
       # Exclude handoff/ subdirectory to prevent self-reference
       if handoff_dir in p.parents or p.parent == handoff_dir:
           continue
       # Exclude __pycache__, .pyc
       if "__pycache__" in p.parts or p.suffix == ".pyc":
           continue
       rel = p.relative_to(feature_dir)
       sha256 = hashlib.sha256(p.read_bytes()).hexdigest()
       entries.append({
           "path": str(rel),
           "sha256": sha256,
           "size_bytes": p.stat().st_size,
           "status": "present"
       })

   print(json.dumps(entries, indent=2))
   print(f"\n{len(entries)} files found", flush=True)
   EOF
   ```
2. Review the list — confirm `handoff/` files are not included.
3. Store the `entries` list for use in T006.

**Files**: No output file yet — data collected here feeds T006 and T007.

**Notes**: The `sorted()` call ensures consistent ordering across runs (lexicographic by path). Do not use filesystem modification time for ordering.

---

### Subtask T006 – Cross-Reference Tree vs Manifest, Flag Absent Artifacts

**Purpose**: Identify expected artifacts from the manifest that are not present in the walked tree. These must appear as explicit `"status": "absent"` entries in the tree snapshot.

**Steps**:
1. Load the manifest from T004 and the entries from T005.
2. Collect expected path_patterns from:
   - `required_always[]`
   - `required_by_step["specify"][]` (the step the 045 feature is currently in)
   - `optional_always[]`
3. For each expected artifact spec, check if any entry in the walked tree matches its `path_pattern` (simple glob or exact match):
   ```python
   import fnmatch

   def matches_any(path_pattern, entries):
       return any(fnmatch.fnmatch(e["path"], path_pattern) for e in entries)
   ```
4. For each manifest entry with NO matching file, add an absent record:
   ```python
   absent_entry = {
       "path": spec["path_pattern"],      # Use pattern as path (no actual file)
       "sha256": None,
       "size_bytes": None,
       "status": "absent"
   }
   ```

**Files**: No new files; produces the `absent_entries` list for T007.

**Notes**:
- The `tasks/` directory (and its contents) are in the tree as present files. `tasks.md` is a workflow artifact, not a manifest-absent item.
- The main absent entry to expect: `tasks.md` is in `required_by_step["plan"]` — but 045 is currently at the "specify" step, so only "specify" step entries are checked for absent status.
- `handoff/` files themselves are excluded from the tree, so they will NOT appear as absent entries (they are the OUTPUT, not the input).

---

### Subtask T007 – Write `artifact-tree.json`

**Purpose**: Combine present and absent entries into the final artifact tree snapshot.

**Steps**:
1. Combine `entries` (from T005) + `absent_entries` (from T006).
2. Compute summary counts.
3. Write the output file:
   ```python
   python3 - <<'EOF'
   import hashlib, json, fnmatch
   from datetime import datetime, timezone
   from pathlib import Path

   feature_dir = Path("kitty-specs/045-mission-handoff-package-version-matrix")
   handoff_dir = feature_dir / "handoff"
   manifest_path = handoff_dir / "artifact-manifest.json"
   out_path = handoff_dir / "artifact-tree.json"

   manifest = json.load(manifest_path.open(encoding="utf-8"))

   # Collect present entries
   present = []
   for p in sorted(feature_dir.rglob("*")):
       if not p.is_file(): continue
       if handoff_dir in p.parents or p.parent == handoff_dir: continue
       if "__pycache__" in p.parts or p.suffix == ".pyc": continue
       rel = str(p.relative_to(feature_dir))
       sha256 = hashlib.sha256(p.read_bytes()).hexdigest()
       present.append({"path": rel, "sha256": sha256, "size_bytes": p.stat().st_size, "status": "present"})

   present_paths = {e["path"] for e in present}

   # Collect absent entries from manifest
   absent = []
   all_specs = list(manifest.get("required_always", []))
   for step_specs in manifest.get("required_by_step", {}).values():
       all_specs.extend(step_specs)
   all_specs.extend(manifest.get("optional_always", []))

   for spec in all_specs:
       pattern = spec["path_pattern"]
       if not any(fnmatch.fnmatch(p, pattern) for p in present_paths):
           absent.append({"path": pattern, "sha256": None, "size_bytes": None, "status": "absent"})

   all_entries = present + absent
   snapshot = {
       "schema_version": "1",
       "feature_slug": "045-mission-handoff-package-version-matrix",
       "root_path": "kitty-specs/045-mission-handoff-package-version-matrix",
       "source_commit": "21ed0738f009ca35a2927528238a48778e41f1d4",
       "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
       "entries": all_entries,
       "total_files": len(all_entries),
       "present_count": len(present),
       "absent_count": len(absent),
   }
   out_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
   print(f"Written: {out_path} — {len(present)} present, {len(absent)} absent")
   EOF
   ```

**Files**:
- `handoff/artifact-tree.json` (new, ~100-200 lines depending on file count)

**Notes**:
- Re-run this script after WP03/WP04/WP05/WP06 add more files to `handoff/` — but since `handoff/` is excluded, those additions don't change the tree. The tree only reflects `kitty-specs/045-.../` non-handoff files.
- `tasks.md` will be in the present entries.

---

## Risks & Mitigations

- **`handoff/` files leak into tree**: Add an assertion after writing: `python3 -c "import json; t=json.load(open('handoff/artifact-tree.json')); bad=[e for e in t['entries'] if e['path'].startswith('handoff/')]; assert not bad, f'handoff/ entries found: {bad}'"`.
- **YAML import fails**: Both `yaml` (PyYAML) and `ruamel.yaml` are in the spec-kitty venv. If neither works, fall back to: `python3 -c "import subprocess,json; ..."` using `yq` — but prefer the Python approach first.
- **SHA-256 mismatch on rerun**: SHA-256 is deterministic for the same file content. If files change between runs, the SHA changes — this is expected behaviour (the snapshot captures the state at the time of generation).

---

## Review Guidance

Reviewers verify:
1. `artifact-manifest.json` has `source_commit`, `captured_at`, and all YAML keys present
2. `artifact-tree.json` has `present_count` + `absent_count` = `total_files`
3. No entries in `artifact-tree.json` have `path` starting with `handoff/`
4. Absent entries have `"sha256": null` and `"size_bytes": null` (not omitted)
5. `spec.md` and `plan.md` appear as `"status": "present"` with non-null SHA-256

---

## Activity Log

- 2026-02-23T18:04:02Z – system – lane=planned – Prompt created.
