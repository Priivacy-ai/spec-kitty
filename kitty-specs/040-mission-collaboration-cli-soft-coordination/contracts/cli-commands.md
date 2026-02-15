# CLI Commands Contract

**Feature**: 040-mission-collaboration-cli-soft-coordination
**Version**: S1/M1 Step 1

## Command: mission join

**Signature:**
```bash
spec-kitty mission join <mission_id> --role <role>
```

**Arguments:**
- `mission_id` (required): Mission identifier (UUID or slug)

**Options:**
- `--role` (required): Participant role
  - Values: `developer`, `reviewer`, `observer`, `stakeholder`
  - No default (explicit choice required)

**Behavior:**
1. Validate role ∈ {developer, reviewer, observer, stakeholder}
2. Reject `llm_actor` role with error message
3. Call SaaS join API (POST /api/v1/missions/{mission_id}/participants)
4. Receive participant_id (ULID) from SaaS
5. Write session file: `~/.spec-kitty/missions/<mission_id>/session.json`
6. Update active mission pointer: `~/.spec-kitty/session.json`
7. Emit ParticipantJoined event to local queue
8. Attempt SaaS delivery (if online)
9. Display success message + role capabilities

**Output (success):**
```
✓ Joined mission-abc-123 as developer

Capabilities:
  - Can focus on work packages and steps
  - Can set drive intent (active/inactive)
  - Can execute tasks
  - Can acknowledge collision warnings
  - Can post comments
  - Can capture decisions
```

**Output (error - invalid role):**
```
✗ Error: Invalid role 'llm_actor'
  Valid roles: developer, reviewer, observer, stakeholder
```

**Output (error - offline):**
```
✗ Error: Cannot join mission offline
  Mission join requires online connection to authenticate with SaaS.
```

**Exit Codes:**
- `0`: Success
- `1`: Error (invalid role, offline, SaaS authentication failure)

---

## Command: mission focus set

**Signature:**
```bash
spec-kitty mission focus set <target>
```

**Arguments:**
- `target` (required): Focus target
  - Format: `wp:<id>` or `step:<id>`
  - Examples: `wp:WP01`, `step:42`

**Options:**
- `--mission` (optional): Mission ID (uses active mission if omitted)

**Behavior:**
1. Load session file (validate participant joined)
2. Validate target exists in mission (wp_id or step_id)
3. Update participant focus in session file
4. Emit FocusChanged event to local queue
5. Attempt SaaS delivery (if online, queue if offline)
6. Display current focus

**Output (success):**
```
✓ Focus set to wp:WP01
```

**Output (error - invalid target):**
```
✗ Error: Work package 'WP99' not found in mission-abc-123
```

**Output (error - not joined):**
```
✗ Error: Not joined to any mission
  Run: spec-kitty mission join <mission_id> --role <role>
```

**Exit Codes:**
- `0`: Success
- `1`: Error (not joined, invalid target)

---

## Command: mission drive set

**Signature:**
```bash
spec-kitty mission drive set --state <state>
```

**Options:**
- `--state` (required): Drive intent state
  - Values: `active`, `inactive`
  - No default (explicit choice required)
- `--mission` (optional): Mission ID (uses active mission if omitted)

**Behavior:**
1. Load session file (validate participant joined)
2. Check if state change (skip if same state)
3. **If setting active**: Run pre-execution collision detection
   - Check for other active drivers on same focus
   - Check for stale context (participant inactive > 30min)
   - Check for dependency collisions
4. **If collision detected**: Emit warning event + prompt acknowledgement
5. **If no collision or acknowledged**: Update drive_intent in session
6. Emit DriveIntentSet event to local queue
7. Attempt SaaS delivery (if online, queue if offline)
8. Display drive state

**Output (success, no collision):**
```
✓ Drive intent set to active
  Focus: wp:WP01
  Last activity: just now
```

**Output (collision warning):**
```
⚠️  ConcurrentDriverWarning
Alice (developer) is actively driving wp:WP01
Last activity: 10 minutes ago

Choose action:
  [c] Continue (work in parallel, high collision risk)
  [h] Hold (set drive=inactive, observe only)
  [r] Reassign (advisory suggestion to Alice)
  [d] Defer (exit without state change)

Your choice: _
```

**Output (after acknowledgement - hold):**
```
✓ Drive intent kept as inactive (hold mode)
  You can still observe and comment.
```

**Output (after acknowledgement - continue):**
```
✓ Drive intent set to active (continue mode)
  ⚠️  Coordination risk: work in parallel with Alice.
```

**Exit Codes:**
- `0`: Success
- `1`: Error (not joined)

---

## Command: mission status

**Signature:**
```bash
spec-kitty mission status [--verbose]
```

**Options:**
- `--verbose` (optional): Show detailed participant state
- `--mission` (optional): Mission ID (uses active mission if omitted)

**Behavior:**
1. Load session file (validate participant joined)
2. Load collaboration state (materialized view from events)
3. Display participants grouped by role
4. Show drive_intent, focus, last_activity_at for each
5. Display collision summary (concurrent drivers per focus)

