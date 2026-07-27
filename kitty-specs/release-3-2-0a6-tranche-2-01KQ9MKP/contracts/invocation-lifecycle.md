# Contract: Profile-Invocation Lifecycle Records

**Issue**: #843
**FRs**: FR-011, FR-012 · **NFR**: NFR-006 · **SC**: SC-005

## Contract

When `spec-kitty next --agent <name>` issues a public action:

1. A `started` profile-invocation lifecycle record is written to the existing local invocation store **before** the action is exposed to the calling agent.
2. When the same action subsequently advances to success or explicit failure, a paired `completed` (or `failed`) record is written.
3. Both records share the same canonical action identifier — derived from the mission step/action that `next` actually issued.

## Record shape

```json
{
  "canonical_action_id": "<mission_step>::<action>",
  "phase": "started" | "completed" | "failed",
  "at": "<ISO-8601 UTC>",
  "agent": "<tool key, e.g. \"claude\">",
  "mission_id": "<ULID>",
  "wp_id": "<WPNN>" | null,
  "reason": "<text>" | null
}
```

- `canonical_action_id`: required. Same value on `started` and its pair.
- `phase`: required. One of `started`, `completed`, `failed`.
- `at`: required. UTC timestamp.
- `agent`: required. The tool key passed via `--agent`.
- `mission_id`: required. ULID for the mission `next` was driving.
- `wp_id`: optional; populated when the action targets a specific work package.
- `reason`: optional; populated for `failed`.

## Pairing rule

```
For each canonical_action_id seen in the local store:
  group_phases = sorted list of phases for that id
  expected: ["started"] or ["started", "completed"] or ["started", "failed"]
  any other shape is a defect (orphans, doubles, missing started)
```

## Orphan behavior

- A `started` without a pair is **not** silently overwritten by a subsequent `started` for the same `canonical_action_id`.
- The doctor surface (existing) lists orphan `started` records. This makes mid-cycle agent crashes observable rather than silently lost.

## Test matrix

| Test | Asserts |
|---|---|
| `next` issues action `<step>::implement` | `started` record present with `canonical_action_id = "<step>::implement"`. |
| Action advances on success | Paired `completed` with same `canonical_action_id`. |
| Action explicitly fails | Paired `failed` with same `canonical_action_id` and non-null `reason`. |
| Mid-cycle crash (agent stops between started and completed) | Orphan `started` is listed by doctor; subsequent `next` does not overwrite it. |
| 5+ issued actions in a session | ≥ 95% pairing rate (NFR-006). |

## Out of scope

- SaaS-side records / sync of these lifecycle records — local-first; SaaS sync is independent and governed by `SPEC_KITTY_ENABLE_SAAS_SYNC`.
- Schema migration for pre-existing local records (this is a new pair-aware shape; old single-shot records, if any, are tolerated by the doctor surface during a deprecation window).
