# Contract: `InnerStateChanged` event + reducer fold

## Wire shape (append-only `status.events.jsonl`)

```json
{
  "event_id": "01KX...",          // ULID; deterministic-namespaced for backfill seeds
  "kind": "annotation",           // discriminator; NOT a lane transition
  "wp_id": "WP01",
  "at": "2026-07-19T07:00:00Z",
  "actor": "claude",
  "delta": { "shell_pid": 12345, "shell_pid_created_at": "..." }
}
```

- **No** `from_lane`/`to_lane`. `StatusEvent.from_dict` MUST NOT be used to parse it (it hard-requires
  the lane keys); a distinct decoder handles `kind == "annotation"`.
- `store.is_non_lane_event` MUST classify it so `read_events` **surfaces** it to `reduce()` (today the
  method skips any `event_type`-bearing event — reconcile the discriminator).

## Reducer fold contract

1. Read events; partition into `transition` and `annotation` kinds.
2. Fold all transitions in `(at, event_id)` order — each transition **preserves** the per-WP runtime
   slots it does not set (do NOT rebuild the dict dropping the runtime slots). The **`planned→claimed`
   transition additionally extracts** `shell_pid`/`shell_pid_created_at`/`agent` from its
   `policy_metadata` sidecar into the snapshot slots (FR-004 claim path — the only transition that
   writes a runtime slot).
3. Fold all annotations after transitions, applying `WPInnerStateDelta` per-field merge
   (replace / per-subtask replace / append / union). **Never** increment `force_count`.
4. Complexity: O(events), single pass per partition, no additional full re-reduction (NFR-005).

## Invariants (architectural tests)

- An `InnerStateChanged` event can **never** mutate `lane` (never reduced as a transition).
- No runtime slot is erased by a subsequent lane transition (per-field preservation).
- At an equal `at`, a backfill seed annotation folds **after** the transition it annotates.
