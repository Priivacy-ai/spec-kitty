#!/usr/bin/env bash
set -euo pipefail

# WP worktree branches must not commit planning artifacts.
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
if [[ "$CURRENT_BRANCH" =~ -WP[0-9]+$ ]]; then
  STAGED_KITTY_SPECS=$(git diff --cached --name-only | grep -E '^kitty-specs/' || true)
  if [[ -n "$STAGED_KITTY_SPECS" ]]; then
    echo "❌ COMMIT BLOCKED: WP branches must not commit kitty-specs/"
    echo "Branch: $CURRENT_BRANCH"
    echo "Staged planning files:"
    echo "$STAGED_KITTY_SPECS" | sed 's/^/  /'
    echo ""
    echo "Fix:"
    echo "  git restore --staged kitty-specs/"
    echo "  git restore --worktree kitty-specs/"
    exit 1
  fi
fi

TASK_PROMPTS=$(git diff --cached --name-only | grep -E '^kitty-specs/.+/tasks/' || true)

if [[ -z "$TASK_PROMPTS" ]]; then
  exit 0
fi

echo "📋 Validating task prompt workflow before commit..."

status=0
for prompt in $TASK_PROMPTS; do
  if [[ ! -f "$prompt" ]]; then
    continue
  fi
  if ! grep -Eq '^[[:space:]]*lane:' "$prompt"; then
    echo "❌ ERROR: $prompt missing 'lane' frontmatter field." >&2
    status=1
  fi
  if ! grep -Eq '^[[:space:]]*shell_pid:' "$prompt"; then
    echo "⚠️  WARNING: $prompt missing 'shell_pid' frontmatter field." >&2
  fi
  if ! grep -Eq '^[[:space:]]*agent:' "$prompt"; then
    echo "⚠️  WARNING: $prompt missing 'agent' frontmatter field." >&2
  fi
  if ! grep -Eq '^## Activity Log' "$prompt"; then
    echo "⚠️  WARNING: $prompt missing Activity Log section." >&2
  fi
  current_lane=$(grep -E '^[[:space:]]*lane:' "$prompt" | tail -1 | sed 's/.*"\(.*\)".*/\1/')
  if [[ "$current_lane" == "doing" ]] && ! grep -q 'Started implementation' "$prompt"; then
    echo "⚠️  WARNING: $prompt in doing lane without activity log entry." >&2
  fi
  if [[ "$current_lane" == "for_review" ]] && ! grep -q 'Ready for review' "$prompt"; then
    echo "⚠️  WARNING: $prompt in for_review lane without completion log entry." >&2
  fi
done

if [[ $status -ne 0 ]]; then
  echo "✋ Commit aborted due to errors above." >&2
  exit $status
fi

echo "✅ Task prompt validation passed"
exit 0
