# Contract: charter list

**Command**: `spec-kitty charter list [--show-available]`

## Synopsis

Displays the project's current activation state, grouped by artifact kind. With `--show-available`, shows both activated artifacts and all available artifacts from doctrine side-by-side.

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--show-available` | flag | No | Also show all doctrine-available artifacts for each kind |

## Behavior

1. Read current activation state from `.kittify/config.yaml` via `PackContext.from_config()`.
2. For each of the 9 activatable kinds:
   - If the kind key is absent from config.yaml: display "All built-ins (default)" — no explicit activation set.
   - If the kind key is present and non-empty: display the activated IDs.
   - If the kind key is present and empty: display "Nothing activated (explicit restriction)".
3. If `--show-available`: also query the doctrine catalog for each kind and display available (but not activated) artifacts indented below the activated section.
4. Output as a structured Rich table or panel — one section per kind.

## Output (human-readable, without --show-available)

```
Charter Activation State
━━━━━━━━━━━━━━━━━━━━━━━━━━
mission-type          software-dev, research
directive             python-style-guide, clean-code
tactic                (All built-ins — no explicit activation)
styleguide            (All built-ins — no explicit activation)
toolguide             (All built-ins — no explicit activation)
paradigm              domain-driven-design
procedure             (All built-ins — no explicit activation)
agent-profile         python-pedro, reviewer-renata
mission-step-contract (All built-ins — no explicit activation)
```

## Output (with --show-available)

```
Charter Activation State (+ Available)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
directive
  ✓ python-style-guide    [activated]
  ✓ clean-code            [activated]
  ○ java-style-guide      [available, not activated]
  ○ go-style-guide        [available, not activated]
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | config.yaml read error or doctrine unavailable |
