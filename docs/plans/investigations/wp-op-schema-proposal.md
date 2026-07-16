---
title: WP Prompt & Ops Debrief — Model / Schema Proposal
description: 'Concrete model+schema suggestion for a YAML-authoritative WP prompt (markdown derived one-way) and a required-on-close structured Ops debrief, grounded in the existing WorkPackageEntry / WPMetadata / OpCompletedEvent surfaces.'
doc_status: proposal
updated: '2026-07-16'
related:
- wp-op-schema-model.md
- wp-op-schema-related-tickets.md
---
# WP Prompt & Ops Debrief — Model / Schema Proposal

First-cut concrete schema suggestion, following the grounded idea note
([wp-op-schema-model.md](wp-op-schema-model.md)) and the ticket map
([wp-op-schema-related-tickets.md](wp-op-schema-related-tickets.md)). Pydantic v2,
model-first (registers into `scripts/generate_schemas.py` like the 10 doctrine
schemas).

## Decisions locked (operator, 2026-07-16)

| Decision | Choice | Consequence |
|---|---|---|
| **WP prompt authority** | **YAML-authoritative, markdown derived** | `wps.yaml` (enriched) is the source of truth; `tasks/WP##.md` is rendered one-way, "do not edit". |
| **Ops debrief obligation** | **Required on every Op close** | A structured `debrief` is a mandatory field on the completion event, not opt-in. |

