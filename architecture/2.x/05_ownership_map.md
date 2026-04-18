# Functional Ownership Map

| Field     | Value                                                                                                                              |
|-----------|------------------------------------------------------------------------------------------------------------------------------------|
| Status    | Active                                                                                                                             |
| Date      | 2026-04-18                                                                                                                         |
| Mission   | [functional-ownership-map-01KPDY72](../../kitty-specs/functional-ownership-map-01KPDY72/spec.md)                                   |
| Manifest  | [05_ownership_manifest.yaml](./05_ownership_manifest.yaml)                                                                         |
| Exemplar  | Mission `charter-ownership-consolidation-and-neutrality-hardening-01KPD880`                                                        |
| Direction | [#461 — Charter as Synthesis & Doctrine Reference Graph](https://github.com/Priivacy-ai/spec-kitty/issues/461)                     |

> **Terminology**: This document uses **Mission** (not "feature") and **Work Package** (not "task") per the repository's terminology canon in `AGENTS.md`. All downstream extraction PRs must follow the same convention.

---

## How to use this map

### Audience A — Extraction-PR Author

**Goal**: Prepare a PR that extracts a slice (e.g. glossary, runtime, lifecycle) to its canonical package without missing any obligation.

**Procedure**:

1. **Locate the slice entry** — open this map and find the H2 for the slice you are extracting.
2. **Read the required fields in order**:
   - `current_state` — list the exact files you will move.
   - `canonical_package` — the target package; use this as the destination path.
   - `adapter_responsibilities` — keep these in `src/specify_cli/` (the CLI shell). Do not move them.
   - `shims` — for each entry, create the shim file at `path` that re-exports from `canonical_import`. Record the `removal_release`.
   - `seams` — for each seam sentence, verify the seam still works after the move (typically a single test at the seam boundary).
   - `extraction_sequencing_notes` — confirm the prerequisites for this slice are landed.
3. **For the runtime slice only**: also honour `dependency_rules`. Add an import-graph test that asserts `may_call` / `may_be_called_by` hold.
4. **Confirm the slice entry in the PR description** — copy the slice's H2 from the map into the PR description and tick every field off. If a field is deferred, name the follow-up tracker.

**Worked example — Glossary extraction (mission #613)**:

- `current_state`: `src/specify_cli/glossary/` (14 modules).
- `canonical_package`: `src/glossary/`.
- `adapter_responsibilities`: CLI argument parsing and Rich rendering for `spec-kitty glossary *` commands stays in `src/specify_cli/cli/commands/glossary.py`.
- `shims`: one shim at `src/specify_cli/glossary/` with `canonical_import: glossary`, `removal_release: 3.4.0`.
- `seams`: doctrine registers a glossary runner via `kernel.glossary_runner.register()`; mission execution reads via `get_runner()` (resolved by ADR `2026-03-25-1`).
- `extraction_sequencing_notes`: depends on #393 and #394 landing first.
- PR moves all 14 modules to `src/glossary/`, adds the shim, ticks every field off in the PR description.

---

### Audience B — Reviewer

**Goal**: Reject extraction PRs that silently skip obligations or place code in the wrong package.

**Procedure**:

1. Open the PR and read its description.
2. Open this map and find the slice entry the PR claims to target.
3. For each required field in the slice entry: confirm the PR delivers it, or confirm the PR names a follow-up tracker, or request changes.
4. Verify **Mission / Work Package** canon — no "feature/task" language in the PR description or commit messages.
5. Verify the CHANGELOG entry exists if the slice had a shim removal.
6. For the runtime slice only: confirm `dependency_rules` have a corresponding test.

**Worked example — Runtime extraction PR review (mission #612)**:

- PR claims: "extracts runtime to `src/runtime/`".
- Reviewer checks `dependency_rules.may_call: [charter_governance, doctrine, lifecycle_status, glossary]` — PR adds an import-graph test covering these four.
- Reviewer checks `may_be_called_by: [cli_shell]` — PR adds the reverse assertion.
- Reviewer checks `adapter_responsibilities` — CLI commands under `src/specify_cli/cli/commands/` that delegate to runtime stay in place.
- Reviewer checks `extraction_sequencing_notes` — PR confirms #393, #394, #395 are in place.
- If every field is accounted for, approve. Otherwise, request changes naming the specific missing field.

---

### Manifest-driven tooling

Third-party tools (CI checks, the shim registry in mission #615, future scripts) parse `05_ownership_manifest.yaml` directly. A typical consumer pattern:

```python
import yaml
from pathlib import Path

manifest = yaml.safe_load(Path("architecture/2.x/05_ownership_manifest.yaml").read_text())
runtime = manifest["runtime_mission_execution"]
may_call = runtime["dependency_rules"]["may_call"]
# assert import-graph compliance
```

---

## CLI Shell

| Field                        | Value                                                                                       |
|------------------------------|---------------------------------------------------------------------------------------------|
| `canonical_package`          | `src/specify_cli/cli/`                                                                      |
| `extraction_sequencing_notes`| Not extracted. The CLI shell is the permanent `src/specify_cli/` surface for CLI-only code. |

**`current_state`**:
- `src/specify_cli/cli/`

**`adapter_responsibilities`**:
- All user-facing CLI commands, argument parsing, and Rich console output
- Entry points for every `spec-kitty *` sub-command
- Permanent home; extraction of other slices moves code *out of* `src/specify_cli/`, not out of the CLI shell

**`shims`**: *(none)*

**`seams`**:
- CLI shell delegates mission execution to `runtime_mission_execution` via `spec-kitty implement / next / review / accept`
- CLI shell reads charter context via `charter.build_charter_context` for `spec-kitty charter *` commands
- CLI shell reads lifecycle status via `status.*` for `spec-kitty agent tasks status`

---

## Charter Governance

| Field                        | Value                       |
|------------------------------|-----------------------------|
| `canonical_package`          | `charter` (= `src/charter/`) |
| `extraction_sequencing_notes`| Already extracted by mission `charter-ownership-consolidation-and-neutrality-hardening-01KPD880`. No further extraction queued. |

**`current_state`**:
- `src/charter/`

**`adapter_responsibilities`**:
- `src/specify_cli/cli/commands/charter.py` — `spec-kitty charter *` CLI commands
- `src/specify_cli/cli/commands/charter_bundle.py` — bundle management CLI surface

**`shims`**: *(none — `src/specify_cli/charter/` compatibility shim deleted by WP02 of mission `functional-ownership-map-01KPDY72`)*

**`seams`**:
- Runtime reads charter context via `charter.build_charter_context` to load project principles at mission start
- Doctrine loads charter bundle for principle synthesis via `charter.ensure_charter_bundle_fresh`

> **Reference exemplar**: Mission `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` (`01KPD880`) is the canonical exemplar for all future slice extractions in this repository. It established the full extraction pattern: move canonical code to `src/<slice>/`, wire adapter CLI commands in `src/specify_cli/cli/commands/`, create a re-export shim at `src/specify_cli/<slice>/` with a `DeprecationWarning` and `__removal_release__`, add the C-005 test-fixture exception, and document the seams. Every downstream extraction Mission (#612, #613, #614) follows this pattern. See [06_unified_charter_bundle.md](./06_unified_charter_bundle.md) for the charter bundle contract.

---

## Doctrine

| Field                        | Value                          |
|------------------------------|--------------------------------|
| `canonical_package`          | `doctrine` (= `src/doctrine/`) |
| `extraction_sequencing_notes`| Already extracted. The `model_task_routing` artefact specialises the **tactic** parent-kind: it adds a schema-validated task/model catalog, routing policy (weights, tier constraints), and freshness policy (R-006). No further extraction queued. |

**`current_state`**:
- `src/doctrine/`

**`adapter_responsibilities`**:
- CLI rendering for doctrine entries stays in `src/specify_cli/cli/`

**`shims`**: *(none)*

**`seams`**:
- Runtime loads `doctrine.model_task_routing` to select the appropriate model for each Work Package task type
- Charter reads doctrine principles during charter synthesis for principle–doctrine alignment checks

---

## Runtime Mission Execution

| Field                        | Value             |
|------------------------------|-------------------|
| `canonical_package`          | `src/runtime/`    |
| `extraction_sequencing_notes`| Target for mission #612. Extraction requires safeguards #393 (architectural tests), #394 (deprecation scaffolding), and #395 (import-graph enforcement) to be in place first. Import-graph enforcement is load-bearing because `dependency_rules` must be verified automatically after the slice boundary moves. |

**`current_state`**:
- `src/specify_cli/runtime/` — runtime bootstrap, resolver, home-path, doctor, migration support
- `src/specify_cli/missions/` — mission type registry and mission-level orchestration
- `src/specify_cli/next/` — canonical `spec-kitty next` control-loop integration
- `src/specify_cli/mission.py`, `src/specify_cli/mission_metadata.py` — mission model and metadata helpers

**`adapter_responsibilities`**:
- `src/specify_cli/cli/commands/implement.py` — `spec-kitty implement` CLI entry point
- `src/specify_cli/cli/commands/accept.py` — `spec-kitty accept` CLI entry point
- `src/specify_cli/cli/commands/init.py` — `spec-kitty init` CLI entry point
- All other `spec-kitty agent action *` CLI entry points

**`shims`**: *(none — runtime has not yet been extracted; code lives directly in `src/specify_cli/runtime/`)*

**`seams`**:
- CLI shell calls runtime to execute the next-step control loop (`spec-kitty next`)
- Runtime reads charter context at mission start via `charter.build_charter_context`
- Runtime reads `doctrine.model_task_routing` for model selection at Work Package dispatch time
- Runtime reads lifecycle lane state via `lifecycle_status` to decide which Work Package to claim next
- Runtime reads glossary state via `glossary` for terminology validation during mission execution

**`dependency_rules`**:
- `may_call`: `charter_governance`, `doctrine`, `lifecycle_status`, `glossary`
- `may_be_called_by`: `cli_shell`

---

## Glossary

| Field                        | Value                                                                                                                               |
|------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| `canonical_package`          | `src/glossary/`                                                                                                                     |
| `extraction_sequencing_notes`| Target for mission #613. Depends on #393 (architectural tests) and #394 (deprecation scaffolding) landing first. #395 is nice-to-have, not blocking. |

**`current_state`**:
- `src/specify_cli/glossary/`

**`adapter_responsibilities`**:
- `src/specify_cli/cli/commands/glossary.py` — CLI argument parsing and Rich rendering for `spec-kitty glossary *` commands

**`shims`**: *(none — glossary has not yet been extracted)*

**`seams`**:
- Doctrine registers a glossary runner via `kernel.glossary_runner.register()`; runtime reads via `get_runner()` (resolved by ADR `2026-03-25-1`)
- Runtime reads canonical terminology via `glossary.store` to validate Work Package and Mission naming during mission execution

---

## Lifecycle Status

| Field                        | Value                                                                                                                               |
|------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| `canonical_package`          | `src/lifecycle/`                                                                                                                    |
| `extraction_sequencing_notes`| Target for mission #614. Has the most cross-slice callers in the codebase (next loop, orchestrator, dashboard, sync, tracker). Requires #393, #394, **and** #395 to be in place before extraction — the import-graph tool is material here due to the high fan-in. |

**`current_state`**:
- `src/specify_cli/status/`

**`adapter_responsibilities`**:
- `src/specify_cli/cli/commands/lifecycle.py` — `spec-kitty agent tasks status` and related commands

**`shims`**: *(none — lifecycle has not yet been extracted)*

**`seams`**:
- Runtime reads Work Package lane state via `status.lane_reader.get_wp_lane()` to decide what to claim next
- Orchestrator reads WP status via `status.reducer.materialize()` for cross-repo drift detection
- CLI shell renders lane state via `status.models.StatusSnapshot` for the kanban display
- Sync writes lane events via `status.emit.emit_status_transition()` after SaaS-side state changes

---

## Orchestrator / Sync / Tracker / SaaS

| Field                        | Value                                                                                                                                    |
|------------------------------|------------------------------------------------------------------------------------------------------------------------------------------|
| `canonical_package`          | `src/orchestrator/` *(forward-looking commitment; no extraction mission queued)*                                                         |
| `extraction_sequencing_notes`| Fragmented across 7 subdirectories today (see `current_state`). No near-term extraction mission. The canonical target is recorded here so future consolidation work has a named destination. Not in scope for missions #612–#615. |

**`current_state`**:
- `src/specify_cli/orchestrator_api/` — external-consumer contract surface (SaaS API)
- `src/specify_cli/lanes/` — lane computation and worktree ownership
- `src/specify_cli/merge/` — merge executor, preflight validation, conflict forecast
- `src/specify_cli/sync/` — sync coordinator, background sync, body queue and transport
- `src/specify_cli/tracker/` — tracker connector gateway (Linear, Jira, local)
- `src/specify_cli/saas/` — SaaS readiness flags and rollout control
- `src/specify_cli/shims/` — orchestrator-internal shim registry

**`adapter_responsibilities`**:
- CLI commands for orchestrator operations (`spec-kitty merge`, `spec-kitty agent config *`, etc.) stay in `src/specify_cli/cli/`

**`shims`**: *(none — no extraction yet; shim registry is documented by mission #615)*

**`seams`**:
- Lifecycle emits status events; sync reads them for SaaS propagation via `status.emit`
- Runtime dispatches Work Packages via `lanes.compute` for worktree allocation
- CLI shell reports merge state via `merge.state.load_state()` for `spec-kitty merge --resume`
- Tracker connector is called by sync after body-queue flush

---

## Migration / Versioning

| Field                        | Value                                                                                                                          |
|------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| `canonical_package`          | `src/specify_cli/migration/` and `src/specify_cli/upgrade/` *(stays)*                                                         |
| `extraction_sequencing_notes`| No near-term extraction. The slice's role as upgrade scaffolding for project-level migrations is distinct from runtime mission execution. Stays under `src/specify_cli/` for the foreseeable future. Not a target of any mission in the #612–#615 wave. |

**`current_state`**:
- `src/specify_cli/migration/` — migration runner, schema version tracking, state rebuild
- `src/specify_cli/upgrade/` — upgrade registry, migration file discovery, compatibility detector

**`adapter_responsibilities`**:
- `spec-kitty upgrade` CLI surface stays in `src/specify_cli/cli/`

**`shims`**: *(none)*

**`seams`**:
- Upgrade command reads the migration registry to apply incremental migrations on `spec-kitty upgrade`
- Runtime bootstrap calls migration path discovery to confirm the project is on the current schema version

---

## Safeguards and Direction

The following issues gate slice extractions and must land before the indicated missions proceed:

| Safeguard | Issue | Slices that depend on it |
|-----------|-------|--------------------------|
| Architectural tests | [#393](https://github.com/Priivacy-ai/spec-kitty/issues/393) | Runtime (#612), Glossary (#613), Lifecycle (#614) |
| Deprecation scaffolding | [#394](https://github.com/Priivacy-ai/spec-kitty/issues/394) | Runtime (#612), Glossary (#613), Lifecycle (#614) |
| Import-graph tooling | [#395](https://github.com/Priivacy-ai/spec-kitty/issues/395) | Runtime (#612, load-bearing for `dependency_rules`), Lifecycle (#614, load-bearing due to high fan-in) |

**Direction**: [#461 — Charter as Synthesis & Doctrine Reference Graph](https://github.com/Priivacy-ai/spec-kitty/issues/461) provides the architectural rationale for extracting charter-adjacent governance into standalone packages. The ownership map is a downstream artefact of that direction: it records the extraction targets once #461's analysis is settled.

---

## Downstream Missions

| Mission | Slice | What it consumes from this map |
|---------|-------|-------------------------------|
| [#612 — Runtime Mission Execution Extraction](https://github.com/Priivacy-ai/spec-kitty/issues/612) | `runtime_mission_execution` | `canonical_package`, `current_state`, `adapter_responsibilities`, `dependency_rules`, `extraction_sequencing_notes` |
| [#613 — Glossary Extraction](https://github.com/Priivacy-ai/spec-kitty/issues/613) | `glossary` | `canonical_package`, `current_state`, `adapter_responsibilities`, `seams`, `extraction_sequencing_notes` |
| [#614 — Lifecycle Status Extraction](https://github.com/Priivacy-ai/spec-kitty/issues/614) | `lifecycle_status` | `canonical_package`, `current_state`, `adapter_responsibilities`, `seams`, `extraction_sequencing_notes` |
| [#615 — Migration Shim Rulebook](https://github.com/Priivacy-ai/spec-kitty/issues/615) | All slices with shims | `shims[].path`, `shims[].canonical_import`, `shims[].removal_release` |

---

## Change Control

This map is a **living document**. Edits land in-place on the target branch; there is no versioned copy. The following rules govern changes:

- **Slice entry edits** (correcting `current_state`, `seams`, etc.): land via a PR that cites the relevant mission or issue. The PR description must reproduce the affected slice entry and state what changed and why.
- **New slice key**: requires a new mission spec; the eight-key set in §2.1 of the data-model is fixed by FR-002. A proposal to add a key is treated as a scope change.
- **Each extraction PR** must confirm in its description that its slice entry is honoured: every field is delivered, deferred with a named tracker, or noted as N/A with a reason.
- **Machine-readable manifest** (`05_ownership_manifest.yaml`) must be updated in the same commit as any map change that alters a field value. The schema test in `tests/architecture/test_ownership_manifest_schema.py` is the enforcing gate.
