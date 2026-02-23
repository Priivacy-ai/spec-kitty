---
work_package_id: WP01
title: Handoff Directory Scaffold + Namespace Tuple
lane: "done"
dependencies: []
base_branch: 2.x
base_commit: 595bf2762385da04c26488fec4d96ea3b1c23939
created_at: '2026-02-23T19:37:18.133502+00:00'
subtasks:
- T001
- T002
- T003
phase: Phase 1 - Foundation
assignee: ''
agent: claude-opus
shell_pid: '31424'
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-02-23T18:04:02Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – Handoff Directory Scaffold + Namespace Tuple

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create the `handoff/` output directory inside the 045 feature directory and commit the canonical `namespace.json` identity anchor for the plan-context-bootstrap-fix wave.

**Done when**:
- [ ] `kitty-specs/045-mission-handoff-package-version-matrix/handoff/` directory exists and is tracked by git
- [ ] `handoff/namespace.json` is valid JSON with all 9 required fields
- [ ] All 4 invariants from data-model.md pass: source_commit is 40-char hex, step_id is null, schema_version is "1", generated_at is ISO 8601 UTC

**Implementation command** (no dependencies):
```bash
spec-kitty implement WP01
```

---

## Context & Constraints

- **Feature dir**: `kitty-specs/045-mission-handoff-package-version-matrix/`
- **Output dir**: `kitty-specs/045-mission-handoff-package-version-matrix/handoff/` (create this)
- **Branch**: `2.x`
- **Source commit anchor** (hardcoded): `21ed0738f009ca35a2927528238a48778e41f1d4`
  - This is the merge commit for WP05 of `041-enable-plan-mission-runtime-support` (2026-02-22)
  - Verify with: `git log --oneline | grep "21ed0738"` — should show "Merge WP05 from 041-enable-plan-mission-runtime-support"
- **C-lite constraint**: No new Python modules, no new CLI subcommands. Files only.
- **Supporting docs**: `kitty-specs/045-.../data-model.md` (namespace.json schema), `plan.md` (context)
- **Constitution**: `.kittify/memory/constitution.md` — Python 3.11+, 2.x branch, no new subcommands

---

## Subtasks & Detailed Guidance

### Subtask T001 – Create `handoff/` Directory

**Purpose**: Establish the output directory that all WP01–WP06 files land in. Git must track this directory before files are written.

**Steps**:
1. Create the directory:
   ```bash
   mkdir -p kitty-specs/045-mission-handoff-package-version-matrix/handoff
   ```
2. Add a `README.md` (preferred over `.gitkeep`) so the directory is self-documenting:
   - Title: `# Handoff Package: plan-context-bootstrap-fix wave`
   - One-liner: `Canonical handoff artifacts for downstream replay. See namespace.json for identity anchor.`
3. Verify the directory is inside `FEATURE_DIR` and not somewhere else.

**Files**:
- `kitty-specs/045-mission-handoff-package-version-matrix/handoff/README.md` (new)

**Notes**:
- Do not use `.gitkeep` — a README is more useful and satisfies the same git-tracking need.

---

### Subtask T002 – Write `handoff/namespace.json`

**Purpose**: Create the identity anchor for this handoff package. All downstream consumers start here to determine which wave, branch, and commit the package represents.

**Steps**:
1. Derive `project_scope_id`:
   ```bash
   basename $(git rev-parse --show-toplevel)
   # Expected output: spec-kitty
   ```
2. Derive `generated_at`:
   ```bash
   python3 -c "from datetime import datetime, timezone; print(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))"
   ```
3. Write `handoff/namespace.json` with this exact structure (fill in `generated_at` with actual current time):
   ```json
   {
     "schema_version": "1",
     "project_scope_id": "spec-kitty",
     "feature_slug": "045-mission-handoff-package-version-matrix",
     "source_branch": "2.x",
     "source_commit": "21ed0738f009ca35a2927528238a48778e41f1d4",
     "mission_key": "software-dev",
     "manifest_version": "1",
     "step_id": null,
     "generated_at": "<ISO 8601 UTC — replace this>"
   }
   ```