Both are the *maximal* choices. This proposal designs to them **and** builds in
the mitigations for the two risks that stance carries (§[Risks](#risks--reconciliation)):
body-authoring collision, `wps.yaml` adoption (stalled at 5/278), and trivial-op
friction.

---

## Part 1 — WP Prompt model

### 1.1 Design principles (from grounding)

1. **One canonical model, not a fourth.** Today three field lists describe a WP
   (`WorkPackageEntry`, `WPMetadata`, `frontmatter.WP_FIELD_ORDER`). This proposal
   **elects and enriches `WorkPackageEntry` → `WorkPackageSpec`** as the single
   authoring model; `WPMetadata`/`WP_FIELD_ORDER` become *derived read-projections*
   of it, not parallel authorities.
2. **Static design-intent only in the spec; dynamic runtime state stays in the
   event log.** This is #2093/#2400's ruling, kept intact — the model carries
   `id/title/deps/owned_files/acceptance/…` but **never** `shell_pid`, `history`,
   `lane`, `review_*`. Those churn and are event-log-owned.
3. **Three content classes, three homes.** Every line in today's `WP##.md` is one
   of: **authored semantic** (→ the spec), **boilerplate** (→ rendered from the
   doctrine step template), or **mutable runtime** (→ rendered from the event log
   at display time). Only the first is authored/hashed.

Body-section census (real WPs) mapped to class:

| Today's `## section` | Freq | Class | Home |
|---|---|---|---|
| Objective / Objectives & Success Criteria | 1727 | authored | `prompt.objective` |
| Context & Constraints | 1557 | authored | `prompt.context` |
| Definition of Done / Acceptance | 1273 | authored | `prompt.acceptance[]` |
| Subtasks & Detailed Guidance | 1267 | authored | `prompt.steps[]` |
| Risks & Mitigations | 1294 | authored | `prompt.risks[]` |
| Test Strategy | 470 | authored | `prompt.test_strategy` |
| Review/Reviewer Guidance | 1396 | authored | `prompt.review_guidance` |
| Non-goals | (sample) | authored | `prompt.non_goals[]` |
| References / Spec anchors | 56+ | authored | `prompt.references[]` |
| **Load Agent Profile** | 1024 | **boilerplate** | doctrine step template |
| Branch Strategy | 1184 | metadata | `WorkPackageSpec` (static) |
| **Activity Log** | 1670 | **mutable** | event log → derived md |
| **Review Feedback / Status** | 316 | **mutable** | event log → derived md |

### 1.2 Model sketch

```python
# specify_cli/core/wp_spec.py  (enriches core/wps_manifest.py:WorkPackageEntry)

class AcceptanceCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str                       # "AC-01"  (pattern ^AC-\d{2}$)
    statement: str = Field(min_length=1)
    verify: str | None = None     # test id / command / "manual: …"

class WPStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str                       # "T001"   (pattern ^T\d{3}$)
    description: str = Field(min_length=1)
    guidance: str | None = None   # multi-line prose allowed

class WPPromptBody(BaseModel):
    """Authored semantic content — the prose an agent needs to do the work."""
    model_config = ConfigDict(extra="forbid")
    objective: str = Field(min_length=1)          # the one required narrative
    context: str | None = None
    scope_note: str | None = None                 # prose; owned_files is structured, below
    steps: list[WPStep] = Field(default_factory=list)
    acceptance: list[AcceptanceCriterion] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    test_strategy: str | None = None
    review_guidance: str | None = None
    references: list[str] = Field(default_factory=list)  # FR-/NFR-/C- anchors, URLs, tracker refs

class WorkPackageSpec(BaseModel):
    """THE canonical WP authoring model. Static design-intent only."""
    model_config = ConfigDict(extra="forbid")
    # identity + dependency graph (from WorkPackageEntry, kept)
    id: str                       # ^WP\d{2}$
    title: str = Field(min_length=1)
    dependencies: list[str] = Field(default_factory=list)     # ^WP\d{2}$
    # static design-intent (from WPMetadata static subset)
    requirement_refs: list[str] = Field(default_factory=list)
    plan_concern_refs: list[str] = Field(default_factory=list)  # ^IC-\d{2}$
    tracker_refs: list[str] = Field(default_factory=list)
    owned_files: list[str] = Field(default_factory=list)
    create_intent: list[str] = Field(default_factory=list)
    authoritative_surface: str | None = None
    scope: Literal["codebase-wide"] | None = None
    task_type: str | None = None
    cross_cutting: bool = False
    agent_profile: str | None = None       # authored assignment; resolved binding → event log
    # authored body
    prompt: WPPromptBody
    # DELIBERATELY ABSENT (event-log owned, never authored/hashed here):
    #   shell_pid, shell_pid_created_at, history, lane, review_status,
    #   reviewed_by, review_feedback, base_branch, base_commit, created_at
```

`wps.yaml` becomes `work_packages: list[WorkPackageSpec]` (the existing
`WpsManifest` container, enriched).

### 1.3 The flow: author → validate → render → hash

```
wps.yaml  (WorkPackageSpec[], SOURCE OF TRUTH — authored by human OR agent)
   │  load + Pydantic validate (extra="forbid", pattern checks)
   ▼
WorkPackageSpec ──► render_wp_markdown(spec, step_template, event_log)
   │                     │
   │                     ├─ authored sections   ← spec.prompt.*
   │                     ├─ boilerplate          ← doctrine step template
   │                     └─ Activity Log / Review ← event log (display-time)
   │                     ▼
   │              tasks/WP03.md   (DERIVED, "_Generated — do not edit directly._")
   ▼
content_hash = sha256(canonical_yaml(spec))     # ← hashes the SPEC, not the md
```

**This kills the hash-churn** the whole arc started from: the dossier/sync hash
(`dossier/hasher.py`, `sync/body_upload.py`) moves off the whole rendered file onto
the canonical `WorkPackageSpec` projection. An Activity-Log append or a review-cycle
write lands only in the *derived* markdown / event log — it never touches the hashed
spec. Extends the proven `generate_tasks_md_from_manifest()` renderer
(`core/wps_manifest.py:170`) from the index to the per-WP file.

### 1.4 On-disk example

<details><summary><code>wps.yaml</code> (source) → <code>tasks/WP03.md</code> (derived)</summary>

```yaml
# wps.yaml  (authored)
work_packages:
  - id: WP03
    title: Semantic-only WP content hash
    dependencies: [WP01]
    requirement_refs: [FR-004, NFR-002]
    owned_files: [src/specify_cli/dossier/hasher.py, src/specify_cli/dossier/indexer.py]
    agent_profile: python-pedro
    prompt:
      objective: Hash the WorkPackageSpec projection, not the rendered markdown bytes.
      context: |
        Today dossier/hasher.py streams whole-file bytes; any inert edit trips parity drift.
      steps:
        - id: T001
          description: Route indexer through WorkPackageSpec canonical projection.
      acceptance:
        - id: AC-01
          statement: An Activity-Log append does not change the WP content hash.
          verify: tests/dossier/test_semantic_hash.py::test_activity_log_inert
      non_goals: [Changing the parity-hash algorithm itself]
      risks: [Legacy WPs without wps.yaml must fall back to whole-file hash]
      test_strategy: Red test first — append to activity log, assert hash stable.
      review_guidance: Confirm no raw-byte hashing path remains for wps.yaml missions.
      references: [FR-004, NFR-002, "docs/.../wp-op-schema-model.md"]
```
```markdown
<!-- tasks/WP03.md — GENERATED, do not edit directly -->
# WP03 — Semantic-only WP content hash
_Generated from wps.yaml. Do not edit directly._
**Dependencies**: WP01 · **Requirement Refs**: FR-004, NFR-002
## ⚡ Do This First: Load Agent Profile   <!-- boilerplate from step template -->
## Objective
Hash the WorkPackageSpec projection, not the rendered markdown bytes.
## Definition of Done
- [ ] AC-01 — An Activity-Log append does not change the WP content hash. _(verify: tests/…)_
## Activity Log                            <!-- rendered from event log, display-only -->
- 2026-07-16 claimed by python-pedro
```
</details>

---

## Part 2 — Ops Debrief model

### 2.1 Design principles

- **Field-extension, not a new primitive.** The debrief attaches to the existing
  `OpCompletedEvent` (`invocation/record.py:65`) — honouring ADR 2026-06-11-1's
  **C-005 no-parallel-primitive**. No "small-WP-for-an-Op" artifact.
- **Required presence, graduated depth.** The operator chose *required on close*.
  To keep that from taxing trivial lookups, **presence is always mandatory but
  required depth scales with `mode_of_work`** (carried from the started event).
  This is the mitigation for the friction the maximal choice accepts.
- **Elevates Tier-1.** Today `MinimalViableTrailPolicy` tier-1 records *facts*.
  This makes a structured *why/what* part of the mandatory tier-1 record — the
  exact "Ops persist intent" change the idea wanted.

### 2.2 Model sketch

```python
class OpDebrief(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    intent: str = Field(min_length=1)          # WHY — restated purpose (≥ request_text)
    change_surface: list[str] = Field(default_factory=list)  # WHAT — files/areas touched/intended
    actions: list[str] = Field(default_factory=list)         # what was done (bullets)
    decisions: list[str] = Field(default_factory=list)       # key choices / tradeoffs
    follow_ups: list[str] = Field(default_factory=list)      # residual work / tickets

class OpCompletedEvent(BaseModel):   # EXTENDED
    ...  # existing: outcome, closed_by, completed_at, evidence_ref
    debrief: OpDebrief               # NOW REQUIRED
```

### 2.3 Graduated-depth rule (the friction mitigation)

Validated against the started event's `mode_of_work`:

| `mode_of_work` | Required in debrief | Auto-fillable |
|---|---|---|
| `query` | `intent` only | `intent` ← `request_text`; rest empty ✔ |
| `advisory` | `intent` | `intent` ← `request_text`; `actions` optional |
| `task_execution` | `intent` + `change_surface` (≥1) + `actions` (≥1) | none — agent must author |
| `mission_step` | `intent` + `change_surface` + `actions` | none |

So a trivial query Op still closes in one line (auto-derived), while a
change-making Op must state what surface it touched and what it did — restoring the
ad-hoc↔op distinction exactly where work happened. `closed_by="doctor_sweep"`
(orphan auto-close) fills a sentinel `intent="unrecorded — swept"`, never fabricates.

### 2.4 Debrief closes the loop with the WP

`OpDebrief.change_surface` is the Op-scale analogue of `WorkPackageSpec.owned_files`;
`intent`/`actions`/`decisions` mirror `prompt.objective`/`steps`/review rationale.
Same vocabulary at both grains — a mission WP and an ad-hoc Op now both answer
"what surface, to what end, with what result."

---

---

## Part 3 — Schema generation & registration

Model-first, reusing `scripts/generate_schemas.py` (the machinery behind the 10
doctrine schemas + the `--check` drift gate).

### 3.1 One structural change: output-dir override

Today `register()` writes every schema under a single module constant
`SCHEMA_DIR = src/doctrine/schemas/` (`generate_schemas.py:34`). WP/Op models live
outside the doctrine tree, so the only pipeline change needed is a **per-entry
output directory**. Minimal, backward-compatible extension:

```python
# generate_schemas.py — add an optional schema_dir to the registry tuple
def register(stem, module, cls, title, description, extra=None, *,
             by_alias=False, schema_dir: Path = SCHEMA_DIR) -> None:
    REGISTRY[stem] = (module, cls, title, description, extra, by_alias, schema_dir)
# _emit() writes to that entry's schema_dir instead of the global SCHEMA_DIR.
```

New sink: `SPECIFY_SCHEMA_DIR = src/specify_cli/schemas/`. No doctrine schema moves;
existing entries default to `SCHEMA_DIR` unchanged.

### 3.2 Registration calls

```python
SPECIFY_SCHEMA_DIR = ROOT / "src" / "specify_cli" / "schemas"

register(
    "work-package-spec",
    "specify_cli.core.wp_spec", "WorkPackageSpec",
    "Work Package Spec",
    "Canonical YAML-authoritative work-package record; tasks/WP##.md is derived.",
    extra=lambda s: _add_item_patterns(s, {
        "dependencies": r"^WP\d{2}$",
        "plan_concern_refs": r"^IC-\d{2}$",
    }),
    schema_dir=SPECIFY_SCHEMA_DIR,
)
register(
    "op-completed-event",
    "specify_cli.invocation.record", "OpCompletedEvent",
    "Op Completed Event",
    "Op completion event carrying the mandatory structured debrief (why/what).",
    schema_dir=SPECIFY_SCHEMA_DIR,
)
```

`AcceptanceCriterion`/`WPStep`/`WPPromptBody`/`OpDebrief` need no separate entry —
they emit as `definitions/*` inside their parent (same as `tactic_step`).

### 3.3 Example generated output — `work-package-spec.schema.yaml`

<details><summary>generated schema (abridged; mirrors the toolguide format)</summary>

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
$id: https://spec-kitty.dev/schemas/doctrine/work-package-spec.schema.yaml
title: Work Package Spec
description: Canonical YAML-authoritative work-package record; tasks/WP##.md is derived.
type: object
additionalProperties: false          # ← from model_config extra="forbid"
required:
- id
- title
- prompt
properties:
  id:
    type: string
    pattern: ^WP\d{2}$
  title:
    type: string
    minLength: 1                      # ← required string, auto-added
  dependencies:
    type: array
    items: {type: string, pattern: ^WP\d{2}$}
  requirement_refs:
    type: array
    items: {type: string}
  plan_concern_refs:
    type: array
    items: {type: string, pattern: ^IC-\d{2}$}
  owned_files:
    type: array
    items: {type: string}
  create_intent:
    type: array
    items: {type: string}
  authoritative_surface: {type: string}
  scope: {type: string, enum: [codebase-wide]}
  task_type: {type: string}
  cross_cutting: {type: boolean}
  agent_profile: {type: string}
  tracker_refs:
    type: array
    items: {type: string}
  prompt:
    $ref: '#/definitions/wp_prompt_body'
definitions:
  acceptance_criterion:
    type: object
    additionalProperties: false
    required: [id, statement]
    properties:
      id: {type: string, pattern: ^AC-\d{2}$}
      statement: {type: string, minLength: 1}
      verify: {type: string}
  wp_step:
    type: object
    additionalProperties: false
    required: [id, description]
    properties:
      id: {type: string, pattern: ^T\d{3}$}
      description: {type: string, minLength: 1}
      guidance: {type: string}
  wp_prompt_body:
    type: object
    additionalProperties: false
    required: [objective]
    properties:
      objective: {type: string, minLength: 1}
      context: {type: string}
      scope_note: {type: string}
      steps:
        type: array
        items: {$ref: '#/definitions/wp_step'}
      acceptance:
        type: array
        items: {$ref: '#/definitions/acceptance_criterion'}
      non_goals: {type: array, items: {type: string}}
      risks: {type: array, items: {type: string}}
      test_strategy: {type: string}
      review_guidance: {type: string}
      references: {type: array, items: {type: string}}
```
</details>

### 3.4 Example generated output — `op-completed-event.schema.yaml`

<details><summary>generated schema (abridged)</summary>

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
$id: https://spec-kitty.dev/schemas/doctrine/op-completed-event.schema.yaml
title: Op Completed Event
description: Op completion event carrying the mandatory structured debrief (why/what).
type: object
additionalProperties: false
required:
- event
- invocation_id
- completed_at
- outcome
- closed_by
- debrief                            # ← now mandatory
properties:
  event: {type: string, const: completed}
  invocation_id: {type: string, pattern: ^[0-9A-HJKMNP-TV-Z]{26}$}
  completed_at: {type: string, minLength: 1}
  outcome: {type: string, enum: [done, failed, abandoned]}
  closed_by: {type: string, enum: [agent, doctor_sweep]}
  evidence_ref: {type: string}
  debrief:
    $ref: '#/definitions/op_debrief'
definitions:
  op_debrief:
    type: object
    additionalProperties: false
    required: [intent]               # graduated depth enforced in-model, not schema
    properties:
      intent: {type: string, minLength: 1}
      change_surface: {type: array, items: {type: string}}
      actions: {type: array, items: {type: string}}
      decisions: {type: array, items: {type: string}}
      follow_ups: {type: array, items: {type: string}}
```
</details>

> **Note — where graduated depth lives.** JSON-Schema `required` is static, so the
> schema fixes only the floor (`intent`). The mode-conditional depth (§2.3 —
> `task_execution` also needs `change_surface`+`actions`) is a **Pydantic
> `model_validator`** on `OpCompletedEvent` that reads the started event's
> `mode_of_work`. Keep it in the model, not the JSON-Schema, so the drift gate and
> the runtime enforce the same floor and the model adds the conditional ceiling.

### 3.5 Drift gate

`python scripts/generate_schemas.py --check` gains both stems; the
`clean-install-verification` / schema-freshness tests fail if
`wp_spec.py` / `record.py` drift from the emitted YAML — identical guarantee to the
doctrine schemas today.

---

## Risks & reconciliation

| Risk (from grounding) | Mitigation in this design |
|---|---|
| **#2093 decided frontmatter stays authority** | This proposal **supersedes** that persistence ruling (YAML-authoritative per operator choice) but **preserves its substance** — static-intent-only, dynamic→event-log. ⚠ **This flip must be ratified with #2400's owner before implementation** — it is the one place we override a decided ticket, not just consume it. |
| **`wps.yaml` stalled at 5/278 missions** | Adoption, not the model, was the blocker. Mitigation: (a) a `spec-kitty migrate wp-spec` backfill that parses today's markdown bodies → `WorkPackageSpec`; (b) runtime reads spec-first, whole-file-hash fallback for un-migrated missions (no flag day); (c) fix #2642 (runtime still requires `tasks.md`) as a hard dependency. |
| **Body no longer hand-editable** | The authoring surface moves to `wps.yaml` (agents author structured fields directly; humans edit YAML). The rendered `WP##.md` carries a "do not edit" stamp + a pre-commit guard that rejects edits to derived files, pointing back to the spec. |
| **Required debrief taxes trivial ops** | Graduated depth (§2.3): query/advisory auto-fill from `request_text`; only change-making ops must author. |

## Smallest shippable path (unchanged from grounding, now concrete)

1. **Tidy-first** — extract `WPPromptBody`/`WorkPackageSpec`, register in
   `generate_schemas.py`; make `WPMetadata` a read-projection. *No behaviour change.*
2. **Semantic-only hash** — repoint `dossier`/`sync` hashing at the spec projection
   (kills churn; the unticketed high-signal slice).
3. **Render per-WP md from spec** — extend `generate_tasks_md_from_manifest`;
   add the do-not-edit guard; ship the `migrate wp-spec` backfill.
4. **Op debrief** — extend `OpCompletedEvent`; graduated-depth validator; update
   `profile-invocation complete` to collect/auto-fill it. *Independent of 1–3.*

## Open questions for the next iteration

1. **Reconciliation gate**: do we take the #2093 authority-flip to #2400's owner as
   an ADR amendment, or fold this under #1676 (which already wants model-first authoring)?
2. **Boilerplate rendering**: does the per-WP `WP##.md` render pull boilerplate from
   the resolved doctrine *step template* live, or snapshot it at finalize time?
3. **Debrief authoring UX**: does `profile-invocation complete` prompt for the debrief
   fields interactively, accept `--debrief-file`, or infer `change_surface` from the
   Op's git diff?
4. **Should `agent_profile` (authored) vs resolved-binding** live as two names, to keep
   #2093's authored-intent/resolved-binding split crisp inside the spec?
