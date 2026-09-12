---
work_package_id: WP01
title: Content-vs-relationship ADR
dependencies: []
requirement_refs:
- C-001
- FR-006
planning_base_branch: feat/doctrine-controlled-transition-gates
merge_target_branch: feat/doctrine-controlled-transition-gates
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-controlled-transition-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-controlled-transition-gates unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-doctrine-controlled-transition-gates-01KY51Z7
base_commit: 9906532c65062fc036eeb015f059eebd39523323
created_at: '2026-07-22T16:14:42.797614+00:00'
subtasks:
- T001
- T002
- T003
phase: Phase 1 - Foundation
history:
- at: '{{TIMESTAMP}}'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: architect-alphonso
authoritative_surface: docs/adr/3.x/
create_intent:
- docs/adr/3.x/2026-07-22-1-gate-binding-content-vs-relationship.md
execution_mode: code_change
model: ''
owned_files:
- docs/adr/3.x/2026-07-22-1-gate-binding-content-vs-relationship.md
- docs/adr/3.x/2026-07-21-1-glossary-first-order-doctrine-artefact.md
role: architect
tags: []
task_type: plan
tracker_refs: []
---

# Work Package Prompt: WP01 – Content-vs-relationship ADR

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` (`plan`) and `authoritative_surface` (`docs/adr/3.x/`). This is a decision-record WP — an architecture/curation lens (e.g. `architect-alphonso` or `curator-carla`) fits better than an implementer.

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
Use language identifiers in code blocks: ````python`,````bash`

---

## Objectives & Success Criteria

Record the **durable, reusable principle** that justifies reusing the existing `mission_step_contract`
ArtifactKind for gate bindings rather than promoting a new `gate` kind — **before** the schema work
(WP05) depends on it, so the reuse decision is a recorded principle rather than a retro-justification.

Complete when:

- A new ADR `docs/adr/3.x/2026-07-22-1-gate-binding-content-vs-relationship.md` exists, follows the
  shared ADR template, and states the **content-vs-relationship principle**:
  - **PROMOTE** a concept to a first-class `ArtifactKind` only when introducing a new *distributable
    content artefact* with its own files / repository / provenance (e.g. the glossary pack — its own
    `*.glossary-pack.yaml` files, migrateable term corpus, `glossary_pack:` URN).
  - **REUSE / attach** when declaring a *relationship or configuration* on an existing artefact — a
    gate binding is a **field on `MissionStepContract`** (`gates: list[GateBinding]`), not a
    standalone repository, so it rides current activation with no new enumeration surface.
- The ADR **reconciles the two opposite precedents** the post-plan squad flagged (C-C4, R-F/carla):
  the glossary was **promoted** (`2026-07-21-1-glossary-first-order-doctrine-artefact.md`, decision 1),
  the gate is **reused** — and explains *why the same governing rule produces opposite outcomes*
  (content vs relationship), so a future reader does not read them as a contradiction.
- It satisfies the **#2468 decision-record obligation** and cites C-001 (spec constraint) as its driver.
- A **reciprocal "Related ADRs" cross-link** is added *from* the glossary-first-order ADR back to this
  one (T002), so a reader landing on either discovers the governing principle.
- `markdownlint` passes on both touched files, and the ADR is registered in the `3.x` index (T003).

Independent test (per tasks.md): `markdownlint` passes; the ADR reconciles the glossary-*promoted* vs
gate-*reused* precedents and is cross-linked **both ways**.

Requirements covered: **C-001** (records the principle), **FR-006** (the reuse this ADR justifies).

## Context & Constraints

- **Charter**: [`.kittify/charter/charter.md`](../../../.kittify/charter/charter.md) — Single-canonical-authority
  and architectural-alignment principles bind this record. If the charter and this prompt disagree, the
  charter wins; flag the drift.
- **Mission artifacts**: [spec.md](../spec.md) (C-001, FR-006), [plan.md](../plan.md) (IC-01),
  [tasks.md](../tasks.md) (WP01), [post-plan-squad.md](../reviews/post-plan-squad.md) (finding C-C4).
- **The precedent to reconcile**: [`docs/adr/3.x/2026-07-21-1-glossary-first-order-doctrine-artefact.md`](../../../docs/adr/3.x/2026-07-21-1-glossary-first-order-doctrine-artefact.md)
  — decision 1 there **promotes** `GLOSSARY_PACK` to "a first-order, charter-activatable `ArtifactKind`
  … it joins the 8-kind charter-activatable universe, **not** the `{template, asset}` exclusion set."
  That is the *content* pole. This ADR records the *relationship* pole.
- **Optional cross-link**: [`docs/adr/3.x/2026-05-16-1-doctrine-layer-merge-semantics.md`](../../../docs/adr/3.x/2026-05-16-1-doctrine-layer-merge-semantics.md)
  — the governing doctrine-integrity ADR; link it if it strengthens the lineage.
- **Slug collision is REAL — pin, do not wildcard.** `2026-07-21` already carries **two** `-1-` ADRs
  (`2026-07-21-1-in-tension-with-drg-edge.md` and `2026-07-21-1-glossary-first-order-doctrine-artefact.md`,
  both listed in `docs/adr/3.x/README.md`). Naming the new file with a wildcard or an unpinned index
  risks a third collision. **Pin `2026-07-22-1`** exactly (a new date, sequence `-1-`).
- **No code.** This WP touches only `docs/adr/3.x/` and the ADR index/registry. `execution_mode` is
  `code_change` because it edits versioned files, but there is no Python and no test suite to author —
  the "independent test" is `markdownlint` + a human read of the reconciliation.

## Branch Strategy

- **Strategy**: single mission branch (file-partitioned ownership; each hot file owned by exactly one WP)
- **Planning base branch**: `feat/doctrine-controlled-transition-gates`
- **Merge target branch**: `feat/doctrine-controlled-transition-gates`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T001 – Author the content-vs-relationship ADR

- **Purpose**: Create the durable decision record justifying gate-binding reuse of `mission_step_contract`.
- **File (create)**: `docs/adr/3.x/2026-07-22-1-gate-binding-content-vs-relationship.md`.
- **Template**: Use the shared ADR template at `docs/architecture/adr-template.md` (referenced by
  `docs/adr/3.x/README.md`). Match the frontmatter + section shape of the glossary-first-order ADR:
  `title` / `status: Accepted` / `date: '2026-07-22'` frontmatter, then **Status**, **Date**,
  **Deciders**, **Technical Story**, **Context and Problem Statement**, **Decision Drivers**,
  **Considered Options**, **Decision Outcome**, **Consequences**.
- **The principle to record (the load-bearing content)**:
  - State the rule crisply: *promote a concept to a first-class `ArtifactKind` only for a new
    distributable **content** artefact with its own files/repository/provenance; reuse/attach when
    declaring a **relationship or configuration** on an existing artefact.*
  - Apply it to this mission: a **gate binding is a field** (`gates: list[GateBinding]` on
    `MissionStepContract`), authored in `review.step-contract.yaml` — it has no independent files,
    repository, or provenance of its own; it configures *when a named handler fires on a transition
    edge*. Therefore **reuse `mission_step_contract`**, do **not** add a `gate` ArtifactKind.
- **Reconcile the two precedents (mandatory — squad C-C4)**: Add an explicit paragraph (or a two-row
  table) contrasting: glossary pack = new content → **promoted** (`2026-07-21-1-glossary-first-order`
  decision 1); gate binding = relationship/config on an existing contract → **reused**. Show the
  *same* governing rule yields the opposite outcome because the *nature of the artefact differs*, not
  because the rule is inconsistent. Without this the ADR reads as a contradiction of its sibling.
- **Considered Options**: at minimum (1, chosen) reuse `mission_step_contract`; (2, rejected) promote a
  new `gate` ArtifactKind — reject it on the content-vs-relationship rule *and* the #2468 cost (a new
  kind means new enumeration surfaces: `pack_context._BUILTIN_ARTIFACT_KINDS`,
  `activations._ALLOWED_KINDS`, `org_pack_loader._ORG_DRG_CANONICAL_KINDS` — the three mirrored
  kind-lists the glossary ADR names as drift-guarded). Rationale is the durable **principle**, not
  merely the cost.
- **Decision Drivers**: C-001 (primary); single-canonical-authority; the #2468 decision-record
  obligation; frames C-002 (native handlers only) and FR-006.
- **Technical Story**: reference epic #2535 (half A), spec C-001, tracker #2468 (the decision-record
  obligation), and the sibling ADR `2026-07-21-1-glossary-first-order-doctrine-artefact.md`.
- **Notes**: keep it short and principled (the glossary ADR is long because it decides a program; this
  ADR decides one reuse rule — a page is plenty). Do NOT restate WP05's schema in detail; link forward
  to `data-model.md §3` and let the schema WP own the field shape.

### Subtask T002 – Reciprocal "Related ADRs" cross-link from the glossary-first-order ADR

- **Purpose**: Make the governing principle discoverable from *either* precedent, closing the squad
  C-C4 "no reciprocal cross-link" gap.
- **File (edit)**: `docs/adr/3.x/2026-07-21-1-glossary-first-order-doctrine-artefact.md`.
- **Steps**: Add a **"Related ADRs"** cross-link *from* that ADR *to* the new
  `2026-07-22-1-gate-binding-content-vs-relationship.md`, framed as "the reuse/attach counterpart of
  this promote decision — same content-vs-relationship rule, opposite outcome." That file already
  links `2026-05-16-1-doctrine-layer-merge-semantics.md` ("Aligns with ADR 2026-05-16-1", line 25) —
  add the reciprocal link near that existing lineage note or under **Consequences → Boundaries**,
  whichever keeps the file's existing shape cleanest. Do not restructure the ADR; add a link, nothing
  more.
- **Optionally** add the same "Related ADRs" note to the new ADR pointing at `2026-05-16-1`
  (doctrine-layer merge semantics) if it strengthens the lineage — optional, not required.
- **Parallel?**: Marked `[P]` in tasks.md — it edits a *different* file than T001 creates, so it can be
  authored alongside T001. Both files are owned by this WP, so there is no cross-WP contention.
- **Notes**: keep the edit minimal and idempotent; do NOT alter the glossary ADR's decisions,
  frontmatter `date`, or status — only add the reciprocal reference.

### Subtask T003 – Markdownlint + ADR index/registry update

- **Purpose**: Register the new ADR so the `docs-freshness` CI gate stays green and the ADR is
  navigable; confirm lint cleanliness on both touched files.
- **Steps**:
  1. Run the canonical registry updater (per `docs/adr/3.x/README.md` and `docs/adr/index.md`):
     ```bash
     python scripts/docs/freshen_adr_inventory.py docs/adr/3.x/2026-07-22-1-gate-binding-content-vs-relationship.md
     ```
     This freshens **both** indexes the `docs-freshness` gate enforces — the page-inventory lockfile
     (`docs/development/3-2-page-inventory.yaml`) and the `3.x/README.md` index table — in one
     idempotent pass. Do NOT hand-edit the README table row if the script maintains it; use the script
     (canonical-sources rule). Use `--check` to verify without writing if you want a dry run first.
  2. Run markdownlint on both owned files and fix any violations (the repo runs markdownlint in CI; a
     forbidden-heading or list-style violation is a real red):
     ```bash
     npx --yes markdownlint-cli2 "docs/adr/3.x/2026-07-22-1-gate-binding-content-vs-relationship.md" "docs/adr/3.x/2026-07-21-1-glossary-first-order-doctrine-artefact.md"
     ```
     (Fall back to the repo's configured markdownlint invocation if that differs.)
- **Files**: `docs/adr/3.x/2026-07-22-1-gate-binding-content-vs-relationship.md` (new),
  `docs/adr/3.x/2026-07-21-1-glossary-first-order-doctrine-artefact.md` (edited); the index/lockfile the
  script maintains are outside this WP's `owned_files` — the script is the sanctioned writer, so run it
  rather than hand-editing shared registry files. If the script touches files owned by no WP, that is the
  registry's own generated surface; note it in the Activity Log.
- **Notes**: the slug-collision guard lives here too — after the script runs, confirm the README table
  has a **distinct `2026-07-22`** row and did not overwrite or merge with a `2026-07-21` entry.

## Test Strategy (include only when tests are required)

- No unit tests — this is a docs WP. The "independent test" (per tasks.md) is: **markdownlint passes**
  and a human confirms the ADR reconciles the glossary-*promoted* vs gate-*reused* precedents and is
  cross-linked **both ways**.
- Verification commands:
  ```bash
  python scripts/docs/freshen_adr_inventory.py --check docs/adr/3.x/2026-07-22-1-gate-binding-content-vs-relationship.md
  npx --yes markdownlint-cli2 "docs/adr/3.x/2026-07-22-1-gate-binding-content-vs-relationship.md"
  ```
- If touching any doctrine prose, also run `pytest tests/architectural/test_no_legacy_terminology.py`
  (≈0.1s) — an ADR using `feature`-family wording would trip the Terminology Canon guard.

## Risks & Mitigations

- **Retro-justification risk** (IC-01 risk): if this ADR lands *after* WP05's schema, the reuse decision
  becomes retro-justification. Mitigation: WP01 has **no dependencies** and lands in Phase 1 alongside
  WP02 — author it first.
- **Slug collision**: `2026-07-21-1` is already doubly used. Mitigation: pin `2026-07-22-1`; after T003
  confirm a distinct README row (see T003 note).
- **Reads as a contradiction of its sibling**: without the explicit reconciliation paragraph a reviewer
  sees "glossary promoted, gate reused" as inconsistent. Mitigation: the reconciliation is a mandatory
  T001 deliverable, not optional prose.
- **CI docs-freshness red**: forgetting the inventory script fails `docs-freshness`. Mitigation: T003
  runs it and `--check`s it.

## Review Guidance

- **Principle stated durably** — the ADR gives a *reusable rule* (content → promote; relationship →
  reuse), not just "we reused `mission_step_contract` because #2468 is expensive."
- **Reconciliation present and correct** — the glossary-promoted vs gate-reused precedents are
  explicitly contrasted and shown to follow one rule.
- **Both-way cross-link** — the new ADR references the glossary ADR *and* the glossary ADR references
  the new one (T002). Reject if either direction is missing.
- **Slug pinned** — file is `2026-07-22-1-...`, not a wildcard; the README table has a distinct
  `2026-07-22` row.
- **Lint + freshness green** — `markdownlint` clean; `freshen_adr_inventory.py --check` passes.
- **#2468 obligation met** — the ADR cites the decision-record obligation and C-001.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Format**:

```
- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>
```

**Why this matters**: The acceptance system reads the LAST activity log entry as the current state. If entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:

- {{TIMESTAMP}} – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task <WPID> --to <status>` to change WP status.
