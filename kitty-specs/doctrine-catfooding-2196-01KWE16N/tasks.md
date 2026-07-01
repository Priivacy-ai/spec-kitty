# Tasks: Doctrine Catfooding

**Mission**: `doctrine-catfooding-2196-01KWE16N`
**Branch**: `design/doctrine-catfooding-2196` → coord `kitty/mission-doctrine-catfooding-2196-01KWE16N`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Research**: [research.md](research.md)
**Total WPs**: 13 | **Total subtasks**: 63

---

## Subtask Index

| ID | Description | WP | Parallel? |
|---|---|---|---|
| T001 | Commit source doc with 50-180 char frontmatter description | WP01 | |
| T002 | Register source doc via `scripts/docs/freshen_adr_inventory.py` / `inventory_lockfile.py` | WP01 | |
| T003 | Verify docs-freshness gates (frontmatter + inventory row) pass | WP01 | |
| T004 | Re-parent epic #2196: drop scope-tracker framing via `gh` (tracker-only, FR-004/PD-3) | WP01 | [P] |
| T005 | [C-001] Overlap-audit §5a: confirm no arch-gate-non-vacuity artifact exists; record create decision | WP02 | |
| T006 | Author `043-close-defect-class-by-construction.directive.yaml` with inline DRG edges | WP02 | |
| T007 | Author `architectural-gate-non-vacuity.tactic.yaml`; cite `test_protection_resolver_call_sites.py` + `_baselines.yaml` | WP02 | |
| T008 | Author `frozen-baseline-shrink-only-ratchet.tactic.yaml` (WP02 sole owner per C-003) | WP02 | |
| T009 | Verify inline DRG edges authored in all WP02 artifacts; graph.yaml regen DEFERRED to WP12 | WP02 | |
| T010 | DoD: `doctor doctrine --json` green + terminology guard green + ruff/mypy clean; profile wiring DEFERRED to WP12 | WP02 | |
| T011 | [C-001] Overlap-audit §5b: confirm no post-merge adjudication procedure exists; record create decision | WP03 | |
| T012 | Author `post-merge-arch-gate-adjudication.procedure.yaml` | WP03 | |
| T013 | Author inline DRG edges (requires DIRECTIVE_043); graph.yaml regen DEFERRED to WP12 | WP03 | |
| T014 | DoD: `doctor doctrine --json` green + terminology guard green; profile wiring DEFERRED to WP12 | WP03 | |
| T015 | [C-001] Overlap-audit §3: grep for existing tracer artifacts; confirm zero coverage; record create decision | WP04 | |
| T016 | Author `mission-tracer-files.procedure.yaml`; cite #2095 in provenance (close-on-land) | WP04 | |
| T017 | Author 3-file template scaffold (`tooling-friction.md`, `approach.md`, `design-decisions.md`) | WP04 | [P] |
| T018 | Author inline DRG edges for procedure; graph.yaml regen DEFERRED to WP12 | WP04 | |
| T019 | DoD: `doctor doctrine --json` green + terminology guard green; profile wiring DEFERRED to WP12 | WP04 | |
| T020 | [C-001] Overlap-audit §6: confirm no existing canonical-sources or unification artifacts; record create decisions | WP05 | |
| T021 | Author `044-canonical-sources-and-unification.directive.yaml` with inline DRG edges | WP05 | |
| T022 | Author `canonical-source-unification.tactic.yaml` with inline DRG edges | WP05 | [P] |
| T023 | Author `terminology-guard.toolguide.yaml`; quote-and-mark forbidden terms (C-004) | WP05 | [P] |
| T024 | DoD: `doctor doctrine --json` green + terminology guard green; profile wiring DEFERRED to WP12 | WP05 | |
| T025 | [C-001] Overlap-audit §7 PRs-only/read-intent: read 029, 033, git-flow.paradigm; record create decision | WP06 | |
| T026 | Author `045-prs-only-and-read-intent.directive.yaml` with inline DRG edges | WP06 | |
| T027 | Verify inline DRG edges; graph.yaml regen DEFERRED to WP12 | WP06 | |
| T028 | DoD: `doctor doctrine --json` green + terminology guard green; profile wiring DEFERRED to WP12 | WP06 | |
| T029 | [C-001] Overlap-audit §7 worktree/no-version: read clean-linear-commit-history.tactic, git-flow.paradigm, 029, 033 | WP07 | |
| T030 | Author `pr-agent-worktree-isolation.tactic.yaml`; REFERENCE `clean-linear-commit-history.tactic` | WP07 | |
| T031 | Author inline DRG edges; graph.yaml regen DEFERRED to WP12 | WP07 | |
| T032 | DoD: `doctor doctrine --json` green + terminology guard green; profile wiring DEFERRED to WP12 | WP07 | |
| T033 | [C-001] Overlap-audit §1: read `adversarial-squad-deployment.procedure.yaml` + `brownfield-onboarding.paradigm.yaml` | WP08 | |
| T034 | Author `adversarial-squad-cadence.styleguide.yaml` (cadence recommendation ONLY, NOT `enforcement: required`) | WP08 | |
| T035 | EXTEND `brownfield-onboarding.paradigm.yaml` with §1 cadence cross-link (WP08 sole owner per C-003) | WP08 | |
| T036 | Author inline DRG edges for styleguide + paradigm extension; graph.yaml regen DEFERRED to WP12 | WP08 | |
| T037 | DoD: `doctor doctrine --json` green + terminology guard green; §1 optionality preserved; profile wiring DEFERRED to WP12 | WP08 | |
| T038 | [C-001] Overlap-audit §2: read 025, 024, 040, planning-and-tracking.styleguide; record uncovered atoms | WP09 | |
| T039 | EXTEND `025-boy-scout-rule.directive.yaml` with domain-matched-fold-at-point-cut atom + 024/040 cross-links | WP09 | |
| T040 | Reference (NOT edit) WP02's ratchet tactic + WP08's paradigm in 025's DRG edges; tracker-hygiene in WP11 | WP09 | |
| T041 | Verify inline DRG edges for extended 025; graph.yaml regen DEFERRED to WP12 | WP09 | |
| T042 | DoD: `doctor doctrine --json` green + terminology guard green; no duplicate campsite directive; profile wiring DEFERRED | WP09 | |
| T043 | [C-001] Overlap-audit §4: read 041, 034 lines 16-22, testing-principles, test-first-bug-fixing.procedure | WP10 | |
| T044 | EXTEND `041-tests-as-scaffold-not-friction.directive.yaml` with "live-evidence-over-static-fixed" atom ONLY | WP10 | |
| T045 | Add cross-link to testing-principles.styleguide from 041; REFERENCE DIRECTIVE_034 in prose for red-first | WP10 | |
| T046 | DoD: `doctor doctrine --json` green + terminology guard green; NO new §4 directive; no triple authority | WP10 | |
| T047 | [C-001] Overlap-audit §8: read planning-and-tracking.styleguide, tiered-standards, mission-runtime.yaml, review/implement prompts | WP11 | |
| T048 | EXTEND `planning-and-tracking.styleguide.yaml` with issue-matrix discipline + §2 tracker-hygiene bullet (SOLE owner) | WP11 | |
| T049 | Author `ownership-map-leeway.tactic.yaml`; align with tasks-packages/tasks prompt "no-overlap" language | WP11 | [P] |
| T050 | Author `reviewer-implementer-role-separation.tactic.yaml`; REFERENCE mission-runtime.yaml wiring | WP11 | [P] |
| T051 | Author inline DRG edges for new tactics + extended styleguide; graph.yaml regen DEFERRED to WP12 | WP11 | |
| T052 | DoD: `doctor doctrine --json` green + terminology guard green; profile wiring DEFERRED to WP12 | WP11 | |
| T053 | Run single `graph.yaml` regeneration via `extractor.py:generate_graph`; verify freshness (regenerated matches committed) | WP12 | |
| T054 | `pytest tests/doctrine/drg/ -q` green: freshness/cycle/relations tests pass; investigate known #1755 gaps | WP12 | |
| T055 | Verify orphan count does not worsen vs. pre-mission baseline (NFR-003); record the count | WP12 | |
| T056 | Append directive IDs 043/044/045 to relevant profile `directives:` lists in `src/doctrine/agent_profiles/built-in/` | WP12 | |
| T057 | Final DoD: `doctor doctrine --json` green for ALL artifacts; ruff + mypy clean on any Python touched | WP12 | |
| T058 | Pre-condition: `pytest tests/doctrine/drg/ -q` green; `doctor doctrine --json` healthy; read existing `charter.md` v1.1.5 | WP13 | |
| T059 | Activate catfooding artifacts: `charter activate --cascade` → writes `.kittify/config.yaml` activated lists | WP13 | |
| T060 | Mirror activation set into `.kittify/charter/interview/answers.yaml` (named manual sub-step; no auto-bridge exists) | WP13 | |
| T061 | Generate: `charter generate` → renders `charter.md` + `references.yaml` from answers + activation-filtered DRG closure | WP13 | |
| T062 | Reconcile: version past 1.1.5; existing content preserved; `charter list` shows all 8 sections (SC-001) | WP13 | |
| T063 | Final acceptance: reference closure non-shallow; `doctor doctrine --json` healthy (NFR-003/SC-003) | WP13 | |

