# Contracts — Degod tasks.py (Wave 1)

Phase 1 output. This mission adds **no** network/API surface — the "contracts" are the internal
**port Protocol interfaces** (the capability boundary the orchestrators depend on) and the **pure
core function signatures** (deterministic decision/aggregation I/O). Indicative; the binding form
lands in WP02/03. Each is paired with its parity obligation.

## Port protocols (`tasks_ports.py`)

```python
class FsReader(Protocol):                       # PROGRAM-REFERENCE — coord READ authority (C-001)
    def planning_read_dir(self, mission: MissionHandle, *, kind: MissionArtifactKind) -> Path: ...
    def wp_tasks_dir(self, mission: MissionHandle) -> Path: ...
    def primary_anchor_dir(self, mission: MissionHandle) -> Path: ...   # blind primitive stays INSIDE

class CoordCommitRouter(Protocol):              # PROGRAM-REFERENCE — coord WRITE (two disjoint capabilities)
    def feature_write_dir(self, mission: MissionHandle) -> Path: ...
    def commit_status(                          # over emit_status_transition_transactional (GuardCapability)
        self, mission: MissionHandle, event: StatusEvent, *, capability: GuardCapability,
    ) -> CommitStatusResult: ...                # self-atomic (BookkeepingTransaction); skip → .skipped
    def commit_artifact(                        # over commit_for_mission (MissionArtifactKind + policy), event-LESS
        self, mission: MissionHandle, paths: Sequence[Path], message: str, *,
        kind: MissionArtifactKind, policy: ProtectionPolicy,
    ) -> CommitArtifactResult: ...              # implement.py uses commit_status only; acceptance commit_artifact only

class GitOps(Protocol):                          # MISSION-LOCAL (#2173 DROP) — porcelain reads only
    def is_dirty(self, path: Path) -> bool: ...
    def current_branch(self, path: Path) -> str: ...
    def is_protected(self, branch: str) -> bool: ...

class Render(Protocol):                          # MISSION-LOCAL (#2173 DROP) — output only
    def human(self, view: object) -> None: ...
    def json_envelope(self, payload: Mapping[str, object]) -> str: ...

@dataclass(frozen=True)
class TasksPorts:                                # the injected bundle
    fs: FsReader
    coord: CoordCommitRouter
    git: GitOps
    render: Render
```

**Injection contract (C-005/D5)**: every orchestrator is `_do_<cmd>(..., *, ports: TasksPorts | None = None)`; `None` builds the Real bundle. The Typer `@app.command` never sees `ports`.

## Pure core signatures

```python
# tasks_transition_core.py — reproduces move_task's EXACT current behavior (D4)
def decide_transition(req: TransitionRequest) -> TransitionOutcome: ...
#   TransitionOutcome = Emit(event, commit_paths, skip_primary) | SkipExit0(reason, json_keys) | RefuseExit1(error)
#   PURE: no filesystem, git, or clock access. Orchestrator executes the outcome via ports.

# tasks_mapping_core.py
def plan_mapping(req: MappingRequest) -> MappingPlan: ...
#   MappingPlan(to_write: dict[str, list[str]], offenders: MappingOffenders, unmapped_fr: list[str])

# tasks_status_view.py
def build_status_view(req: StatusRequest) -> StatusView: ...
#   StatusView(lanes, stale, progress, dependency_readiness) — PURE aggregation; Render does the drawing
```

## Parity obligations (per contract)

| Contract element | Parity obligation | Verified by |
|---|---|---|
| `FsReader.planning_read_dir` (kind-aware) | resolves the **same on-disk dir** as the pre-migration kind-blind `resolve_feature_dir_for_mission` for the in-scope mission kinds (FR-010/D8) | golden harness (CLI output byte-identical) + a targeted equivalence unit test |
| `CoordCommitRouter.commit_status` | atomic via the transactional emitter; the skip arm returns `.skipped=True` and drives exit-0 with identical `--json` keys + **primary HEAD unchanged** (INV-2) | golden coord-topology fixture (IC-01) |
| `CoordCommitRouter.commit_artifact` | event-less artifact commit routed by `MissionArtifactKind`+policy; matches the pre-refactor coord-vs-primary write target | golden coord-topology fixture (IC-01) |
| `decide_transition` | for every golden-frozen input, the executed side-effects match pre-refactor byte-for-byte (NFR-001); every branch reachable (NFR-002) | `test_tasks_transition_core.py` + golden |
| `plan_mapping` / `build_status_view` | pure; identical output for identical request; no I/O (INV-4) | per-core unit tests with Fakes |
| `Render.json_envelope` | emits the identical JSON string the inline `json.dumps` sites produced (key order, separators) | golden `--json` snapshots |

## Non-contracts (explicitly out)

- No cross-command behavior reconciliation (skip-vs-refuse) — deferred #2300 (D4).
- No change to `primary_feature_dir_for_mission` internals — called only, never re-implemented (C-003/INV-3).
- No new ports beyond the four above; the coord WRITE port carries two capabilities (`commit_status`, `commit_artifact`) — StatusEmit is `commit_status`, a co-equal method, not a hidden sub-step (D2).
