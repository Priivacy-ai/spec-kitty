# Contract: Synthesizer Hook

**Status**: pinned for this tranche.
**Source of truth**: `specify_cli.doctrine.synthesizer` (new subpackage).
**Caller**: `specify_cli.cli.commands.agent_retrospect` (`spec-kitty agent retrospect synthesize`).

The synthesizer is the **only** path that mutates project-local doctrine, DRG, or glossary state from a retrospective finding. It does not auto-run. (FR-021.)

---

## Public API

```python
# specify_cli.doctrine.synthesizer

def apply_proposals(
    *,
    mission_id: MissionId,
    repo_root: Path,
    proposals: list[Proposal],
    approved_proposal_ids: set[ProposalId],
    actor: ActorRef,
    dry_run: bool = True,
) -> SynthesisResult: ...
```

### Inputs

| Argument | Type | Notes |
|---|---|---|
| `mission_id` | `MissionId` | Source mission for provenance. |
| `repo_root` | `Path` | Project root; doctrine/DRG/glossary mutations are scoped to project-local state under this root. |
| `proposals` | `list[Proposal]` | Full proposal list from the source retrospective record. |
| `approved_proposal_ids` | `set[ProposalId]` | Subset to attempt to apply. `flag_not_helpful` proposals are auto-included even if absent from this set. |
| `actor` | `ActorRef` | Who approved the application. Recorded in provenance. |
| `dry_run` | `bool` | Default `True`. When `True`, the synthesizer plans application, runs conflict detection, and returns a result without mutating any file. When `False`, application is performed. |

### Output

```python
class SynthesisResult(BaseModel):
    dry_run: bool
    planned: list[PlannedApplication]      # always populated
    applied: list[AppliedChange]           # populated only when dry_run is False
    conflicts: list[ConflictGroup]         # may be non-empty in either mode
    rejected: list[RejectedProposal]       # apply-time rejections (stale evidence, invalid payload)
    events_emitted: list[EventId]          # the EventIds of `retrospective.proposal.{applied,rejected}` events written
```

```python
class PlannedApplication(BaseModel):
    proposal_id: ProposalId
    kind: str                              # proposal kind
    targets: list[str]                     # URNs that will be created or modified
    diff_preview: str                      # short human-readable description; used by --dry-run report

class AppliedChange(BaseModel):
    proposal_id: ProposalId
    target_urn: str
    artifact_path: str                     # path on disk that was modified
    provenance_path: str                   # path to provenance metadata sidecar (FR-022)

class ConflictGroup(BaseModel):
    proposal_ids: list[ProposalId]
    reason: str                            # describes the conflict (per R-006 predicates)

class RejectedProposal(BaseModel):
    proposal_id: ProposalId
    reason: Literal["conflict", "stale_evidence", "invalid_payload"]
    detail: str
```

---

## Behavior

### 1. Conflict detection (always runs, even in `dry_run`)

The synthesizer applies the conflict predicates from `research.md` R-006 across the **set of approved proposals** plus any `flag_not_helpful` proposals. If any conflict is found:

- The entire batch fails closed. (FR-023.)
- `SynthesisResult.conflicts` enumerates the conflict groups.
- `SynthesisResult.applied` is empty even if `dry_run is False`.
- The synthesizer emits one `retrospective.proposal.rejected` event per proposal in a conflict group, with `reason: conflict`.

### 2. Staleness check (always runs)

For every approved proposal, the synthesizer verifies that the `evidence_event_ids` referenced by the proposal's provenance still exist in the source mission's event log. If any referenced event id is unreachable, the proposal is rejected with `reason: stale_evidence`. The proposal stays in `state.status == "accepted"`; only the apply attempt is recorded.

### 3. Apply order (when `dry_run is False`)

After conflict + staleness checks pass:

1. Group proposals by target surface (doctrine, DRG, glossary).
2. Within each group, apply in a deterministic order (sorted by `proposal_id`).
3. After each apply, write a provenance metadata sidecar (see "Provenance" below).
4. Emit a `retrospective.proposal.applied` event.
5. If a single proposal's apply itself fails (e.g., file write error), the synthesizer halts the remaining batch, records the failure as `RejectedProposal(reason="invalid_payload", detail=...)`, and returns. Already-applied changes are **not** rolled back; the synthesizer is forward-only and designed to be idempotent on retry. (See "Idempotency" below.)

### 4. Idempotency

Re-running the synthesizer with the same approved proposal ids on the same project state MUST be safe. The synthesizer detects "already applied" by inspecting provenance sidecars: if a sidecar with `(source_mission_id, proposal_id)` already exists at the target artifact, the synthesizer treats the proposal as already-applied, emits no new event, and reports it under `applied` with a `re_applied: true` marker (see provenance below).

### 5. `flag_not_helpful` auto-application

`flag_not_helpful` proposals are auto-applicable. They are processed in the same batch as approved proposals, but they do NOT require explicit `approved_proposal_ids` membership. They still:

- run through conflict detection (none currently conflict; reserved for future);
- run through staleness check;
- write provenance;
- emit `retrospective.proposal.applied`.

### 6. What the synthesizer does **not** do

- It does not change runtime behavior at apply time. Applying a `flag_not_helpful` annotates a doctrine artifact with a "flagged" provenance entry; it does not unilaterally remove the artifact. (Removal would be a separate `remove_edge` proposal.)
- It does not introduce prompt-builder filtering. (C-011.)
- It does not modify any artifact outside the project's local scope (`src/doctrine/graph.yaml`, project-local graph overlays, project-local glossary state under `.kittify/`). It does **not** modify the global, packaged DRG/glossary that ships with `spec-kitty`.

---

## Provenance (FR-022, NFR-006)

For every applied change, the synthesizer writes a sidecar provenance record colocated with the target artifact's storage:

```yaml
# in .kittify/<surface>/.provenance/<artifact-id>.yaml (or analogous per surface)
artifact_id: <artifact-id>
source: retrospective
source_mission_id: 01KQ6YEGT4YBZ3GZF7X680KQ3V
source_proposal_id: 01KQ6YE...P1
source_evidence_event_ids: [01KQ6YE...A, 01KQ6YE...B]
applied_by:
  kind: human
  id: rob@robshouse.net
  profile_id: null
applied_at: 2026-04-27T11:30:00+00:00
re_applied: false
```

Reversibility (C-012): the provenance sidecar contains enough context to roll back via the inverse proposal (`add_edge` ↔ `remove_edge`, etc.). Rollback is a future operator action, not part of this tranche; the contract here ensures the data needed for rollback is captured.

---

## Caller contract

`spec-kitty agent retrospect synthesize` MUST:

1. Resolve the mission via `--mission <handle>` (mission_id / mid8 / mission_slug).
2. Load the retrospective record from the canonical path.
3. Display proposals in `state.status == "accepted"` plus auto-applicable `flag_not_helpful` proposals.
4. Default to `--dry-run`. Operator must pass `--apply` to mutate.
5. Pass results through to `apply_proposals(...)`.
6. Print `SynthesisResult` as Rich + JSON (informational equivalence; see CLI contract).
7. Exit non-zero if `conflicts` or `rejected` is non-empty AND `--apply` was passed.