---

## Work Packages

### WP01 — Foundation: Source Doc + Epic Re-parent (Priority: P0)

**Goal**: Establish the preconditions all conversions depend on: commit the canonical source doc (`quality-and-tech-debt-standing-orders.md`) with valid docs-freshness metadata, register it in the page inventory via the canonical freshener script, and re-parent epic #2196 to be a genuine functional epic (drop scope-tracker framing).
**Phase**: L0 — Foundation (blocks all conversions)
**Estimated prompt size**: ~230 lines
**Dependencies**: none
**Enables**: all conversion WPs (WP02-WP11)
**Prompt**: `tasks/WP01-foundation-source-doc-and-epic-re-parent.md`

#### Included Subtasks

- [x] T001 Commit `docs/development/quality-and-tech-debt-standing-orders.md` with valid frontmatter (50-180 char description)
- [x] T002 Register via `scripts/docs/freshen_adr_inventory.py` / `inventory_lockfile.py`; regenerate if tail-conflict with PR #2277
- [x] T003 Verify docs-freshness gates pass (frontmatter + inventory row)
- [x] T004 [P] Re-parent epic #2196: drop scope-tracker framing via `gh` (tracker-only, FR-004/PD-3)

#### Implementation Notes

- Content = `research/quality-and-tech-debt-standing-orders.source.md` (already committed).
- Do NOT hand-edit `3-2-page-inventory.yaml` — use the canonical freshener script.
- PD-1 (directive numbers 043-049 reserved) and PD-2 (graph.yaml single-regen at WP12) are recorded plan decisions — NOT subtasks here.

