# Spec-Kitty Architecture Guide

**Version**: 1.0
**Last Updated**: 2025-11-13
**Audience**: Architects, agents, advanced users
**Status**: Phase 2A Documentation

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER/AGENT INTERFACE                               │
│                                                                               │
│  /spec-kitty.create-feature  /spec-kitty.plan  /spec-kitty.tasks  ...     │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BASH SCRIPT LAYER                                    │
│  (common.sh + individual scripts with unified UX/exit codes/flag parsing)   │
│                                                                               │
│  • Argument parsing (--help, --json, --quiet, --dry-run)                   │
│  • Output stream separation (stderr for logs, stdout for data)              │
│  • Context detection (current branch, worktree location)                    │
│  • Input validation (fail-fast with clear errors)                          │
│  • Auto-context switching (merge/move-to-lane from main)                   │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
        ┌────────────────────────────┐  ┌─────────────────────────┐
        │    Python Helper Layer      │  │   Git Integration       │
        │  (tasks_cli.py helpers)     │  │  (worktrees, branches)  │
        │                             │  │                         │
        │ • Task workflow management  │  │ • Branch management     │
        │ • Lane transitions          │  │ • Worktree operations   │
        │ • Task history tracking     │  │ • Merge operations      │
        │ • Prompt management         │  │ • Status checking       │
        └────────────────────────────┘  └─────────────────────────┘
                         │                         │
                         └────────────┬────────────┘
                                      ▼
        ┌─────────────────────────────────────────────────────────┐
        │           File System & Git Repository                  │
        │                                                           │
        │  project-root/                                           │
        │  ├── .git/                (shared across all worktrees) │
        │  ├── .kittify/            (templates & scripts)         │
        │  ├── .worktrees/          (feature development)         │
        │  │   ├── 001-feature/     (feature worktree)           │
        │  │   │   └── kitty-specs/ (active specs)               │
        │  │   └── 002-feature/     (another feature)            │
        │  ├── kitty-specs/         (archived specs)             │
        │  └── src/                 (main branch code)            │
        └─────────────────────────────────────────────────────────┘
```

## Component Layers

### 1. User Interface Layer

**What users/agents interact with**: Shell commands

```bash
/spec-kitty.create-feature "Description"
/spec-kitty.plan
/spec-kitty.tasks
/spec-kitty.accept
/spec-kitty.merge
/spec-kitty.check-prerequisites
```

**Key Properties**:
- Consistent interface (all support --help, --quiet, --json, --dry-run)
- Self-documenting (--help shows usage)
- Machine-readable output (--json mode)
- Standardized exit codes (0 success, 1-4 errors)

### 2. Bash Script Layer

**15 bash scripts** implementing spec-kitty workflow

#### Category A: Core Workflow (5 scripts)
- `create-new-feature.sh` - Create feature + worktree
- `setup-plan.sh` - Setup implementation plan
- `check-prerequisites.sh` - Validate prerequisites
- `accept-feature.sh` - Accept completed feature
- `merge-feature.sh` - Merge to main + cleanup

#### Category B: Task Management (5 scripts)
- `tasks-move-to-lane.sh` - Transition tasks between workflow states
- `mark-task-status.sh` - Mark task completion
- `move-task-to-doing.sh` - Move task to doing lane
- `validate-task-workflow.sh` - Validate workflow state
- `tasks-add-history-entry.sh` - Add task history

#### Category C: Utilities (5 scripts)
- `tasks-list-lanes.sh` - List all tasks
- `tasks-rollback-move.sh` - Rollback task moves
- `refresh-kittify-tasks.sh` - Update helpers
- `update-agent-context.sh` - Update agent files
- `setup-sandbox.sh` - Bootstrap sandboxes

#### Shared Infrastructure: common.sh

268 lines of reusable utilities:

```bash
# Logging (Issue #1: Separate Streams)
show_log()                    # Log to stderr
show_log_timestamped()        # Timestamped logs
output_json()                 # JSON to stdout
is_quiet()                    # Check quiet mode

# Flag Handling (Issue #4: Standardized Interface)
handle_common_flags()         # Parse standard flags
show_script_help()            # Display help text

# Context Detection
get_feature_paths()           # Extract feature info
get_current_branch()          # Current branch name
find_latest_feature_worktree()# Find recent worktree
get_repo_root()               # Repository root

