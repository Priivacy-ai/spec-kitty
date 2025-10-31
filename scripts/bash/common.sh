#!/usr/bin/env bash
# Common functions and variables for all scripts

# Get repository root, with fallback for non-git repositories
get_repo_root() {
    if git rev-parse --show-toplevel >/dev/null 2>&1; then
        git rev-parse --show-toplevel
    else
        # Fall back to script location for non-git repos
        local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        (cd "$script_dir/../../.." && pwd)
    fi
}

# Get current branch, with fallback for non-git repositories
get_current_branch() {
    # First check if SPECIFY_FEATURE environment variable is set
    if [[ -n "${SPECIFY_FEATURE:-}" ]]; then
        echo "$SPECIFY_FEATURE"
        return
    fi
    
    # Then check git if available
    if git rev-parse --abbrev-ref HEAD >/dev/null 2>&1; then
        git rev-parse --abbrev-ref HEAD
        return
    fi
    
    # For non-git repos, try to find the latest feature directory
    local repo_root=$(get_repo_root)
    local specs_dir="$repo_root/kitty-specs"
    
    if [[ -d "$specs_dir" ]]; then
        local latest_feature=""
        local highest=0
        
        for dir in "$specs_dir"/*; do
            if [[ -d "$dir" ]]; then
                local dirname=$(basename "$dir")
                if [[ "$dirname" =~ ^([0-9]{3})- ]]; then
                    local number=${BASH_REMATCH[1]}
                    number=$((10#$number))
                    if [[ "$number" -gt "$highest" ]]; then
                        highest=$number
                        latest_feature=$dirname
                    fi
                fi
            fi
        done
        
        if [[ -n "$latest_feature" ]]; then
            echo "$latest_feature"
            return
        fi
    fi
    
    echo "main"  # Final fallback
}

# Check if we have git available
has_git() {
    git rev-parse --show-toplevel >/dev/null 2>&1
}

check_feature_branch() {
    local branch="$1"
    local has_git_repo="$2"

    # For non-git repos, we can't enforce branch naming but still provide output
    if [[ "$has_git_repo" != "true" ]]; then
        echo "[spec-kitty] Warning: Git repository not detected; skipped branch validation" >&2
        return 0
    fi

    if [[ ! "$branch" =~ ^[0-9]{3}- ]]; then
        echo "ERROR: Not on a feature branch. Current branch: $branch" >&2
        echo "Feature branches should be named like: 001-feature-name" >&2
        echo "" >&2

        # Help agents find the worktree by checking if any exist
        local repo_root=$(get_repo_root)
        if [[ -d "$repo_root/.worktrees" ]] && [[ -n "$(ls -A "$repo_root/.worktrees" 2>/dev/null)" ]]; then
            echo "Available worktrees:" >&2
            ls -1 "$repo_root/.worktrees" 2>/dev/null | sed 's/^/  • .worktrees\//' >&2
            echo "" >&2
            echo "To work on a feature, navigate to its worktree:" >&2
            echo "  cd .worktrees/<feature-name>" >&2
            echo "" >&2
            echo "Or set the feature manually:" >&2
            echo "  export SPECIFY_FEATURE=<feature-name>" >&2
        else
            echo "No worktrees found. Create a new feature with:" >&2
            echo "  /spec-kitty.specify" >&2
        fi

        return 1
    fi

    return 0
}

get_feature_dir() { echo "$1/kitty-specs/$2"; }

get_mission_exports() {
    local repo_root="$1"

    # Use python3 for mission detection to keep logic in sync with CLI behavior
    local python_bin="python3"
    if ! command -v "$python_bin" >/dev/null 2>&1; then
        python_bin="python"
    fi
    if ! command -v "$python_bin" >/dev/null 2>&1; then
        echo "[spec-kitty] Error: python interpreter not found; mission detection unavailable" >&2
        return 1
    fi

    "$python_bin" - "$repo_root" <<'PY'
from pathlib import Path
import sys

try:
    from specify_cli.mission import get_active_mission, MissionNotFoundError  # type: ignore
except Exception as exc:  # pragma: no cover - defensive: script execution path
    print(f"[spec-kitty] Error: Unable to import mission module ({exc})", file=sys.stderr)
    sys.exit(1)

repo_root = Path(sys.argv[1])

try:
    mission = get_active_mission(repo_root)
except MissionNotFoundError as exc:
    print(f"[spec-kitty] Error: {exc}", file=sys.stderr)
    sys.exit(1)

def emit(key: str, value: str) -> None:
    import shlex

    print(f"{key}={shlex.quote(str(value))}")

emit("MISSION_KEY", mission.path.name)
emit("MISSION_PATH", mission.path)
emit("MISSION_NAME", mission.name)
emit("MISSION_TEMPLATES_DIR", mission.templates_dir)
emit("MISSION_COMMANDS_DIR", mission.commands_dir)
emit("MISSION_CONSTITUTION_DIR", mission.constitution_dir)

spec_template = mission.templates_dir / "spec-template.md"
plan_template = mission.templates_dir / "plan-template.md"
tasks_template = mission.templates_dir / "tasks-template.md"
task_prompt_template = mission.templates_dir / "task-prompt-template.md"

emit("MISSION_SPEC_TEMPLATE", spec_template)
emit("MISSION_PLAN_TEMPLATE", plan_template)
emit("MISSION_TASKS_TEMPLATE", tasks_template)
emit("MISSION_TASK_PROMPT_TEMPLATE", task_prompt_template)
PY
}

get_feature_paths() {
    local repo_root=$(get_repo_root)
    local current_branch=$(get_current_branch)
    local has_git_repo="false"
    
    if has_git; then
        has_git_repo="true"
    fi
    
    local feature_dir=$(get_feature_dir "$repo_root" "$current_branch")
    local mission_exports
    mission_exports=$(get_mission_exports "$repo_root") || return 1
    
    cat <<EOF
REPO_ROOT='$repo_root'
CURRENT_BRANCH='$current_branch'
HAS_GIT='$has_git_repo'
FEATURE_DIR='$feature_dir'
FEATURE_SPEC='$feature_dir/spec.md'
IMPL_PLAN='$feature_dir/plan.md'
TASKS='$feature_dir/tasks.md'
RESEARCH='$feature_dir/research.md'
DATA_MODEL='$feature_dir/data-model.md'
QUICKSTART='$feature_dir/quickstart.md'
CONTRACTS_DIR='$feature_dir/contracts'
EOF

    printf '%s\n' "$mission_exports"
}

check_file() { [[ -f "$1" ]] && echo "  ✓ $2" || echo "  ✗ $2"; }
check_dir() { [[ -d "$1" && -n $(ls -A "$1" 2>/dev/null) ]] && echo "  ✓ $2" || echo "  ✗ $2"; }