#### Dependencies

- None (first WP).

#### Risks

- Docs-freshness gates are CI-only; run `pytest tests/architectural/ -k freshness` locally before pushing.
- Tail-conflict with PR #2277 on `3-2-page-inventory.yaml` is expected — regenerate the file, don't hand-merge.

---

### WP02 — §5a Arch-Gate Construction + Non-Vacuity (Priority: P1) [HEAVIEST]

**Goal**: Author DIRECTIVE_043 (close-defect-class-by-construction) and two new tactics: the AST call-site gate non-vacuity tactic and the frozen-baseline shrink-only ratchet tactic. WP02 is sole owner of the ratchet tactic (shared with §2) per C-003.
**Phase**: LA — New-Artifact Conversions
**Estimated prompt size**: ~420 lines
**Dependencies**: WP01
**Enables**: WP03 (§5b depends on the §5a directive)
**Prompt**: `tasks/WP02-arch-gate-construction-and-non-vacuity.md`

#### Included Subtasks

- [x] T005 [C-001] Overlap-audit §5a: confirm no arch-gate-non-vacuity artifact; record augment-vs-create decision
- [x] T006 Author `043-close-defect-class-by-construction.directive.yaml` with inline DRG edges
- [x] T007 Author `architectural-gate-non-vacuity.tactic.yaml`; cite `test_protection_resolver_call_sites.py` + `_baselines.yaml`
- [x] T008 Author `frozen-baseline-shrink-only-ratchet.tactic.yaml` (WP02 sole owner per C-003)
- [x] T009 Verify inline DRG edges in all three artifacts; graph.yaml regen DEFERRED to WP12
- [x] T010 DoD: `doctor doctrine --json` green + terminology guard green + ruff/mypy clean; profile wiring DEFERRED to WP12

