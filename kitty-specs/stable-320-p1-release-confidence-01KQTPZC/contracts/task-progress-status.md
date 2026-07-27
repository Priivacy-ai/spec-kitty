# Contract: Task Progress Status Output

## Human Output

Command:

```bash
spec-kitty agent tasks status --mission <mission>
```

Required behavior:

- Show total WP count.
- Show done count separately from weighted or ready progress.
- Do not show a done-only numerator next to a weighted percentage unless the label states that the percentage is weighted/ready.
- Approved-only boards must communicate readiness without implying that WPs are done.

Accepted examples:

```text
Done: 0/6 (0.0% done)
Ready progress: 80.0% weighted
```

```text
Ready: 6/6 ready (0 done, 80.0% weighted)
```

Rejected example:

```text
Progress: 0/6 (80.0%)
```

## JSON Output

Command:

```bash
spec-kitty agent tasks status --mission <mission> --json
```

Required behavior when JSON output is touched:

- Output must remain valid JSON on stdout.
- The existing mission identity fields must remain present.
- `total_wps` must remain numeric.
- Lane counts must remain machine-readable.
- Any percentage field must have clear semantics through its name or accompanying label.

Recommended additive fields:

```json
{
  "total_wps": 6,
  "done_count": 0,
  "done_percentage": 0.0,
  "weighted_percentage": 80.0,
  "progress_percentage": 80.0,
  "progress_semantics": "weighted_readiness"
}
```

Compatibility rule:

- If `progress_percentage` remains weighted for compatibility, add `progress_semantics` or an equivalent explicit field.
- If `progress_percentage` changes to done-only, document that as a compatibility break and update all call sites/tests touched by this mission.
