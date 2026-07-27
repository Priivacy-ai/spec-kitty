# Quickstart: Verifying the Synthesized DRG Stale-Refresh Fix

**Mission:** `synthesized-drg-stale-refresh-01KXN8KZ` · Fixes [#2681](https://github.com/Priivacy-ai/spec-kitty/issues/2681)

This walkthrough reproduces the #2681 deadlock on pre-fix code, then verifies
the fix clears it for **both** remediation entry points. Intended for a
developer validating this mission's WPs, or an operator confirming an
upgraded CLI actually fixes their stuck project.

## Prerequisites

A project with a synthesized (non-built-in) charter DRG — `.kittify/charter/`
contains `governance.yaml`, `directives.yaml`, `references.yaml`,
`metadata.yaml`, and `synthesis-manifest.yaml`, and `.kittify/doctrine/`
contains `graph.yaml` plus at least one synthesized artifact.

## Part A — Reproduce #2681 (pre-fix behavior)

1. Synthesize once from a clean project:
   ```bash
   spec-kitty charter synthesize
   spec-kitty charter status --json | jq .freshness.synthesized_drg
   # → {"state": "fresh", ...}
   ```
2. Re-run synthesize with no content changes (the #1912/#1913 no-op-stable
   guarantee — `created_at` in `synthesis-manifest.yaml` is NOT rewritten):
   ```bash
   spec-kitty charter synthesize
   git status --porcelain   # must be empty
   ```
3. Perform a git operation that advances the bundle's mtime without changing
   content (a `touch` on the bundle files stands in for clone/checkout/
   rebase in this walkthrough):
   ```bash
   touch .kittify/charter/references.yaml
   spec-kitty charter status --json | jq .freshness.synthesized_drg
   # Pre-fix: → {"state": "stale", "remediation": "spec-kitty charter synthesize"}
   ```
4. Attempt remediation via `synthesize` (pre-fix: reports success, does NOT
   clear the state — the no-op-stable skip means `created_at` stays frozen,
   so the mtime comparison still trips):
   ```bash
   spec-kitty charter synthesize
   spec-kitty charter status --json | jq .freshness.synthesized_drg.state
   # Pre-fix: still "stale"
   ```
5. Attempt remediation via `resynthesize` (pre-fix: same outcome — the
   deadlock the #2681 reporter hit):
   ```bash
   spec-kitty charter resynthesize --topic <any-known-topic>
   spec-kitty charter status --json | jq .freshness.synthesized_drg.state
   # Pre-fix: still "stale"
   ```
6. `implement` is blocked:
   ```bash
   spec-kitty agent action implement WP01
   # Pre-fix: Error: synthesized_drg stale
   ```

## Part B — Apply the fix, verify `fresh` + `implement` unblocked

With this mission's fix applied, repeat steps 1-3 above (synthesize once,
no-op re-run stays clean, then advance a bundle mtime with no content
change):

```bash
spec-kitty charter status --json | jq .freshness.synthesized_drg.state
# Post-fix: → "fresh"  (content hash unchanged → mtime bump is irrelevant)
```

`implement` proceeds without needing any remediation step at all, because a
pure mtime perturbation with unchanged content never reports `stale` in the
first place (AS-1):

```bash
spec-kitty agent action implement WP01   # no error
```

## Part C — Genuine staleness still detected and clearable (AS-2/AS-3)

1. Edit doctrine content the DRG was built from (e.g. append a line to
   `.kittify/charter/directives.yaml` — simulating an upstream doctrine
   change synced in):
   ```bash
   echo "# drift marker" >> .kittify/charter/directives.yaml
   spec-kitty charter status --json | jq .freshness.synthesized_drg.state
   # → "stale"  (content hash genuinely changed)
   ```
2. Clear it via `synthesize`:
   ```bash
   spec-kitty charter synthesize
   spec-kitty charter status --json | jq .freshness.synthesized_drg.state
   # → "fresh"
   ```
3. Repeat with `resynthesize` on a fresh drift (both remediation paths must
   independently clear genuine staleness — FR-003):
   ```bash
   echo "# drift marker 2" >> .kittify/charter/directives.yaml
   spec-kitty charter resynthesize --topic <any-known-topic>
   spec-kitty charter status --json | jq .freshness.synthesized_drg.state
   # → "fresh"
   ```

## Part D — Pre-fix manifest self-heals in one remediation run

Simulates an operator upgrading the CLI on a project that is already stuck
`stale` from before the fix (the spec's "Pre-fix / already-deadlocked
manifest" edge case):

1. Hand-craft (or use a fixture from before this mission) a
   `synthesis-manifest.yaml` with `schema_version: '2'` and no
   `bundle_content_hash` key.
2. `spec-kitty charter status --json` reports `stale` (the field is absent →
   "cannot prove freshness").
3. Run the prescribed remediation **once**:
   ```bash
   spec-kitty charter synthesize   # or: spec-kitty charter resynthesize --topic ...
   ```
4. Check again — `fresh`, with no second `stale` bounce and no manual edit
   to any file:
   ```bash
   spec-kitty charter status --json | jq .freshness.synthesized_drg.state
   # → "fresh"
   ```

## Part E — Unaffected states (regression pins)

```bash
# built_in_only project — unchanged before/after this mission (FR-004/C-002)
spec-kitty charter status --json | jq .freshness.synthesized_drg
# → {"state": "built_in_only", "remediation": null}

# missing graph.yaml, no built_in_only opt-in — unchanged (FR-006)
rm .kittify/doctrine/graph.yaml
spec-kitty charter status --json | jq .freshness.synthesized_drg
# → {"state": "missing", "remediation": "spec-kitty charter synthesize"}
```

## Part F — No-op-stability still holds (C-001/NFR-001)

```bash
spec-kitty charter synthesize     # baseline
git add -A && git commit -m "baseline"
spec-kitty charter synthesize     # re-run, no content changes
git status --porcelain            # must be empty — this is the guarantee
                                   # #1912/#1913 introduced and this mission
                                   # must not weaken
```
