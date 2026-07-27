# Contract — `--topic` Selector Grammar and Error Shape

**Mission**: `phase-3-charter-synthesizer-pipeline-01KPE222`
**Surface**: `spec-kitty charter resynthesize --topic <selector>` (FR-011)
**Data model ref**: [data-model.md §E-7 / §E-8](../data-model.md)
**Spec refs**: FR-012, FR-013, US-6, SC-008, C-004

This contract freezes (a) the grammar of structured `--topic` selectors and (b) the structured-error shape that surfaces when a selector cannot resolve. Both are user-facing. Changes require an ADR amendment.

---

## 1. Grammar

A selector is a single string argument. Free-text selectors are rejected (C-004).

Three forms, with a **local-first** resolution order for synthesizable artifact kinds (directive / tactic / styleguide).

### 1.1 Artifact kind + slug (project-local, synthesizable kinds)

```
<artifact-kind>:<slug>
```

- `<artifact-kind>` ∈ `{"directive", "tactic", "styleguide"}` (C-005 bound).
- `<slug>` matches `^[a-z][a-z0-9-]*$` for tactic / styleguide. For directive, `<slug>` is the directive artifact's canonical id (matches `Directive.id` regex `^[A-Z][A-Z0-9_-]*$`, typically `PROJECT_<NNN>`).
- Matches only against the **project-local** artifact set (i.e. the committed `.kittify/doctrine/<kind-dir>/` content for this project).

When the LHS is one of the three synthesizable artifact kinds and a project-local artifact with that id exists, this form wins — before any DRG URN interpretation. This is the rule that makes `tactic:how-we-apply-directive-003` route to the project artifact the operator actually wants to regenerate, rather than being misinterpreted as a DRG URN lookup.

Examples:
- `directive:PROJECT_001` (project-local synthesized directive)
- `tactic:how-we-apply-directive-003` (project-local synthesized tactic)
- `styleguide:python-testing-style` (project-local synthesized styleguide)

### 1.2 DRG URN

```
<node-kind>:<identifier>
```

- `<node-kind>` ∈ known DRG node kinds (see `src/doctrine/drg/models.py :: NodeKind`) — e.g. `directive`, `tactic`, `paradigm`, `styleguide`, `toolguide`, `procedure`, `agent_profile`, `action`, `glossary_scope`.
- `<identifier>` matches `^[A-Za-z0-9_.-]+$`.
- Resolved against the **merged shipped + project** DRG graph.
- Used when: (a) the LHS is a DRG node kind that is NOT in the synthesizable set (e.g. `paradigm`, `procedure`), OR (b) the LHS is in the synthesizable set but step 1.1 did not hit a project-local artifact (i.e. the operator is asking to regenerate every project-local artifact whose provenance references this shipped URN).

Examples:
- `directive:DIRECTIVE_003` — shipped directive URN; matches no project-local directive (shipped IDs use `DIRECTIVE_<NNN>`, project-local uses `PROJECT_<NNN>`), so resolver falls to step 1.2 and regenerates every synthesized artifact whose provenance references `directive:DIRECTIVE_003`.
- `paradigm:evidence-first` — shipped paradigm; directly a DRG URN.

### 1.3 Interview section label

```
<section-label>
```

- Must match an entry in the known interview-section label set (maintained alongside `src/charter/interview.py`).
- Case-sensitive, exact match.
- No colon → this form is tried only when forms 1.1 and 1.2 cannot apply (because they require a `:`).

Examples:
- `testing-philosophy`
- `language-scope`
- `neutrality-posture`

### 1.4 Resolution order

1. If the string contains `:` AND LHS ∈ `{"directive","tactic","styleguide"}`, attempt 1.1 (project-local artifact set lookup). Hit → resolve, done.
2. If the string contains `:`, attempt 1.2 (DRG URN against the merged shipped+project graph). Hit → resolve, done.
3. If the string contains no `:`, attempt 1.3 (interview section label). Hit → resolve, done.
4. No hit in any form → `TopicSelectorUnresolvedError` (see §2).

No step is skipped. No silent fallback (FR-013).

This ordering is the critical correctness property: operators reading their own project doctrine and typing `tactic:<slug>` for an artifact they can see on disk under `.kittify/doctrine/tactics/<slug>.tactic.yaml` must always resolve to that artifact — regardless of whether a shipped DRG node happens to carry the same URN shape.

---

## 2. Error shape

All resolver errors carry structured fields. CLI renders them via `rich` panels; machine consumers (tests, JSON output) can use the structured form.

### 2.1 `TopicSelectorUnresolvedError`

Raised when steps 1–3 all fail.

```yaml
error_kind: topic_selector_unresolved
raw: "<user-supplied topic string>"
attempted_forms:
  - kind_slug          # included only if string contained ":" AND LHS was synthesizable
  - drg_urn            # included only if string contained ":"
  - interview_section  # included only if string contained no ":"
candidates:
  - kind: kind_slug
    value: "tactic:how-we-apply-directive-003"
    distance: 2
  - kind: drg_urn
    value: "directive:DIRECTIVE_003"
    distance: 3
  - kind: interview_section
    value: "testing-philosophy"
    distance: 4
remediation: >
  Use one of the enumerated candidates, or run
  `spec-kitty charter resynthesize --list-topics` to see all valid selectors.
```

- `candidates` is bounded to the top 5 nearest matches by Levenshtein distance across all three forms.
- `candidates` is always present and may be empty (`[]`) when no reasonable suggestion exists.
- `attempted_forms` faithfully records which forms were tried, for debuggability.

### 2.2 Exit code + CLI surface

- Exit code `2` (invalid usage).
- Rendered panel title: `Cannot resolve --topic "<raw>"`.
- No files are written. No model calls occur. No staging directory is created.

### 2.3 Observable SLA (SC-008)

From invocation to structured-error return: **< 2 seconds** on a cold cache. Verified by `tests/charter/synthesizer/test_topic_resolver.py::test_unresolved_sla`.

---

## 3. Success semantics

On a successful resolution:

- The resolver returns a `ResolvedTopic` record carrying:
  - `targets: list[SynthesisTarget]` — the bounded slice to regenerate.
  - `matched_form: Literal["kind_slug","drg_urn","interview_section"]`.
  - `matched_value: str` — normalized form of the successful selector.
- Orchestration pipes `targets` into the same stage → validate → promote machinery used by full synthesis, with `run_id` tagged as a resynthesis run.
- The updated manifest rewrites only the entries for regenerated artifacts; other entries retain prior `content_hash` (FR-017).

### 3.1 Target expansion rules per form

- **`kind_slug`** (project-local hit): targets = `[the matched artifact]`. One artifact regenerated.
- **`drg_urn`**: targets = every project-local artifact whose provenance `source_urns` contains the URN. Zero artifacts → the resolver returns a structured "no-op with diagnostic" result (EC-4); no writes, no model call.
- **`interview_section`**: targets = every project-local artifact whose provenance `source_section` equals the section label.

---

## 4. Non-goals (repeated from spec for clarity)

- **No free-text**: "tighten security wording" is rejected outright (C-004).
- **No globs/regex**: `directive:*` is not valid. Per-run batch is captured by `--all` in a later tranche, not by selector syntax.
- **No negation**: `!tactic:premortem-risk-identification` is not valid.

If operators want batch semantics, they run `spec-kitty charter synthesize` (full run). If they want a single slice, they use a structured selector.
