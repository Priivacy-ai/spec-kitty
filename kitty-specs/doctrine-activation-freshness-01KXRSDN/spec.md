# Mission Specification: Doctrine-activation freshness integrity

**Mission Branch**: `feat/doctrine-activation-freshness`
**Created**: 2026-07-17
**Status**: Draft
**Input**: Functional slice of epic #2519 (Charter authoring & lifecycle robustness). Folds #2770, #2759, #2758, #2157. Grounded by an architect-alphonso design-seam lens on `main` @ `7bc635aa7`.

## Context & Problem *(why this mission exists)*

Epic #2519's root finding: **`config.yaml` `activated_*` and the derived doctrine
signals are disjoint ledgers with no reconciler.** Concretely — `charter activate`
and `charter deactivate` route every write through a single chokepoint,
`charter.activation_engine.commit_plan`, which writes **exactly one file:
`.kittify/config.yaml`**. It never runs `sync` (which writes
`governance/directives/metadata.yaml`), never runs `generate` (which compiles
`references.yaml`), never runs `synthesize`/`regenerate-graph` (which writes the
DRG `graph.yaml`), and never re-stamps the manifest.

The just-landed #2732 content-identity freshness signal
(`charter.bundle.compute_bundle_content_hash`) hashes **four** bundle files —
`governance.yaml`, `directives.yaml`, `references.yaml`, `metadata.yaml` — and the
read-side comparator (`freshness/computer.py::_compute_synthesized_drg`)
recomputes that hash and compares it to the manifest stamp. **`config.yaml` is not
among the four hashed files.** So the content-identity signal is, by construction,
**blind to activation**: you can `charter activate` a directive and every freshness
gate still reports fresh, because nothing the gate hashes changed.

This is not a one-off. It is a **recurring, revision-driven drift class** that has
surfaced four times in the same window and has a year-long paper trail:

- **#2770** — a built-in procedure (`red-main-release-discipline`) was activated as
  a doctrine source without regenerating the shipped `graph.yaml` or wiring its
  charter citation into compiled references → 4 DRG tests went red. (The S-C
  landing fold already routed those to a *non-blocking* CI gate as
  `@pytest.mark.regression`; the durable fix — un-pinning them — is this mission's
  acceptance signal.)
- **#2759** — the seam itself: activate/deactivate mutate config without refreshing
  the bundle-content signal.
- **#2758** — `compute_bundle_content_hash` returns `None` when `references.yaml` is
  missing, but `sync` never writes `references.yaml` (`_SYNC_OUTPUT_FILES` omits it;
  it is compiled only by `charter generate`) → a permanent-stale that `synthesize`
  cannot self-heal.
- **#2157** — the implement-boundary preflight raises on the *first* stale
  prerequisite and bounces a clean specified+planned+analyzed mission through three
  downstream prerequisites (`charter_source → stale_analysis → synthesized_drg`)
  one-at-a-time.

The mission closes the **`activate ⇒ refresh-or-fail-closed`** seam: after a
doctrine mutation, the freshness signal must reflect the change (stale until
reconciled, or refreshed on explicit opt-in) — it must never silently report fresh
when the derived artifacts are stale.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Activation is visible to freshness (Priority: P1)

An operator runs `charter activate directive DIR-014` (or `deactivate`). Today,
every freshness gate keeps reporting "fresh" even though the compiled references and
DRG no longer reflect the active doctrine set. After this mission, the derived
freshness signal **reflects the mutation** — it reports stale (the default,
hot-path-preserving behaviour) until the derived artifacts are reconciled, so no
downstream gate can pass on a config-vs-derived mismatch.

