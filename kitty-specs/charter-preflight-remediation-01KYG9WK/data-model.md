# Data Model: Charter Preflight Remediation Authority

**Mission**: `charter-preflight-remediation-01KYG9WK` · **Date**: 2026-07-27

This mission adds no persistent storage. The entities below are in-memory shapes and the
filesystem artifacts they resolve against.

---

## Existing entities (constrained, not redefined)

### `FreshnessSubState`

`src/specify_cli/charter_runtime/freshness/computer.py:131-139`

| Field | Type | Role in this mission |
|---|---|---|
| `state` | `str` | `missing` \| `invalid` \| `fresh` \| `stale` \| `built_in_only`. FR-005's absent-vs-unusable distinction may already live here (`missing` vs `invalid`) — IC-05 verifies before adding anything. |
| `last_change` | `str \| None` | Untouched. |
| `remediation` | `str \| None` | **The entity this mission governs.** Its defining property — executing it changes the emitting check's state — is currently unenforced. |
| `detail` | `str \| None` | Carries the human explanation (e.g. *"charter.yaml exists but cannot be parsed"*). |

**Invariant introduced (FR-001)**: for any check whose `state` is non-passing, either
`remediation` is a command whose execution changes that check's `state`, or `remediation` is `None`
**and** the check is a member of the exemption set.

### `PreflightCheck`

`src/specify_cli/charter_runtime/preflight/result.py:54-62` — `remediation: str | None`, documented
as *"Exact recovery command, or `None` when no action is…"*. The docstring already asserts the
contract this mission makes enforceable.

**Invariant introduced (FR-003, R-006)**: the invariant binds the operator-visible composed output,
not only this field. A `None` here must not become a command downstream.

---

## New entity

### Remediation exemption set

The explicit, enumerable set of checks that legitimately have no self-service remediation.

| Property | Value |
|---|---|
| Membership | Declared explicitly per check — never inferred from a `None` remediation |
| Size | Pinned as a concrete count (NFR-001) |
| Effect on enforcement | Members are excluded from the effectiveness assertion and **only** them |
| Effect on operator output | Members produce output containing no command (IC-03) |

**Why pinned**: without a pinned size, a check failing the effectiveness assertion could be moved
into the set to make the enforcement pass — shrinking coverage silently. Pinning makes
reclassification turn the enforcement red, which is exactly the spec's US1 Acceptance Scenario 3.

---

## Filesystem artifacts

| Artifact | Path | Status |
|---|---|---|
| `charter.yaml` | `.kittify/charter/charter.yaml` | **Authoritative resolving source** post-inversion (R-001). Tracked/authored, not derived. The sole content-hash input. |
| `charter.md` | `.kittify/charter/charter.md` | Tracked/authored. Still a manifest member, but **not** the resolving source. Read by the diverged diagnostics. |
| Legacy four-file bundle | `.kittify/charter/{directives,governance,metadata,references}.yaml` | Pre-#2773 shape. Its presence with no `charter.yaml` is the mission's trigger state. |

Per `src/charter/bundle.py:128-132`: `tracked_files = [CHARTER_MD, CHARTER_YAML]`,
`derived_files = []`, `content_hash_files = [CHARTER_YAML]`. No artifact moves or is renamed (C-003).

---

## Fixture shapes (the NFR-003 / SC-004 evaluation matrix)

| # | Shape | Expected treatment |
|---|---|---|
| F1 | No charter at all (never initialised) | Advisory, non-blocking — **must not change** (FR-006) |
| F2 | Legacy bundle, no `charter.yaml` | Blocking, with an **effective** remediation (the P0 fix) |
| F3 | `charter.yaml` present and valid | Passing |
| F4 | `charter.yaml` present, unparseable | Blocking, distinguishable from F1 (FR-005) |

**Invariant (NFR-003)**: the count of blocking shapes after the change is same-or-lower than before,
never higher. Today F2 and F4 block; F1 and F3 do not.

---

## State transitions

The mission changes no state machine. It constrains the **exit edge** from every non-passing state:

```
non-passing state ──emits remediation──> operator executes it ──> state MUST change
                  └─emits nothing──────> check MUST be in the exemption set
```

The defect is that this edge is currently unenforced in both directions: BC-2 takes the upper path
with a command that cannot change the state, and R-006 shows the lower path is unreachable because
the runner backfills a command.
