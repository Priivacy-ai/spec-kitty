# Data Model: Implement-Loop Coord-Authority Completion

This mission has no persistent data schema. The "model" is the **artifact-kind
partition** that decides read authority, and the **residual taxonomy** the FR-008 sweep
classifies against.

## Artifact-kind partition (authority: `src/specify_cli/mission_runtime/artifacts.py`)

| Partition | Kinds (examples) | Read authority | Topology behavior |
|-----------|------------------|----------------|-------------------|
| **PRIMARY** | `SPEC`, `WORK_PACKAGE_TASK` (`tasks/`, `WP*.md`), `LANE_STATE` (`lanes.json`), `PRIMARY_METADATA` (`meta.json`), plan/data-model/tasks-index | the **primary checkout** for all topologies (via `resolve_planning_read_dir(kind=...)` → `_canonicalize_primary_read_handle`) | identical across flat / lanes / coord |
| **STATUS** | `STATUS_STATE` (`status.events.jsonl`, `status.json`), `ISSUE_MATRIX`, `ACCEPTANCE_MATRIX`, `ANALYSIS_REPORT` | the **coordination surface** when materialized | coord-aware (keeps #1718/#1848 transients) |

**Invariant (the bug):** for a COORDINATION-topology mission post-#2106, the `-coord`
worktree carries STATUS artifacts ONLY — no `meta.json`, no `tasks/`, no `lanes.json`
(authoritative: `implement.py:1020-1028`; live-probe confirmed). A PRIMARY-kind read
through a coordination-aware resolver therefore lands on a husk that lacks the artifact →
hard-fail or stale/empty result.

## Coordination-aware resolvers (the wrong authority for PRIMARY reads)

`candidate_feature_dir_for_mission`, `resolve_feature_dir_for_slug`,
`resolve_feature_dir_for_mission`, `resolve_handle_to_read_path` — all topology-aware;
all return the coord surface for a coord-topology mission. The fix is not to change them
(C-003: they stay handle-blind) but to re-point **PRIMARY-kind call sites** onto the seam.

## Residual taxonomy (FR-008 classification)

| Class | Definition | Action |
|-------|------------|--------|
| **ROUTE** | PRIMARY-kind read on the implement/review loop | re-point to `resolve_planning_read_dir(kind=...)` (this mission) |
| **MIXED-READ** | one resolved dir feeds BOTH a PRIMARY and a STATUS read | split per-leg (C-001); PRIMARY→seam, STATUS→coord-aware; may need a signature change |
| **KEEP** | STATUS-kind read, or deliberate coord-aware probe | unchanged |
| **TICKET-AND-PIN** | PRIMARY-kind read out of this mission's loop scope | pin in `_DIR_READ_KNOWN_RESIDUALS` + tracking issue (no silent skip) |

**Call-site shapes:** *two-hop* (`d = resolver(...); d / "x"` — the only shape the legacy
scanner caught) and *inline* (`resolver(...) / "x"` — the blind spot FR-007 fixes).

## Gate state (the ratchet)

| Element | Pre-mission | Post-mission target |
|---------|-------------|---------------------|
| dir-read scan scope | `cli/commands/` (+`acceptance/`) | all of `src/specify_cli/` |
| inline-call-shape detection | absent | present + self-test |
| `_DIR_READ_KNOWN_RESIDUALS` | 6 pins (loop residuals) | in-loop residuals drained to 0; out-of-scope residuals pinned-and-ticketed |
| `ROUTED_CANONICALIZER_FLOOR` | 27 (live 31) | recomputed strictly below post-fix live census |
| resolution-gate permanent allowlist | 7 hand-sanctioned | 3 (4 auto-route via the bare-modern fold) |