**Why this priority**: This is the seam core (#2759) — the structural blind spot
the whole epic-slice exists to close. Every other story is either a prerequisite
correctness fix, an ergonomics improvement, or the acceptance signal for this one.

**Independent Test**: On a fresh project with a clean/fresh derived bundle, run
`charter activate <kind> <id>`, then compute freshness — the synthesized-DRG signal
reports `stale` (config↔derived mismatch), where before the change it reported
`fresh`. `deactivate` behaves symmetrically.

**Acceptance Scenarios**:

1. **Given** a project whose bundle + DRG are fresh, **When** `charter activate`
   flips an `activated_*` key in `config.yaml`, **Then** the freshness computation
   reports the derived signal as **stale** (not silently fresh).
2. **Given** the same project, **When** the operator then reconciles (via the
   documented refresh path), **Then** the signal returns to **fresh**.
3. **Given** a mismatch between `config.yaml` and compiled `references.yaml`/`graph.yaml`,
   **When** the freshness/preflight signal is computed, **Then** the existing
   `run_consistency_check` parity is consulted and the mismatch surfaces as a
   blocking, actionable condition rather than a silent pass.

---

### User Story 2 - The shipped DRG is durably fresh (Priority: P1)

The four DRG-staleness tests currently carry `@pytest.mark.regression` (accepted-red,
routed to a non-blocking CI gate). After this mission they pass as **ordinary
tests**: the shipped `graph.yaml` is regenerated, the charter→reference citation is
compiled into references, and the zero-delta baseline is re-frozen so a fresh
regeneration is byte-identical to what ships.

**Why this priority**: This is the mission's concrete **acceptance signal** for
#2770 and, transitively, proof the seam holds — the drift that made these tests red
is exactly the drift the seam prevents recurring.

**Planning constraint (operator decision 2026-07-17)**: #2770 is release-sensitive
(P0 per the red-main ADR). US2/FR-004 (the durable un-pin) MUST be planned as an
**early / standalone work package** — landable ahead of, and independent from, the
seam WPs (#2758→#2759→#2157a) — so a release-gating fix is not held behind the whole
mission. It has no hard dependency on the seam mechanism; the seam prevents
*recurrence*, the un-pin clears the *current* red.

**Independent Test**: The 4 tests (`test_no_new_charter_reference_danglers`,
`TestDRGZeroDelta::test_regenerated_graph_matches_baseline_counts`,
`TestDRGZeroDelta::test_shipped_graph_is_fresh_and_byte_identical`,
`test_check_reports_committed_graph_fresh`) pass with their `@pytest.mark.regression`
markers removed; `spec-kitty doctrine regenerate-graph --check` is green.

**Acceptance Scenarios**:

1. **Given** the shipped doctrine source, **When** the graph is regenerated,
   **Then** it is byte-identical to the committed `graph.yaml` and the zero-delta
   baseline counts match.
2. **Given** a charter that cites a built-in doctrine artifact, **When** references
   are compiled, **Then** no dangling charter reference remains
   (`test_no_new_charter_reference_danglers` passes un-pinned).

---

### User Story 3 - The freshness signal is definitionally correct (Priority: P2)

A project that has synced but not yet run `charter generate` is missing
`references.yaml`. Today `compute_bundle_content_hash` returns `None` → permanent
stale that `synthesize` cannot clear. After this mission the signal is either
computed over the files that actually exist, or the operator is told exactly which
step (`charter generate`) to run — no dead-end permanent-stale.

**Why this priority**: A definitional bug in the freshness input-set (#2758) that
must be fixed *before* wiring more consumers onto the signal (US1), otherwise the
seam inherits a false-stale. Sequenced first among the correctness fixes.

**Independent Test**: On a project missing `references.yaml`, freshness no longer
returns an un-clearable `None`; the resolution path (narrow-hash or fail-closed
preflight — see Q1) is deterministic and self-healing or actionable.

**Acceptance Scenarios**:

1. **Given** a project with `governance/directives/metadata.yaml` present but
   `references.yaml` absent, **When** freshness is computed, **Then** the result is
   not a permanent-stale `None` that `synthesize` cannot resolve.
2. **Given** the same project, **When** the operator follows the surfaced recovery
   step, **Then** the signal resolves to a definite fresh/stale verdict.

---

### User Story 4 - The prerequisite gate reports in one pass (Priority: P2)

An operator with a clean specified + planned + analyzed mission hits the implement
boundary. Today the gate raises on the first stale prerequisite, they fix it, re-run,
hit the second, fix it, re-run, hit the third — three round-trips. After this
mission the charter-owed prerequisite set is computed in **one pass** and reported
together.

**Why this priority**: A UX/ergonomics fix (#2157a) on the same freshness substrate.
Valuable but not the structural core; the analyzer-freshness coupling (#2157b) is a
different subsystem and is fenced out (C-004).

**Independent Test**: With multiple charter-owed prerequisites stale, the
implement-boundary preflight enumerates the full owed set in a single invocation
rather than raising on the first.

**Acceptance Scenarios**:

1. **Given** a mission with `charter_source`, synced-bundle, and synthesized-DRG all
   owing refresh, **When** the implement preflight runs, **Then** it reports all
   outstanding charter-owed prerequisites at once (one pass), not one-at-a-time.

---

### User Story 5 - Opt-in eager resynthesis (Priority: P3)

An operator who wants the derived artifacts refreshed immediately on activation
passes `charter activate <kind> <id> --resynthesize`; the derived bundle/DRG are
refreshed as part of the command. Without the flag, activation stays fast (no
synthesis) and the signal simply reports stale until a later reconcile.

**Why this priority**: The ergonomic escape hatch that makes fail-closed-by-default
tolerable, without paying synthesis cost on every routine activation. P3 because the
seam is sound (US1) even if the operator always reconciles separately.

**Independent Test**: `charter activate … --resynthesize` leaves the derived signal
**fresh** immediately after the command; `charter activate …` without the flag
leaves it **stale** and spawns no synthesis subprocess.

**Acceptance Scenarios**:

1. **Given** a fresh project, **When** `charter activate <kind> <id> --resynthesize`
   runs, **Then** the freshness signal is fresh immediately afterward.
2. **Given** a fresh project, **When** `charter activate <kind> <id>` runs without
   the flag, **Then** the signal is stale and **no** synthesis/regenerate subprocess
   was spawned (hot-path preserved).

---

### Edge Cases

- **Upgrade migration path** — `spec-kitty upgrade`'s `m_unify_charter_activation`
  migration drives `promote_activations` through the same chokepoint. It must stay
  lightweight: the seam must **not** make the migration trigger synthesis (NFR-003).
- **Org-pack `required_*` union** — `doctrine/org_charter.py` fans activations in via
  `promote_activations`; same lightweight constraint.
- **Fresh-seed early-exit** — a never-synthesized project must still short-circuit to
  the #2732 fresh-seed early-exit and not be forced stale spuriously.
- **Cascade activation** — `charter activate … --cascade` flips several keys in one
  command; the seam must reconcile/invalidate once, not per-artifact.
- **Deactivation to empty** — deactivating the last artifact of a kind must reflect
  in the signal identically to activation.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Activation reflected in freshness | As an operator, I want `charter activate`/`deactivate` to make the derived freshness signal reflect the config mutation so that no downstream gate passes on a config↔derived mismatch. | High | Open |
| FR-002 | Consistency-parity wired into freshness | As a maintainer, I want the existing `run_consistency_check` config↔references / config↔graph parity consulted by the freshness/preflight signal so that an un-derived activation is detectable without eager regeneration. | High | Open |
| FR-003 | Fail-closed by construction | As a maintainer, I want a doctrine mutation with no reconciliation to report **stale** (gate blocks), never silently fresh, so drift cannot slip past a green gate. | High | Open |
| FR-004 | Shipped DRG regenerated + citation compiled | As a maintainer, I want the shipped `graph.yaml` regenerated, the charter→reference citation compiled, and the zero-delta baseline re-frozen so the 4 `@regression` DRG tests pass un-pinned. | High | Open |
| FR-005 | Freshness input-set correctness | As an operator, I want a missing `references.yaml` to not yield a permanent-stale `None` that `synthesize` cannot heal, so freshness always resolves to a definite, actionable verdict. | Medium | Open |
| FR-006 | One-pass prerequisite gate | As an operator, I want the implement-boundary preflight to enumerate the full charter-owed prerequisite set in one pass instead of raising on the first. | Medium | Open |
| FR-007 | Opt-in `--resynthesize` | As an operator, I want `charter activate`/`deactivate --resynthesize` to eagerly refresh the derived bundle/DRG, while the default stays fast (no synthesis). | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Activation hot-path preserved | Default `charter activate`/`deactivate` (no `--resynthesize`) spawns **zero** synthesis/`regenerate-graph` subprocesses and adds no new filesystem graph walk; measured by a call-count/subprocess spy. | Performance | High | Open |
| NFR-002 | #2732 machinery not regressed | The content-identity freshness machinery — per-file BOM-strip/CRLF hash recipe, write-side manifest stamps, `built_in_only` read-time normalization, fresh-seed early-exit — is preserved; its existing tests stay green (no behavioural change to the hash of an unchanged bundle). | Reliability | High | Open |
| NFR-003 | Upgrade migration unaffected | `spec-kitty upgrade`'s `promote_activations` path (incl. `m_unify_charter_activation`) triggers no synthesis and pays no new per-call cost. | Reliability | High | Open |
| NFR-004 | DRG zero-delta | After regeneration, `spec-kitty doctrine regenerate-graph --check` is green and a fresh regeneration is byte-identical to the committed `graph.yaml`; baseline node/edge/orphan counts re-frozen exactly. | Reliability | High | Open |
| NFR-005 | Clean gates | ruff + mypy `--strict` clean, zero new suppressions; cyclomatic complexity ≤ 15 per function; literals appearing ≥ 3× hoisted to constants. | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Layer boundary | `commit_plan` stays pure `charter` layer and must not import `specify_cli` or write a `specify_cli`-owned marker; any reconcile/invalidation orchestration that needs the synthesis pipeline lives at the CLI / `promote_activations` layer or in the freshness read-path, never in the chokepoint. | Technical | High | Open |
| C-002 | No eager-always regen | Design (a) "regenerate-on-activate as the default" is rejected: it inverts the layer boundary, taxes the activation hot-path, and harms the migration path. Regeneration on activate is **opt-in only** (`--resynthesize`). | Technical | High | Open |
| C-003 | #2760 out of scope | Overlay-vs-new-built-in DRG URN collision on `spec-kitty upgrade` is an upgrade⇒overlay-revalidation concern owned by the DRG-model lane (#2721), not the activation seam. Note as a follow-up; do not implement here. | Technical | High | Open |
| C-004 | #2157b out of scope | The analyzer-freshness coupling (charter creation retroactively invalidating a clean analysis report) is a different subsystem from the charter/activation freshness seam. Only the charter-owed aggregation (#2157a) is in scope. | Technical | Medium | Open |
| C-005 | Writer-agnostic reconciler | `commit_plan` is the sole writer for **operator** activate/deactivate + `promote_activations`, but **not** the sole writer of `activated_*` state: `CharterPackManager.merge_defaults` (`pack_manager.py:747/753`) writes activation keys directly, bypassing the chokepoint (test-covered; ADR 2026-07-15-1 S1 slates it to provision default activation on the `init` path). The reconciler therefore MUST be **writer-agnostic** — it must see config-activation regardless of which writer produced it. | Technical | High | Open |
| C-006 | Read-path parity, not call-site enumeration | Because of the `merge_defaults` bypass (C-005), the reconciler is the **read-path** `run_consistency_check` parity (which reads `config.yaml` directly), **not** a write-side marker stamped at the ~7 known activation call-sites. A write-side marker (Q2c) is rejected: it would be blind to `merge_defaults`/`init` and re-open the config↔derived hole on the init path. Call-site enumeration is not the guard. | Technical | High | Open |
| C-007 | Reuse `consistency_check` | The config↔references / config↔graph parity is the **already-built** `run_consistency_check` (`consistency_check.py:645`; sole production caller today is the `charter consistency-check` CLI at `pack.py:30` — NOT the freshness/preflight path). Wire it into the read-path; do not reimplement a parallel parity check. | Technical | Medium | Open |

### Key Entities

- **Activation ledger** — `.kittify/config.yaml` `activated_<kind>` keys, written
  solely by `commit_plan`. The mutation source the freshness signal is currently
  blind to.
- **Bundle-content signal** — `compute_bundle_content_hash` over the four bundle
  files, stamped into the manifest and recomputed by `_compute_synthesized_drg`. The
  #2732 machinery to preserve.
- **Consistency parity** — `run_consistency_check` with `_check_reference_id_parity`
  (config↔references) and `_check_graph_kind_parity` (config↔graph): built, but
  currently unwired from the freshness/gate path.
- **Prerequisite owed-set** — the collection of charter-owed refresh steps the
  implement-boundary preflight (`_attempt_auto_refresh` / `_require_current_*`)
  enumerates; today raised one-at-a-time.

## Known Open Questions *(resolve in /plan — not blocking spec)*

- **Q1 (#2758 fork)**: narrow the content-hash to the sync triad
  (`governance/directives/metadata`), OR keep the four-file hash and add a
  fail-closed synthesize preflight that tells the operator to run `charter generate`
  first? Determines whether `references.yaml` drift is covered by the signal at all.
  **Coordination dependency (#2773)**: #2773 (under this same epic #2519) deprecates
  `references.yaml` and makes `charter.yaml` authoritative — it *retires the 4th
  hashed file*. Q1 must not ship a `references.yaml`-shaped stopgap that #2773 then
  rips out (its body already flags the #2767 references recompile as exactly that
  anti-pattern). The fail-closed-preflight fork leaves #2773 clean; the
  narrow-to-triad fork pre-empts/overlaps it and must be coordinated with #2773's
  owner. Resolve in /plan with #2773 in view.
- **Q2 (#2759 mechanism)**: make config-activation visible by (a) wiring the existing
  `run_consistency_check` parity into the freshness read-path [grounding
  recommendation — **now strongly favoured**], (b) pulling `config.yaml` into the
  content-hash [couples config↔bundle, contradicts the deliberate file separation], or
  (c) a separate invalidation marker stamped at the write-path? **Code-state finding
  (paula):** option (c) is **rejected** — `merge_defaults` (`pack_manager.py:747`)
  writes `activated_*` outside `commit_plan` and is ADR-slated for the `init` path, so a
  write-side marker would be blind to it and re-open the hole on init. Option (a) reads
  `config.yaml` directly (`consistency_check.py:_load_raw_activation_lists:197`) and is
  therefore **writer-agnostic** — it dominates. /plan should confirm (a) unless a
  concrete objection surfaces.
- **Q5 (#2758 dual-edit contract)**: if Q1 chooses narrow-to-triad, BOTH
  `bundle.py:47 BUNDLE_CONTENT_HASH_FILES` and `computer.py:137 _BUNDLE_FILES` must
  change together (intentional documented duplicate per data-model Decision 5). Note
  also: `bundle.py:110-119 CANONICAL_MANIFEST.derived_files` lists **3** files
  (references.yaml excluded) while the hash set is **4** — a pre-existing internal
  disagreement the #2758 WP must reconcile deliberately, not blind-match one to the other.
- **Q3 (reconciler placement)**: given C-001, where does the reconcile/invalidation
  responsibility sit — CLI command layer, `promote_activations`, or the freshness
  read-path?
- **Q4 (#2770 home)**: is the shipped-DRG regeneration an in-mission WP, or a sibling
  slice? Its fix is entangled with the doctrine-synthesis pipeline (fixture
  adapters); its acceptance (the 4 tests) is concrete either way.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The 4 `@pytest.mark.regression` DRG-staleness tests pass with their
  markers removed; `spec-kitty doctrine regenerate-graph --check` is green. *(FR-004; #2770)*
- **SC-002**: On a fresh project, `charter activate <kind> <id>` makes the
  synthesized-DRG freshness signal report **stale** (where it previously reported
  fresh); reconciliation returns it to fresh. *(FR-001/FR-002/FR-003; #2759)*
- **SC-003**: A project missing `references.yaml` never yields a permanent-stale
  `None`; freshness resolves to a definite verdict or a single actionable recovery
  step. *(FR-005; #2758)*
- **SC-004**: The implement-boundary preflight reports all outstanding charter-owed
  prerequisites in one pass. *(FR-006; #2157a)*
- **SC-005**: Default `charter activate` spawns **zero** synthesis/regenerate
  subprocesses (verified by spy); `--resynthesize` leaves the signal fresh
  immediately; the `spec-kitty upgrade` migration path is unaffected. *(FR-007, NFR-001, NFR-003)*
- **SC-006**: The #2732 content-identity tests remain green; the hash of an unchanged
  bundle is unchanged by this mission. *(NFR-002)*
