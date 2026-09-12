# Quickstart: Verifying the Missing-Charter Advisory Fix

Manual verification walkthrough for canonical missing-charter advisory mode and its two warning presentations. Display-only `charter.md` may change warning copy but never pass/block behavior.

## Scenario 1 — Fully absent charter (Story 1)

```bash
mkdir -p /tmp/spec-kitty-fresh-check && cd /tmp/spec-kitty-fresh-check
git init -q
spec-kitty init --ai claude --here    # or equivalent minimal .kittify/ scaffold, no charter/ contents
rm -rf .kittify/charter .kittify/doctrine
spec-kitty next --json                 # expect: no exit 1, JSON reports success (or the next actionable step), NOT a charter blocked_reason
```

Expected: command proceeds past charter preflight; if run with verbose/log output, the fresh-project warning is visible.

## Scenario 2 — Legacy charter.md-only bundle (Story 2)

```bash
mkdir -p /tmp/spec-kitty-legacy-check/.kittify/charter && cd /tmp/spec-kitty-legacy-check
git init -q
spec-kitty init --ai claude --here
rm -f .kittify/charter/charter.yaml
echo "# Legacy charter prose" > .kittify/charter/charter.md
rm -rf .kittify/doctrine
spec-kitty next --json                 # expect: no exit 1
```

Expected: command proceeds; stderr warning is visibly different from Scenario 1, names the legacy `charter.md` bundle, and points to the executable migration path: `spec-kitty charter generate --no-from-interview`.

## Scenario 3 — Regression guard (Story 3)

```bash
cd /tmp/spec-kitty-legacy-check
echo "not: valid: yaml: [" > .kittify/charter/charter.yaml
spec-kitty next --json                 # expect: exit 1, blocked_reason mentions invalid charter.yaml
```

Expected: still blocks exactly as before this mission even though `charter.md` remains present. This proves prose presence cannot exempt invalid canonical state.

## Cleanup

```bash
rm -rf /tmp/spec-kitty-fresh-check /tmp/spec-kitty-legacy-check
```
