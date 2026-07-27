# Randy Reducer — Adoption Census: `resolve_action_context` / `ExecutionContext`

**Lens:** behavior-preserving reduction, dead/aspirational-code detection, adoption census.
**Question settled by evidence, not opinion:** is the central API *load-bearing* or *vestigial/aspirational*?

---

## Verdict (lead)

- **Load-bearing? PARTIALLY — yes for one thin slice, no for the rest.**
  The *call entry* `resolve_action_context` is on the hot path of `next` (query/answer),
  `implement`, and `context resolve`. But what those callers actually consume is the **flat
  substrate** (`feature_dir`, `target_branch`) plus exactly **one** fragment
  (`artifact_placement`). The other five doc-09 fragments (`identity`, `branch_ref`,
  `workspace`, `status_surface`, `prompt_source`) have **zero live readers** — they are
  assembled on every call and never read.
- **REDUCTION VERDICT: ADOPT-NARROW + RETIRE-WIDE.** Keep `resolve_action_context` and
  `resolve_placement_only` as thin projections over the *real* load-bearing primitives
  (`_read_path_resolver.resolve_mission_read_path` + `resolve_status_surface` +
  `get_feature_target_branch`); **retire the unconsumed fragment scaffolding** on
  `ExecutionContext`. The fragment/op-composite model is the aspirational part.
- **Adopted:bypassed ratio (read-path resolution): ~7 : ~40+** — roughly **1 : 6**.
  The single read primitive (`resolve_mission_read_path`) is what is genuinely adopted
  codebase-wide; `resolve_action_context` is *not* the read authority, it merely wraps it.

---

## 1. Consumer census — LIVE callers (src/, tests excluded)

`resolve_action_context` has **6 live caller files / 7 call sites**. Classification is by what
each caller *reads off the returned context*:

| Caller (file:line) | Action passed | Reads off context | Classification |
|---|---|---|---|
| `cli/commands/agent/context.py:135` | passed-through | `mission_slug`, `target_branch`, `wp_id`, `workspace_path`, `commands`, `to_dict()` | **Adopted** (reference adopter — `agent context resolve`; emits the whole flat substrate) |
| `cli/commands/implement.py:554` (`_resolve_placement_ref`) | `implement` | **`context.artifact_placement.placement_ref`** only | **Partial** (uses 1 fragment; discards the rest) |
| `cli/commands/agent/mission.py:720` (`_resolve_record_analysis_placement_ref`) | `tasks` | **`context.artifact_placement.placement_ref`** only | **Partial** (uses 1 fragment; discards the rest) |
| `cli/commands/agent/workflow.py:969` (`_ensure_target_branch_checked_out`) | `tasks` | `context.target_branch` only — then **falls back** to `get_feature_target_branch` on error | **Bypass-while-holding** (resolves a full context to read one flat field that has a direct helper) |
| `runtime/next/runtime_bridge.py:3122` (`query_current_state`) | `tasks` | `context.feature_dir` only | **Bypass-while-holding** (full resolve to get `feature_dir`; the read primitive returns this directly) |
| `runtime/next/runtime_bridge.py:3259` (`answer_decision_via_runtime`) | `tasks` | `context.feature_dir` only | **Bypass-while-holding** (same) |
| `missions/feature_dir_resolver.py:60` (`resolve_feature_dir_for_mission`) | `tasks` | `Path(context.feature_dir)` only | **Bypass-while-holding** (full resolve to project a single dir; immediately discards the context) |

`resolve_placement_only` (the WP-less projection over the *same* builder) has **1 live caller**:
`cli/commands/agent/mission.py` → `_resolve_planning_placement` (`mission.py:742`) → drives every
planning-phase commit (spec/plan/tasks/finalize). This IS adopted and load-bearing for placement.

### Fragment-consumption census (the decisive cut)

Grepping every `*.py` (non-test) for reads of the doc-09 fragments off a resolved context:

| Fragment | Live readers off a context | Status |
|---|---|---|
| `artifact_placement` | 3 (`implement.py:562`, `mission.py:727`, both `→ .placement_ref`) | **ADOPTED** |
| `identity` | **0** | dead — assembled, never read |
| `branch_ref` | **0** (only assembled internally to feed `artifact_placement`) | internal-only |
| `workspace` | **0** | dead — assembled, never read |
| `status_surface` | **0** | dead — see below |
| `prompt_source` | **0** | dead — assembled, never read |

