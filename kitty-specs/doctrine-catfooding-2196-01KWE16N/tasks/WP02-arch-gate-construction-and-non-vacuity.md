---
work_package_id: WP02
title: §5a Arch-Gate Construction + Non-Vacuity
dependencies:
- WP01
requirement_refs:
- FR-009
tracker_refs: []
planning_base_branch: design/doctrine-catfooding-2196
merge_target_branch: design/doctrine-catfooding-2196
branch_strategy: Planning artifacts for this mission were generated on design/doctrine-catfooding-2196. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/doctrine-catfooding-2196 unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
phase: Phase 1 - New-Artifact Conversions (LA)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1933221"
history:
- at: '2026-07-01T06:14:46Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/directives/built-in/
create_intent:
- src/doctrine/directives/built-in/043-close-defect-class-by-construction.directive.yaml
- src/doctrine/tactics/built-in/architectural-gate-non-vacuity.tactic.yaml
- src/doctrine/tactics/built-in/frozen-baseline-shrink-only-ratchet.tactic.yaml
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/directives/built-in/043-close-defect-class-by-construction.directive.yaml
- src/doctrine/tactics/built-in/architectural-gate-non-vacuity.tactic.yaml
- src/doctrine/tactics/built-in/frozen-baseline-shrink-only-ratchet.tactic.yaml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – §5a Arch-Gate Construction + Non-Vacuity

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `doctrine-daphne`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

Author three genuinely-new doctrine artifacts for §5a of the Quality & Tech-Debt Standing Orders:

1. **DIRECTIVE_043** — `close-defect-class-by-construction`: the principle that defect classes should be eliminated by structural enforcement (AST gates, type constraints, shrink-only ratchets) rather than by manual process. Directive number 043 is pre-allocated per PD-1.
2. **Tactic** — `architectural-gate-non-vacuity`: concrete recipe for building an AST call-site gate with a concrete floor (non-zero baseline), a self-mutation test (the gate rejects its own violation), a shrink-only allowlist, and a routed-count floor. Must cite real live exemplars.
3. **Tactic** — `frozen-baseline-shrink-only-ratchet`: the shared ratchet pattern that compares current call-site counts to a committed baseline and fails if the count grows. **WP02 is sole owner** of this tactic per C-003 (§2 and §5a both reference it; having one owner eliminates the shared-surface collision).

**Conversion DoD (per `contracts/conversion-dod.md`):**
- [ ] Overlap-audit recorded (T005 output)
- [ ] `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid (note: doctor-green is NOT schema proof for new artifacts — see below)
- [ ] `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green (per-artifact schema validation — catches malformed YAML before WP12; run against all three new artifacts)
- [ ] `pytest tests/architectural/test_no_legacy_terminology.py` → green
- [ ] Inline DRG edges (`requires`/`suggests`/`refines`) authored in each artifact YAML
- [ ] 🔜 Agent-profile `directives:` wiring DEFERRED to WP12 (C-003)
- [ ] 🔜 `graph.yaml` regeneration DEFERRED to WP12 (PD-2)

## Context & Constraints

