---
work_package_id: WP08
title: Field-authority ADR + identity vocabulary
dependencies:
- WP07
requirement_refs:
- FR-013
planning_base_branch: feat/runtime-state-corpus-cutover
merge_target_branch: feat/runtime-state-corpus-cutover
branch_strategy: Planning artifacts for this mission were generated on feat/runtime-state-corpus-cutover. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/runtime-state-corpus-cutover unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
agent: "claude"
shell_pid: "359894"
shell_pid_created_at: "1784570891.77"
history:
- timestamp: '2026-07-20T08:39:02Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: architect-alphonso
authoritative_surface: docs/adr/3.x/
create_intent: []
execution_mode: planning_artifact
model: claude-opus-4-8
owned_files:
- docs/adr/3.x/2026-07-19-1-wp-runtime-state-event-log-eviction-via-innerstatechanged.md
- docs/context/identity.md
role: architect
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

**Before reading any further**, load the `architect-alphonso` architect profile via the
`/ad-hoc-profile-load` skill. Adopt its identity, governance scope, boundaries, and the initialization
declaration it prints. Everything below is authored for that profile: a system-design ruling recorded as
doctrine of record, terminology adherence, single-canonical-authority discipline. This is a **pure
doctrine/prose** WP — no code. Do not begin editing until the profile is loaded and its init declaration
is on the record.

## Objective

Ratify the **per-field authority** for a WP's runtime identity as an ADR of record, and adopt the two
governing terms into the identity glossary — **before** the IC-08 event vocabulary (WP09) lands. The
ruling: the *resolved actual* `role`/`agent_profile`/`model` that take a WP are **dynamic /
event-log-authoritative** (latest-wins); the *authored recommendation* stays **static /
frontmatter-canonical**. The recorded resolved value MUST originate from
`resolve_profile`/`resolved_agent()` / the dispatch resolution — never a copy of the frontmatter string
(C-007) — and authored intent is never conflated with the resolved actual (C-008). Record this as an
**addendum to ADR `2026-07-19-1`** (which deferred model election as blocker B4), and add `authored
intent` / `resolved binding` to `docs/context/identity.md`. This WP is the **C-009 gate**: WP09's
vocabulary change is not sanctioned until this ADR exists.

## Context & grounding

