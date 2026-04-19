# Phase 0 — Research Notes

**Mission**: Functional Ownership Map (`functional-ownership-map-01KPDY72`)
**Scope**: Resolve plan-phase unknowns. No `NEEDS CLARIFICATION` markers remain after Phase 0.

---

## R-001 — Baseline inventory of `src/specify_cli/charter/`

**Decision**: The shim is four files. All four are deleted by this mission (FR-012).

**Files confirmed at HEAD**:

- `src/specify_cli/charter/__init__.py` — ~123 lines, single DeprecationWarning emission site, re-exports the full public API of `charter`.
- `src/specify_cli/charter/compiler.py` — silent re-export.
- `src/specify_cli/charter/interview.py` — silent re-export.
- `src/specify_cli/charter/resolver.py` — silent re-export.

**Rationale**: The exemplar mission `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` already verified that both hard-success-criterion functions (`build_charter_context`, `ensure_charter_bundle_fresh`) have exactly one definition in `src/charter/` and that the shim has no internal call sites. Deleting the shim is safe at the code level; external importers have had a deprecation warning since 3.1.0 per `__removal_release__ = "3.3.0"`.

**Alternatives considered**: Keeping the shim one more minor (rejected — the spec's FR-012 explicitly deletes it; the map cannot read as "fully consolidated" with the shim present).

---

## R-002 — CI / release-script / installer references to `specify_cli.charter`

**Decision**: Plan-phase grep during Work Package `implement` confirms zero non-test references. If any are found, an extra WP is added by the implementer (per spec §Edge cases: "a post-mission PR that proposes altering the map"). No such references are expected — exemplar mission `01KPD880` already removed the stale `pyproject.toml` mypy-override entry that referenced `specify_cli.charter.context`.

**Rationale**: Spec assumption A3 ("Deleting `src/specify_cli/charter/` does not break any currently-shipped CI job or release script. A plan-phase grep confirms this").

**Alternatives considered**: Treating A3 as an unknown and blocking on a grep here (rejected — the grep is a trivial verification step that belongs inside the deletion WP, not inside planning).

---

## R-003 — Safeguard tracker status

**Decision**: The map cites issues #393 (architectural tests), #394 (deprecation scaffolding), #395 (import-graph tooling), and #461 (direction) per FR-008 and FR-009. Each slice entry states which safeguards must be in place *before* that slice extracts — not which are in place *today*.

**Mapping** (to be encoded into slice entries):

- **CLI shell slice** — no extraction target, no safeguard dependencies.
- **Charter slice** — already extracted; the map cites `01KPD880` as the exemplar.
- **Doctrine slice** — already extracted to `src/doctrine/`; #393 architectural tests enforce the boundary.
- **Runtime slice** — extraction (#612) depends on #393 (prevent regressions), #394 (shim scaffolding for the runtime removal cycle), #395 (import-graph enforcement for "runtime may call" / "may be called by" rules).
- **Glossary slice** — extraction (#613) depends on #393 + #394. #395 is nice-to-have, not blocking.
- **Lifecycle slice** — extraction (#614) depends on #393 + #394 + #395 — lifecycle has the most cross-slice callers (next loop, orchestrator, dashboard, sync, tracker), so the import-graph tool is material.
- **Orchestrator slice** — fragmented today; extraction is not a single mission and the map documents that factually.
- **Migration slice** — lives under `src/specify_cli/migration/` + `upgrade/`; no extraction planned in the near term.

**Rationale**: Mapping safeguards to slices by extraction readiness is what makes the map usable as a gating artefact for downstream missions.

**Alternatives considered**: Listing all safeguards against all slices uniformly (rejected — less useful, fails FR-008's "must be in place before each slice extracts" semantics).

---

## R-004 — Three C-005 test-fixture exceptions from mission `01KPD880`

**Decision**: All three are deleted by this mission (NFR-003). The exceptions existed to keep legacy-import tests passing while the shim was alive; with the shim gone, the legacy-import tests are gone too and the exceptions have nothing to guard.

**Files to revisit during the deletion WP**:

- `tests/specify_cli/charter/test_defaults_unit.py` — retained previously by design as a C-005 compatibility fixture; deleted with the shim.
- `tests/charter/test_sync_paths.py` — if it contains a `specify_cli.charter` import, that line (and any surrounding exception marker) is deleted. If the file has canonical `from charter import …` lines, those stay; only the legacy-path lines go.
- `tests/charter/test_chokepoint_coverage.py` — same pattern.

**Rationale**: Spec's FR-012 explicitly says "and removes any test-fixture or lint exceptions scoped to that shim (the three C-005 exceptions documented in mission `01KPD880`)". NFR-003 reinforces "zero new test-fixture exceptions introduced; the three prior C-005 exceptions for the charter shim are deleted".

**Alternatives considered**: Migrating the fixtures to canonical imports (rejected — their purpose was legacy-path coverage; migrating removes the purpose, which is equivalent to deletion).

---

## R-005 — Current filesystem reality of the orchestrator/sync/tracker/SaaS slice

**Decision**: The map documents the slice's **fragmented current state** factually under a single slice entry named `orchestrator_sync_tracker_saas`, listing the seven subdirectories that make it up:

- `src/specify_cli/orchestrator_api/` (external-consumer contract surface)
- `src/specify_cli/lanes/` (lane computation + worktree ownership)
- `src/specify_cli/merge/` (merge executor + preflight + forecast)
- `src/specify_cli/sync/` (sync coordinator + background + body queue)
- `src/specify_cli/tracker/` (tracker connector gateway)
- `src/specify_cli/saas/` (SaaS readiness + rollout)
- `src/specify_cli/shims/` (orchestrator-internal shim registry)

The slice entry picks a single canonical target: `src/orchestrator/` (dotted package name `orchestrator`). That is a forward-looking commitment, not a mandate for this mission — C-002 forbids moving any of these. The commitment is recorded so future extraction work (outside mission #612/#613/#614 scope) has a named target.

**Rationale**: Spec §Edge cases — "a slice whose current boundary is ambiguous… resolution: the map documents the current fragmented state factually, then commits to a single canonical target". Spec §Out of Scope — "authoring the shim registry YAML itself (that's #615)", but #615 will reference this slice entry as its input.

**Alternatives considered**: Splitting into four slice entries (orchestrator / sync / tracker / SaaS) — rejected; that inflates FR-002's "eight slices" commitment and duplicates the fragmented-extraction narrative. Collapsing under `orchestrator` — chosen; matches the spec's slice taxonomy verbatim.

---

## R-006 — `model_task_routing` parent-kind selection

**Decision**: `tactic` (per Structure Decisions table in `plan.md`).

**Evidence from the artefact itself** (`src/doctrine/model_task_routing/models.py`):

- `RoutingPolicy` carries `objective` (quality_first / balanced / cost_first), `weights`, `tier_constraints`, `override_policy`, `freshness_policy`.
- The artefact *drives a decision procedure*: given a task type, produce a model choice.
- It is **not** paradigm-shaped (no mental model framing), **not** directive-shaped (no `enforcement: required|advisory` field), **not** styleguide-shaped (no output format), **not** toolguide-shaped (the subject is models, not tools).

**How the specialization adds value** (for the map's slice entry):

1. It carries a schema-validated catalog (task_types + models + task_fit) that a plain tactic would not.
2. It carries a routing policy with explicit weights and tier constraints.
3. It carries a freshness policy (catalog staleness).
4. The override policy (`advisory` / `gated` / `required`) echoes directive enforcement semantics without being a directive — agents apply the policy inside the procedure rather than being bound by a standalone rule.

The map records this as: `model_task_routing` **specializes** the tactic kind; parent kind is `tactic`; the specialization adds the schema-validated catalog layer and the routing/override/freshness policy layers.

**Alternatives considered**:

- **Directive** — rejected; directives carry `enforcement` semantics that the routing catalog does not have at the top level. The override policy is *inside* the tactic, not a standalone rule.
- **Paradigm** — rejected; paradigms are mental models, not executable procedures.
- **First-class new kind** (peer of tactic/directive/toolguide) — rejected per FR-005 ("a specialization, not a first-class kind"). Adding a new kind would require schema, registry, and downstream consumer changes well beyond this mission's scope.

---

## No NEEDS CLARIFICATION remaining

The plan proceeds to Phase 1 (Design & Contracts) with all plan-phase unknowns resolved.
