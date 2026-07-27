# CLI Contract: spec-kitty review --mission

**Added in**: WP07
**Command**: `spec-kitty review --mission <slug>`

---

## Invocation

```
spec-kitty review --mission <handle>
```

`<handle>` accepts: `mission_id` (ULID), `mid8` (first 8 chars), or `mission_slug`.

---

## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--mission` | str | required | Mission handle (id, mid8, or slug) |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All checks passed; report written with `verdict: pass` or `verdict: pass_with_notes` |
| 1 | One or more WPs not in `done` lane, or hard findings present; `verdict: fail` |
| 2 | Mission not found / ambiguous handle |

---

## Output (stdout)

```
Reviewing mission: <friendly_name> (<mission_slug>)

  ✓  WP lane check: all 7 WPs in done
  ✓  Dead-code scan: 0 unreferenced public symbols
  ✓  BLE001 audit: 0 unjustified suppressions

Verdict: pass
Report written: kitty-specs/<slug>/mission-review-report.md
```

Or on failure:

```
Reviewing mission: <friendly_name> (<mission_slug>)

  ✓  WP lane check: all 7 WPs in done
  ✗  Dead-code scan: 2 unreferenced public symbols
       src/specify_cli/cli/commands/review.py:42  def _unused_helper
       src/specify_cli/cli/commands/review.py:67  def another_dead_fn
  ✓  BLE001 audit: 0 unjustified suppressions

Verdict: fail  (2 findings)
Report written: kitty-specs/<slug>/mission-review-report.md
```

---

## Report File (`mission-review-report.md`)

```markdown
---
verdict: pass
reviewed_at: 2026-04-30T15:00:00+00:00
findings: 0
---

No findings.
```

Or with findings:

```markdown
---
verdict: fail
reviewed_at: 2026-04-30T15:00:00+00:00
findings: 2
---

## Findings

- **dead_code** `src/specify_cli/cli/commands/review.py:42` — `_unused_helper`: no non-test callers found
- **dead_code** `src/specify_cli/cli/commands/review.py:67` — `another_dead_fn`: no non-test callers found
```

---

## move-task Additions (WP02)

### New option on `spec-kitty agent tasks move-task`

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--skip-review-artifact-check` | bool | False | Suppress the rejected-verdict guard when force-approving |

### Guard behaviour

When `--to approved --force` or `--to done --force` is used and the latest
`review-cycle-N.md` for the WP has `verdict: rejected`:

```
Error: WP05 review-cycle-2.md has verdict: rejected.
Update the review artifact or pass --skip-review-artifact-check to suppress.
```

Exit code: 1 (unless `--skip-review-artifact-check` is passed).
