---
work_package_id: WP07
title: Gate terminology registration
dependencies:
  - "WP05"
requirement_refs:
- FR-015
planning_base_branch: feat/doctrine-controlled-transition-gates
merge_target_branch: feat/doctrine-controlled-transition-gates
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-controlled-transition-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-controlled-transition-gates unless the human explicitly redirects the landing branch.
subtasks:
- T032
- T033
- T034
phase: Phase 3 - Binding
history:
- at: '{{TIMESTAMP}}'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: "doctrine-daphne"
authoritative_surface: src/doctrine/glossary_packs/
create_intent:
- tests/glossary/test_gate_terms.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/glossary_packs/built-in/spec-kitty-core.glossary-pack.yaml
- docs/context/orchestration.md
- tests/glossary/test_gate_terms.py
role: "curator"
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP07 – Gate terminology registration

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `` (unset — select below)
- **Role**: ``
- **Agent/tool**: ``

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` (`implement`) and `authoritative_surface` (`src/doctrine/glossary_packs/`). This is a terminology/doctrine-curation WP; a curator- or doctrine-leaning profile fits.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``. Use language identifiers in code blocks (` ```yaml `, ` ```bash `).

---

## Objectives & Success Criteria

Register the three new gate-family terms — **`transition gate`**, **`gate handler`**, **`gate binding`** — as canonical terms in BOTH glossary surfaces, each carrying an explicit "Do NOT confuse with" guard against the five *real* pre-existing gate senses, so the new vocabulary does not fragment the now-first-order, enforced glossary (FR-015, IC-06).

**Done when:**

- The three terms are authored in the glossary pack `src/doctrine/glossary_packs/built-in/spec-kitty-core.glossary-pack.yaml` (verify the actual built-in pack path first — see Context) with disambiguation guards.
- The same three terms are authored in `docs/context/orchestration.md`, the canonical **human** term home per CLAUDE.md's Terminology Canon, following the existing `### branch strategy gate` entry pattern (`docs/context/orchestration.md:369-377`) including a **Related terms** cross-link row.
- A focused terminology regression `tests/glossary/test_gate_terms.py` proves the terms resolve in **both** surfaces and that no forbidden casing / phantom sense is introduced.
- The full terminology-guard suite (`pytest tests/architectural/test_no_legacy_terminology.py`) stays green.
- NO third divergent copy is added to the legacy seed `.kittify/glossaries/` (that reconciliation is #1418's job — see Guards).

**Tracker**: FR-015 (IC-06).

## Context & Constraints

- **Mission**: `doctrine-controlled-transition-gates-01KY51Z7` · **Branch**: `feat/doctrine-controlled-transition-gates`.
- **Spec**: [spec.md](../spec.md) FR-015 (`spec.md:117`). **Plan**: [plan.md](../plan.md) IC-06 (`plan.md:149-155`). **Squad**: [reviews/post-plan-squad.md](../reviews/post-plan-squad.md) findings C-C5 (orchestration.md omitted) and C-C6 (phantom `semantic gate` dropped).
- **The FIVE real senses** these new terms must disambiguate against (grep-verified in the glossary pack — do NOT invent a sixth). Each new term's guard clause should name these and, briefly, why it differs:

  | Real sense | Anchor | What it is (so the guard is meaningful) |
  |---|---|---|
  | `branch strategy gate` | `spec-kitty-core.glossary-pack.yaml:48` (surface) · `docs/context/orchestration.md:369` | The mission-create guard requiring an explicit branch decision before planning artifacts are written on a primary branch. |
  | `diff compliance gate` | `spec-kitty-core.glossary-pack.yaml:153` (surface) | The review-time check validating a WP diff against its occurrence map (bulk-edit guardrail). |
  | `dependency gate` | `spec-kitty-core.glossary-pack.yaml:284` (surface) | The claim/implement gate blocking a WP until its `dependencies` are `approved`/`done`. |
  | `merge dependency gate` | referenced at `spec-kitty-core.glossary-pack.yaml:263` (`policy/merge_gates.py` sense) | The merge-time dependency check (distinct from the claim-time `dependency gate`). |
  | `sonar quality gate` | `spec-kitty-core.glossary-pack.yaml:547` (surface) | The SonarCloud new-code quality-gate status aggregate. |

  None of these is a *transition gate* (a lane-edge check resolved from active doctrine), a *gate handler* (a named `GATE_REGISTRY` callable), or a *gate binding* (a doctrine declaration on the review contract) — that is precisely the confusion the guards must foreclose.
- **Do NOT reference a phantom `semantic gate`** — squad finding C-C6 confirmed no such surface exists; naming it would fabricate a sense.
- **Glossary-pack entry shape** (alphabetical by `surface`, verify against `spec-kitty-core.glossary-pack.yaml:148-153`):
  ```yaml
  - confidence: 0.95
    definition: <one paragraph; may include an inline "Do NOT confuse with …" guard>
    status: active
    surface: <term>
  ```
- **Pack-file header caveat**: the pack file's top comment (`spec-kitty-core.glossary-pack.yaml:1-6`) says it was migrated from the seed and "Do not hand-edit; re-run the migration script." The plan (IC-06, `plan.md:153`) nonetheless directs editing the pack directly for this mission, because the seed is being retired by Mission C / #1418 and a re-migration would clobber unrelated in-flight pack edits. **Reconcile this before writing**: prefer a direct, alphabetically-correct hand edit of the pack, and note in the Activity Log that the migration header is stale for the #1418-retirement window. If the built-in pack path has moved, verify the actual path (`ls src/doctrine/glossary_packs/built-in/`) and own the real file.
- **New/changed code** passes `ruff` clean; the test module passes `mypy --strict`; ≥90% coverage of any helper it introduces. No `# noqa` / `# type: ignore`.
- **Pre-push discipline** (CLAUDE.md): touching `src/doctrine/` or user-facing prose requires `pytest tests/architectural/test_no_legacy_terminology.py` before pushing — some repo-wide terminology gates only run in CI's `integration-tests-core-misc` job.
- **Why BOTH surfaces** (per CLAUDE.md Terminology Canon + squad C-C5): the glossary pack is the machine-readable authority consumed by the semantic-integrity pipeline; `docs/context/orchestration.md` is the canonical human home operators and agents read (it hosts the `#primary-partition`/`#branch-strategy-gate` senses the footgun note links). A term present in only one surface is half-registered — the pipeline cannot resolve a human-only term, and a human cannot discover a pack-only term. FR-015 requires both.
- **Ordering within the WP**: author T034 (the test) FIRST and confirm it is red; then land T032 and T033; then confirm T034 green. This makes the WP genuinely ATDD red-first rather than test-after.

## Branch Strategy

- **Strategy**: feature-branch (PR-bound, C-004).
- **Planning base branch**: `feat/doctrine-controlled-transition-gates`.
- **Merge target branch**: `feat/doctrine-controlled-transition-gates`.

> Populated by `spec-kitty agent mission tasks`. Do NOT change manually unless the branch topology changed. **Deps**: WP05 (terms are authored *after* the gate-binding schema fixes their precise meaning — `plan.md:154`, IC-06 rides alongside IC-04).

## Subtasks & Detailed Guidance

### Subtask T032 – Register the three terms in the glossary pack

- **Purpose**: Give the machine-readable glossary pack canonical definitions for `transition gate`, `gate handler`, `gate binding`, each guarding against the five real senses so the semantic-integrity pipeline treats them as distinct (FR-015).
- **Steps** (ATDD red-first: T034's test is authored first and fails until this lands):
  1. Confirm the built-in pack path (`src/doctrine/glossary_packs/built-in/spec-kitty-core.glossary-pack.yaml`) and read the entry shape at `:148-153`.
  2. Insert three `surface`-keyed entries in **alphabetical position** (`gate binding`, `gate handler`, `transition gate` all sort under `g`/`t` — place each where the `surface` ordering demands; do not append at EOF).
  3. Each `definition` must (a) state the mission's meaning and (b) carry an inline "Do NOT confuse with `branch strategy gate` / `diff compliance gate` / `dependency gate` / `merge dependency gate` / `sonar quality gate`" clause. Anchor the definitions to this mission's data-model:
     - **`transition gate`** — a check that must pass before a WP status-transition edge (e.g. `in_progress->for_review`) is allowed; resolved from the repo's active doctrine, dispatched through `_mt_run_transition_gates` (see [data-model.md](../data-model.md) §8, `contracts/transition-gate-hook.md`).
     - **`gate handler`** — a named, dispatchable check in `GATE_REGISTRY` (`data-model.md` §4); the Spec-Kitty pre-review engine is the first registered handler keyed to `for_review`.
     - **`gate binding`** — a versioned doctrine declaration attaching a named handler to a transition edge (`{on_transition, handler, handler_kind, schema_version, fail_open, provenance}`), authored on the review `MissionStepContract` (`data-model.md` §3).
  4. Suggested definition skeletons (adapt wording; keep them parallel with the T033 human entries so T034's cross-surface consistency check passes):
     - `transition gate`: "A check that must pass before a work-package status-transition edge (e.g. `in_progress->for_review`) is allowed. Resolved from the repo's active doctrine and dispatched through the inverted move-task hook (`_mt_run_transition_gates`); the flagship handler is the scoped pre-review regression check. Do NOT confuse with the five pre-existing `*gate*` senses (branch strategy / diff compliance / dependency / merge dependency / sonar quality) — those are unrelated one-off guards, not doctrine-resolved lane-edge checks."
     - `gate handler`: "A named, dispatchable check registered in `GATE_REGISTRY`; the Spec-Kitty pre-review engine is the first handler, keyed to the `for_review` edge. Registry membership is the callable source; activation decides whether it runs. Do NOT confuse with … (five senses)."
     - `gate binding`: "A versioned doctrine declaration attaching a named gate handler to a status-transition edge (`{on_transition, handler, handler_kind, schema_version, fail_open, provenance}`), authored on the review `MissionStepContract`. A binding is a field/relationship, not a standalone artefact. Do NOT confuse with … (five senses)."
- **Files**: `src/doctrine/glossary_packs/built-in/spec-kitty-core.glossary-pack.yaml`.
- **Parallel?**: `[P]` — independent of T033 (different file); both feed T034.
- **Notes**: Do NOT touch the phantom `semantic gate`. Keep `confidence: 0.95`, `status: active`. Record the migration-header reconciliation (see Context) in the Activity Log. The semantic-integrity pipeline (`src/specify_cli/glossary/`) may flag near-duplicate surfaces — the "Do NOT confuse with" clause is what keeps the five senses + three new terms distinct rather than collapsed.

### Subtask T033 – Author the three terms in `docs/context/orchestration.md`

- **Purpose**: `docs/context/orchestration.md` is the canonical **human** term home per CLAUDE.md's Terminology Canon (the glossary anchors the `#primary-partition` / `#branch-strategy-gate` senses there). The three terms must exist here too so operators and agents discover them, and so cross-links resolve (squad C-C5).
- **Steps**:
  1. Follow the exact entry pattern of `### branch strategy gate` (`docs/context/orchestration.md:369-377`): an `### <term>` heading, a two-column `| | |` table with **Definition**, **Context** (`Orchestration`), **Status** (`canonical`), **Applicable to** (`3.x`), and a **Related terms** row.
  2. Place the three `###` entries in the file's existing alphabetical run of `###` term headings (near the other `gate`-family entries around `:369`).
  3. **Related terms** must cross-link the sibling new terms and the nearest real senses, e.g. `transition gate` → [gate handler], [gate binding], [branch strategy gate], and cross-reference the hook contract. Use the `[term](#anchor)` slug form already used at `:365`/`:377`.
  4. Keep the human definitions consistent with the pack definitions (T032) — divergence between the two surfaces is exactly what T034 guards against.
- **Concrete pattern to copy** (from `### branch strategy gate`, `docs/context/orchestration.md:369-377`):
  ```markdown
  ### transition gate

  | | |
  |---|---|
  | **Definition** | <one-paragraph human definition; include the five-sense "Do NOT confuse with" clause> |
  | **Context** | Orchestration |
  | **Status** | canonical |
  | **Applicable to** | `3.x` |
  | **Related terms** | [gate handler](#gate-handler), [gate binding](#gate-binding), [branch strategy gate](#branch-strategy-gate), [diff compliance gate](#diff-compliance-gate) |
  ```
- **Files**: `docs/context/orchestration.md`.
- **Parallel?**: `[P]` — independent of T032.
- **Notes**: Markdownlint must pass. Do not renumber or disturb the `#primary-*` / `#target-ref` anchors CLAUDE.md's footgun note depends on. Anchor slugs are the lowercased, hyphenated heading (`### gate handler` → `#gate-handler`); verify the cross-links resolve to real headings (a dangling `[term](#anchor)` is a silent doc rot).

### Subtask T034 – Terminology regression `tests/glossary/test_gate_terms.py` (authored red-first)

- **Purpose**: Lock both surfaces so a later edit cannot silently drop a term, diverge the two definitions, or reintroduce forbidden casing / the phantom sense (FR-015 acceptance: "terms resolve in both surfaces; terminology-guard suite green; no `semantic gate` phantom").
- **Steps** (write this FIRST; it must be red before T032/T033 land):
  1. Assert each of `transition gate`, `gate handler`, `gate binding` resolves as an active `surface` in the parsed glossary pack (load via the glossary pipeline under `src/specify_cli/glossary/`, not a raw string grep, so it exercises the real resolver).
  2. Assert each of the three terms is present as an `### <term>` heading in `docs/context/orchestration.md`.
  3. Assert each pack definition contains the disambiguation guard clause and that NONE of the three definitions references `semantic gate` (phantom-sense guard).
  4. Assert no forbidden casing regression (e.g. `Feature`/`feature` per the Terminology Canon) is introduced by the new prose — reuse the assertion style from `tests/architectural/test_no_legacy_terminology.py` rather than re-deriving.
  5. Keep the test focused and deterministic: three terms × two surfaces × the phantom/casing guards. Aim ≥90% coverage of any helper the test module introduces (e.g. a small pack-loader wrapper); do not add broad, slow glossary-integration coverage here — that belongs to the pipeline's own suite.
- **Files**: `tests/glossary/test_gate_terms.py` (create; declared in `create_intent`).
- **Parallel?**: No — it is the acceptance oracle for T032+T033.
- **Notes**: `PYTHONPATH=$(pwd)/src`. If the glossary pipeline exposes a term-lookup helper (under `src/specify_cli/glossary/`), prefer it over hand-parsing YAML so the test breaks if the pack schema changes. Parse `docs/context/orchestration.md` for the `### <term>` headings rather than a substring match, so a term mentioned only in prose (not defined as a heading) does not false-pass.
- **Acceptance mapping**: this test is the machine proof of FR-015's "terms resolve in both surfaces; terminology-guard suite green; no `semantic gate` phantom."

## Test Strategy (tests required)

- **New test**: `tests/glossary/test_gate_terms.py` — the red-first oracle above.
- **Existing guard to keep green**: `pytest tests/architectural/test_no_legacy_terminology.py` (≈0.1s; run before push).
- **Commands**:
  ```bash
  PYTHONPATH=$(pwd)/src pytest tests/glossary/test_gate_terms.py -q
  PYTHONPATH=$(pwd)/src pytest tests/architectural/test_no_legacy_terminology.py -q
  ruff check src/doctrine/glossary_packs/built-in/spec-kitty-core.glossary-pack.yaml tests/glossary/test_gate_terms.py
  ```
- **Red-first proof**: run `test_gate_terms.py` before authoring T032/T033 and capture the failure in the Activity Log; then land T032/T033 and show it green.
- **Semantic-integrity check** (if the pipeline exposes a validate entrypoint): run the glossary validation over the pack after the edit to confirm the three new surfaces are accepted and not flagged as duplicate/conflicting with the five existing senses:
  ```bash
  PYTHONPATH=$(pwd)/src python -c "from specify_cli import glossary"  # smoke-import the pipeline package
  ```
  If a dedicated glossary-validate CLI/subcommand exists, prefer it; the goal is to catch a near-duplicate-surface rejection before CI.

## Risks & Mitigations

- **Fabricating a sixth sense** — naming `semantic gate` (or any non-existent surface) would create a phantom. *Mitigation*: guard list is exactly the five grep-verified senses; T034 asserts the phantom's absence.
- **Two surfaces drift** — pack and orchestration.md definitions diverge over time. *Mitigation*: T034 asserts both surfaces carry the term; keep the wording parallel.
- **Migration-header clobber** — re-running the glossary migration script would overwrite unrelated in-flight pack edits. *Mitigation*: hand-edit the pack for this #1418-retirement window and log the rationale; do NOT re-run the migration.
- **Legacy-seed third copy** — editing `.kittify/glossaries/spec_kitty_core.yaml` would create a third divergent copy. *Mitigation (GUARD)*: do NOT touch the legacy seed — seed↔pack reconciliation is #1418's job (plan Punt-check, `post-plan-squad.md:37`).
- **Premature term authoring** — defining the terms before WP05 fixes their meaning risks a definition that contradicts the shipped schema. *Mitigation*: this WP depends on WP05; anchor definitions to `data-model.md` §3/§4/§8 as landed, not to a guessed shape.
- **Dangling cross-links** — a `[term](#anchor)` pointing at a non-existent heading. *Mitigation*: verify every Related-terms link resolves to a real `###` heading; markdownlint + manual anchor check.

## Review Guidance

- Confirm all three terms exist in BOTH surfaces with matching meaning and a five-sense guard, and that `semantic gate` appears nowhere.
- Confirm `.kittify/glossaries/` is untouched (`git diff --stat` shows only the three owned files).
- Confirm `test_gate_terms.py` exercises the real glossary resolver (not a bare grep) and that the terminology-guard suite is green.
- Confirm alphabetical placement in the pack and markdownlint-clean orchestration.md.
- Confirm the pack and orchestration.md definitions are parallel (no drift between the machine and human surfaces) and anchored to the mission's data-model, not a guessed schema.
- Confirm every Related-terms cross-link resolves to a real `###` heading (no dangling anchors).
- Confirm the WP was executed red-first: the Activity Log should show `test_gate_terms.py` red before T032/T033 and green after.
- Confirm the pre-push terminology guard (`tests/architectural/test_no_legacy_terminology.py`) was run and is green — this is the CI-only-gate the pack/prose edit can otherwise trip.

## Activity Log

> **CRITICAL**: entries in chronological order (oldest first, newest last). Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>` (UTC, `date -u "+%Y-%m-%dT%H:%M:%SZ"`).

- {{TIMESTAMP}} – system – Prompt created.