# Input Validation (Issue #5: Fail-Fast)
validate_feature_exists()
validate_arg_provided()
validate_in_git_repo()
validate_tasks_file_exists()

# Execution
exec_cmd()                    # Execute with dry-run support
```

### 3. Python Helper Layer

**Python modules** for complex logic

`tasks/tasks_cli.py`:
- Task workflow management
- Lane transitions (planned → doing → review → done)
- Task history tracking
- Prompt file management

These are called from bash scripts:
```bash
python3 "$PY_HELPER" move "$@"  # tasks-move-to-lane.sh
python3 "$PY_HELPER" history    # tasks-add-history-entry.sh
```

### 4. Git Integration Layer

Direct Git operations:

- Worktree creation: `git worktree add .worktrees/NNN branch`
- Worktree listing: `git worktree list`
- Branch operations: `git checkout`, `git merge`
- Status checking: `git branch`, `git status`

### 5. File System Layer

Directory structure:

```
project-root/
├── .git/                          # Shared Git database
├── .kittify/
│   ├── scripts/bash/              # All 15 bash scripts
│   ├── templates/                 # Spec templates
│   └── tasks/                     # Python helpers
├── .worktrees/                    # Feature worktrees
│   └── NNN-feature/
│       └── kitty-specs/NNN-feature/ # Active specs
├── kitty-specs/                   # Archived specs
└── src/                           # Project code
```

## Context Detection Architecture

### How Context is Resolved

```
┌─ Script execution
│
├─ Step 1: Determine current location
│  └─ Run: git branch (or check pwd)
│
├─ Step 2: Check if in feature branch
│  ├─ Pattern match: ^[0-9]{3}-
│  └─ If yes → Use this branch as feature
│
├─ Step 3: If on main, auto-detect
│  ├─ Look for: .worktrees/ directory
│  ├─ Find: Most recently modified worktree
│  └─ Switch to: Latest worktree directory
│
├─ Step 4: Extract feature information
│  ├─ Get: Branch name from git
│  ├─ Find: kitty-specs/NNN-feature/ directory
│  └─ Load: spec.md, plan.md, tasks.md
│
└─ Step 5: Execute in correct context
   └─ All subsequent operations use detected feature
```

### Context Detection Code Flow

```bash
# In common.sh
get_current_branch() {
    git rev-parse --abbr-ref HEAD 2>/dev/null || echo "unknown"
}

find_latest_feature_worktree() {
    local repo_root="$1"
    local worktrees_root="$repo_root/.worktrees"

    if [[ -d "$worktrees_root" ]]; then
        # Find most recently modified worktree
        find "$worktrees_root" -type d -maxdepth 1 \
            -exec ls -td {} + | head -1
    fi
}

# In scripts
eval $(get_feature_paths)  # Sets variables from context

# Auto-switch in scripts
if [[ ! "$CURRENT_BRANCH" =~ ^[0-9]{3}- ]]; then
    if latest=$(find_latest_feature_worktree "$repo_root"); then
        cd "$latest" && "$0" "$@"  # Recurse in new context
        exit $?
    fi
fi
```

## Data Flow: Creating a Feature

### Step-by-Step Data Flow

```
1. User/Agent runs:
   /spec-kitty.create-feature "My feature" --json

2. create-new-feature.sh:
   ├─ Parse arguments
   ├─ Validate input
   ├─ Call git to create branch: git branch 001-my-feature
   ├─ Create worktree: git worktree add .worktrees/001-my-feature 001-my-feature
   ├─ Create spec file: touch kitty-specs/spec.md
   ├─ Output JSON to stdout:
   │  {
   │    "BRANCH_NAME": "001-my-feature",
   │    "WORKTREE_PATH": "/abs/path/.worktrees/001-my-feature",
   │    "FEATURE_DIR": "/abs/path/.worktrees/001-my-feature/kitty-specs/001-my-feature"
   │  }
   └─ Logs to stderr: [spec-kitty] ✓ Git worktree created...

3. Agent/User:
   ├─ Parses JSON from stdout
   ├─ Extracts WORKTREE_PATH
   ├─ Changes directory: cd WORKTREE_PATH
   └─ Now in correct context for next scripts