#### Parallel Opportunities

- T007 and T008 can proceed in parallel after T006 is scaffolded.

#### Dependencies

- Depends on WP01.

#### Risks

- §5a is tooling-design (AST gate with concrete floor + self-mutation test + shrink-only allowlist + routed-count floor) — the tactic must describe the concrete pattern, not hand-wavy prose.
- Do NOT invent exemplars; cite the live gate and in-flight ratchet as specified.

---

### WP03 — §5b Post-Merge Arch-Gate Adjudication (Priority: P1)

**Goal**: Author the post-merge-arch-gate-adjudication procedure: full-gate sweep on the merged branch, cross-base "pre-existing" verification, and instruction to run CI-only shards locally.
**Phase**: LA — New-Artifact Conversions
**Estimated prompt size**: ~260 lines
**Dependencies**: WP01, WP02
**Enables**: WP12 (procedure is a DRG node)
**Prompt**: `tasks/WP03-post-merge-arch-gate-adjudication.md`

#### Included Subtasks

- [x] T011 [C-001] Overlap-audit §5b: confirm no post-merge adjudication procedure exists; record create decision
- [x] T012 Author `post-merge-arch-gate-adjudication.procedure.yaml` (full-gate sweep, cross-base verification, CI-only shards locally)
- [x] T013 Author inline DRG edges (`requires` DIRECTIVE_043 from WP02); graph.yaml regen DEFERRED to WP12
- [x] T014 DoD: `doctor doctrine --json` green + terminology guard green; profile wiring DEFERRED to WP12

#### Dependencies

- Depends on WP01, WP02 (procedure `requires` DIRECTIVE_043).

#### Risks

- "Pre-existing" verification means cross-base diff vs. the mission base, not just the lane base — the procedure must make this distinction explicit.

---

### WP04 — §3 Mission Tracer Files (Priority: P1)

**Goal**: Author the mission-tracer-files procedure (seed→append→assess lifecycle) and the 3-file template scaffold under `src/doctrine/templates/mission-tracer-files/`. Folds experiment #2095 (cite in provenance, close on land).
**Phase**: LA — New-Artifact Conversions
**Estimated prompt size**: ~290 lines
**Dependencies**: WP01
**Enables**: WP12
**Prompt**: `tasks/WP04-mission-tracer-files.md`

#### Included Subtasks

- [x] T015 [C-001] Overlap-audit §3: grep for existing tracer artifacts; confirm zero coverage; record create decision
- [x] T016 Author `mission-tracer-files.procedure.yaml`; cite #2095 in provenance; close #2095 on land
- [x] T017 [P] Author 3-file template scaffold (`tooling-friction.md`, `approach.md`, `design-decisions.md`) under `templates/mission-tracer-files/`
- [x] T018 Author inline DRG edges for procedure; graph.yaml regen DEFERRED to WP12
- [x] T019 DoD: `doctor doctrine --json` green + terminology guard green; profile wiring DEFERRED to WP12

#### Parallel Opportunities

- T017 (template authoring) can proceed in parallel with DRG edge authoring once T016 is committed.

#### Dependencies

- Depends on WP01.

#### Risks

- Tracer file templates must be sparse scaffolds (headings + placeholder prompts), not opinionated essays.

---

### WP05 — §6 Canonical Sources + Unification (Priority: P1)

**Goal**: Author DIRECTIVE_044 (canonical-sources-and-unification; three rules: use-canonical-sources, unification-not-parity, missing-command-is-a-gap), the companion tactic, and a new terminology-guard toolguide. Toolguide must quote-and-mark forbidden terms, never use them (C-004).
**Phase**: LA — New-Artifact Conversions
**Estimated prompt size**: ~320 lines
**Dependencies**: WP01
**Enables**: WP12
**Prompt**: `tasks/WP05-canonical-sources-and-unification.md`

#### Included Subtasks

