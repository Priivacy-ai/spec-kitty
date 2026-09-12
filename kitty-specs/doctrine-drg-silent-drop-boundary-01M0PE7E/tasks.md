# Tasks: Doctrine DRG Silent-Drop Boundary Fix

**Mission**: `doctrine-drg-silent-drop-boundary-01M0PE7E`
**Branch**: `fix/doctrine-drg-silent-drop-boundary` (planning base + merge target)
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Contracts**: [contracts/failloud-seams.md](./contracts/failloud-seams.md)
**Squad-amended**: [research/post-plan-brownfield-squad.md](./research/post-plan-brownfield-squad.md)

5 work packages, 24 subtasks. Most WPs are red-first (write the failing test, then
the fix); the exception is WP03 T013, a **characterization pin** for the
already-landed built-in guard (it passes on arrival — not a bug fix). Tests are
targeted (never the full suite in-session). Completion is event-sourced:
`spec-kitty agent tasks mark-status Txxx --status done`.

**Post-tasks squad amendments** (research/post-tasks-brownfield-squad.md): WP03's
org-tier raise moved to `validator.py` (post-merge) with the invocation wired by
WP04 → **WP04 now depends on WP03**; WP02 gained a missed fixture consumer +
CHANGELOG/version + a corrected migration name (`m_3_3_1_*`, not `m_3_2_6_*`).