**Files**:
- `kitty-specs/045-mission-handoff-package-version-matrix/handoff/namespace.json` (new)

**Notes**:
- `source_commit` is NOT the current HEAD — it is the hardcoded anchor above. Do not use `git rev-parse HEAD`.
- `step_id` MUST be `null` (JSON null, not the string "null").
- Use 2-space indentation for readability.

---

### Subtask T003 – Validate Namespace Invariants

**Purpose**: Catch errors before the file is committed. The data-model defines 4 invariants that must hold.

**Steps**:
1. Run this inline validation script from repo root:
   ```bash
   python3 - <<'EOF'
   import json, re, sys
   f = "kitty-specs/045-mission-handoff-package-version-matrix/handoff/namespace.json"
   ns = json.load(open(f))

   errors = []
   if not re.fullmatch(r"[0-9a-f]{40}", ns.get("source_commit", "")):
       errors.append(f"source_commit must be 40-char lowercase hex, got: {ns.get('source_commit')}")
   if ns.get("step_id") is not None:
       errors.append(f"step_id must be null, got: {ns.get('step_id')}")
   if ns.get("schema_version") != "1":
       errors.append(f"schema_version must be '1', got: {ns.get('schema_version')}")
   if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", ns.get("generated_at", "")):
       errors.append(f"generated_at must be ISO 8601 UTC (Z suffix), got: {ns.get('generated_at')}")

   if errors:
       print("VALIDATION FAILED:")
       for e in errors: print(f"  - {e}")
       sys.exit(1)
   else:
       print("namespace.json: all invariants PASS")
   EOF
   ```
2. Fix any failures before proceeding.

**Files**: No new files; validates the file from T002.

**Notes**: If validation passes, the namespace.json is correct and ready. Commit both T001 and T002 files together after validation.

---

## Risks & Mitigations

- **Wrong source_commit**: Confirm with `git show 21ed0738f009ca35a2927528238a48778e41f1d4 --format="%H %s" --no-patch` → should show `Merge WP05 from 041-enable-plan-mission-runtime-support`.
- **step_id as JSON string "null"**: Python's `json.dumps({"step_id": None})` produces `{"step_id": null}` correctly. Do not use the Python string `"null"`.
- **generated_at drift**: The timestamp records when the handoff package was generated, not the source commit date. Using current time is correct.

---

## Review Guidance

Reviewers should verify:
1. `handoff/` directory exists with a README (not .gitkeep)
2. `namespace.json` has exactly 9 top-level keys per the schema
3. `source_commit` == `21ed0738f009ca35a2927528238a48778e41f1d4` (exact match)
4. `step_id` is JSON `null`, not `"null"` string
5. `generated_at` matches ISO 8601 UTC format (`Z` suffix, no timezone offset)
6. Validation script from T003 exits 0 when run against the committed file

---

## Activity Log

- 2026-02-23T18:04:02Z – system – lane=planned – Prompt created.
- 2026-02-23T19:37:18Z – claude – shell_pid=29627 – lane=doing – Assigned agent via workflow command
- 2026-02-23T19:38:35Z – claude – shell_pid=29627 – lane=for_review – Ready for review: handoff/ directory with README.md and namespace.json (9 fields, all 4 invariants pass)
- 2026-02-23T19:39:34Z – claude-opus – shell_pid=31424 – lane=doing – Started review via workflow command
- 2026-02-23T19:42:33Z – claude-opus – shell_pid=31424 – lane=done – Review passed: All 6 review checks pass. namespace.json has 9 keys, 4 invariants validated, source_commit verified, step_id is JSON null, generated_at is proper ISO 8601 UTC. README.md present. C-lite constraint satisfied.
