#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 TASK_ID FEATURE_DIR [AGENT]" >&2
  exit 1
fi

TASK_ID="$1"
FEATURE_DIR="$2"
FEATURE_DIR="${FEATURE_DIR%/}"
AGENT="${3:-unknown}"

if [[ ! -d "$FEATURE_DIR" ]]; then
  echo "❌ ERROR: Feature directory not found: $FEATURE_DIR" >&2
  exit 1
fi

PLANNED_PROMPT=$(find "$FEATURE_DIR/tasks/planned" -maxdepth 3 -name "${TASK_ID}-*.md" -print -quit | tr -d '\r')
if [[ -z "$PLANNED_PROMPT" ]]; then
  echo "❌ ERROR: Task $TASK_ID not found in tasks/planned/." >&2
  exit 1
fi

PHASE_DIR=$(dirname "$PLANNED_PROMPT" | xargs basename)
FILENAME=$(basename "$PLANNED_PROMPT")
DOING_DIR="$FEATURE_DIR/tasks/doing/$PHASE_DIR"
DOING_PROMPT="$DOING_DIR/$FILENAME"

mkdir -p "$DOING_DIR"

SHELL_PID=$$
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Move prompt using git to preserve history
if command -v git >/dev/null 2>&1; then
  git mv "$PLANNED_PROMPT" "$DOING_PROMPT"
else
  mv "$PLANNED_PROMPT" "$DOING_PROMPT"
fi

python3 - "$DOING_PROMPT" "$SHELL_PID" "$AGENT" "$TIMESTAMP" <<'PY'
import sys
from pathlib import Path

prompt_path = Path(sys.argv[1])
shell_pid = sys.argv[2]
agent = sys.argv[3]
timestamp = sys.argv[4]
text = prompt_path.read_text()
lines = text.splitlines()
if not lines or lines[0].strip() != '---':
    sys.exit('Prompt missing frontmatter header')

# locate end of frontmatter
end_idx = None
for idx in range(1, len(lines)):
    if lines[idx].strip() == '---':
        end_idx = idx
        break
if end_idx is None:
    sys.exit('Prompt frontmatter not terminated with ---')

front = lines[1:end_idx]
body = lines[end_idx+1:]

def replace_or_insert(key, value, comment=''):
    key_prefix = f'{key}:'
    for i, line in enumerate(front):
        if line.strip().startswith(key_prefix):
            suffix = ''
            parts = line.split('#', 1)
            if len(parts) == 2:
                suffix = '  #' + parts[1]
            front[i] = f'{key_prefix} "{value}"{suffix}'
            return
    insert_line = f'{key_prefix} "{value}"'
    if comment:
        insert_line += f'  # {comment}'
    front.append(insert_line)

replace_or_insert('lane', 'doing')
replace_or_insert('agent', agent)
replace_or_insert('shell_pid', shell_pid)

# Rebuild document
new_lines = ['---'] + front + ['---'] + body
text = '\n'.join(new_lines)
if not text.endswith('\n'):
    text += '\n'

# Append activity log entry under Activity Log section
needle = '## Activity Log'
if needle in text:
    segments = text.split(needle, 1)
    head = segments[0] + needle
    rest = segments[1]
    head += '\n\n'
    entry = f'- {timestamp} – {agent} – shell_pid={shell_pid} – lane=doing – Started implementation\n\n'
    text = head + entry + rest.lstrip('\n')
else:
    text += f"\n- {timestamp} – {agent} – shell_pid={shell_pid} – lane=doing – Started implementation\n"

prompt_path.write_text(text)
PY

echo "✅ Moved $TASK_ID to doing lane"
echo "   Location: $DOING_PROMPT"
echo "   Shell PID: $SHELL_PID"
echo "   Agent: $AGENT"
echo "   Timestamp: $TIMESTAMP"
echo ""
echo "Next: Implement the task following the prompt guidance"
