# WP11 review cycle 1 — changes requested

## Verdict

Reject. The reduction and executable gates are green, but causal disposition evidence is not row-valid.

## Independently verified

- Frozen 3,140→2,663 nodes (`-477`); five files retired.
- Focused 2,662 passed, one skipped, eight warnings.
- Fault replay: 13 intended failures, six unaffected controls.
- Ruff/diff clean; no production files changed.

## Blocking findings

1. Sixty-one of 77 YAML rows cite an authority different from the row's causal survivor. Several cross production path, input, and oracle boundaries. Each deletion/material KEEP needs the actual surviving node plus targeted or valid-family proof over identical callable/path, input, oracle, outcome, and platform.
2. All 15 DELETE groups (40 members) have `retained_members: []` in JSON while YAML injects replacements. Make both artifacts agree and validate every survivor exists/collects and every deleted member has one terminal explanation.
3. Persist bounded timeout command/deadline/wall/exit evidence for focused and causal gates.

## Anti-pattern checklist

- No production additions or frozen-surface/ownership violations.
- Migrated live dashboard tests are valid.
- FR causal/deletion evidence completeness: FAIL pending corrections above.