**Output (success):**
```
Mission: mission-abc-123
Participants: 3

DEVELOPER
  Alice (active)    wp:WP01    last: 2m ago
  Bob (inactive)    wp:WP02    last: 15m ago

REVIEWER
  Charlie (active)  step:42    last: 5m ago

⚠️  1 potential collision:
  - wp:WP01: Alice (active)

✓ No high-severity collisions
```

**Output (verbose):**
```
Mission: mission-abc-123
Participants: 3

DEVELOPER
  Alice
    Status: active
    Focus: wp:WP01
    Drive: active
    Last activity: 2m ago
    Capabilities: focus, drive, execute, ack_warning, comment, decide

  Bob
    Status: inactive
    Focus: wp:WP02
    Drive: inactive
    Last activity: 15m ago (⚠️  stale)
    Capabilities: focus, drive, execute, ack_warning, comment, decide

...
```

**Exit Codes:**
- `0`: Success
- `1`: Error (not joined)

---

## Command: mission comment

**Signature:**
```bash
spec-kitty mission comment --text <text>
spec-kitty mission comment [--stdin]
```

**Options:**
- `--text` (mutually exclusive with --stdin): Comment text (single line)
- `--stdin` (mutually exclusive with --text): Read multiline text from stdin
- `--mission` (optional): Mission ID (uses active mission if omitted)

**Behavior:**
1. Load session file (validate participant joined)
2. Validate capability: can_comment=true (reject observer without capability)
3. Read text (from --text flag or stdin)
4. Validate text length (max 500 chars, warn if truncated)
5. Capture current focus context (wp/step or mission-level if none)
6. Generate comment_id (ULID)
7. Emit CommentPosted event to local queue
8. Attempt SaaS delivery (if online, queue if offline)
9. Display comment_id

**Output (success):**
```
✓ Comment posted (comment_id: 01HQRS8ZMBE6XYZABC0123CMT)
  Focus: wp:WP01
```

**Output (truncation warning):**
```
⚠️  Comment truncated to 500 characters
✓ Comment posted (comment_id: 01HQRS8ZMBE6XYZABC0123CMT)
```

**Output (error - no capability):**
```
✗ Error: Role 'observer' cannot post comments
  Only roles with can_comment capability can post comments.
```

**Exit Codes:**
- `0`: Success
- `1`: Error (not joined, no capability, empty text)

---

## Command: mission decide

**Signature:**
```bash
spec-kitty mission decide --text <text>
spec-kitty mission decide [--stdin]
```

**Options:**
- `--text` (mutually exclusive with --stdin): Decision text
- `--stdin` (mutually exclusive with --text): Read multiline text from stdin
- `--mission` (optional): Mission ID (uses active mission if omitted)

**Behavior:**
1. Load session file (validate participant joined)
2. Validate capability: can_decide=true (reject observer without capability)
3. Read text (from --text flag or stdin)
4. Support markdown formatting (stored as-is, rendered in SaaS UI)
5. Capture current focus context (wp/step level)
6. Generate decision_id (ULID)
7. Emit DecisionCaptured event to local queue
8. Attempt SaaS delivery (if online, queue if offline)
9. Display decision_id

**Output (success):**
```
✓ Decision captured (decision_id: 01HQRS8ZMBE6XYZABC0123DEC)
  Focus: step:42
  Decision: Approved: use REST API for now
```

**Output (error - no capability):**
```
✗ Error: Role 'observer' cannot capture decisions
  Only roles with can_decide capability can capture decisions.
```

**Exit Codes:**
- `0`: Success
- `1`: Error (not joined, no capability, empty text)

---

## Global Options

All commands support:
- `--help`: Display command help
- `--version`: Display spec-kitty version
- `--json`: Output as JSON (for scripting)

**JSON Output Format:**
```json
{
  "result": "success",
  "mission_id": "mission-abc-123",
  "participant_id": "01HQRS8ZMBE6XYZ0000000001",
  "data": { ... }
}
```

**JSON Error Format:**
```json
{
  "result": "error",
  "error_code": "INVALID_ROLE",
  "error_message": "Invalid role 'llm_actor'",
  "details": {
    "valid_roles": ["developer", "reviewer", "observer", "stakeholder"]
  }
}
```

---

## Environment Variables

- `SAAS_API_URL`: SaaS API base URL (default: https://api.spec-kitty-saas.com)
- `SAAS_API_KEY`: API key for authentication (required for join/replay)
- `MOCK_SAAS`: Enable mock SaaS mode for local testing (default: false)

---

## Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| `INVALID_ROLE` | Role not in {developer, reviewer, observer, stakeholder} | Use valid role |
| `NOT_JOINED` | Participant not joined to mission | Run mission join first |
| `NO_CAPABILITY` | Participant lacks required capability | Check role permissions |
| `OFFLINE_JOIN` | Cannot join mission offline | Connect to network |
| `INVALID_TARGET` | Focus target (wp/step) not found | Check mission WP/step IDs |
| `SAAS_AUTH_FAILED` | SaaS authentication failure | Check API key |

---

## Backward Compatibility

**S1/M1 Scope:**
- These commands are greenfield (2.x branch, no 1.x compatibility)
- No migration from 1.x required

**Future Compatibility:**
- Commands follow semver (major.minor.patch)
- Breaking changes require major version bump
- Deprecated commands show warning before removal
