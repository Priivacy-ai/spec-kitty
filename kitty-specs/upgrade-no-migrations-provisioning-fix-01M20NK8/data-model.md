# Data Model — the provisioning-decision state

This mission changes one decision's shape, not a persisted schema. The "entity" is the in-memory provisioning decision flowing through assessment → finalize.

## Entity: ProvisioningDecision (derived at assessment time)

| Field | Source | Meaning |
|-------|--------|---------|
| `authority_present` | `write.before_bytes is not None and not write.absent_parents` | Whether a config authority exists to provision into |
| `descriptor` | `prepare_mission_type_activations(root)` → **Optional** | The canonical write; **None** when `authority_present` is false (the mission's change) |
| `diagnostic` | new | `deferred_provisioning` (non-error) when descriptor is None; absent otherwise |
| `complete` | `assessment.py:65` | Must stay true on the absent path (non-error diagnostic does not poison it) |

## State transitions (the provisioning arm of `upgrade`)

```
                 authority present
   assessment ───────────────────────► descriptor kept ──► finalizer apply (in-place UPDATE) ──► complete
       │                                                         (recheck validates inode-preserving update)
       │ authority ABSENT (before_bytes is None / absent_parents)
       ▼
   descriptor = None + deferred_provisioning diagnostic ──► finalizer: nothing to apply (NO create) ──► complete
```

## Invariants

- **INV-1 (C-001)**: when `descriptor is None`, the finalizer performs **no** create and **no** parent-dir creation — create-from-absent is #4047.
- **INV-2 (A2)**: the absent-path diagnostic severity is non-error; `complete` stays true; the outcome is not `failed`.
- **INV-3 (NFR-003)**: when `authority_present`, the apply path and emitted outcome are byte-for-byte unchanged vs pre-mission behavior.
- **INV-4 (non-vacuity, DIRECTIVE_043)**: the reduced installer guard still raises on a malformed/non-canonical descriptor (a self-mutation/negative test proves the raise arm is live).