- **Plan IC-08a** (`plan.md:406-408`, also `plan.md:151-153` + the Structure map): author the
  field-authority ADR as an addendum to `2026-07-19-1` (model-election blocker B4) — resolved
  `role`/`agent_profile`/`model` → dynamic/event; authored → static/frontmatter — and add the two terms to
  `identity.md`. **IC-08a precedes the vocabulary** (`plan.md:409`: "IC-08a ADR precedes the vocabulary
  change").
- **Spec C-009** (`spec.md:270`): the per-field authority decision is recorded as an ADR (addendum to
  `2026-07-19-1`) **before the vocabulary lands** — a per-field authority ruling is ADR-worthy **per the
  #2093 precedent** (a canonical-authority ruling is a system-design decision, not an implementation detail).
- **Spec C-007** (`spec.md:268`) + **INV-6** (`data-model.md:98-100`): the recorded resolved value comes
  from `resolve_profile`/`resolved_agent()` / dispatch resolution — copying the static frontmatter
  `agent_profile` string into an event manufactures a *new* split-brain (the exact #2093 anti-pattern).
- **Spec C-008** (`spec.md:269`) + **INV-7** (`data-model.md:101-102`): authored recommendation and resolved
  actual are surfaced as **distinct** values — no consumer treats the authored value as "what ran" or the
  resolved value as "what was intended".
- **Spec Domain Language** (`spec.md:298-309`): the canonical definitions of **authored intent** /
  **resolved binding** (umbrella **canonical authority** = static → frontmatter, dynamic → event log),
  explicitly flagged *"pending glossary adoption in `docs/context/identity.md` — see C-009"* — the adoption
  this WP performs.
- **Spec Assumptions — role reversal** (`spec.md:402-404`): `role` is a **resolved actual** (per the #2093
  ruling text), reversing the interim "keep role frontmatter" note — authored role stays frontmatter, the
  *actual* role that ran is event-sourced. Ratified here in the C-009 ADR.
- **Research D-10** (`research.md:155-177`): the field-authority decision + its lifecycle rationale (the
  actual identity **shifts** implementer→reviewer / model swaps, so a static value is wrong mid-cycle);
  notes these fields are **not** event-sourced today and that `2026-07-19-1` deferred model as blocker B4.
  **Research D-12** (`research.md:195-212`): the dispatch→claim linkage supplying the genuine resolved
  binding — grounding for *why* C-007 is satisfiable (a real resolver exists) without re-reading frontmatter.
- **Data-model — resolved runtime identity vs authored recommendation** (`data-model.md:60-72`): the
  two-column table this ADR + glossary must stay faithful to (Meaning / Authority / Fields / Written /
  Lifecycle / recorded-value source-of-truth).
- **ADR of record** (`docs/adr/3.x/2026-07-19-1-…md`): **Decision 6** deferred static-model election as
  **blocker B4** (`WPMetadata` cannot become a clean static-only projection until its runtime half is
  stripped). The corpus cutover (WP01–WP07) strips that runtime half → B4 is now actionable; the addendum
  extends Decision 6 with the per-field authority ruling.

## Subtasks

### T031 — Author the field-authority ADR (addendum to `2026-07-19-1`, extending blocker B4)

**Purpose**: Record the per-field authority ruling as doctrine of record so the WP09 vocabulary change is
sanctioned (C-009 gate).

**Posture (verified)**: The plan's Structure map marks `2026-07-19-1-*.md` as **EDIT** and the provided
`owned_files` carry no `create_intent` → the addendum is an **appended section on the existing Accepted
ADR**, not a new file. Keep the existing frontmatter (`title`/`status`/`date`) unchanged so the ADR
page-inventory/README index (keyed on frontmatter) is not disturbed.

**Steps**:
1. Append an `## Addendum (2026-07-20): Per-field authority for WP runtime identity` section after the
   existing body. Open by stating it **resolves blocker B4** (Decision 6's deferred static-model
   election), now actionable because the #2816 corpus cutover strips `WPMetadata`'s runtime half.
2. State the **ruling unambiguously, per field**: the *resolved actual* `role`, `agent_profile`
   (+`agent_profile_version`), `model`, and `provider` are **dynamic → event-log/snapshot-authoritative**,
   folded **latest-wins** at each pick-up/claim/reassign; the *authored/recommended* `role`/`agent_profile`/
   `model` are **static → frontmatter-canonical**, authored once at tasks-finalize. Mirror the
   `data-model.md:60-72` table so no field's authority is left implicit.
3. Capture **C-007** as a binding constraint of the ruling: the recorded resolved value MUST be produced by
   `resolve_profile`/`resolved_agent()` / the dispatch resolution — **never** a copy of the frontmatter
   `agent_profile` string (that would manufacture a new split-brain #2093 forbids).
4. Capture **C-008**: authored intent and resolved actual are **never conflated** — every WP-view consumer
   surfaces them as distinct values; the reconstruction reader (IC-07/WP11) is the single assembly point.
5. **Ratify the role reversal** explicitly (`spec.md:402-404`): supersede the interim "keep role
   frontmatter" note — authored role → frontmatter; **actual** role → event-sourced.
6. Record scope + lineage: this is #2093's resolved-binding **"record + reconstruct"** slice + #2400's
   WP-metadata half; the full #2399 fail-closed **enforcement** stays OUT. Reference C-009/FR-013 so the
   ADR is traceable to the requirement it gates.

**Edge cases**: do not restate the whole 2026-07-19 decision — reference it and *extend* B4. Do not flip
`status`/`date`/`title` frontmatter (avoids a spurious inventory-lockfile / README-table diff).

**Validation**: the addendum states the per-field authority (resolved → dynamic/event; authored →
static/frontmatter) with **no** ambiguity; C-007 and C-008 are each captured; the role reversal is ratified;
the section is dated and traceable to C-009/FR-013.

### T032 — Add `authored intent` + `resolved binding` to `docs/context/identity.md`

**Purpose**: Adopt the #2093-ruling vocabulary into the identity glossary (the adoption the spec's Domain
Language section defers to C-009), so canonical terms exist before the vocabulary + reader land.

**Steps**:
1. Add two glossary entries in the existing house table format (mirror the `Agent Profile`/`Role` blocks —
   Definition / Context: Identity / Status / Applicable to: `3.x` / Related terms), taking the canonical
   text from `spec.md:300-306`. **Authored intent** — who/what a WP was *designed* to be run by; authored
   once at planning; **frontmatter-canonical**, never mirrored into events (authored `role`/`agent_profile`/
   `model`). **Resolved binding** — who/what **actually** resolved and ran the WP at a lifecycle transition;
   **event-log/snapshot-authoritative**, latest-wins; shifts across the lifecycle; produced by
   `resolve_profile`/`resolved_agent()`, never a re-read of the frontmatter string. Cross-link both to
   `Agent Profile`, `Role`, and each other; note the umbrella **canonical authority** rule (static →
   frontmatter; dynamic → event log).
2. **Bump the `updated:` frontmatter** date on `identity.md` to the edit date (docs-freshness gate reads
   it); keep the `related:` list and frontmatter otherwise valid (a `test_related_validator.py` guards it).
3. Run the **terminology guard** and the **docs-freshness** gate after the prose edits (commands in Test
   strategy). Fix any forbidden-term / freshness finding at the source — no suppression.

**Edge cases**: match the exact table markup already used in `identity.md` (pipe rows, `---` separators) so
the page renders and the related-terms validator stays green; do not introduce any `feature*` wording
(Terminology Canon).

**Validation**: both terms present with canonical definitions and cross-links; `updated:` bumped;
terminology guard green; docs-freshness green.

## Branch Strategy

Planning artifacts were generated on `feat/runtime-state-corpus-cutover`; this WP's completed changes merge back into `feat/runtime-state-corpus-cutover` (both `planning_base_branch` and `merge_target_branch`). This is a `planning_artifact` (doctrine/prose) WP — doctrine of record, not runtime code. Execute in the workspace `spec-kitty implement WP08` prepares; consume the resolved path. **Depends on WP07** (chains Phase 2 after the Phase-1 cutover tail).

## Test strategy

This is a **prose/doctrine** WP — the gates are the terminology guard and docs-freshness, not code tests. Run per-file with `uv run` (bare `python` resolves a sibling checkout → false greens):

```bash
uv run --extra test python -m pytest -p no:cacheprovider tests/architectural/test_no_legacy_terminology.py
uv run --extra test python -m pytest -p no:cacheprovider tests/docs/test_check_docs_freshness.py
# The addendum edits an existing ADR body (frontmatter unchanged); confirm the ADR indexes are not stale:
uv run python scripts/docs/freshen_adr_inventory.py --check docs/adr/3.x/2026-07-19-1-wp-runtime-state-event-log-eviction-via-innerstatechanged.md
uv run --extra test python -m pytest -p no:cacheprovider tests/docs/test_related_validator.py
```

If `freshen_adr_inventory --check` reports staleness (it should not for a body-only addendum), regenerate with `… freshen_adr_inventory.py --all` and commit the refreshed index — never suppress the gate.

## Definition of Done

- [ ] The **C-009 ADR addendum exists** on `2026-07-19-1`, states the per-field authority (resolved
  `role`/`agent_profile`/`model` → dynamic/event-log; authored → static/frontmatter) unambiguously, and
  **extends blocker B4** (Decision 6) — and **precedes** the IC-08 vocabulary (WP09 is gated on it).
- [ ] **C-007** (resolved value from `resolve_profile`/`resolved_agent()`/dispatch, never a frontmatter
  copy) and **C-008** (authored ≠ resolved, never conflated) are captured in the ruling.
- [ ] The **role reversal** is ratified (authored role → frontmatter; actual role → event-sourced).
- [ ] `docs/context/identity.md` carries **both** `authored intent` and `resolved binding` with canonical
  definitions, cross-links, and `updated:` bumped.
- [ ] **Terminology guard green** (`tests/architectural/test_no_legacy_terminology.py`).
- [ ] **Docs-freshness green** (`tests/docs/test_check_docs_freshness.py`; ADR inventory `--check` clean;
  related-terms validator green) — no suppression.

## Risks & out-of-map edits

- **Ordering (C-009 gate)**: this ADR MUST land **before WP09** (the IC-08 vocabulary) — that is the whole
  point of IC-08a. WP09/WP10 depend transitively; do not let the vocabulary WP proceed without this ruling
  of record. The dependency edge (`WP08 → WP09`) enforces it during merge.
- **No out-of-map edits**: both owned files are in `owned_files`; **none owned by another WP**. Do not edit
  `status/models.py`, `reducer.py`, or any code surface here — the *vocabulary implementation* is WP09/WP10;
  this WP only records the ruling and the glossary.
- **Frontmatter stability**: do not change the ADR's `title`/`status`/`date` frontmatter — a body-only
  addendum keeps the ADR page-inventory / README index stable; changing them forces an inventory refresh.
- **Do NOT** restate #2399 enforcement as in-scope — the ADR records **record + reconstruct** only; #2399
  owns enforce.

## Reviewer guidance (adversarial)

- **Is the per-field authority stated unambiguously?** For **each** of `role`, `agent_profile`, `model`
  (and `provider`), is it explicit that the *resolved actual* is dynamic/event-log and the *authored
  recommendation* is static/frontmatter? Reject any wording that leaves a field's authority implicit or
  reads as "keep role/model frontmatter" (the reversed interim note).
- **Are C-007 and C-008 captured?** Confirm the ruling binds the recorded resolved value to
  `resolve_profile`/`resolved_agent()`/dispatch (never a frontmatter copy — C-007) and declares authored vs
  resolved non-conflatable (C-008). A ruling missing either is incomplete.
- **Does it extend B4, not duplicate the ADR?** Confirm the addendum references Decision 6 / blocker B4 and
  *resolves* it, rather than re-deciding the 2026-07-19 eviction.
- **Is the glossary canonical, and the ordering right?** Both terms present, matching the spec Domain
  Language text, cross-linked, `updated:` bumped, no `feature*` wording; terminology guard + docs-freshness
  pass. Confirm nothing presupposes the WP09 vocabulary already exists — the ADR is the gate, authored first.

## Activity Log

- 2026-07-20T17:58:55Z – claude – shell_pid=335985 – Started implementation via action command
- 2026-07-20T18:07:19Z – claude – shell_pid=335985 – Ready for review
- 2026-07-20T18:08:16Z – claude – shell_pid=359894 – Started review via action command
- 2026-07-20T18:09:42Z – user – shell_pid=359894 – Approved: field-authority ADR (B4 resolved) + identity vocabulary; C-009 gate satisfied for WP09