`StatusSurfaceFragment` has a designed consumer — `MissionStatus.load(..., surface=...)` in
`status/aggregate.py:199` — but **no caller ever passes a fragment to it**. Every `surface=`
hit in `src/` (non-test) is an unrelated glossary/ownership/decision parameter. The carried
`status_surface` fragment is **wired to a parameter that is always `None` in production** →
dead path (`aggregate.py:262`, `:309`).

**Conclusion of §1:** of the resolved context, only the *flat substrate* (`feature_dir`,
`target_branch`, `mission_slug`, `workspace_path`, `commands`) and the single
`artifact_placement` fragment are load-bearing. The op-composite fragment model is aspirational.

---

## 2. Bypass census — read-path resolutions that DON'T go through the central API

The central API is NOT the read authority. The read authority is the single primitive
`specify_cli.missions._read_path_resolver.resolve_mission_read_path` (and its surface sibling
`coordination.surface_resolver.resolve_status_surface`). `resolve_action_context` *calls* that
primitive (`resolution.py:128`). So "bypass" here means: code that resolves a mission read path
**directly via the primitive / its re-exports**, not through `resolve_action_context`.

Direct consumers of the read primitive & its facades (src/, non-test), counted from the
import/call census:

| Surface | Distinct caller files (non-test) |
|---|---|
| `resolve_mission_read_path` (direct) | 14 files — incl. `runtime_bridge.py`, `mission_read_path.py`, `retrospective/writer.py`, `implement.py`, `decision.py`, `agent/context.py`, `agent/workflow.py`, `agent/tasks.py`, `agent/mission.py`, `orchestrator_api/commands.py`, `acceptance/__init__.py`, `feature_dir_resolver.py`, `_read_path_resolver.py`, `resolution.py` |
| `candidate_feature_dir_for_mission` | ~29 files (paths, git_ops, worktree_topology, sync, status/aggregate, review/cycle, surface_resolver, status_transition, merge, lanes/*, dossier, mission_loader, …) |
| `resolve_feature_dir_for_mission` / `_for_slug` | ~32 files (workspace/context, agent_utils/status, post_merge, decisions/*, materialize, validate_*, research, doctor, plan/specify interviews, lanes/*, widen, …) |
| inline `KITTY_SPECS_DIR / <slug>` composition | 26 occurrences (non-test) |
| `.parent.parent` root walks | 55 occurrences (non-test) |

**Adopted (route through `resolve_action_context`/`resolve_placement_only`): ~7 caller files.**
**Bypassed (resolve via primitive/facade/inline directly): 40+ distinct caller files**
(deduping the overlap, well over 40 across `candidate_*` + `resolve_feature_dir_*` + inline).

**Ratio adopted : bypassed ≈ 7 : 40+  →  ~1 : 6.**

Crucially, several of the "adopted" callers are **bypass-while-holding** (§1): they invoke the
central API but then read a single flat field that the primitive returns directly — i.e. they
pay for a full context assembly to obtain `feature_dir` or `target_branch`.

---

## 3. Load-bearing test — what breaks if you delete the central API?

Hypothetically delete `resolve_action_context` (the function), keeping the read primitive,
`resolve_status_surface`, `get_feature_target_branch`, and `resolve_placement_only`:

- **`agent context resolve`** (`context.py`) — breaks. It is the only consumer that emits the
  *whole* flat substrate as JSON. It is the reference adopter and genuinely routes the API.
  However it would be trivially re-expressible as: read primitive → `feature_dir`,
  `get_feature_target_branch` → `target_branch`, `_resolve_wp_id` → wp fields. The "context"
  it returns is a flat bag, not the fragments.
- **`next` query/answer** (`runtime_bridge.py:3122`, `:3259`) — these only need `feature_dir`.
  Replacing `resolve_action_context(...).feature_dir` with
  `resolve_mission_read_path(repo_root, slug, mid8)` is behavior-equivalent (the central API
  *is* that call plus discarded work). **Hot path of `next`, but skippable** — the read
  primitive already does the load-bearing part.
- **`implement`** (`implement.py:554`) — needs `placement_ref`. That is `resolve_placement_only`
  for the WP-less case, or `artifact_home_for` over a placement. **Skippable** via
  `resolve_placement_only` (already a sibling projection).
- **`record-analysis`** (`mission.py:720`) — same: needs `placement_ref` → `resolve_placement_only`.
- **`workflow._ensure_target_branch_checked_out`** — already falls back to
  `get_feature_target_branch` on error; deleting the API just makes the fallback the primary
  path. **Skippable.**
- **`feature_dir_resolver.resolve_feature_dir_for_mission`** — already wraps the primitive one
  level up; the central-API hop is pure overhead. **Skippable.**

**Net:** deleting `resolve_action_context` would break compile-time imports in 6 files, but the
*behavior* of every caller is reproducible from the primitives the API already delegates to.
The genuinely irreplaceable surfaces are **`resolve_mission_read_path`**, **`resolve_status_surface`**,
**`get_feature_target_branch`**, and the **`CommitTarget`/`artifact_home_for` placement contract**
— none of which is the fragment/op-composite machinery. The central API is a **convenience
aggregator**, not a load-bearing authority.

---

## 4. REDUCTION VERDICT

### ADOPT-NARROW (keep + finish the thin slice that pays its way)

Keep and rely on:
- `resolve_placement_only` + `artifact_home_for` + `CommitTarget` — this is the single placement
  authority that fixed #1784/#1816 and is genuinely consumed (3 placement sites). **Load-bearing.**
- `resolve_action_context` as a *thin* aggregator returning the **flat substrate** for the one
  consumer that wants a whole bag (`agent context resolve`).

Finish adoption ONLY where it removes a real second authority: the bypass-while-holding callers
(`runtime_bridge` ×2, `feature_dir_resolver`, `workflow`) should call the **primitive directly**
(`resolve_mission_read_path` / `get_feature_target_branch`) rather than a full context they
immediately gut. That is *less* code, not more — it deletes the aggregation overhead.

### RETIRE-WIDE (the aspirational part — delete the scaffolding)

The doc-09 **fragment / op-composite model is vestigial**. Evidence:
- 5 of 6 fragments have **0 live readers** (`identity`, `branch_ref`, `workspace`,
  `status_surface`, `prompt_source`).
- The one consumer designed for `StatusSurfaceFragment` (`MissionStatus.load(surface=...)`)
  is **never passed a fragment** in production — dead parameter + dead `_resolve_read_dir`
  branch (`aggregate.py:262`, `:309`).
- `branch_ref` exists only to feed `artifact_placement` internally — collapse it.

**Quantified reduction available:**
- `mission_runtime/context.py` — **276 LOC**. Of the 6 fragment dataclasses + `ExecutionContext`
  fragment fields + `_FRAGMENT_FIELDS` exclusion plumbing, only `CommitTarget`,
  `CommitTargetKind`, `ArtifactPlacementFragment`, and the flat `ExecutionContext` substrate are
  consumed. Deleting `IdentityFragment`, `WorkspaceFragment`, `StatusSurfaceFragment`,
  `BranchRefFragment` (and `PromptSourceFragment`) + their assembly removes an estimated
  **~120–150 LOC** of dataclasses, `__post_init__` invariants, and the `to_dict` fragment-strip
  dance.
- `mission_runtime/resolution.py` — **824 LOC**. `_assemble_core_fragments`,
  `_assemble_workspace_fragment`, `_assemble_prompt_source_fragment`,
  `_assemble_artifact_placement_fragment` (~120 LOC of assembly) collapse to: resolve
  `feature_dir` (primitive) + `target_branch` (helper) + one `CommitTarget` (the placement
  authority `resolve_placement_only` already computes). Estimated **~100+ LOC** removable.
- `status/aggregate.py` — the `surface=` parameter and its dead `_resolve_read_dir` branch
  (~20 LOC) go once `StatusSurfaceFragment` is retired.

**Behavioral envelope to preserve (do NOT change):**
- `resolve_mission_read_path` topology resolution + fail-closed `StatusReadPathNotFound`
  → `ActionContextError` boundary translation (PR #1850 M6).
- The single `CommitTarget` placement contract (FR-004 invariant; #1784/#1816 fixes).
- `agent context resolve` JSON shape (`to_dict()`), which is already fragment-free (NFR-001).

### Bottom line

The mission's premise — "adopt `resolve_action_context`/`ExecutionContext` central API +
Context-passthrough" — is **half right and half cruft**. The *placement* slice is load-bearing
and worth finishing. The *op-composite fragment passthrough* is aspirational: nothing consumes
the fragments, the one wired consumer is dead-parametered, and adoption-by-passthrough would
propagate ~200+ LOC of unused scaffolding. **ADOPT the placement + flat-substrate slice via the
primitives; RETIRE the fragment model.** Net change is a **reduction**, not an expansion.