- [x] T020 [C-001] Overlap-audit §6: confirm no canonical-sources or unification-not-parity artifacts; record create decisions
- [x] T021 Author `044-canonical-sources-and-unification.directive.yaml` with inline DRG edges
- [x] T022 [P] Author `canonical-source-unification.tactic.yaml` with inline DRG edges
- [x] T023 [P] Author `terminology-guard.toolguide.yaml`; quote-and-mark forbidden terms per C-004
- [x] T024 DoD: `doctor doctrine --json` green + terminology guard green; profile wiring DEFERRED to WP12

#### Parallel Opportunities

- T022 and T023 are fully parallel after T021 is scaffolded.

#### Dependencies

- Depends on WP01.

#### Risks

- The toolguide is the guard-invocation artifact, not a prose restatement of the forbidden terms — it should describe when and how to run the check command.

---

### WP06 — §7 Git/Workflow: PRs-Only + Read-Intent (Priority: P1)

**Goal**: Author DIRECTIVE_045 covering the two PRs-only/operator-merge and read-intent-before-high-risk-ops rules. These are the 2 of 4 §7 rules assigned to this WP; the other 2 (worktree isolation + no-version) are in WP07.
**Phase**: LA — New-Artifact Conversions
**Estimated prompt size**: ~250 lines
**Dependencies**: WP01
**Enables**: WP12
**Prompt**: `tasks/WP06-prs-only-and-read-intent.md`

#### Included Subtasks

- [x] T025 [C-001] Overlap-audit §7 (PRs-only/read-intent): read 029, 033, git-flow.paradigm; record create decision for uncovered rules
- [x] T026 Author `045-prs-only-and-read-intent.directive.yaml` with inline DRG edges
- [x] T027 Verify inline DRG edges authored; graph.yaml regen DEFERRED to WP12
- [x] T028 DoD: `doctor doctrine --json` green + terminology guard green; profile wiring DEFERRED to WP12

#### Dependencies

- Depends on WP01.

#### Risks

- §7 overlap-audit must check `paradigms/built-in/git-flow.paradigm.yaml` in addition to directives 029/033.
- Avoid using `"feature branch"` in canonical voice — quote it as a forbidden idiom if the rule requires mentioning it (C-004).

---

### WP07 — §7 Git/Workflow: Worktree Isolation + No-Version (Priority: P1)

**Goal**: Author the `pr-agent-worktree-isolation` tactic covering isolate-PR-touching-agents-in-worktree and no-version-prescription-in-scope. REFERENCE `clean-linear-commit-history.tactic` for compress-history (do NOT re-author that rule).
**Phase**: LA — New-Artifact Conversions
**Estimated prompt size**: ~250 lines
**Dependencies**: WP01
**Enables**: WP12
**Prompt**: `tasks/WP07-worktree-isolation-and-no-version.md`

#### Included Subtasks

- [x] T029 [C-001] Overlap-audit §7 (worktree/no-version): read `clean-linear-commit-history.tactic`, git-flow.paradigm, 029, 033; confirm worktree-isolation + no-version not covered; record create decision
- [x] T030 Author `pr-agent-worktree-isolation.tactic.yaml`; REFERENCE `clean-linear-commit-history.tactic` for compress-history
- [x] T031 Author inline DRG edges; graph.yaml regen DEFERRED to WP12
- [x] T032 DoD: `doctor doctrine --json` green + terminology guard green; profile wiring DEFERRED to WP12

#### Dependencies

- Depends on WP01.

#### Risks

- The tactic must carry both rules (worktree-isolation AND no-version-in-scope) since they are cohesive "PR agent discipline" content — splitting further would be over-decomposition.

---

### WP08 — §1 Adversarial Squad Cadence (Priority: P2)

**Goal**: Author the adversarial-squad-cadence styleguide (cadence recommendation ONLY; must NOT be `enforcement: required`) and extend the brownfield-onboarding paradigm. REFERENCE `adversarial-squad-deployment.procedure` for the playbook/point-cut table — do NOT re-author it. Folds #2094 (provenance + close on land).
**Phase**: LB — Extend Conversions
**Estimated prompt size**: ~310 lines
**Dependencies**: WP01
**Enables**: WP09 (WP08 owns brownfield-onboarding.paradigm; WP09 references it), WP12
**Prompt**: `tasks/WP08-adversarial-squad-cadence.md`

#### Included Subtasks

