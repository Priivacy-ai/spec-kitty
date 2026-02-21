---
work_package_id: WP02
title: Script Mission Parameter
lane: done
history:
- timestamp: '2025-12-15T11:55:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude
assignee: ''
phase: Phase 1 - Foundation
review_status: ''
reviewed_by: ''
shell_pid: '41644'
subtasks:
- T006
- T007
- T008
- T009
- T010
---

# Work Package Prompt: WP02 – Script Mission Parameter

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Add `--mission <key>` parameter to `create-new-feature.sh`
- Validate mission exists before writing to meta.json
- Include mission field in generated meta.json
- Update help text to document new parameter

**Success Metrics**:

- Running `create-new-feature.sh --mission research "desc"` creates feature with `"mission": "research"` in meta.json
- Running with invalid mission shows error listing available missions
- Running without `--mission` flag still works (no mission field written)

## Context & Constraints

**Reference Documents**:

- Spec: `kitty-specs/006-per-feature-mission/spec.md` (FR-009, FR-010)
- Data Model: `kitty-specs/006-per-feature-mission/data-model.md` (create-new-feature.sh Interface)

**Existing Code**:

- `.kittify/scripts/bash/create-new-feature.sh` - Main script (~387 lines)
- Lines 9-34: Argument parsing with while loop
- Lines 304-327: meta.json generation with cat heredoc
- Lines 331-353: JSON output mode

**Constraints**:

- Follow existing argument parsing pattern in the script
- Mission validation should check `.kittify/missions/$MISSION/mission.yaml` exists
- If `--mission` not provided, don't add mission field (allows backward compat)

## Subtasks & Detailed Guidance

### Subtask T006 – Add `--mission` flag parsing

- **Purpose**: Accept mission parameter from command line
- **Files**: `.kittify/scripts/bash/create-new-feature.sh`
- **Steps**:
  1. Add MISSION variable at top with other variables (line ~7):

     ```bash
     MISSION=""
     ```

  2. Add cases in the while loop (after `--feature-name` handling, around line 24):

     ```bash
     --mission=*)
         MISSION="${1#*=}"
         ;;
     --mission)
         shift
         if [ -z "${1:-}" ]; then
             echo "Error: --mission requires a value" >&2
             exit 1
         fi
         MISSION="$1"
         ;;
     ```

- **Parallel?**: No (foundational for T007-T009)

### Subtask T007 – Validate mission exists

- **Purpose**: Fail early with helpful error if invalid mission provided
- **Files**: `.kittify/scripts/bash/create-new-feature.sh`
- **Steps**:
  1. Add validation after REPO_ROOT is determined (around line 75), before worktree creation:

     ```bash
     # Validate mission if provided
     if [ -n "$MISSION" ]; then
         MISSION_DIR="$REPO_ROOT/.kittify/missions/$MISSION"
         if [ ! -f "$MISSION_DIR/mission.yaml" ]; then
             echo "Error: Mission '$MISSION' not found" >&2
             echo "Available missions:" >&2
             for m in "$REPO_ROOT/.kittify/missions"/*/mission.yaml; do
                 [ -f "$m" ] && echo "  - $(basename "$(dirname "$m")")" >&2
             done
             exit 1
         fi
     fi
     ```

  2. Ensure error message lists all available missions
- **Parallel?**: No (depends on T006)

### Subtask T008 – Write mission to meta.json

