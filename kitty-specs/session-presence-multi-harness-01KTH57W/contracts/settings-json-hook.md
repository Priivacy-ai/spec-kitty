# Contract: Claude Code settings.json Hook Structure

## Purpose

Specifies the exact JSON structure added to `.claude/settings.json` by `ClaudeCodeHookRegistrar.register()`.

## Added Structure

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          { "type": "command", "command": "spec-kitty session-start" }
        ]
      }
    ]
  }
}
```

## Merge Semantics

- The file is read as JSON if it exists; treated as `{}` if absent or malformed.
- `hooks` key is created if absent.
- `hooks.SessionStart` key is created as `[]` if absent.
- The spec-kitty entry object is appended only if no existing list element contains `{"type": "command", "command": "spec-kitty session-start"}` (exact match on these two fields).
- All other keys at any level are left untouched.
- The result is written back atomically (temp file + `os.replace()`).

## Idempotency Check

`is_registered()` returns `True` if `hooks.SessionStart` contains any element whose `hooks` list contains `{"type": "command", "command": "spec-kitty session-start"}`.

## Removal Semantics (`unregister()`)

- Filter out only the spec-kitty entry from the `hooks.SessionStart` list.
- If the list becomes empty, leave `hooks.SessionStart: []` (do not delete the key).
- All other entries and keys are preserved.
- Write back atomically.