- [x] T033 [C-001] Overlap-audit §1: read `adversarial-squad-deployment.procedure.yaml` + `brownfield-onboarding.paradigm.yaml`; record cadence-only recommendation gap
- [x] T034 Author `adversarial-squad-cadence.styleguide.yaml` (NOT `enforcement: required`; REFERENCE procedure for playbook); cite #2094 in provenance; close #2094 on land
- [x] T035 EXTEND `brownfield-onboarding.paradigm.yaml` with §1 cadence cross-link (WP08 sole owner per C-003)
- [x] T036 Author inline DRG edges for styleguide + paradigm extension; graph.yaml regen DEFERRED to WP12
- [x] T037 DoD: `doctor doctrine --json` green + terminology guard green; §1 optionality preserved (NOT `enforcement: required`); profile wiring DEFERRED to WP12

#### Dependencies

- Depends on WP01.
- WP09 must run after WP08 (WP09 references the paradigm WP08 owns).

#### Risks

- §1 MUST remain optional — gate-hardwiring is an anti-pattern per the shipped procedure. Any `enforcement: required` on the styleguide is a review rejection.
- Preserve all existing content in `brownfield-onboarding.paradigm.yaml` when extending it.

---

### WP09 — §2 Campsite Cleaning + Debt Paydown (Priority: P2)

**Goal**: Extend DIRECTIVE_025 (boy-scout-rule) with the domain-matched-fold-at-point-cut atom and 024/040 cross-links. REFERENCE (do NOT edit) WP02's ratchet tactic and WP08's brownfield paradigm via inline DRG edges. The tracker-hygiene bullet is RELOCATED to §8/WP11 — do NOT touch planning-and-tracking.styleguide here.
**Phase**: LB — Extend Conversions
**Estimated prompt size**: ~270 lines
**Dependencies**: WP01, WP02
**Enables**: WP12
**Prompt**: `tasks/WP09-campsite-cleaning-and-debt-paydown.md`

#### Included Subtasks

- [x] T038 [C-001] Overlap-audit §2: read 025, 024, 040, planning-and-tracking.styleguide; record which atoms are uncovered (frozen-baseline ratchet owned by WP02; domain-matched fold)
- [x] T039 EXTEND `025-boy-scout-rule.directive.yaml` with domain-matched-fold-at-point-cut atom; add 024/040 cross-links (edit 025 ONLY — do NOT edit 024 or 040)
- [x] T040 Verify inline DRG edges reference WP02's ratchet tactic + WP08's paradigm; tracker-hygiene bullet goes to WP11
- [x] T041 Verify inline DRG edges for extended 025; graph.yaml regen DEFERRED to WP12
- [x] T042 DoD: `doctor doctrine --json` green + terminology guard green; no duplicate campsite directive created; profile wiring DEFERRED to WP12

#### Dependencies