- **Purpose**: Include mission field in feature metadata
- **Files**: `.kittify/scripts/bash/create-new-feature.sh`
- **Steps**:
  1. Find the meta.json generation section (around line 319):

     ```bash
     cat > "$META_FILE" <<EOF
     {
       "feature_number": "$FEATURE_NUM",
       ...
     }
     EOF
     ```

  2. Conditionally add mission field if MISSION is set:

     ```bash
     # Build mission line if provided
     MISSION_LINE=""
     if [ -n "$MISSION" ]; then
         MISSION_LINE=",\n  \"mission\": \"$MISSION\""
     fi

     cat > "$META_FILE" <<EOF
     {
       "feature_number": "$FEATURE_NUM",
       "slug": "$BRANCH_NAME",
       "friendly_name": "$FRIENDLY_JSON",
       "source_description": "$DESCRIPTION_JSON",
       "created_at": "$timestamp"$([ -n "$MISSION" ] && echo ",")
       $([ -n "$MISSION" ] && echo "\"mission\": \"$MISSION\"")
     }
     EOF
     ```

  3. Alternative approach using printf for cleaner JSON:

     ```bash
     if [ -n "$MISSION" ]; then
         printf '{\n  "feature_number": "%s",\n  "slug": "%s",\n  "friendly_name": "%s",\n  "source_description": "%s",\n  "created_at": "%s",\n  "mission": "%s"\n}\n' \
             "$FEATURE_NUM" "$BRANCH_NAME" "$FRIENDLY_JSON" "$DESCRIPTION_JSON" "$timestamp" "$MISSION" > "$META_FILE"
     else
         # existing cat heredoc
     fi
     ```

- **Parallel?**: No (depends on T006)

### Subtask T009 – Update script help text

- **Purpose**: Document new --mission parameter for users
- **Files**: `.kittify/scripts/bash/create-new-feature.sh`
- **Steps**:
  1. Find help text (around line 26):

     ```bash
     --help|-h)
         echo "Usage: $0 [--json] [--feature-name \"Friendly Title\"] <feature_description>"
         exit 0
         ;;
     ```

  2. Update to include --mission:

     ```bash
     --help|-h)
         echo "Usage: $0 [--json] [--feature-name \"Friendly Title\"] [--mission <key>] <feature_description>"
         echo ""
         echo "Options:"
         echo "  --json              Output JSON format"
         echo "  --feature-name      Friendly title for the feature"
         echo "  --mission           Mission key (e.g., software-dev, research)"
         exit 0
         ;;
     ```

- **Parallel?**: No (depends on T006)

### Subtask T010 – Update PowerShell variant

- **Purpose**: Maintain parity between bash and PowerShell scripts
- **Files**: `.kittify/scripts/powershell/create-new-feature.ps1`
- **Steps**:
  1. Check if file exists:

     ```bash
     ls -la .kittify/scripts/powershell/create-new-feature.ps1
     ```

  2. If exists, add `-Mission` parameter:

     ```powershell
     param(
         [switch]$Json,
         [string]$FeatureName,
         [string]$Mission,  # NEW
         [Parameter(ValueFromRemainingArguments)]
         [string[]]$Description
     )
     ```

  3. Add validation and meta.json generation similar to bash
  4. If file doesn't exist, skip this subtask
- **Parallel?**: Yes (independent of bash changes once pattern established)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| JSON syntax errors in meta.json | Test with both --mission and without to ensure valid JSON |
| Breaking existing script callers | --mission is optional; existing calls work unchanged |
| PowerShell version drift | Either update both or document bash-only for now |

## Definition of Done Checklist

- [ ] `--mission` flag accepted and parsed correctly
- [ ] Invalid mission shows helpful error with available options
- [ ] meta.json includes `mission` field when --mission provided
- [ ] meta.json valid JSON both with and without --mission
- [ ] Help text updated
- [ ] PowerShell variant updated (if exists)

## Review Guidance

- Test: `./create-new-feature.sh --json --mission software-dev "test feature"`
- Test: `./create-new-feature.sh --json --mission invalid "test"` (should error)
- Test: `./create-new-feature.sh --json "test"` (should work, no mission field)
- Verify JSON output is valid in all cases
- Check error message lists all available missions

## Activity Log

- 2025-12-15T11:55:00Z – system – lane=planned – Prompt created.
- 2025-12-15T11:03:45Z – claude – shell_pid=41263 – lane=doing – Started implementation
- 2025-12-15T11:05:17Z – claude – shell_pid=41644 – lane=for_review – Ready for review - script tests pass
