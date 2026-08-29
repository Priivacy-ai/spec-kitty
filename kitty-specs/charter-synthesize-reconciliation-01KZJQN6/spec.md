# Mission Specification: Charter Synthesize Reconciliation

**Mission Branch**: `fix/charter-synthesize-reconciliation`
**Created**: 2026-08-09
**Status**: Draft
**Input**: Unify issues #3270 (P0), #2777, #3052 under epic #2519 — make `charter synthesize` non-destructive and the implement/next charter boundary trustworthy and complete.

## Context & Motivation

An authoring-only edit to `charter.yaml` (for example adding `mission_type_activations`)
trips the `synthesized_drg` freshness signal to `stale`. `spec-kitty agent action
implement` — and `spec-kitty next` — then **hard-block**, and the only prescribed
remediation is `spec-kitty charter synthesize`. Running that command **silently deletes**
doctrine graph nodes (and their edges) that the current synthesis target set does not
reproduce — content written by an earlier CLI or a broader prior activation, still backed
by artifact `.yaml` files on disk. The command reports only "Charter synthesis complete";
`--dry-run` does not surface the deletion. The operator's only escape today is to abandon
the charter edit — unavailable to any project that genuinely needs new charter content.

This is release-blocking (issue #3270, `priority:P0`): silent governance-data loss **and** a
trapped core workflow with no broadly-available workaround. Both halves are P0.

The mission folds in two open siblings under the same seam:
- **#2777** — the implement-boundary auto-refresh reconciler runs `sync → synthesize →
  validate`, never `generate`, so references-parity drift cannot self-heal. Its blocker is
  now clear: #2772 (curated `charter.md` preservation) and #2759 (freshness seam) are both
  merged, giving a landed preservation contract to honor.
- **#3052** — `synthesize` derives graph edges only from each target's `source_urns`, so
  consumer packs with no built-in derivation emit `edges: []`, and the DRG lint then flags
  the very directives synthesize just generated.

### Confirmed design decision — preserve-and-warn (post-spec squad revision)

Ledger decision `01KZJV6H7TW63M6ZGNM05XKM2S` (supersedes `01KZJQP5K4C0VGNB53GZZT3QWP`).
A post-spec adversarial squad established, with code and doctrine evidence, that an
abort-on-any-backed-drop default would break the very self-heal it targets (the boundary
`auto_refresh` runs a flagless `synthesize` and judges it by exit code, so an abort keeps
`implement`/`next` trapped), contradict the committed red-first test, fight the prevailing
"warn, do not hard-block" doctrine grain, and risk turning silent loss into a hard
validation crash. The confirmed contract:

- The **shared library seam** (`orchestrator.synthesize`) **preserves-and-succeeds**:
  it reconciles the freshly-emitted overlay against the on-disk overlay, drops nothing,
  exits 0, and reports retained content. `auto_refresh` and `activate`/`deactivate` consume
  this preserve behavior.
- **`--prune`** (a CLI opt-in) removes content, listing every deletion.
- A **non-zero refusal** is reserved for the **manual CLI only**, and only for
  genuinely-unpreservable states: content whose backing artifact was deleted (orphaned) being
  removed without `--prune`, or an unparseable on-disk overlay.

The canonical doctrine anchor is ADR `2026-07-26-3`, whose posture is warn/report, not
hard-block. The mission introduces a NEW `ReconciliationConflict` (in
`src/charter/activation/synthesizer/reconcile.py`) **modeled after** — not reusing — the DRG
typed-conflict shape in `src/doctrine/drg/merge.py`. That `OrgDRGConflict`/`
_CONFLICT_REMEDIATIONS` model belongs to the org-pack fragment-merge subsystem (its `kind`
is a closed `Literal` with no `duplicate_triple`, and it carries no `backing_artifact`/
`remediation` fields); it is neither reused nor edited by the synthesize path, which today
returns `list[str]` from `validate_graph`. ADR
`2026-05-16-1-doctrine-layer-merge-semantics` remains relevant only as the field-grain
non-destruction precedent.

## Domain Language *(canonical terms)*

- **Project DRG overlay (`graph.yaml`)** — project-authored nodes + edges layered additively
  over the built-in DRG. The single source truncated by the bug.
- **Synthesis manifest** — the registry of synthesized artifacts + `bundle_content_hash`,
  rebuilt alongside the overlay and subject to the same reconciliation.
- **Synthesis target set** — the nodes the *current* run recomputes from the interview
  snapshot plus config-activated directives. Divergence from the on-disk overlay is what
  triggers loss.
- **Backed content** — a graph node whose backing doctrine artifact `.yaml` still exists on
  disk. Backed content is preserved by default; removal is explicit.
- **Orphaned content** — a graph node whose backing artifact no longer exists on disk.
- **Reconciliation** — merging the freshly-emitted overlay and manifest against the existing
  on-disk overlay and manifest so untouched content survives (the behavior the `resynthesize`
  path already has via `_merge_project_overlay` / `_rewrite_manifest`; the full `synthesize`
  path lacks it).
- **Preserve-and-warn** — the confirmed default: reconcile, drop nothing, exit 0, report.
- **Prune** — the `--prune` opt-in that actually removes divergent content, listing deletions.
- **Reconciliation delta** — the computed set of nodes/edges/manifest entries a run would add,
  retain, or (with `--prune`) remove; surfaced by `--dry-run` and in refusal/prune output.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Synthesize preserves backed governance content (Priority: P1)

A charter author has a project DRG overlay containing directives/tactics (and their edges)
backed by artifact files on disk. They run `charter synthesize` during a routine edit.
Synthesize reconciles: content the current run does not target but which is still backed on
disk is preserved (node and edges), the manifest stays consistent with the graph, and the
command succeeds while reporting what it retained. Removal happens only via `--prune`.

**Why this priority**: The release-blocking data-loss defect (#3270 D1). Without it the
mission delivers nothing.

**Independent Test**: `tests/charter/synthesizer/test_synthesize_node_preservation.py`
(already committed, currently red): inject a backed legacy tactic node + its `applies` edge
into the on-disk graph, run a routine re-synthesis, assert node and edge survive.

**Acceptance Scenarios**:

1. **Given** an on-disk overlay with a backed node the current target set omits, **When**
   `charter synthesize` runs, **Then** the node and its edges remain in `graph.yaml`, the
   command exits 0, and it reports the retained content.
2. **Given** the same state, **When** `charter synthesize --prune` runs, **Then** the
   divergent content is removed and every deletion is listed in the command output.
3. **Given** an identical re-synthesis (no divergence), **When** `charter synthesize` runs,
   **Then** both `graph.yaml` and the manifest are byte-stable (no churn — preserves #1912).

### User Story 2 - The implement/next boundary self-heals non-destructively (Priority: P1)

An operator makes an authoring-only charter edit, then runs `implement` (or `next`). The
boundary auto-refresh reconciles via the preserve path: it never deletes backed content, it
clears the `synthesized_drg` stale signal, and the workflow proceeds — and a second
invocation is not re-blocked.

**Why this priority**: The deadlock half of #3270 (D2), which Context frames as equally P0. A
non-lossy synthesize (US1) is the precondition that makes auto-refresh safe to trust.

**Independent Test**: drive the preflight reconciler over a repo whose only drift is an
authoring-only edit; assert `implement`/`next` proceed, 0 nodes/edges lost, `synthesized_drg`
resolves to fresh, and a repeat invocation does not re-block.

**Acceptance Scenarios**:

1. **Given** an authoring-only charter edit that trips `synthesized_drg` stale, **When**
   `implement` runs with auto-refresh, **Then** it completes without deleting any backed
   content and without a destructive-only remediation.
2. **Given** the heal has run, **When** freshness is recomputed, **Then** `synthesized_drg`
   is `fresh` and a second `implement`/`next` proceeds without remediation.
3. **Given** references-parity drift, **When** the boundary auto-refresh runs, **Then** the
   references artifact is recompiled (its content reflects current activation) and curated
   `charter.md` is unchanged.
4. **Given** an **orphaned** node (backing artifact deleted) or an **unparseable on-disk
   overlay** as the drift cause, **When** the boundary auto-refresh runs, **Then** the flagless
   `synthesize` still **refuses** (it inherits the preserve default; a genuinely-unpreservable
   state is not silently pruned at the boundary), and the boundary surfaces an actionable
   `blocked_reason` naming the orphan/unparseable cause and the remediation (e.g. `--prune`, or
   repair the overlay). The "never trapped" guarantee of US2 holds **only** for the
   backed/authoring-only cause — it is not a claim that the boundary can never refuse.

### User Story 3 - Dry-run surfaces the reconciliation delta (Priority: P2)

Before committing a synthesis, an operator previews it with `--dry-run` and sees exactly
which nodes/edges/manifest entries would be removed under `--prune`, so a regeneration can
never silently truncate content.

**Why this priority**: Guards against loss even when `--prune` is used deliberately. Depends
on US1's delta computation.

**Independent Test**: on a superset on-disk overlay, run `charter synthesize --dry-run` and
assert a non-empty planned-deletions delta and that nothing is written.

**Acceptance Scenarios**:

1. **Given** an on-disk overlay with content the current target set omits, **When**
   `charter synthesize --dry-run` runs, **Then** the output enumerates the planned deletions
   (not only additive would-write artifacts) and no file is modified.
2. **Given** no divergence, **When** `--dry-run` runs, **Then** the planned-deletions delta
   is empty.

### User Story 4 - Synthesize emits charter-relevant edges (no fabrication) (Priority: P2)

A consumer-pack charter is synthesized. Where the interview mapping declares an upstream
relationship, synthesize emits the corresponding edge instead of leaving the node orphaned,
so the DRG lint no longer flags the just-generated directives — and no edge is emitted where
no licensing evidence exists.

**Why this priority**: Consistency defect #3052 in the same command; reconciliation already
touches overlay construction. Not release-blocking; must not gate the spine.

**Independent Test**: synthesize a pack whose sections declare `source_urns`; assert the
overlay contains those edges and the DRG lint passes; assert a pack with no such evidence
emits no fabricated edges.

**Acceptance Scenarios**:

1. **Given** a charter section that declares an upstream doctrine relationship, **When**
   `charter synthesize` runs, **Then** the overlay includes the corresponding edge rather
   than `edges: []`, and the DRG lint does not flag the generated directives.
2. **Given** a section with no declared upstream relationship, **When** `charter synthesize`
   runs, **Then** no edge is fabricated for that node.

### User Story 5 - Activation flows do not reintroduce the loss (Priority: P3)

`charter activate`/`deactivate` (which internally reach the full synthesize seam via the
mis-named `run_resynthesize_pipeline`) go through the same preserve reconciliation, so
activation never silently truncates the overlay.

**Why this priority**: Closes the third lossy surface funneling through the shared seam;
low-frequency but same root cause.

**Acceptance Scenarios**:

1. **Given** a backed overlay, **When** `charter activate`/`deactivate` runs, **Then** backed
   nodes/edges are preserved (no deletion without an explicit prune path).

### Edge Cases

- **Orphaned node** (backing artifact deleted): preserved by a plain run; removed only with
  `--prune`, and only after being listed; a manual CLI run that would remove it without
  `--prune` refuses (non-zero) and names it.
- **Manifest version-skew** (manifest registers fewer artifacts than the on-disk graph, the
  reporter's committed state): reconciled as content to retain, not silently discarded.
- **Preserved node's own edges**: retained/removed atomically with the node.
- **Dangling edge introduced by the merge** (a preserved edge whose target the current run
  legitimately removed/renamed): detected and reported through the conflict channel, not left
  to crash the DRG validator or silently corrupt the graph.
- **Preserved edge duplicating a built-in triple**: reported as a reconciliation conflict, not
  an uncaught `ProjectDRGValidationError`.
- **Unparseable / half-written on-disk `graph.yaml`**: the run fails closed with no write; it
  never falls back to a wholesale rebuild (which would reproduce the bug).
- **Identical re-synthesis**: byte-stable graph + manifest, empty delta, no spurious report.
- **`--prune` with nothing to prune**: succeeds as a no-op with an empty deletions list.
- **Concurrent writers** (manual `synthesize` racing boundary `auto_refresh` on `graph.yaml`):
  single-writer semantics on the overlay (documented; no interleaved partial writes).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Reconcile graph overlay on synthesize | As a charter author, I want `charter synthesize` to merge the freshly-emitted overlay against the existing on-disk `graph.yaml` so that content I did not change survives. | High | Open |
| FR-002 | Preserve nodes AND their edges atomically | As a charter author, I want preserved nodes to keep their edges (and dropped nodes to drop theirs together) so that the graph stays consistent. | High | Open |
| FR-003 | Preserve-and-warn default; explicit `--prune` | As a charter author, I want a plain synthesize to preserve backed content and exit 0 with a report, and to require `--prune` (which lists deletions) to remove content. | High | Open |
| FR-004 | Reconcile the synthesis manifest | As a charter author, I want the manifest reconciled alongside the graph (reusing `_rewrite_manifest`) so that manifest and graph never drift back into version-skew. | High | Open |
| FR-005 | Fix at the shared library seam | As a maintainer, I want the preserve reconciliation applied at the single shared synthesize seam so that manual `synthesize`, boundary `auto_refresh`, and `activate`/`deactivate` are all covered. | High | Open |
| FR-006 | Report merged-overlay conflicts, never crash | As an operator, I want a conflict/dangling edge introduced by preserving on-disk content surfaced through the conflict/remediation channel rather than an uncaught validation crash, and only new-emit collisions to hard-error. | High | Open |
| FR-007 | Corrupt overlay fails closed | As an operator, I want an unparseable on-disk overlay to abort with no write so that a parse failure never triggers a wholesale rebuild that loses content. | High | Open |
| FR-008 | Non-destructive boundary heal clears stale | As an operator, I want `implement`/`next` auto-refresh to reconcile non-destructively AND clear `synthesized_drg` stale so that I am never trapped and not re-blocked on the next run. | High | Open |
| FR-009 | Library seam mode + delta envelope | As a maintainer, I want the reconcile/preserve/prune/dry-run behavior threaded through the library seam and a planned/effected-deletions delta returned, with refuse/prune/dry-run decisioning owned by the CLI (not a `--prune` default baked into the library signature). | High | Open |
| FR-010 | Dry-run reports the reconciliation delta | As an operator, I want `charter synthesize --dry-run` to enumerate content that would be removed and write nothing. | Medium | Open |
| FR-011 | Complete auto-refresh (references parity) | As an operator relying on auto-refresh, I want it to recompile references parity (`generate`) when that is the stale cause, honoring curated `charter.md`, so the boundary self-heals fully. | Medium | Open |
| FR-012 | Emit charter-relevant edges from evidence | As a charter author, I want synthesize to emit edges where the interview mapping declares an upstream relationship (populating `source_urns` for currently-empty consumer-pack sections) so the DRG lint passes — without fabricating edges absent evidence. | Medium | Open |
| FR-013 | Rename the resynthesize-pipeline footgun | As a maintainer, I want the mis-named `run_resynthesize_pipeline` (which calls full synthesize) corrected so activation flows do not reintroduce loss through a misleading name. | Low | Open |
| FR-014 | Conflict/refusal messaging via a typed conflict object | As an operator, I want refusal/prune/dry-run output to use a `ReconciliationConflict` (kind + target id + backing artifact + remediation line) — a new object in `reconcile.py` modeled after the DRG typed-conflict shape (not reusing `merge.py`) — so every reported class is actionable. | Medium | Open |

> **Scope of "drop nothing" (bounds FR-001 / NFR-001 honestly).** Preservation applies to nodes
> **not in the current target set** (and their edges). Edges of **re-targeted** nodes — those the
> current run recomputes — are **authoritatively regenerated**: `_merge_project_overlay` replaces
> every edge whose `source` is in the fresh target set with the freshly-emitted edges for that
> source, and only preserves edges whose `source` is outside it. So "zero silent deletions" means
> no loss of *untargeted* backed content; it is not a promise to freeze the edges of a node the run
> deliberately re-emits.

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Zero silent deletions | Across all synthesize entry points, the count of graph nodes/edges OR manifest entries removed without either `--prune` or an explicit listed refusal is exactly 0, enforced by regression tests. | Reliability | High | Open |
| NFR-002 | No-op stability preserved | An identical re-synthesis produces byte-identical `graph.yaml` AND manifest (0 changed bytes), preserving #1912. | Reliability | High | Open |
| NFR-003 | No new hard-crash paths | Reconciliation introduces 0 new uncaught exceptions on the "backed content the current run omits" inputs; such conflicts route to the report channel (measured by tests covering duplicate-triple and dangling-endpoint preserved content). | Reliability | High | Open |
| NFR-004 | Synthesis overhead bound | **Acceptance**: the existing performance-envelope test stays green (the absolute ~30s envelope). The "≤ 20% wall-clock overhead versus current synthesize on an overlay of up to 200 nodes" is an **informational target only** — there is no relative before/after benchmark in the suite, only the absolute envelope, so it is not independently gated. | Performance | Medium | Open |
| NFR-005 | Clean static analysis | New/changed code passes `ruff` and `mypy` with zero new issues and no new suppressions; complexity ≤ 15. | Maintainability | High | Open |
| NFR-006 | Curated charter.md untouched | Boundary auto-refresh changes 0 bytes of a curated `charter.md` (honors #2772). | Reliability | High | Open |
| NFR-007 | No fabricated edges | Synthesize emits 0 edges lacking licensing evidence (no relationship inferred without a declared `source_urns`). | Correctness | Medium | Open |
| NFR-008 | Coverage on new branches | Every new branch/helper (reconcile, prune, delta, conflict-report, edge-wiring) has focused direct tests in the same PR; new-code coverage meets the project gate. | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Anchor to the DRG conflict *shape* (model after, don't reuse) | Behavior conforms to ADR `2026-07-26-3`'s warn/report posture (hard-fail reserved). The mission introduces a NEW `ReconciliationConflict` in `src/charter/activation/synthesizer/reconcile.py` **modeled after** the `src/doctrine/drg/merge.py` typed-conflict/remediation shape — `merge.py` is the org-pack fragment-merge subsystem (closed `kind` Literal, no `duplicate_triple`, no `backing_artifact`/`remediation`) and is NOT reused or edited; the synthesize path's `validate_graph` returns `list[str]`, so this is net-new translation. ADR `2026-05-16-1` applies only as the field-grain non-destruction precedent. | Technical | High | Open |
| C-002 | Reuse canonical reconciliation | Preservation reuses the existing `resynthesize` primitives — `_merge_project_overlay` (graph) AND `_rewrite_manifest` (manifest) — not a parallel hand-rolled merge. | Technical | High | Open |
| C-003 | P0 spine independently landable | The P0 spine (FR-001..009 + the committed test) — which now includes the non-destructive boundary heal (FR-008) — must be shippable even if the folded slices (FR-010..014) run long; the P2/P3 work must not gate the release-blocker. | Business | High | Open |
| C-004 | Same-PR test + remediation | The red-first reproduction test and the remediation ship in the same pull request (test not marked `regression`/`quarantine`). | Technical | High | Open |
| C-005 | Terminology guard on touched surfaces | Run `tests/architectural/test_no_legacy_terminology.py` on the `src/charter/`, `src/doctrine/`, and `docs/` surfaces the mission edits (the guard excludes `kitty-specs/`); honor the Terminology Canon (Mission, not feature). | Technical | Medium | Open |

### Key Entities

- **Project DRG overlay (`graph.yaml`)**: nodes + edges authored over the built-in DRG; the
  artifact truncated by the defect. Nodes reference backing artifact files; edges reference
  source/target URNs.
- **Synthesis manifest**: registry of synthesized artifacts + `bundle_content_hash`;
  reconciled with the overlay under the same contract.
- **Backing doctrine artifact**: the per-node `.yaml` under `.kittify/doctrine/**`; its
  presence defines "backed" vs "orphaned" content.
- **Reconciliation delta**: added / retained / removed nodes, edges, and manifest entries;
  surfaced by dry-run and refusal/prune output.
- **Freshness substate `synthesized_drg`**: the stale/fresh signal the boundary preflight
  gates on; a non-destructive heal must resolve it to fresh.
- **ReconciliationConflict**: a new typed object in `reconcile.py` (kind + target id +
  backing artifact + remediation + provenance), modeled after — not reusing — the DRG
  typed-conflict shape; used for refusal/prune/dry-run reporting.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A routine `charter synthesize` over an overlay containing backed content the
  current target set omits results in 0 silently deleted nodes/edges/manifest entries (100%
  preserved unless `--prune`).
- **SC-002**: An operator who makes an authoring-only charter edit can run `implement`/`next`
  to completion with 0 governance content deleted and 0 trapped states, and a second run is
  not re-blocked (`synthesized_drg` is fresh). The "0 trapped states" guarantee is scoped to the
  **backed/authoring-only** cause; an **orphaned** node or an **unparseable overlay** still blocks
  at the boundary — by design, non-destructively — with an actionable `blocked_reason` (name +
  remediation), never a silent prune.
- **SC-003**: `charter synthesize --dry-run` reports 100% of the nodes/edges/manifest entries
  a `--prune` run would remove, before any file is written.
- **SC-004**: Synthesized consumer-pack overlays pass the DRG lint with 0 orphaned
  just-generated directives, and 0 fabricated edges are emitted.
- **SC-005**: Across all four entry points (manual synthesize, `--prune`, boundary
  auto-refresh, activate/deactivate), 0 nodes/edges/manifest entries are dropped without an
  explicit listed action, verified by regression tests (the previously-red reproduction and
  the added prune/dry-run/heal/edge tests pass; the charter slice stays green in CI).
