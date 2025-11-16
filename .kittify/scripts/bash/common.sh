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
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
        echo "❌ ERROR: Command run from wrong location!" >&2
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
        echo "" >&2
        echo "Current location: $(pwd)" >&2
        echo "Current branch: $branch" >&2
        echo "Required: Feature branch (e.g., 001-feature-name)" >&2
        echo "" >&2

        # Help agents find the worktree by checking if any exist
        local repo_root=$(get_repo_root)
        if [[ -d "$repo_root/.worktrees" ]] && [[ -n "$(ls -A "$repo_root/.worktrees" 2>/dev/null)" ]]; then
            echo "🔧 TO FIX THIS ISSUE:" >&2
            echo "" >&2
            echo "1. List available worktrees:" >&2
            echo "   ls .worktrees/" >&2
            echo "" >&2
            echo "2. Navigate to a worktree:" >&2
            local first_worktree=$(ls -1 "$repo_root/.worktrees" 2>/dev/null | head -1)
            if [[ -n "$first_worktree" ]]; then
                echo "   cd .worktrees/$first_worktree" >&2
            else
                echo "   cd .worktrees/<feature-name>" >&2
            fi
            echo "" >&2
            echo "3. Retry the command" >&2
            echo "" >&2
            echo "Available worktrees:" >&2
            ls -1 "$repo_root/.worktrees" 2>/dev/null | sed 's/^/  ✓ /' >&2
        else
            echo "🔧 TO FIX THIS ISSUE:" >&2
            echo "" >&2
            echo "No worktrees found. Create a new feature with:" >&2
            echo "  spec-kitty specify" >&2
            echo "" >&2
            echo "Or if you have a feature branch, create its worktree:" >&2
            echo "  git worktree add .worktrees/001-your-feature 001-your-feature" >&2
        fi
        echo "" >&2
        echo "💡 TIP: Run 'spec-kitty verify-setup' to diagnose issues" >&2
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2

        return 1
    fi

    return 0
}

find_latest_feature_worktree() {
    local repo_root="$1"
    local worktrees_root="$repo_root/.worktrees"
    local latest_path=""
    local highest=-1

    if [[ ! -d "$worktrees_root" ]]; then
        return 1
    fi

    while IFS= read -r dir; do
        [[ -d "$dir" ]] || continue
        local base="$(basename "$dir")"
        if [[ "$base" =~ ^([0-9]{3})- ]]; then
            local number=$((10#${BASH_REMATCH[1]}))
            if (( number > highest )); then
                highest=$number
                latest_path="$dir"
            fi
        fi
    done < <(find "$worktrees_root" -mindepth 1 -maxdepth 1 -type d -print 2>/dev/null)

    if [[ -n "$latest_path" ]]; then
        printf '%s\n' "$latest_path"
        return 0
    fi

    return 1
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
import os
import sys

try:
    from specify_cli.mission import get_active_mission, MissionNotFoundError  # type: ignore
except Exception:
    class MissionNotFoundError(Exception):
        """Local fallback when specify_cli isn't importable."""

    class _FallbackMission:
        def __init__(self, mission_path: Path):
            self.path = mission_path.resolve()
            self._config: dict | None = None

        def _load_config(self) -> dict:
            if self._config is not None:
                return self._config
            config_path = self.path / "mission.yaml"
            if not config_path.exists():
                self._config = {}
                return self._config
            try:
                import yaml  # type: ignore

                with config_path.open("r", encoding="utf-8") as fh:
                    data = yaml.safe_load(fh) or {}
            except Exception:
                data = {}
            self._config = data if isinstance(data, dict) else {}
            return self._config

        @property
        def name(self) -> str:
            config = self._load_config()
            return str(config.get("name") or self.path.name)

        @property
        def templates_dir(self) -> Path:
            return self.path / "templates"

        @property
        def commands_dir(self) -> Path:
            return self.path / "commands"

        @property
        def constitution_dir(self) -> Path:
            return self.path / "constitution"

    def _resolve_mission_path(project_root: Path) -> Path:
        kittify_dir = project_root / ".kittify"
        if not kittify_dir.exists():
            raise MissionNotFoundError(
                f"No .kittify directory found in {project_root}. "
                "Is this a Spec Kitty project?"
            )

        active_link = kittify_dir / "active-mission"
        if active_link.exists():
            mission_path = None
            if active_link.is_symlink():
                mission_path = active_link.resolve()
            elif active_link.is_file():
                try:
                    mission_name = active_link.read_text(encoding="utf-8").strip()
                except OSError:
                    mission_name = ""
                if mission_name:
                    mission_path = kittify_dir / "missions" / mission_name
            if mission_path is None:
                try:
                    target = Path(os.readlink(active_link))
                    mission_path = (active_link.parent / target).resolve()
                except (OSError, RuntimeError):
                    mission_path = None
            if mission_path is None:
                mission_path = kittify_dir / "missions" / "software-dev"
        else:
            mission_path = kittify_dir / "missions" / "software-dev"

        if mission_path.exists():
            return mission_path

        missions_dir = kittify_dir / "missions"
        available = []
        if missions_dir.exists():
            available = sorted(
                p.name for p in missions_dir.iterdir()
                if p.is_dir() and (p / "mission.yaml").exists()
            )
        raise MissionNotFoundError(
            f"Active mission directory not found: {mission_path}\n"
            f"Available missions: {', '.join(available) if available else 'none'}"
        )

    def get_active_mission(project_root: Path) -> _FallbackMission:
        return _FallbackMission(_resolve_mission_path(project_root))

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