- **Section source**: §5a of `docs/development/quality-and-tech-debt-standing-orders.md` (committed by WP01).
- **No existing coverage**: grep confirms no arch-gate-non-vacuity artifact in `src/doctrine/` — this is a genuinely-new authoring task.
- **Live exemplars to cite (do NOT invent)**: `tests/architectural/test_protection_resolver_call_sites.py` (an active AST call-site gate in the repo) and `tests/architectural/_baselines.yaml` (the in-flight shrink-only ratchet from issue #2159). Read these files before authoring the tactic — the tactic should describe the pattern they instantiate.
- **C-001 (reconcile-not-duplicate)**: First subtask is the mandatory overlap-audit. Even though §5a has no existing coverage, the audit must be recorded explicitly.
- **C-003 (shared-target lock)**: WP02 is the sole owner of `frozen-baseline-shrink-only-ratchet.tactic.yaml`. WP09 (§2) and WP03 (§5b) may reference it via DRG edges but must NOT edit the file.
- **PD-1 (directive number)**: 043 is reserved for this directive. Do not mint 044-049 here.
- **PD-2 (graph.yaml)**: Author inline DRG edges in the artifact YAML only. Do NOT run `generate_graph` — that is WP12's job.
- **C-004 (terminology)**: All prose must pass the legacy-terminology guard. No forbidden terms in canonical voice.
- **Complexity ceiling**: The tactic describes a *pattern*, not production code. Keep the body focused on the concrete steps and decision points; the exemplar citations provide the "proof of concept."

## Branch Strategy

- **Strategy**: Coord topology. WP execution lanes branch from `kitty/mission-doctrine-catfooding-2196-01KWE16N`.
- **Planning base branch**: `design/doctrine-catfooding-2196`
- **Merge target branch**: `kitty/mission-doctrine-catfooding-2196-01KWE16N`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T005 – [C-001] Overlap-audit §5a

- **Purpose**: Fulfill the mandatory per-conversion overlap-audit (C-001 / DIRECTIVE_003) before authoring any new artifact. Even though §5a has no existing coverage, the absence must be confirmed and recorded.
- **Steps**:
  1. Run `grep -r "arch.gate\|non.vacuity\|call.site.gate\|shrink.only\|frozen.baseline" src/doctrine/ --include="*.yaml" -l` — record zero hits.
  2. Run `grep -r "close.*by.*construction\|defect.class" src/doctrine/ --include="*.yaml" -l` — record zero hits.
  3. Write a brief augment-vs-create decision record (2-4 sentences in the Activity Log or inline comment): §5a has zero existing doctrine coverage; all three artifacts are new creations; the frozen-baseline ratchet is new and solely owned here (WP09/§2 will reference via DRG edge).
- **Files**: None (audit only — record findings in Activity Log).
- **Parallel?**: No — must be first.
- **Notes**: The audit record is a review gate. A reviewer who finds no audit record will return the WP without approval.

### Subtask T006 – Author DIRECTIVE_043

- **Purpose**: Create the directive that establishes closing defect classes by construction as a first-class engineering principle.
- **Steps**:
  1. Create `src/doctrine/directives/built-in/043-close-defect-class-by-construction.directive.yaml`.
  2. Follow the existing directive YAML schema (see any `src/doctrine/directives/built-in/*.directive.yaml` for the format — id, title, body, enforcement, requires/suggests/refines).
  3. Set `id: DIRECTIVE_043`, `enforcement: required`, `title: "Close Defect Classes by Construction"`.
  4. Body (concise): the principle that a repeating defect class signals a missing structural constraint; the correct response is to eliminate the recurrence path via an AST gate, type invariant, or shrink-only ratchet — not to add a process rule.
  5. Add inline DRG edges: `suggests: [urn:tactic:architectural-gate-non-vacuity, urn:tactic:frozen-baseline-shrink-only-ratchet]`.
  6. Do NOT add `requires` edges to artifacts authored in other WPs unless those artifacts already exist on disk.
- **Files**: `src/doctrine/directives/built-in/043-close-defect-class-by-construction.directive.yaml` (create new)
- **Parallel?**: No — T007/T008 can start after this.
- **Notes**: Do NOT set `enforcement: optional` — this is a required directive. Directive number 043 is pre-allocated (PD-1).

### Subtask T007 – Author architectural-gate-non-vacuity tactic

- **Purpose**: Encode the concrete recipe for building an AST call-site gate that is non-vacuous (never trivially passes by having zero calls to check).
- **Steps**:
  1. First read `tests/architectural/test_protection_resolver_call_sites.py` and `tests/architectural/_baselines.yaml` to understand the live gate's structure.
  2. Create `src/doctrine/tactics/built-in/architectural-gate-non-vacuity.tactic.yaml`.
  3. Follow the tactic YAML schema (id, title, body, requires/suggests/refines).
  4. Body must cover the four concrete elements:
     - **Concrete floor**: the gate fails if the count of call sites drops below a minimum (not just "fails if it grows") — prevents the gate from trivially passing on a codebase with zero calls.
     - **Self-mutation test**: the gate must be able to detect its own violation (i.e., if you add a disallowed call site in the gate file itself, the gate must still catch it).
     - **Shrink-only allowlist**: use `_baselines.yaml` (or equivalent) to track the current call-site set; the gate fails if any new entry appears.
     - **Routed-count floor**: verify that the count of *routed* calls (i.e., through the sanctioned surface) is above a minimum, not just that *total* calls haven't grown.
  5. Cite the live exemplars: reference `tests/architectural/test_protection_resolver_call_sites.py` as the canonical in-repo example, and `tests/architectural/_baselines.yaml` as the shrink-only ratchet companion.
  6. Add inline DRG edges: `requires: [urn:directive:DIRECTIVE_043]`, `suggests: [urn:tactic:frozen-baseline-shrink-only-ratchet]`.
  7. **Exemplar mapping (SHOULD-TIGHTEN 7)**: after reading `tests/architectural/test_protection_resolver_call_sites.py`, record in the Activity Log an explicit mapping of each of the four non-vacuity elements to a concrete line/construct in that file:
     - **Concrete floor** → identify the specific assertion or constant in the test that enforces a minimum call-site count (the gate must fail if the count drops BELOW this floor, not only if it grows). If the current exemplar only checks "count must not increase" and does NOT enforce a minimum floor, mark this element as "aspirational — floor not demonstrated in current exemplar."
     - **Self-mutation test** → identify the specific check that would catch a violation introduced in the gate file itself (i.e., if a disallowed call site is added to the gate module, the gate still catches it). If absent from the exemplar, mark as "aspirational."
     - **Shrink-only allowlist** → identify the specific line(s) where `tests/architectural/_baselines.yaml` (or equivalent) is loaded and where the live count is compared to the baseline.
     - **Routed-count floor** → identify the specific assertion that checks the count of *routed* calls (calls through the sanctioned surface), distinct from total calls. If absent, mark as "aspirational."
     Record this four-element mapping in the Activity Log before T009. The tactic body must describe all four elements as part of the complete pattern; aspirational elements should be noted as the full target even if the current exemplar only demonstrates some.
- **Files**: `src/doctrine/tactics/built-in/architectural-gate-non-vacuity.tactic.yaml` (create new)
- **Parallel?**: [P] Can proceed alongside T008 after T006 is scaffolded.
- **Notes**: This tactic describes a pattern, not production code. The body should be concrete enough that a maintainer can implement a new gate from it without reading the exemplar. Cite the exemplar for reference, not as a substitute for the description.

### Subtask T008 – Author frozen-baseline-shrink-only-ratchet tactic

- **Purpose**: Encode the baseline-comparison ratchet pattern: commit the current count as a baseline; fail the gate if the count grows beyond the baseline. This tactic is the shared surface for §2 (WP09) and §5a (WP02); WP02 is sole owner.
- **Steps**:
  1. Create `src/doctrine/tactics/built-in/frozen-baseline-shrink-only-ratchet.tactic.yaml`.
  2. Body: describe the pattern — (a) capture the current call-site / occurrence count into a committed baseline file (e.g. `_baselines.yaml`); (b) in CI, compare the live count to the baseline and fail if `live_count > baseline_count`; (c) the baseline is updated only intentionally by a human (never auto-updated by CI); (d) the allowed direction is "shrink or stay" — growth is a gate failure.
  3. Cite `tests/architectural/_baselines.yaml` (#2159) as the live in-repo exemplar.
  4. Add inline DRG edges: `requires: [urn:directive:DIRECTIVE_043]`.
- **Files**: `src/doctrine/tactics/built-in/frozen-baseline-shrink-only-ratchet.tactic.yaml` (create new)
- **Parallel?**: [P] Can proceed alongside T007 after T006 is scaffolded.
- **Notes**: WP09 and WP03 will reference this tactic via their DRG edges but will NOT edit this file. If another WP adds an edge pointing to this tactic, that is fine — they are consumers, not owners.

### Subtask T009 – Verify inline DRG edges

- **Purpose**: Confirm that all three WP02 artifacts have their inline DRG edges (`requires`/`suggests`/`refines`) present in the YAML before marking this WP ready for review.
- **Steps**:
  1. Open each of the three artifact files and confirm:
     - `043-close-defect-class-by-construction.directive.yaml`: has `suggests` edges to the two tactics.
     - `architectural-gate-non-vacuity.tactic.yaml`: has `requires: DIRECTIVE_043`, `suggests: frozen-baseline-shrink-only-ratchet`.
     - `frozen-baseline-shrink-only-ratchet.tactic.yaml`: has `requires: DIRECTIVE_043`.
  2. Confirm `graph.yaml` has NOT been regenerated (it must NOT be touched — PD-2).
  3. Record confirmation in Activity Log.
- **Files**: No files changed — verification only.
- **Parallel?**: No — must run after T006, T007, T008.
- **Notes**: The graph.yaml regen is intentionally deferred to WP12. Inline edges in the artifact YAML are the persisted signal; the graph is a derived artifact.

### Subtask T010 – DoD verification

- **Purpose**: Run the per-conversion Definition of Done gates before moving to `for_review` (per `contracts/conversion-dod.md`).
- **Steps**:
  1. `spec-kitty doctor doctrine --json` → confirm 0 skipped / 0 invalid. Note: doctor-green does NOT schema-validate new artifact YAMLs — run the DRG test in step 2 for real schema validation.
  2. `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green. This validates the YAML schema of the newly authored artifacts (`043`, `architectural-gate-non-vacuity`, `frozen-baseline-shrink-only-ratchet`). A malformed YAML that passes doctor must still pass this test. Fix any failures here; do NOT defer them to WP12.
  3. `pytest tests/architectural/test_no_legacy_terminology.py -q` → green. Forbidden terms in examples must be quoted-and-marked, not used in canonical voice (C-004).
  4. `ruff check src/doctrine/directives/built-in/043-close-defect-class-by-construction.directive.yaml src/doctrine/tactics/built-in/architectural-gate-non-vacuity.tactic.yaml src/doctrine/tactics/built-in/frozen-baseline-shrink-only-ratchet.tactic.yaml` — YAML files are not Python; run ruff only on any Python files touched. If no Python was touched, note that in the log.
  5. `mypy` — same scope as ruff: only if Python was touched.
  6. Confirm: agent-profile `directives:` wiring is DEFERRED to WP12; `graph.yaml` regen is DEFERRED to WP12.
  6. Move WP to `for_review` only after all gates above are green.
- **Files**: No files changed — verification only.
- **Parallel?**: No — last subtask.
- **Notes**: If `doctor doctrine --json` reports an invalid artifact, read the error output carefully — the most common cause is a missing required YAML field or a malformed URN reference.

## Test Strategy

- `spec-kitty doctor doctrine --json` after each new artifact is created (catch schema errors early).
- `pytest tests/architectural/test_no_legacy_terminology.py -q` before moving to `for_review`.
- Manual inspection: read each artifact's `requires`/`suggests` fields and verify they reference valid URNs (`urn:directive:DIRECTIVE_043`, `urn:tactic:<slug>`).

## Risks & Mitigations

- **Tooling-design complexity**: §5a is tooling-design prose, not code. The tactic must be concrete enough to implement from; if it reads as vague guidance, tighten the body to name the exact structural elements (floor value, baseline file, self-mutation check).
- **Shared-surface collision (C-003)**: WP02 is sole owner of `frozen-baseline-shrink-only-ratchet.tactic.yaml`. If WP09 or another WP attempts to edit this file, that is a C-003 violation. Confirm via `git diff --stat` that only WP02-owned files are modified.
- **Invented exemplar**: Do NOT describe a fictional test gate. Read the actual files in `tests/architectural/` before writing the tactic body.

## Review Guidance

- T005 overlap-audit record present in Activity Log — explicit "no existing coverage" statement.
- DIRECTIVE_043 has number 043 and `enforcement: required`.
- Tactic `architectural-gate-non-vacuity` names all four concrete elements and cites the live exemplar. Activity Log contains the four-element exemplar mapping (each element mapped to a concrete line/construct in `test_protection_resolver_call_sites.py`, or explicitly marked "aspirational" if not demonstrated).
- `frozen-baseline-shrink-only-ratchet` describes the pattern precisely; WP02 is sole owner.
- `doctor doctrine --json` green; terminology guard green.
- `graph.yaml` is UNCHANGED (regen deferred to WP12).
- Agent-profile wiring NOT done here (deferred to WP12).

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-07-01T06:14:46Z – system – Prompt generated via /spec-kitty.tasks
- 2026-07-01T10:05:30Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1724705 – Assigned agent via action command
- 2026-07-01T10:19:52Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1724705 – Ready for review: DIRECTIVE_043 + architectural-gate-non-vacuity + frozen-baseline-shrink-only-ratchet authored. All DoD gates green. Four-element exemplar mapping recorded in tactic notes (floor/self-mutation/routed-count-floor=aspirational; shrink-only-allowlist=demonstrated). graph.yaml untouched (WP12). Agent-profile wiring deferred (WP12).
- 2026-07-01T10:20:06Z – claude:opus:reviewer-renata:reviewer – shell_pid=1826920 – Started review via action command
- 2026-07-01T10:24:20Z – user – shell_pid=1826920 – Review passed (reviewer-renata). 3 doctrine artifacts authored (DIRECTIVE_043 enforcement:required, architectural-gate-non-vacuity + frozen-baseline-shrink-only-ratchet tactics; WP02 sole-owns ratchet per C-003). No test/src gate code smuggled — WP02 commit 50687f9f5 touches only the 3 owned YAMLs. DRG edges use canonical references: schema (extractor maps type:directive->REQUIRES, type:tactic->SUGGESTS) matching prompt intent exactly. Four-element exemplar mapping VERIFIED REAL against tests/architectural/test_protection_resolver_call_sites.py: concrete-floor=aspirational (only builds violations dict + fail, no min-count assert, lines 123-146), self-mutation=aspirational (scan _SRC_ROOT=src/ only line 69/125, gate module in tests/ outside scope), shrink-only-allowlist=DEMONSTRATED (_ALLOWLIST frozenset lines 76-83 + 'if rel in _ALLOWLIST: continue' lines 129-130; _baselines.yaml+test_ratchet_baselines.py both exist), routed-count-floor=aspirational (no assert allowlisted files retain calls). Aspirational markings honest+correct. graph.yaml UNTOUCHED (PD-2). Gates green: doctor doctrine 0 invalid/0 skipped; test_shipped_graph_valid + test_no_legacy_terminology 5 passed; no forbidden terms.
- 2026-07-01T10:37:25Z – user – shell_pid=1826920 – Moved to planned
- 2026-07-01T10:37:39Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1920066 – Started implementation via action command
- 2026-07-01T10:41:03Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1920066 – Cycle 1: removed root-vs-step duplicate reference in architectural-gate-non-vacuity; compliance suite passes (468 tests green, DRG valid, terminology clean)
- 2026-07-01T10:41:28Z – claude:opus:reviewer-renata:reviewer – shell_pid=1933221 – Started review via action command
- 2026-07-01T10:46:04Z – user – shell_pid=1933221 – Cycle 1: root-vs-step duplicate ref removed; full compliance suite green; four-element mapping intact