4. Next script (/spec-kitty.plan):
   ├─ Detects context: Current branch = 001-my-feature
   ├─ No auto-switching needed (already in worktree)
   ├─ Finds kitty-specs/001-my-feature/ directory
   ├─ Creates plan.md
   └─ Returns success
```

## Data Flow: Task Workflow

```
User runs: /spec-kitty.tasks-move-to-lane NNN-TASK doing

tasks-move-to-lane.sh:
├─ handle_common_flags()
├─ validate arguments
├─ Call Python: python3 tasks_cli.py move NNN-TASK doing
│
└─ tasks_cli.py:
   ├─ Find task in tasks.md
   ├─ Read task frontmatter
   ├─ Update lane metadata: lane: "doing"
   ├─ Create history entry
   ├─ Write back to tasks.md
   └─ Print success
```

## Error Handling Architecture

### Exit Codes (Global Convention)

```bash
EXIT_SUCCESS=0           # Success
EXIT_USAGE_ERROR=1       # Wrong arguments
EXIT_VALIDATION_ERROR=2  # Input validation failed
EXIT_EXECUTION_ERROR=3   # Command execution failed
EXIT_PRECONDITION_ERROR=4 # Missing dependencies
```

### Error Flow

```
Error occurs
    │
    ├─ Log error to stderr: show_log "❌ ERROR: ..."
    ├─ Provide remediation: show_log "🔧 TO FIX: ..."
    ├─ Return exit code: exit $EXIT_VALIDATION_ERROR
    │
    └─ Agent/User can:
       ├─ Detect error from exit code
       ├─ Read remediation from stderr
       └─ Take corrective action
```

### Example Error Handling

```bash
# Validation error
if [[ ! -d "$FEATURE_DIR" ]]; then
    show_log "❌ ERROR: Feature directory not found: $FEATURE_DIR"
    show_log "🔧 TO FIX: cd .worktrees/NNN-feature"
    exit $EXIT_VALIDATION_ERROR
fi

# Agent detects error from exit code, reads remediation from stderr
```

## I/O Architecture

### Output Streams (Issue #1)

```
          ┌─────────────────────┐
          │  Script Execution   │
          └──────────┬──────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
   LOGS (stderr)             DATA (stdout)
   ├─ [spec-kitty] ...       ├─ {"RESULT":"..."}
   ├─ ✓ Status updates      ├─ JSON output
   ├─ ❌ Error messages     └─ Machine-readable
   ├─ ⚠️  Warnings
   ├─ 🔧 Remediation
   └─ Human-readable
        │
        └─ Agent: Suppress with --quiet
```

### Flag Architecture (Issue #4)

```
Script Invocation
    │
    ├─ handle_common_flags "$@"
    │  ├─ Parse --help, --quiet, --json, --dry-run
    │  ├─ Set global variables
    │  └─ Extract remaining args
    │
    ├─ Check SHOW_HELP
    │  └─ If yes → show_script_help() → exit 0
    │
    ├─ Check DRY_RUN
    │  └─ If yes → Preview changes → exit 0
    │
    ├─ Check JSON_OUTPUT
    │  └─ If yes → output_json() → exit 0
    │
    └─ Check QUIET_MODE
       └─ If yes → Suppress logs, output only data → exit 0
```

## Validation Architecture (Issue #5)

```
Before Execution

1. Argument Validation
   ├─ validate_arg_provided "$1" "argument_name"
   └─ Exit 1 if missing

2. Prerequisite Validation
   ├─ validate_in_git_repo
   ├─ validate_feature_exists
   ├─ validate_tasks_file_exists
   └─ Exit 4 if missing

3. State Validation
   ├─ Check git branch
   ├─ Check worktree status
   └─ Exit 2 if invalid state

4. Input Validation
   ├─ Validate arguments
   ├─ Check file formats
   └─ Exit 1 if invalid

5. Business Logic Validation
   └─ Exit 3 if execution fails

After Validation → Execute Operation
```

## Context Auto-Detection Architecture (Issue #3)

```
Script Start
    │
    ├─ Check: Am I in a feature branch?
    │  └─ git branch | grep "^* 001-"
    │     ├─ YES → Use this branch
    │     └─ NO → Continue
    │
    ├─ Check: Is this script context-aware?
    │  └─ Does script support auto-switching?
    │     ├─ YES → Continue
    │     └─ NO → Fail with error
    │
    ├─ Check: Auto-detect latest worktree
    │  └─ find_latest_feature_worktree
    │     ├─ FOUND → Continue
    │     └─ NOT FOUND → Fail with remediation
    │
    ├─ Switch context
    │  └─ cd ".worktrees/NNN-feature" && "$0" "$@"
    │
    └─ Re-execute script in new context
       └─ Set SPEC_KITTY_AUTORETRY=1 to prevent infinite loop