## Subtask Index (reference table — not a tracking surface)

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Derive `_DRG_NODE_KINDS` from `NodeKind` (reuse `merge.py:504` twin) | WP01 | |
| T002 | Behaviour-pinned drift-guard (monkeypatch a NodeKind member) | WP01 | [P] |
| T003 | Test previously-dropped URN kinds resolve at the gate | WP01 | [P] |
| T004 | Extractor: project agent_profile edges from `*-references` + reconcile pedro/034 overlay | WP02 | |
| T005 | Remove `context-sources` from models + schema + `__all__` | WP02 | |
| T006 | Update non-test consumers (generate_schemas, inline_reference_inventory) | WP02 | |
| T007 | Upgrade migration: set-merge → `*-references`, re-home `additional` binding, drop `doctrine-layers` | WP02 | |
| T008 | Migrate the 25 shipped `*.agent.yaml` profiles | WP02 | |
| T009 | Regenerate `agent_profile.graph.yaml` + composition-ledger entry (pedro 9→10) | WP02 | |
| T010 | Update asserting tests (profile/model/extractor/emit-bind/supply-chain) | WP02 | |
| T011 | Divergent user-profile fixture + pre-migration snapshot + C-006 golden-diff | WP02 | |
| T012 | Doc-nit `extractor.py:557` (reflect the re-ledger) [IC-6] | WP02 | |
| T013 | Built-in end-to-end `generate_graph` fail-loud test | WP03 | [P] |
| T014 | Implement org-tier governance-profile scope extraction | WP03 | |
| T015 | Org-tier fail-loud guard (unresolved selection raises) | WP03 | |
| T016 | Org-tier fail-loud tests (red-first: raise; valid passes) | WP03 | |
| T017 | Thread `org_fragments` at `executor.py:362` (+ pre-probe) | WP04 | |
| T018 | Thread `org_fragments` at `action_doctrine_bundle.py:192` (not `:245`) | WP04 | [P] |
| T019 | Valid-fragment red test + multiset no-double-fold assertion | WP04 | |
| T020 | Refresh `packs/internal/` README | WP04 | [P] |
| T021 | 2nd minimal org fixture pack | WP05 | |
| T022 | Class-b test: built-in + internal delivers every declared kind via the seam | WP05 | |
| T023 | Class-a test: 2nd fixture fragment (pack #2) reaches merged graph | WP05 | |
| T024 | Enumerated misconfig fail-loud tests (raise vs warn) | WP05 | |

---

## WP01 — DRG node-kind SSOT (#3608) [IC-1]

**Goal**: Derive the resolver's recognized DRG node-kind set from `NodeKind`; kill
the hand-copy; pin the boundary with a behaviour test.
**Priority**: P1 · **Est.**: ~220 lines · **Depends**: none · **Prompt**: [tasks/WP01-drg-node-kind-ssot.md](./tasks/WP01-drg-node-kind-ssot.md)
**Independent test**: monkeypatch a `NodeKind` member → resolver recognizes its URN
without editing `topic_resolver.py`; the 6 previously-dropped kinds resolve.

Subtasks: T001, T002, T003. Requirements: FR-001, FR-002, FR-003.

## WP02 — Profile-reference consolidation + re-ledger (#3629 p1, p3) [IC-2, IC-6]

**Goal**: Remove the redundant `context-sources.*` surface, consolidate on
`*-references`, migrate 25 profiles + all consumers, regenerate the golden graph
with a deliberate pedro/034 ledger entry. Atomic — keeps the repo green.
**Priority**: P1 · **Est.**: ~640 lines (9 subtasks — the heavy WP) · **Depends**: none · **Prompt**: [tasks/WP02-profile-reference-consolidation.md](./tasks/WP02-profile-reference-consolidation.md)
**Independent test**: divergent user-profile fixture proves the migration moves
non-duplicated refs; C-006 golden diff empty except the ledgered pedro/034 delta;
`context-sources` rejected at load.

Subtasks: T004–T012. Requirements: FR-004, FR-005, FR-006, FR-007, FR-013.

## WP03 — Governance-profile fail-loud: built-in e2e + org-tier implement (#3629 p2) [IC-3]

**Goal**: Add an end-to-end `generate_graph` test pinning the built-in guard
(close #3629 p2 built-in), and implement the net-new org-tier governance-profile
scope extraction + fail-loud guard (no org-tier path exists today).
**Priority**: P2 · **Est.**: ~360 lines · **Depends**: none · **Prompt**: [tasks/WP03-governance-profile-failloud.md](./tasks/WP03-governance-profile-failloud.md)
**Independent test**: fictional `selected_*` id in a built-in AND an org-tier
governance-profile each raise naming the id; valid selections pass.

Subtasks: T013–T016. Requirements: FR-008.

## WP04 — Org fragment silent-drop fix at the callers (#3530) [IC-4]

**Goal**: Thread `org_fragments=load_org_drg(repo_root, strict=False)` at the two
deficient callers (executor, action_doctrine_bundle) — NOT the seam — so an org
pack's `drg/fragment.yaml` reaches those consumers; refresh the internal README.
**Priority**: P1 · **Est.**: ~340 lines · **Depends**: WP03 (invokes its governance validator) · **Prompt**: [tasks/WP04-org-fragment-callers-fix.md](./tasks/WP04-org-fragment-callers-fix.md)
**Independent test**: a valid fragment-only org pack's node reaches the merged DRG
via the executor/action-bundle path (red before, green after); multiset count ==
single-fold (no double-fold regression for dual-callers).

Subtasks: T017–T020. Requirements: FR-009, FR-010.

## WP05 — Chain-delivery verification, both classes (#3530 close) [IC-5]

**Goal**: Verify chain delivery on the real spec-kitty-internal pack (class-b) AND
a 2nd minimal org fixture (class-a multi-org-pack fold); enumerated misconfig
fail-loud. Closes #3530.
**Priority**: P2 · **Est.**: ~380 lines · **Depends**: WP04 · **Prompt**: [tasks/WP05-chain-delivery-verification.md](./tasks/WP05-chain-delivery-verification.md)
**Independent test**: built-in+internal delivers every internal kind via the seam;
built-in+internal+fixture-2 folds pack #2's fragment; 3 enumerated misconfigs raise.

Subtasks: T021–T024. Requirements: FR-011, FR-012.

---

## Dependency graph

```
WP01   WP02        (independent, parallel)
WP03 ──► WP04 ──► WP05
```

- WP04 depends on WP03 (WP04 invokes WP03's org-governance validator post-merge).
- WP05 depends on WP04 (needs the fragment-delivery seam fixed).
- WP01, WP02 independent — parallel with the WP03→WP04→WP05 chain.

## MVP / sequencing

- **MVP = WP01** (smallest, highest-leverage SSOT fix; the mission's thesis).
- WP02 is the heaviest (atomic consolidation) — one focused session; owns
  `extractor.py` (imports the governance field-constant read by WP03). WP03 owns
  `org_pack_loader.py` + `org_governance.py` + `validator.py`; WP04 owns the two
  caller seams and invokes WP03's guard — no file overlap.

## Pre-implementation gate

`/spec-kitty.analyze` must run before any WP implementation (the implement gate
enforces `analysis_report_required`).
