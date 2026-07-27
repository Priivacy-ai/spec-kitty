# Contract: Strict JSON Envelope for `--json` Commands

**Issue**: #842
**FRs**: FR-003, FR-004 · **NFR**: NFR-001 · **SC**: SC-002

## Contract

For every `--json` command in the covered set:

- **stdout**: a single top-level JSON object. `json.loads(stdout)` MUST succeed without preprocessing.
- **stderr**: free-form text; receives all sync, auth, tracker, and other diagnostic output by default.
- **exit code**: as today (success / non-zero error).

The contract holds **regardless of SaaS state**:

| SaaS state | Trigger | stdout requirement |
|---|---|---|
| `disabled` | `SPEC_KITTY_ENABLE_SAAS_SYNC` unset / 0 | Strict JSON. |
| `unauthorized` | SaaS reachable, no valid auth | Strict JSON. Diagnostic on stderr. |
| `network-failed` | SaaS unreachable | Strict JSON. Diagnostic on stderr. |
| `authorized-success` | SaaS reachable, authorized | Strict JSON. No diagnostic required. |

## Rules for diagnostics

1. **Default**: route all diagnostic prints (sync attempts, auth failures, network errors, tracker noise) to **stderr**.
2. **In-envelope diagnostics** are permitted ONLY when the consumer needs to programmatically observe the diagnostic. They go under a documented top-level key, proposed:

   ```json
   {
     "result": "success",
     "...": "...",
     "diagnostics": {
       "sync": { "status": "skipped", "reason": "not_authenticated" }
     }
   }
   ```

3. **Forbidden**: bare diagnostic lines on stdout outside the JSON object. This includes lines such as `Not authenticated, skipping sync` — these MUST NOT precede or follow the JSON envelope on stdout.

## Covered commands

The contract surface is defined as: every `--json` command exercised by the strict-JSON parametrised integration test (Assumption A3). At minimum the test includes:

- `spec-kitty agent mission create --json`
- `spec-kitty agent mission setup-plan --json`
- `spec-kitty agent mission branch-context --json`
- `spec-kitty agent context resolve --json`
- `spec-kitty charter context --action <action> --json`
- `spec-kitty agent decision open|resolve|defer|cancel|verify --json`
- `spec-kitty agent action implement --json` (when `--json` is supported)
- Any other CLI surface that accepts `--json` and is exercised in the test matrix

Adding a new `--json` flag to a command outside this set requires extending the test matrix in the same change.

## Test matrix (NFR-001)

For each covered command × each of the four SaaS states:

```python
def test_strict_json(command, saas_state):
    set_saas_state(saas_state)
    result = run_cli([*command, "--json"])
    parsed = json.loads(result.stdout)            # MUST succeed
    assert isinstance(parsed, dict)               # top-level object
    # Diagnostics, if any, live in parsed["diagnostics"] or on stderr.
    assert "Not authenticated" not in result.stdout
```

A bare-string scan on `stdout` for any text outside the JSON envelope is sufficient to detect the original bug class.

## Versioning note

This contract is **additive-only** — new top-level keys MAY be added to the envelope but existing consumers MUST continue to parse successfully. If a future change renames a key, that requires a deprecation window, not in scope here.