- Depends on WP01, WP02 (WP09's DRG edges reference the ratchet tactic WP02 authors).
- WP08 should be done before WP09 (WP09 references brownfield paradigm WP08 owns).

#### Risks

- Do NOT author a new campsite directive — the only new artifact is the DRG-edge reference + the domain-matched-fold atom extending 025.

---

### WP10 — §4 Test Remediation (Priority: P2) [LIGHTEST]

**Goal**: Extend DIRECTIVE_041 with ONLY the "live evidence over static-fixed / carry OPEN until live repro" atom. REFERENCE DIRECTIVE_034 IN PROSE for the red-first "pre-existing entry point" refinement — do NOT restate it into 041 or `test-first-bug-fixing.procedure` (avoids the 034↔041↔procedure triple authority). No new §4 directive.
**Phase**: LB — Extend Conversions
**Estimated prompt size**: ~220 lines
**Dependencies**: WP01
**Enables**: WP12
**Prompt**: `tasks/WP10-test-remediation.md`

#### Included Subtasks

- [x] T043 [C-001] Overlap-audit §4: read 041, 034 (lines 16-22 for red-first), testing-principles.styleguide, test-first-bug-fixing.procedure; confirm only "live-evidence-over-static-fixed" is absent from all
- [x] T044 EXTEND `041-tests-as-scaffold-not-friction.directive.yaml` with "live-evidence-over-static-fixed / carry OPEN until live repro" atom ONLY
- [x] T045 Add cross-link to `testing-principles.styleguide.yaml` from 041; REFERENCE DIRECTIVE_034 in prose for red-first rule
- [x] T046 DoD: `doctor doctrine --json` green + terminology guard green; NO new §4 directive; 034↔041↔procedure triple authority NOT introduced; profile wiring DEFERRED to WP12

#### Dependencies

- Depends on WP01.

#### Risks

- This is the lightest WP: one atom + cross-links. Do not pad it. The hard constraint is NOT restating DIRECTIVE_034's red-first content into 041.

---

### WP11 — §8 Mission Hygiene (Priority: P2)

**Goal**: Extend planning-and-tracking.styleguide (issue-matrix discipline + relocated §2 tracker-hygiene bullet; WP11 is SOLE owner). Author ownership-map-leeway tactic (aligned with tasks-packages prompt language) and reviewer-implementer-role-separation tactic (references mission-runtime.yaml wiring, does not restate it).
**Phase**: LB — Extend Conversions
**Estimated prompt size**: ~330 lines
**Dependencies**: WP01
**Enables**: WP12
**Prompt**: `tasks/WP11-mission-hygiene.md`

#### Included Subtasks

- [x] T047 [C-001] Overlap-audit §8: read planning-and-tracking.styleguide, tiered-standards.styleguide (ref complete), mission-runtime.yaml + review/implement prompts; confirm ownership-leeway + role-separation gaps
- [x] T048 EXTEND `planning-and-tracking.styleguide.yaml` with issue-matrix discipline + §2 tracker-hygiene bullet (WP11 is SOLE owner; WP09 must NOT also edit this file)
- [x] T049 [P] Author `ownership-map-leeway.tactic.yaml`; align language with tasks-packages/tasks mission-step prompts ("no-overlap is the real guard")
- [x] T050 [P] Author `reviewer-implementer-role-separation.tactic.yaml`; REFERENCE `mission-runtime.yaml` + review/implement mission-step prompts; do NOT restate the profile wiring
- [x] T051 Author inline DRG edges for new tactics + extended styleguide; graph.yaml regen DEFERRED to WP12
- [x] T052 DoD: `doctor doctrine --json` green + terminology guard green; profile wiring DEFERRED to WP12

#### Parallel Opportunities

- T049 and T050 can proceed in parallel once T047-T048 are complete.

#### Dependencies

- Depends on WP01.

#### Risks

- `planning-and-tracking.styleguide.yaml` is owned SOLELY by WP11 — ensure WP09 does not also edit it.

---

### WP12 — Wiring: Profiles + Single Graph Regen + DRG Tests (Priority: P3)

**Goal**: The sole WP that owns agent-profile edits and `graph.yaml` regeneration. Run the single `graph.yaml` regen, verify DRG freshness/cycle/relations tests, check orphan count, and append new directives 043/044/045 to relevant agent-profile `directives:` lists (C-002c, C-003).
**Phase**: LC — Wiring (serialized after all conversions)
**Estimated prompt size**: ~300 lines
**Dependencies**: WP02, WP03, WP04, WP05, WP06, WP07, WP08, WP09, WP10, WP11
**Enables**: WP13
**Prompt**: `tasks/WP12-wiring-profiles-graph-regen-drg-tests.md`

#### Included Subtasks

- [x] T053 Run single `graph.yaml` regeneration via `src/doctrine/drg/migration/extractor.py:generate_graph`; verify freshness
- [x] T054 `pytest tests/doctrine/drg/ -q` green: freshness/cycle/relations tests pass; investigate known #1755 generator gaps
- [x] T055 Verify orphan count does not worsen vs. pre-mission baseline (NFR-003); record the count
- [x] T056 Append directive IDs 043/044/045 to relevant profile `directives:` lists in `src/doctrine/agent_profiles/built-in/*.agent.yaml`
- [x] T057 Final DoD: `doctor doctrine --json` green for ALL artifacts mission-wide; ruff + mypy clean on any Python touched

#### Dependencies

- ALL conversion WPs (WP02-WP11) must be approved first.

#### Risks

- DRG generator has known gaps (#1755) — the regen must be verified, not assumed clean.
- A bad edge (dangling URN, cycle) fails the freshness test here; must be fixed before WP13 can start.

---

### WP13 — Capstone: Compile the Spec Kitty Charter (Priority: P4)

**Goal**: Assemble the activated catfooding set into the Spec Kitty Charter. Strict sequence per C-007 and `contracts/capstone-compile.md`: activate → mirror answers → generate → reconcile. Must reconcile existing `charter.md` v1.1.5, not clobber it.
**Phase**: Capstone
**Estimated prompt size**: ~350 lines
**Dependencies**: WP12
**Enables**: mission acceptance
**Prompt**: `tasks/WP13-capstone-compile-charter.md`

#### Included Subtasks

- [ ] T058 Pre-condition: `pytest tests/doctrine/drg/ -q` green; `doctor doctrine --json` healthy; read existing `.kittify/charter/charter.md` v1.1.5
- [ ] T059 Activate: `charter activate --cascade` for each catfooding artifact kind/id; writes `.kittify/config.yaml` activated lists
- [ ] T060 Mirror answers (named manual sub-step — no auto-bridge): update `.kittify/charter/interview/answers.yaml` selected lists with catfooding IDs
- [ ] T061 Generate: `charter generate` → `charter.md` + `references.yaml` from answers + activation-filtered DRG closure
- [ ] T062 Reconcile: version past 1.1.5; existing content preserved; `charter list` shows all 8 sections (SC-001)
- [ ] T063 Final acceptance: reference closure non-shallow; `doctor doctrine --json` healthy; SC-001/SC-002/SC-003/SC-004/SC-005 verified

#### Dependencies

- Depends on WP12.

#### Risks

- Generate-before-activate yields a shallow reference closure — the sequence is STRICTLY activate → generate (C-007).
- Skipping the answers mirror means charter references no catfooding directives even after activation.
- Must reconcile not clobber v1.1.5.

---

## Dependency & Execution Summary

- **L0 (Foundation)**: WP01 — blocks all.
- **LA (New-artifact conversions, parallel after WP01)**: WP02, WP04, WP05, WP06, WP07 — mutually parallel (disjoint new files); WP03 depends on WP02.
- **LB (Extend conversions, parallel after WP01)**: WP08, WP10, WP11 — parallel; WP09 depends on WP01 + WP02 (DRG edge) and should run after WP08 (paradigm ownership).
- **LC (Wiring, serialized)**: WP12 — after ALL WP02-WP11 approved.
- **Capstone**: WP13 — after WP12.

**Parallelization summary**:
- WP02 ∥ WP04 ∥ WP05 ∥ WP06 ∥ WP07 ∥ WP08 ∥ WP10 ∥ WP11 (all after WP01, disjoint surfaces)
- WP03 after WP02; WP09 after WP02+WP08

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|---|---|
| FR-001 | WP01 |
| FR-002 | WP01 (PD-1 recorded; no subtask) |
| FR-003 | WP01 (PD-2 recorded; no subtask) |
| FR-004 | WP01 (T004) |
| FR-005 | WP08 |
| FR-006 | WP09 |
| FR-007 | WP04 |
| FR-008 | WP10 |
| FR-009 | WP02 |
| FR-010 | WP03 |
| FR-011 | WP05 |
| FR-012 | WP06, WP07 |
| FR-013 | WP11 |
| FR-014 | WP13 |
| NFR-001 | WP02-WP11 (per-conversion), WP12, WP13 |
| NFR-002 | WP02-WP11 (overlap-audit T005/T011/T015/T020/T025/T029/T033/T038/T043/T047) |
| NFR-003 | WP12 (T055), WP13 (T063) |
| NFR-004 | WP02-WP11 (T010/T014/T019/T024/T028/T032/T037/T042/T046/T052), WP12 (T057) |
| C-001 | All conversion WPs (first subtask each) |
| C-002 | WP02-WP11 (inline edges + doctor green), WP12 (profile wiring) |
| C-003 | WP02 (ratchet tactic), WP08 (brownfield paradigm), WP11 (planning-and-tracking), WP12 (profiles + graph) |
| C-004 | WP05 (toolguide), WP06-WP07 (git), all (terminology guard gate) |
| C-005 | All (no version numbers in scope) |
| C-006 | WP08 (§1 NOT enforcement:required) |
| C-007 | WP13 (activate→generate; reconcile not clobber) |
