# Agent Utilities

Python utilities that AI agents can import and call directly, without running CLI commands.

## Quick Status Check

### `show_kanban_status(feature_slug)`

Display a beautiful kanban status board with parallelization analysis.

**Usage:**
```python
from specify_cli.agent_utils.status import show_kanban_status

# Auto-detect feature from current directory
result = show_kanban_status()

# Or specify feature explicitly
result = show_kanban_status("012-documentation-mission")
```

**Why use this instead of CLI command?**
- ✅ **No truncation** - Full output displays inline (CLI gets truncated at ~50 lines)
- ✅ **Direct import** - No need to run `spec-kitty` via Bash tool
- ✅ **Instant output** - Displays immediately in agent's console
- ✅ **Structured data** - Returns dict for programmatic decision-making

**What it displays:**

1. **Feature header** with cyan border
2. **Progress bar** visual (████████░░░) with percentage
3. **Kanban Board Table** showing all WPs in 4 lanes:
   - 📋 Planned
   - 🔄 Doing
   - 👀 For Review
   - ✅ Done
4. **🔀 Parallelization Strategy** - NEW! Shows:
   - Which WPs are ready to start (all dependencies satisfied)
   - Which can run in parallel (no inter-dependencies)
   - Which must run sequentially (depend on each other)
   - Exact `spec-kitty implement` commands with correct `--base` flags
5. **Next Steps** - What's ready for review, in progress, or next up
6. **Summary Panel** - Total WPs, completed %, in progress, planned

**Example Output:**

```
╭──────────────────────────────────────────────────────────────────╮
│ 📊 Work Package Status: 012-documentation-mission                │
╰──────────────────────────────────────────────────────────────────╯
Progress: 8/10 (80.0%)
████████████████████████████████░░░░░░░░

                        Kanban Board
┏━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ 📋 Planned  ┃ 🔄 Doing  ┃ 👀 For Rev  ┃ ✅ Done     ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ WP09        │           │             │ WP01        │
│ Testing     │           │             │ Mission...  │
│ WP10        │           │             │ WP02        │
│ Docs        │           │             │ Core...     │
│             │           │             │ ...         │
│ 2 WPs       │ 0 WPs     │ 0 WPs       │ 8 WPs       │
└─────────────┴───────────┴─────────────┴─────────────┘

🔀 Parallelization Strategy:

  ▶️  Ready to start:
     • WP09 - Testing & Validation
     spec-kitty implement WP09 --base WP08

╭─────────────────── Summary ───────────────────╮
│ Total WPs:    10                              │
│ Completed:    8 (80.0%)                       │
│ In Progress:  0                               │
│ Planned:      2                               │
╰───────────────────────────────────────────────╯
```

**Returns (structured dict):**
```python
{
    'feature': '012-documentation-mission',
    'total_wps': 10,
    'done_count': 8,
    'progress_percentage': 80.0,
    'in_progress': 0,
    'planned_count': 2,
    'by_lane': {'done': 8, 'planned': 2},
    'work_packages': [
        {
            'id': 'WP01',
            'title': 'Mission Infrastructure',
            'lane': 'done',
            'phase': 'Phase 0 - Foundation',
            'dependencies': []
        },
        # ... more WPs
    ],
    'parallelization': {
        'ready_wps': [
            {
                'id': 'WP09',
                'title': 'Testing & Validation',
                'lane': 'planned',
                'dependencies': ['WP01', 'WP02', ..., 'WP08']
            }
        ],
        'can_parallelize': False,  # True if multiple WPs can run simultaneously
        'parallel_groups': [
            {
                'type': 'single',  # 'parallel' | 'single' | 'sequential'
                'wps': [...],
                'note': 'Ready to start'
            }
        ]
    }
}
```

**Use Cases:**

1. **Check status before starting work:**
   ```python
   result = show_kanban_status("012-documentation-mission")
   if result['parallelization']['ready_wps']:
       print(f"✅ Can start {result['parallelization']['ready_wps'][0]['id']}")
   ```

2. **Find parallelization opportunities:**
   ```python
   result = show_kanban_status()
   if result['parallelization']['can_parallelize']:
       parallel_wps = [g for g in result['parallelization']['parallel_groups']
                      if g['type'] == 'parallel'][0]
       print(f"🚀 Can run {len(parallel_wps['wps'])} WPs in parallel!")
   ```

3. **Track progress:**
   ```python
   result = show_kanban_status()
   print(f"Progress: {result['progress_percentage']}%")
   print(f"Remaining: {result['planned_count'] + result['in_progress']} WPs")
   ```

## When to Use Agent Utilities

**Always prefer Python functions over CLI commands when:**
- Output might be truncated (>50 lines)
- You need structured data for decision-making
- You want instant inline display
- You're working programmatically

**Use CLI commands when:**
- Running from terminal manually
- Output is short and won't truncate
- You need the command for documentation/user instructions
