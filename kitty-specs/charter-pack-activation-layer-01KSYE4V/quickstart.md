# Quickstart: Charter Pack Activation Layer

**Mission**: charter-pack-activation-layer-01KSYE4V

---

## Scenario 1: New project — spec-kitty upgrade writes the default charter pack

```bash
# User runs upgrade on a fresh project (no .kittify/charter/charter.md)
spec-kitty upgrade

# Output:
# ✓ Migration m_3_2_8_default_charter_pack applied
#   Default charter pack written to config.yaml.
#   All built-in artifacts activated across all 9 kinds.
#   Run 'spec-kitty charter list' to see what was activated.

spec-kitty charter list
# Shows: all 9 kinds → "All built-ins activated"
```

All prior behavior is preserved. No artifact access changes for existing workflows.

---

## Scenario 2: Existing project with charter — upgrade backs up and merges defaults

```bash
spec-kitty upgrade

# Output:
# ✓ Migration m_3_2_8_default_charter_pack applied
#   Existing charter backed up to .kittify/charter/backups/charter-2026-05-31T08-29-15.md
#   Default pack merged into config.yaml.
# ⚠ REVIEW RECOMMENDED:
#   Your existing charter has been updated with default pack values.
#   Review the merged charter before continuing:
#     spec-kitty charter list
#     spec-kitty charter pack consistency-check
#   The backup is at: .kittify/charter/backups/charter-2026-05-31T08-29-15.md
```

---

## Scenario 3: Activate a mission type (no cascade)

```bash
spec-kitty charter activate mission-type software-dev

# Output:
# Activated: mission-type/software-dev
# Cross-references not cascaded (use --cascade to include):
#   - directive/clean-code (referenced by software-dev profile)
#   - tactic/test-driven-development
# Hint: spec-kitty charter activate mission-type software-dev --cascade all
```

---

## Scenario 4: Deactivate with cascade — see shared vs exclusive artifacts

```bash
spec-kitty charter deactivate directive python-style-guide --cascade tactics

# Output:
# Deactivated: directive/python-style-guide
# Cascade-deactivated (tactics): clean-arch
# Shared (skipped — still referenced by directive/clean-code):
#   tactic/test-driven-development
```

`test-driven-development` is also referenced by `directive/clean-code` (another activated directive), so it is protected. Only `clean-arch` was exclusively referenced by `python-style-guide`.

---

## Scenario 5: List activated artifacts

```bash
spec-kitty charter list

# Shows current activation state per kind (9 kinds).
# Kinds with no explicit activation show "All built-ins (default)".

spec-kitty charter list --show-available

# Shows activated + all available from doctrine side-by-side.
```

---

## Scenario 6: Charter pack consistency check

```bash
spec-kitty charter pack consistency-check

# If coherent:
# ✓ COHERENT — All activated artifacts are present in doctrine.

# If not coherent (e.g., after removing a doctrine artifact):
# ✗ INCOHERENT
# Issues:
#   directive/old-guide — not found in doctrine
#   → Run: spec-kitty charter deactivate directive old-guide
```

---

## Scenario 7: WP finalize-tasks hard fails — assigned profile not in activated set

```bash
spec-kitty agent mission finalize-tasks --mission my-feature

# Error output:
# ✗ Charter activation gate FAILED
#   WP03 assigns profile: java-developer
#   java-developer is not in the activated agent-profile set.
#   Currently activated: python-pedro, reviewer-renata
#
#   Resolution:
#     spec-kitty charter activate agent-profile java-developer
#   Then re-run finalize-tasks.
```

---

## Scenario 8: WP start hard fails — assigned profile not in activated set

```bash
spec-kitty agent action implement WP03 --agent claude:sonnet

# Error output:
# ✗ WP03 charter precondition FAILED
#   Assigned profile 'java-developer' is not accessible through the active charter.
#   Run: spec-kitty charter activate agent-profile java-developer
```

---

## Scenario 9: Review prompt resolution — non-activated tactic hard fails

```bash
# During review prompt rendering, a tactic not in the activated set is referenced
# Error output:
# ✗ Charter activation hard fail
#   Tactic 'dependency-injection' is not in the activated charter set.
#   Charter has explicit tactic activations: [test-driven-development, clean-arch]
#
#   Resolution:
#     spec-kitty charter activate tactic dependency-injection
#   Or to check all activated artifacts:
#     spec-kitty charter list
```
