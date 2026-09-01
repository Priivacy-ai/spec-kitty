# Mission Specification: Cascade drops asset-kind targets with no report

**Mission Branch**: `fix/cascade-asset-silent-drop-3705`
**Created**: 2026-08-24
**Status**: Specified
**Input**: GitHub issue [#3705](https://github.com/Priivacy-ai/spec-kitty/issues/3705) — "A cascade drops every `asset`-kind target with no report, so a pack's executable check is unreachable and unmentioned"

## Summary

`charter activate ... --cascade all` silently drops every DRG edge whose target is a
non-charter-activatable kind (`template`, `asset`): no activation line, no warning line,
no "skipped" line, exit 0. The dropped node is not collected anywhere in
`src/charter/cascade.py`, so nothing downstream — the cascade activation report, the
no-cascade warning, or a future consumer — can say it existed. From the operator's side, an
edge pointing at a structurally non-activatable kind is indistinguishable from an edge that
failed to resolve and from an edge that does not exist at all. This is the D-005 ("degrade,
but never silent") half of the asset gap; the executable half (actually invoking a
pack-shipped code asset as a gate handler) is tracked separately as #2599 and is explicitly
out of scope here.

This mission makes the drop loud: every kind-filtered node the cascade reaches is collected
and reported, by name, in both the cascade-activation report and the no-cascade warning
path, labelled as structurally non-activatable rather than as a failure. A cascade that
resolves zero activatable targets says so explicitly instead of printing nothing.

## Clarifications

**Q: How verbose should the new "not cascaded: kind not charter-activatable" diagnostic be?**

**A — Option A (chosen): always render one line per dropped kind-filtered node, in BOTH the
cascade report and the no-cascade warning path.** This matches the issue's suggested shape
and its literal reproduction (same command, both edges reported) and closes the issue as
filed.

**Accepted consequence**: cascade output volume rises for every source reaching
`template`/`asset` — most visibly, every mission-type `--cascade all` now prints a line per
template reached via `instantiates`. ADR
[2026-08-20-1](../../docs/adr/3.x/2026-08-20-1-cascade-kind-complete-relation-set.md) lists
the *removal* of that noise ("for all 137 affected sources") as one of its positive
consequences, so this change knowingly trades some of that back for diagnosability. See
NFR-002 and C-003 below, which make this trade-off an explicit, PR-body-visible requirement
rather than a silent reversal.

**Required**: the eventual PR body must cite ADR 2026-08-20-1 explicitly and explain that
this is a visibility change, NOT a reversal of the kind-exclusion policy — so a maintainer
does not read it as quietly undoing that ADR. This is FR-006 / C-003 below, not left to be
lost by mission close.

**Options considered and rejected** (recorded so a later reviewer does not re-propose them):

- **Option B — only report dropped nodes when the cascade resolves zero activatable targets
  overall.** Rejected: the issue's own reproduction (tactic activates, asset silently drops)
  would STILL print nothing for the asset edge, because the tactic edge already gives a
  non-empty result — under-delivers against the issue as filed.
- **Option C — gate the per-node listing behind a new opt-in flag (e.g.
  `--show-skipped-kinds`), default off.** Rejected: default `charter activate ...
  --cascade all` output stays silent by default, which is exactly the behavior #3705 reports
  as broken.

This decision was made by the operator during mission readiness review (readiness probe
3705-cascade-asset-silent-drop, Q1/Option A recommendation, operator-confirmed).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cascade activation reports the kind-filtered nodes it drops (Priority: P1)

As a doctrine-pack author running `charter activate <kind> <id> --cascade all` on a pack
whose DRG declares an edge to an `asset`- or `template`-kind node (e.g. a validator/lint
script shipped in `assets/`), I want the CLI to tell me that edge was reached but could not
be cascade-activated, so that I can see the asset exists in governance output and is not
silently unreachable from every direction.

**Why this priority**: this is the literal reproduction in issue #3705 and the mission's
primary deliverable — without it, the issue is not closed.

**Independent Test**: run `charter activate toolguide qa-carrier-lint --cascade all` against
an org pack whose `drg/fragment.yaml` declares one node with two outgoing `suggests` edges —
one to a `tactic`, one to `asset:qa-traceability-lint` (the issue's own repro fixture shape).
Confirm the tactic edge produces a `Cascade-activated:` line (unchanged) AND the asset edge
now produces a distinct, kind-labelled "not cascaded" line — not silence.

**Acceptance Scenarios**:

1. **Given** a DRG source with both an activatable-kind edge and an `asset`-kind edge,
   **When** `charter activate <kind> <id> --cascade all` runs, **Then** the console output
   contains one `[cyan]Cascade-activated[/cyan]` line for the activatable target AND one
   distinct line for the `asset` target that names its kind and ID and states it was not
   cascaded because the kind is not charter-activatable (not phrased as an error/failure).
2. **Given** a DRG source whose *only* outgoing reference-relation edges target
   non-activatable kinds (e.g. only `asset`/`template`), **When** `--cascade all` runs,
   **Then** the console explicitly states that the cascade resolved zero activatable targets
   (not silence, not just the per-node lines with no summary) — closing the issue's step 3
   ask.
3. **Given** a DRG source with no outgoing reference-relation edges at all, **When**
   `--cascade all` runs, **Then** behavior is unchanged from today (no activation lines, no
   kind-filtered lines) — a source that references nothing is not a defect and must not be
   reported as one.
4. **Given** a DRG source whose referenced nodes are ALL activatable-kind (zero
   kind-filtered nodes among them) but every one is excluded by a narrow `--cascade <scope>`
   (e.g. `--cascade tactic` against a source that only references `directive` nodes), **When**
   the cascade runs, **Then** the console shows only the existing per-node
   `Skipped (out of scope)` lines and the FR-004 zero-activatable-targets message does NOT
   appear — this is pure scope-narrowing, already fully communicated by the per-node lines,
   and must not be conflated with the kind-filtered zero-target case in Scenario 2.

**FAILS if**: the asset/template edge in Scenario 1 produces no line at all (today's bug,
reproduced red-first before the fix); or the zero-target case in Scenario 2 exits 0 with
empty output; or Scenario 3 gains a spurious "zero activatable targets" line where none
existed before (over-reporting a source that has nothing to report); or Scenario 4's
pure-scope-narrowing case (zero kind-filtered nodes, zero land in `activated`) also prints
the FR-004 zero-activatable-targets message (over-reporting a case already fully covered by
the per-node `Skipped (out of scope)` lines).

---

### User Story 2 - No-cascade warning path reports the same kind-filtered nodes (Priority: P1)

As an operator who runs `charter activate <kind> <id>` **without** `--cascade`, I want the
existing "referenced but not activated" warning to also name kind-filtered nodes (labelled
distinctly from scope-skip and from "would activate with --cascade"), so the two render
paths agree on what a source references and I am not misled by one path being louder than
the other.

**Why this priority**: the issue's suggested shape (step 2) explicitly asks for both render
paths; the readiness probe's Option A requires it; leaving this path silent while fixing only
the cascade-report path would reintroduce the exact asymmetry-and-partial-fix risk the
Clarifications section rejects (Option B).

**Independent Test**: run `charter activate <kind> <id>` with no `--cascade` flag against the
same fixture as User Story 1's Independent Test. Confirm the existing
`[yellow]Warning[/yellow]: referenced .../was not activated (no --cascade)` line still
appears for the activatable target, AND a new, distinctly-labelled line appears for the
`asset` target that does NOT suggest re-running with `--cascade` (since re-running with
`--cascade` would not activate it either — that would be a misleading recovery hint).

**Acceptance Scenarios**:

1. **Given** the same mixed-kind DRG source as User Story 1, **When** `charter activate
   <kind> <id>` runs with no `--cascade`, **Then** the activatable target gets the existing
   no-cascade warning line (recovery hint: re-run with `--cascade`), and the `asset` target
   gets a separate line stating it is structurally non-activatable — never the same wording,
   and never the recovery hint that implies `--cascade` would fix it.
2. **Given** a DRG source whose *only* outgoing reference-relation edges target
   non-activatable kinds (no activatable-kind refs at all — e.g. only `asset`/`template`),
   **When** `charter activate <kind> <id>` runs with no `--cascade`, **Then** the
   kind-filtered line(s) still render, even though there is no activatable-kind ref present
   to keep the render path's own "anything to report" guard true. This closes the exact gap
   where `NoCascadeReport.has_skipped` (`src/charter/cascade.py:407-410`,
   `any(self.skipped.values())`) inspects only the pre-existing `skipped` dict: a source with
   zero activatable refs leaves `skipped` empty, so `has_skipped` alone must NOT be the sole
   gate on `_render_no_cascade_warning` (`src/specify_cli/cli/commands/charter/activate.py:383-417`)
   rendering anything — the guard must also evaluate true when the new kind-filtered field is
   non-empty.

**FAILS if**: the asset target's line reuses the "no --cascade" recovery hint verbatim
(misleading — re-running with `--cascade` does not activate an asset); or the asset line is
missing entirely (today's bug in this path too — the readiness probe's blast radius names
`_render_no_cascade_warning` as in scope, not just `_render_cascade_activation`); or a source
whose only referenced nodes are kind-filtered produces no output at all because the render
guard only checked the (empty) `skipped` dict — reproducing the exact silent-drop bug #3705
reports, one level up, inside the fix itself.

---

### User Story 3 - `charter deactivate --cascade` agrees with `charter activate --cascade` on what a source references (Priority: P2)

As an operator, when I run `charter deactivate <kind> <id> --cascade all` on the same source
that a prior `charter activate ... --cascade all` reported a kind-filtered node for, I want
the deactivation-side cascade report to name that same kind-filtered node (not silently
disagree with the activation-side report), because activation and deactivation share the
single `_referenced_artifacts` seam (ADR 2026-08-20-1's stated symmetry requirement).

**Why this priority**: P2, not P1 — deactivation cascades only fire when `--cascade` is
explicitly supplied (there is no deactivation-side "no-cascade warning" equivalent to FR-013
of the prior mission), so the blast radius here is narrower than User Stories 1/2, but the
ADR's symmetry requirement is explicit and binding, and this repo's own doctrine treats an
asymmetric fix as a defect class, not a lesser concern.

**Independent Test**: activate the fixture from User Story 1 with `--cascade all`
(kind-filtered line appears for the asset target), then run `charter deactivate <kind> <id>
--cascade all` on the same source and confirm the equivalent kind-filtered line appears in
the deactivation output too (not `Cascade-deactivated`, not `Skipped (shared artifact)` — a
third, distinctly-labelled line matching the activation side's wording/kind).

**Acceptance Scenarios**:

1. **Given** a DRG source whose forward-reference closure includes an `asset`-kind node,
   **When** `charter deactivate <kind> <id> --cascade all` runs, **Then** the console names
   that node as not-cascaded/kind-not-charter-activatable, using language consistent with the
   activation-side rendering (same underlying data source), not silence.

**FAILS if**: `charter activate --cascade all` reports a kind-filtered node for a source but
`charter deactivate --cascade all` on the same source reports nothing for it — the asymmetry
the ADR's "Symmetry" section explicitly forbids.

### Edge Cases

- **A source with zero reference-relation edges of any kind** (Scenario 3, User Story 1):
  must NOT gain a spurious "resolved zero activatable targets" line — that phrasing is
  reserved for a source that *reaches* something but none of it is activatable, not a source
  that reaches nothing. Distinguish "nothing referenced" from "referenced nothing
  activatable" in the implementation and in the rendered text.
- **A source reaching the same kind-filtered node via two different paths** (e.g. both
  `requires` and `instantiates` land on the same `template:x`): the existing
  `_forward_reference_closure` already de-duplicates by URN before kind-filtering: this must
  render as ONE line, not two, for that node.
- **`--cascade` with an explicit non-`all` scope** (e.g. `--cascade agent-profile,tactic`)
  reaching a `template`/`asset` node: the node is still structurally non-activatable
  regardless of scope — it must be reported as kind-filtered (not as `skipped_by_scope`,
  which is a different, pre-existing bucket for activatable kinds the operator's scope string
  excluded). The two must remain visibly distinct in the rendered output; conflating them
  would make an operator believe re-running with a wider `--cascade` scope would activate a
  kind that structurally cannot be activated.
- **A running mission or script parsing today's cascade output** (Reflexivity — see NFR-004):
  today's output has a fixed set of line shapes (`Cascade-activated:`, `Warning: ... was not
  activated (no --cascade)`, `Skipped (out of scope)`, `Skipped (shared artifact)`). This
  mission adds a new, additional line shape; it does not remove, rename, or reorder any
  existing line. A parser matching on today's exact strings continues to match unchanged
  lines; a parser that assumed cascade output was exhaustive of everything a source
  references was already wrong (that is the bug this mission fixes) and will now see more,
  not less, information.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Collect kind-filtered nodes at the shared seam | `_referenced_artifacts` (`src/charter/cascade.py:266-295`) currently drops a reached node via a bare `continue` (line 291-292) when its kind is not in `CHARTER_ACTIVATABLE_KINDS`, with no collection anywhere. As a maintainer, I want this function's existing single loop over `reachable` (cascade.py:266-295) — the one place in the codebase that tests `kind not in CHARTER_ACTIVATABLE_KINDS` — to return both partitions (the existing activatable-refs list plus the dropped nodes: kind + bare ID + URN) from that same pass, so every caller of this seam can report them instead of losing them. A separate "sibling helper" implementation is permitted only if it calls this single shared kind-classification test rather than re-running `_forward_reference_closure` and reimplementing the `kind not in CHARTER_ACTIVATABLE_KINDS` check as a second, independently-maintained copy — there must be exactly one place in the codebase that decides kind-filtered-vs-activatable. | P1 | Open |
| FR-002 | Thread dropped nodes through `CascadeActivationResult` | As the cascade-activation caller, I want `cascade_activation_targets` (`src/charter/cascade.py:340-379`) to populate a new field on `CascadeActivationResult` (alongside the existing `activated` / `skipped_by_scope`) carrying the kind-filtered nodes, so `_render_cascade_activation` has real data to render (User Story 1). | P1 | Open |
| FR-003 | Render kind-filtered nodes in the cascade-activation report | As an operator, I want `_render_cascade_activation` (`src/specify_cli/cli/commands/charter/activate.py:274-338`) to print one line per kind-filtered node, labelled distinctly from `Cascade-activated` and `Skipped (out of scope)`, stating the kind is not charter-activatable — never phrased as a warning/error/failure (User Story 1, Scenario 1). | P1 | Open |
| FR-004 | Explicit zero-activatable-targets message | As an operator, when `cascade_activation_targets` resolves at least one referenced node, zero of them land in `activated`, AND at least one of the referenced nodes is specifically kind-filtered (not merely scope-excluded), I want `_render_cascade_activation` to print one explicit line saying the cascade resolved zero activatable targets, distinct from and in addition to the per-node kind-filtered lines (User Story 1, Scenario 2; issue's suggested-shape step 3). The trigger is scoped to the kind-filtered case, not the broader "zero landed in `activated`" condition: a pure scope-narrowing case (every referenced node is activatable-kind but excluded by a narrow `--cascade <scope>`, zero kind-filtered nodes involved) is already fully communicated by the per-node `Skipped (out of scope)` lines and does NOT trigger this message — adding it there would be redundant with information already rendered. A source with zero referenced nodes at all (Edge Case 1) must NOT trigger this line either. | P1 | Open |
| FR-005 | Thread dropped nodes through `NoCascadeReport` and render them | As the no-cascade-warning caller, I want `referenced_but_not_cascaded` (`src/charter/cascade.py:413-444`) to populate an equivalent field on `NoCascadeReport`, and `_render_no_cascade_warning` (`src/specify_cli/cli/commands/charter/activate.py:383-417`) to render one line per kind-filtered node with wording that does NOT reuse the "re-run with --cascade" recovery hint (that hint would be actively misleading for a kind that `--cascade` can never activate) (User Story 2). | P1 | Open |
| FR-005a | `has_skipped`-equivalent render guard must also fire on kind-filtered-only sources | `NoCascadeReport.has_skipped` (`src/charter/cascade.py:407-410`, `return any(self.skipped.values())`) inspects ONLY the existing `skipped` dict, and `_render_no_cascade_warning` (`src/specify_cli/cli/commands/charter/activate.py:404-405`, `if not report.has_skipped: return`) gates its ENTIRE body on it. As a maintainer, I want the render guard (whether by redefining `has_skipped` to check both `skipped` and the new field, or by replacing the guard with an explicit "anything to report across both fields" check) to also evaluate `True` when kind-filtered nodes are present even if `skipped` is empty — so a source whose ONLY referenced nodes are kind-filtered still renders those lines instead of returning silently before the render loop is ever reached (User Story 2, Scenario 2). | P1 | Open |
| FR-006 | ADR-citation requirement carried into the PR | As a reviewer, I want the eventual PR body for this mission to cite ADR 2026-08-20-1 explicitly and state that this change is additive visibility, not a reversal of the `template`/`asset` exclusion — so the PR is not misread as quietly undoing that ADR's "positive consequence" of noise removal. This is a mission-completion requirement, checked at PR-open time, not a runtime behavior. It is verified by the pre-merge review squad / accept gate checking the PR body for the ADR citation before operator merge — not by a work package or an automated test, and no red-first ATDD test should be manufactured for it under charter C-011 (the plan/tasks phase must not decompose it into a WP+test); a specific reviewer step at mission close owns SC-005. | P1 | Open |
| FR-007 | Deactivation-side symmetry | As an operator, I want `deactivation_plan` (`src/charter/cascade.py:489-565`) — which already calls the shared `_referenced_artifacts` seam internally for its candidate set — to also expose the kind-filtered nodes it reaches (via a new field on `DeactivationPlan`, alongside `deactivate` / `skipped_shared`), and `_render_cascade_deactivation` (`src/specify_cli/cli/commands/charter/deactivate.py:133-194`) to render them, so `charter deactivate --cascade` agrees with `charter activate --cascade` on what a source references (User Story 3). | P2 | Open |
| FR-008 | Distinguish kind-filtered from scope-skipped in rendering | As an operator reading `--cascade <explicit-kind-list>` output, I want the kind-filtered line (structurally non-activatable) to remain visibly distinct from the existing `Skipped (out of scope)` line (activatable kind the operator's scope excluded) — different wording, never merged into one bucket — so I do not conclude that widening `--cascade` would activate a kind that never can be (Edge Case 3). | P1 | Open |
| FR-009 | One shared rendering helper defines the kind-filtered label once | FR-003, FR-005, and FR-007 each render a kind-filtered line at a different call site (`activate.py`'s `_render_cascade_activation`, `activate.py`'s `_render_no_cascade_warning`, `deactivate.py`'s `_render_cascade_deactivation`). As a maintainer, I want the exact label/wording for the new line defined in exactly ONE shared rendering helper function that all three call sites invoke, rather than each call site independently coining its own wording — so "labelled distinctly" (FR-003/FR-005/FR-008) resolves to one literal, comparable string across all three renders instead of three implementers each satisfying the letter of the requirement with non-comparable text. Plan phase picks the exact wording; this requirement fixes that it is picked once and shared. | P1 | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No silent path in the new code | Every new code path this mission adds (the collection helper, the two/three render sites) must either report the kind-filtered nodes it finds or explicitly report that it found none worth flagging (Edge Case 1) — never a bare `None`/`0`/silently-swallowed branch that a caller could mistake for "nothing to report." This is the repo's dominant failure mode (silent success) and this issue is a textbook instance of it; the fix must not reproduce the pattern in a new corner. **Fails if**: any new collection/render path can produce a caller-visible `None`/empty result for a source that in fact reached a kind-filtered node, with no corresponding report — including the `has_skipped`-guard corner FR-005a exists to close. | Reliability | High | Open |
| NFR-002 | Output-volume trade-off is deliberate and documented, not accidental | The rise in cascade output volume for sources reaching `template`/`asset` (ADR 2026-08-20-1's "137 affected sources," most visibly every mission-type `--cascade all` via `instantiates`) is an accepted, operator-approved consequence of this mission (see Clarifications), not a regression to be minimized by suppressing lines. No implementation may silently cap, truncate, or sample the per-node lines to control volume — if volume becomes a real operational problem it is a follow-up issue, not a reason to under-render here. **Fails if**: any implementation caps, truncates, samples, or otherwise suppresses per-node kind-filtered lines to keep output volume down. | Usability | Medium | Open |
| NFR-003 | Activation/deactivation symmetry is verified, not merely mirrored | FR-007's `deactivation_plan` extension must be verified against the SAME fixture used for FR-001-005 (a source reaching a `template`/`asset` node), not merely code-reviewed for shape-alikeness — i.e., a test asserting `charter activate --cascade all` and `charter deactivate --cascade all` on the same source report the same kind-filtered node. **Fails if**: the deactivation-side extension is verified only by code review or a differently-shaped fixture, with no test exercising both commands against the same source (subsumed by SC-003, restated here as the NFR's own falsification condition). | Reliability | Medium | Open |
| NFR-004 | Reflexivity — output is additive, not restructured | This change must not remove, rename, or reorder any existing cascade/no-cascade/deactivation console line shape (`Cascade-activated:`, `Warning: ... was not activated (no --cascade)`, `Skipped (out of scope)`, `Cascade-deactivated:`, `Skipped (shared artifact)`). It adds new, additional line shapes only. A mission or script mid-flight that parses today's output by matching these existing strings is unaffected; a parser that assumed cascade output was exhaustive of everything a source references was already relying on the bug this mission fixes and will now see additional lines it did not see before. **Fails if**: any existing line shape is removed, renamed, reordered, or has its exact string changed (subsumed by SC-006, restated here as the NFR's own falsification condition). | Compatibility | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No reversal of `CHARTER_ACTIVATABLE_KINDS` | `CHARTER_ACTIVATABLE_KINDS` (`src/doctrine/artifact_kinds.py:330-333`, `frozenset(ArtifactKind) - {TEMPLATE, ASSET}`) is ADR-recorded policy (ADR 2026-08-20-1) and is NOT reopened by this mission. No code change may add `TEMPLATE` or `ASSET` back into this set, and no requirement above may be satisfied by doing so — the fix is exclusively about reporting what the filter already drops, never about narrowing what it drops. | Technical | High | Open |
| C-002 | Activation/deactivation symmetry (ADR-required) | ADR 2026-08-20-1's "Symmetry" section states `REFERENCE_RELATIONS` and the candidate filter apply consistently to activation, the no-cascade warning, AND deactivation exclusivity via the shared `_referenced_artifacts` seam. Any field this mission adds to report kind-filtered nodes must be added consistently across all three consumers (`CascadeActivationResult`, `NoCascadeReport`, `DeactivationPlan`) rather than to only one or two — an activation-only fix would itself reintroduce an asymmetry the ADR forbids. | Technical | High | Open |
| C-003 | PR body must cite the ADR (mission-completion gate) | Per FR-006, the PR that closes this mission must explicitly reference ADR 2026-08-20-1 and state that the change is a visibility addition, not a policy reversal. This is a required section of the PR body, not optional context — a reviewer unfamiliar with the ADR must be able to read the PR body alone and understand the relationship. | Process | High | Open |
| C-004 | Existing pinned tests do not need weakening | `tests/charter/test_cascade.py::test_instantiates_is_followed_but_template_dropped_at_candidacy` (line 648) asserts `result.activated == {}` only — it does not assert console silence, and does not assert anything about `skipped_by_scope` or any other field. `tests/charter/test_cascade.py::test_cascade_never_proposes_template_or_asset` (line 603) makes the same class of assertion against the real built-in DRG graph — `"template"`/`"asset"` not in `result.activated` and not in `report.skipped`. Both have been verified by reading the tests directly on this checkout. Adding a new field to `CascadeActivationResult`/`NoCascadeReport` for kind-filtered nodes does not require weakening or deleting either assertion; new assertions are added alongside them, not in place of them. | Technical | Medium | Open |
| C-005 | Not the same defect as SK-76 | Ledger entry SK-76 describes a DISTINCT defect: two URN-minting paths (`doctrine/drg/merge.py`'s fragment-id keying vs. `charter/kind_vocabulary.py::resolve_artifact_urn`'s body-id keying) that can diverge for an org pack, causing an edge to dangle before it ever reaches the kind filter this mission touches. SK-76's own text calls #3705's silent-drop-of-non-activatable-kinds "the one worth fixing first" and treats the two as independent. This mission does NOT fix SK-76's URN-mismatch defect, does not touch `merge.py` or `kind_vocabulary.py`'s URN-minting logic, and a reviewer should not conflate the two when assessing this mission's scope. | Technical | Low | Open |
| C-006 | Dropped-node data must never flow through `CascadeScope.selects()` or an existing bucketing loop | `CascadeScope.selects()` (`src/charter/cascade.py:180`, `return self.is_all or kind in self.kinds`) is kind-agnostic under `--cascade all` — `is_all=True` returns `True` for ANY kind, including `template`/`asset`. The existing scope-gated bucketing loops this mission's new fields are threaded alongside — `cascade_activation_targets`'s `activated`/`skipped_by_scope` partition (`src/charter/cascade.py:373-375`) and `deactivation_plan`'s candidate loop (`src/charter/cascade.py:533-535`) — both gate on `scope.selects(ref.kind)`. The kind-filtered/dropped nodes FR-001 collects MUST be threaded to their new result fields (`CascadeActivationResult`'s new field, `NoCascadeReport`'s new field, `DeactivationPlan`'s new field) via a path that NEVER passes through `CascadeScope.selects()` or these existing bucketing/candidate loops — they populate the new field directly, unconditionally, independent of scope. A kind-filtered node must never be merged back into the same iterable as activatable refs before scope-partitioning; doing so would let `--cascade all` (where `is_all=True` selects everything) actually (de)activate a `template`/`asset` node, a functional reversal of C-001 at runtime, not merely a rendering bug. **Required test**: under `--cascade all` specifically, assert a kind-filtered node never appears in `activated`, `skipped_by_scope`, or `deactivate`/candidates — only in the new field. | Technical | High | Open |

### Key Entities

- **Cascade candidate**: a URN reached by the forward transitive closure of `REFERENCE_RELATIONS` from an activation/deactivation source, before any kind filtering is applied. Existing concept (`_forward_reference_closure`, `src/charter/cascade.py:235-254`); not new.
- **Kind-filtered node** (new, this mission's core data shape): a cascade candidate whose `ArtifactKind` (resolved by `_kind_of`) is NOT `None` (i.e. it IS a real artifact-kind node, not an action/glossary node dropped by the pre-existing first filter) and IS excluded from `CHARTER_ACTIVATABLE_KINDS` (i.e. `template` or `asset` today). Carries the same shape as `ReferencedArtifact` (`kind`, `artifact_id`, `urn`) so it can reuse the existing dataclass or a structurally identical sibling. This is the record that today's `_referenced_artifacts` computes and discards via the bare `continue` at line 291-292, and that this mission makes visible.
- **`CascadeActivationResult`** (`src/charter/cascade.py:321-337`, existing): gains a new field (name TBD at plan time, e.g. `not_cascaded_kind_filtered: dict[str, list[str]]`) alongside `activated` and `skipped_by_scope`, following the same kind → sorted bare IDs shape.
- **`NoCascadeReport`** (`src/charter/cascade.py:387-410`, existing): gains an equivalent new field alongside `skipped`.
- **`DeactivationPlan`** (`src/charter/cascade.py:469-486`, existing): gains an equivalent new field alongside `deactivate` and `skipped_shared`, per FR-007/C-002.

## Non-Goals / Out of Scope

The following are explicitly OUT OF SCOPE for this mission. Folding any of them in — even
opportunistically, even if they "fall out naturally" during implementation — is a scope
violation per the issue's own Non-goals section, not helpfulness:

- **Reversing or narrowing `CHARTER_ACTIVATABLE_KINDS`.** The `template`/`asset` exclusion
  stays exactly as ADR-recorded. See C-001.
- **#2599** — actually invoking a pack-shipped code asset as a gate handler (the executable
  half of the asset gap). This mission is the visibility half only.
- **#3037, #2536, #3418** — separately-tracked, maintainer-scoped concerns named explicitly
  by the issue as non-goals. Not investigated, not touched.
- **The fail-open `_mt_dispatch_one_gate` wrapper.** Named explicitly by the issue as a
  non-goal. Not touched.
- **SK-76's URN-minting divergence** (ledger). Distinct defect, independently filed, not this
  mission's fix target. See C-005.
- **`doctrine pack validate` warning for packs whose only DRG edges target non-activatable
  kinds.** The issue itself calls this "optionally, separately arguable... out of scope
  unless it falls out naturally." Given the explicit scope-discipline instructions for this
  mission, this mission treats it as fully out of scope rather than opportunistically folding
  it in — it can be filed as a follow-up if the maintainer wants it.
- **Any of the eleven other issues referenced in the full #3705 issue body.** Read for
  context only; none are folded into this mission's scope.

## Success Criteria *(mandatory)*

**Test-run scope note (SC-001-004, SC-006-007)**: verify these six test-verified Success
Criteria by running scoped to `tests/charter/test_cascade.py` and the relevant `charter
activate`/`charter deactivate` CLI command tests, not a full-repo `pytest` sweep (SC-005 is
excluded — it is a PR-body check, not a test). `main` carries a known-red baseline
(CLAUDE.md's "Test-run baseline-red gotcha" — currently ~23 tests/2 errors) that applies to
every agent, including dispatched subagents; classify any other red observed against that
baseline per CLAUDE.md before attributing it to this mission.

### Measurable Outcomes

- **SC-001**: Running the issue's own reproduction (`charter activate toolguide
  qa-carrier-lint --cascade all` against a pack with one `suggests` edge to a tactic and one
  to `asset:qa-traceability-lint`) produces a `Cascade-activated:` line for the tactic AND a
  distinct, non-silent line for the asset — verified by a red-first test that fails on
  today's `main` (asserting the asset line is present) and passes after the fix. **Fails if**
  the asset edge still produces no output.
- **SC-002**: A cascade source whose entire referenced set is non-activatable kinds prints an
  explicit "zero activatable targets" statement — verified by a test constructing such a
  source and asserting the message is present, exit code remains 0 (this is a diagnostic, not
  a hard error). **Fails if** the command exits 0 with no output for this case, matching
  today's bug.
- **SC-003**: `charter activate --cascade all` and `charter deactivate --cascade all` run
  against the same fixture source report the same kind-filtered node (same kind, same ID) —
  verified by a single test exercising both commands' underlying functions against one graph.
  **Fails if** one reports it and the other does not.
- **SC-004**: `tests/charter/test_cascade.py::test_instantiates_is_followed_but_template_dropped_at_candidacy`
  AND `tests/charter/test_cascade.py::test_cascade_never_proposes_template_or_asset` (line 603)
  both continue to pass unmodified (their existing assertions, not a superset or a relaxed
  version of them) after this mission's changes land. **Fails if** either assertion had to be
  weakened, deleted, or wrapped to keep passing.
- **SC-005**: The PR body for this mission contains an explicit citation of ADR
  2026-08-20-1 and a sentence distinguishing this change (visibility) from a policy reversal.
  **Fails if** the PR is opened without that citation.
- **SC-006**: No existing cascade/no-cascade/deactivation test that asserts a specific console
  line's exact text for an *activatable*-kind node changes its expected string — only new
  assertions are added for the new, additional kind-filtered lines. **Fails if** an existing
  assertion for `Cascade-activated:`, `Skipped (out of scope)`, the no-cascade warning line,
  `Cascade-deactivated:`, or `Skipped (shared artifact)` had to change to accommodate this
  mission.
- **SC-007**: A cascade source whose referenced nodes are all activatable-kind but excluded
  by a narrow `--cascade` scope (e.g. `--cascade tactic` against a source that only
  references `directive` nodes) does NOT print the FR-004 zero-activatable-targets message —
  verified by a test constructing such a source and asserting the message's absence while the
  per-node `Skipped (out of scope)` lines are still present. **Fails if** the
  zero-activatable-targets message appears for this pure scope-narrowing case.