```

## Scripts Supporting Auto-Detection

```
┌─────────────────────────────────┐
│  Scripts with Auto-Context      │
│  (Auto-switch if on main)       │
├─────────────────────────────────┤
│ • merge-feature.sh              │
│ • tasks-move-to-lane.sh         │
│ • check-prerequisites.sh        │
│ • (others may auto-switch)      │
└─────────────────────────────────┘

Implemented in: These scripts check git branch,
and if on main and not in a feature, they:

1. Find latest worktree
2. Output: "Auto-switching to ..."
3. cd to worktree
4. Re-exec script with SPEC_KITTY_AUTORETRY=1
```

## Integration Points

### For Agents/LLMs

```
Agent decides to create feature
    │
    ├─ Call: /spec-kitty.create-feature --json
    ├─ Parse: WORKTREE_PATH from output
    ├─ Execute: cd "$WORKTREE_PATH"
    │
    └─ All subsequent commands work in correct context
```

### For CI/CD Systems

```
CI Pipeline
    │
    ├─ Create feature: /spec-kitty.create-feature --quiet
    ├─ Plan: /spec-kitty.plan
    ├─ Validate: /spec-kitty.check-prerequisites
    ├─ Merge: /spec-kitty.merge
    │
    └─ All with exit codes for pipeline decisions
```

### For IDE Integrations

```
IDE runs spec-kitty commands
    │
    ├─ Use --json for structured output
    ├─ Parse JSON to populate IDE UI
    ├─ Use --quiet to suppress logs
    └─ Show success/error based on exit code
```

## Performance Considerations

### Worktree Operations

- **Create**: ~100ms (git worktree add)
- **List**: ~10ms (git worktree list)
- **Remove**: ~50ms (git worktree remove)

### Context Detection

- **Branch detection**: ~5ms
- **Worktree search**: ~20ms (with file system operations)
- **Total overhead**: ~30ms per script invocation

### Optimization Strategies

```bash
# Avoid redundant context detection
# Reuse context info in script chains:

feature_json=$(/spec-kitty.create-feature ...)  # ~100ms
worktree=$(echo $feature_json | jq -r .WORKTREE_PATH)

cd "$worktree"
/spec-kitty.plan    # ~5ms context detection (in correct location)
/spec-kitty.tasks   # ~5ms context detection
```

## Scalability Considerations

### Number of Worktrees

```
N worktrees = N directories in .worktrees/
├─ Listing: O(N) - linear scan
├─ Detection: O(N) - finds most recent
└─ Recommended: < 10 active worktrees at once
   (For performance, merge features regularly)
```

### Repository Size

```
Impact: Minimal
├─ Worktrees share Git objects (copy-on-write)
├─ No duplication of binary files
└─ Disk overhead: ~10MB per active worktree
```

## Security Considerations

### Isolation

```
Each worktree is isolated:
├─ Different branch = different file set
├─ Different git index (per worktree)
├─ Operations in one don't affect another
└─ Safe to run multiple agents in parallel
```

### Permissions

```
Git manages permissions:
├─ Worktrees share .git database
├─ File permissions within worktrees are independent
├─ Safe to have different users in different worktrees
└─ Use normal file system permissions
```

## Summary

**Spec-Kitty Architecture provides:**

1. **Consistent Interface** - 15 scripts with unified UX
2. **Stream Separation** - Logs to stderr, data to stdout
3. **Context Detection** - Automatic feature detection
4. **Input Validation** - Fail-fast with clear errors
5. **Git Integration** - Worktrees for isolation
6. **Agent Support** - JSON output, quiet mode, auto-switching
7. **Scalability** - Efficient file operations
8. **Security** - Isolated worktrees, no cross-contamination

---

**Next Steps**: See [WORKTREE_MODEL.md](WORKTREE_MODEL.md) and [CONTEXT_SWITCHING_GUIDE.md](CONTEXT_SWITCHING_GUIDE.md) for detailed usage documentation.
