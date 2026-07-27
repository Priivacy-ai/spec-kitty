# Fold-Cluster Pre-Mission Research
**Researcher:** researcher-robbie · **Date:** 2026-06-12 · **Branch:** feat/doctrine-glossary-consolidation-01KTNWFC

---

## Scope 1 — #1865/#1866/#1867 Doctrine Refinements

### Source authority

The three tickets are the "upstream doctrine-refinement" items routed from WP11's dogfood gaps.  
Gap evidence lives in `docs/development/391-doctrine-usage-test.md` (the authoritative run record).

| Ticket | Gap | Target artifact |
|--------|-----|-----------------|
| **#1865** | Gap #1 — no guidance for residual/legacy triage-snapshot label schemes (e.g. `p1:verified`, `p1-decision:*`). WP11 review noted **two addenda**: (a) the primary pattern request, and (b) a secondary-label clarification about when `triage:*` vs other triage markers apply. Both land in the styleguide. | `planning-and-tracking.styleguide.yaml` |
| **#1866** | Gap #2 — procedure has no "do not mutate protected/canonical-tree nodes" carve-out; hygiene-step would drive retype of #1797 but #1797 is governed/off-limits. | `tracker-organisation-workflow.procedure.yaml` |
| **#1867** | Gap #3 — `--paginate` applies to all `gh list` surfaces, not just `sub_issues`; the procedure's hygiene step used `gh issue list` without `--paginate` in draft (silent truncation risk). Plus provisional-priority default unspecified. Gap #3 was split: provisional-priority → styleguide (close to Gap #1); pagination generalization → toolguide. | `planning-and-tracking.styleguide.yaml` + `GITHUB_TRACKER.md` |

> Note: the reviewer's gap-routing from WP11 (WP status log line at 2026-06-11T19:01:09Z) says "gap#1 + gap#3 → WP05 styleguide follow-up; gap#2 → WP04 procedure follow-up." The three-ticket split (1865/1866/1867) is the filed form of those three gaps as separate upstream doctrine tickets.

---

### 1A — planning-and-tracking.styleguide.yaml deltas

#### Schema conformance check

Schema `src/doctrine/schemas/styleguide.schema.yaml`:
- `schema_version: "1.0"` — **no change** needed (not a breaking schema change; `schema_version` is locked to `"1.0"` by the `^1\.0$` pattern; DIRECTIVE_018 versioning requirement satisfied without a version bump since these are additive prose additions to existing `patterns`/`anti_patterns` arrays).
- `patterns` and `anti_patterns` items need `name`, `description`, and `bad_example`/`good_example` (required by schema for `anti_pattern`; optional for `pattern`).
- `references` field: plain `list[str]` (file paths), already present — no change needed.

**DIRECTIVE_018 verdict:** additive `patterns` entries in an existing `schema_version: "1.0"` file do not require a version bump. The directive requires "breaking doctrine changes require explicit upgrade guidance" — these are non-breaking additions.

#### Exact YAML deltas — `planning-and-tracking.styleguide.yaml`

**Delta 1 — Triage-snapshot label reconciliation pattern** (Gap #1 primary, #1865 addendum 1)

Append to `patterns:` array after the existing `Triage namespace for pending disposition` pattern:

```yaml
  - name: Triage-snapshot label reconciliation
    description: >
      When a ticket carries a bespoke triage-snapshot label scheme from a
      prior pass (e.g. `p1:verified`, `p1-decision:keep|split|defer|close-if-stale`),
      reconcile it into the canonical namespaces or explicitly bless it as an
      immutable audit snapshot. Migration map:
      `p1-decision:close-if-stale` → `triage:stale`;
      `p1-decision:defer` → `future`;
      `p1:verified` → remove (disposition is captured by the canonical priority label).
      If the snapshot predates the current canonical scheme and the owning team
      treats it as an audit artefact, document the decision and leave it
      untouched — but add the canonical `priority:Px` and `triage:*` labels
      alongside so the quality-test can answer its question in one pass.
    good_example: |
      Ticket carrying `p1-decision:split` migrated: label removed, `triage:needs-revision`
      added alongside existing `priority:P1`. Quality-test can answer in one pass.
    bad_example: |
      Ticket carries `p1:verified` + `p1-decision:keep` with no canonical
      `priority:Px` label. The quality-test cannot answer its question and the
      canonical triage namespace is bypassed.
```

**Delta 2 — Secondary-label clarification** (Gap #1 addendum 2 / #1865 addendum 2)

Append to `patterns:` after Delta 1:

```yaml
  - name: Secondary-label coexistence
    description: >
      Secondary labels (`usability`, `future`, `bug`, `epic`, `enhancement`)
      coexist with the `priority:Px` primary label and with `triage:*` disposition
      labels. They are orthogonal dimensions: `bug` expresses kind, `priority:P1`
      expresses urgency, `triage:stale` expresses triage state. No label from one
      dimension replaces a label from another. A ticket may carry at most one
      `priority:Px` label (the single-canonical-priority invariant), any number of
      kind labels, and at most one `triage:*` label per triage cycle.
    good_example: |
      Labels: priority:P1, bug, triage:needs-revision
      (one priority, one kind, one triage state — all orthogonal)
    bad_example: |
      Labels: P1-bug, triage:stale
      (conflated priority+kind; missing canonical priority:Px)
```

**Delta 3 — Provisional-priority default naming** (Gap #3 / #1867)

Modify the existing principle 9 (hygiene invariants). Current text ends: "Priority is triage — assign a provisional default and flag it rather than silently guessing." Change to:

```yaml
  - "Hygiene invariants for every open ticket: it resolves to a functional epic (not an orphan, not meta-rooted, not under a closed epic); it carries an issue type; and it carries a priority label. Type is objective — derive it from the conventional-commit prefix and labels. Priority is triage — assign `priority:P2` as the canonical provisional default and add `triage:needs-revision` as the flag, rather than silently guessing. Two operators applying this rule will converge on the same labels."
```

> Note: the change is in `principles` (plain `list[str]`), not `patterns`. Schema allows this as a string replacement in the array. No `bad_example`/`good_example` required here since it is a principle, not a pattern.

---

### 1B — tracker-organisation-workflow.procedure.yaml deltas

#### Schema conformance check

Schema `src/doctrine/schemas/procedure.schema.yaml`:
- Steps are `list[procedure_step]` — each step has `title`, optional `description`, `actor` (enum: `human|agent|system`), `on_success`, `on_failure`.
- `notes` is a free-form string — the carve-out guidance can go here as well as into Step 8's description.
- `additionalProperties: false` — no new top-level keys may be added.

**DIRECTIVE_018 verdict:** additive description changes to steps and `notes` are non-breaking; no version bump required.

#### Exact YAML deltas — `tracker-organisation-workflow.procedure.yaml`

**Delta 1 — Canonical-tree carve-out in Step 8 description** (Gap #2 / #1866)

The label-only-mutation question Priti's triage raised: "Can I mutate labels (like adding `priority:P2`) on a governed canonical-tree node, or is even label-mutation forbidden?" Answer: label-only mutations (adding a `priority:Px` or `triage:*` label) are **permitted** — they are additive and do not rewrite the node's identity, type, or parent relationship. Type changes and reparenting are the protected operations.

Current Step 8 description ends: "Confirm each open ticket resolves to a functional epic, carries an issue type (Task, Bug, or Feature; epics are typed Feature), and carries exactly one priority label. Derive type objectively from the conventional-commit prefix and existing labels. Priority is triage judgement — assign a provisional default and flag it rather than silently guessing — and audit for conflicting multi-value priority after any migration."

Replace with:

```yaml
    description: >
      Confirm each open ticket resolves to a functional epic, carries an issue
      type (Task, Bug, or Feature; epics are typed Feature), and carries exactly
      one priority label. Derive type objectively from the conventional-commit
      prefix and existing labels. Priority is triage judgement — assign
      `priority:P2` + `triage:needs-revision` as the canonical provisional default
      and flag it rather than silently guessing — and audit for conflicting
      multi-value priority after any migration.

      Canonical-tree carve-out: some roots or buckets may be under change-control
      (e.g. a governed canonical-tree node whose type or parent relationship must
      not change without a tree-owner decision). For such nodes, additive
      label-only mutations (adding a canonical `priority:Px` or `triage:*` label)
      are permitted. Type changes, reparenting, and closure require a recorded
      proposal to the tree owner rather than execution. Record the prescribed fix
      as a named proposal with an owner reference.
```

**Delta 2 — `notes` addendum for label-only-mutation question**

The current `notes:` field does not address the label-only-mutation question. Append to it:

```yaml
notes: >
  Distilled from a full-backlog tracker remediation (235 open tickets reviewed,
  zero genuine orphans remaining). Pair this workflow with the
  iterative-deepening-review tactic to sequence the sweep in widening time
  windows, and with moscow-scoping-lens when negotiating which slices a bucket
  must, should, could, or won't carry. The supporting planning-and-tracking
  vocabulary (functional epic, meta-tracker, issue type, priority scheme, triage
  status) is defined in the planning-and-tracking glossary subset. DRG wiring of
  the references below is performed by the consolidation mission's graph step.

  Label-only mutations (adding a `priority:Px` or `triage:*` label) on a
  canonical-tree node are permitted — they are additive. Type changes,
  reparenting, and closure of governed nodes require a proposal recorded for the
  tree owner. When a node is off-limits to type/parent mutations, record the
  prescribed fix as a named deferred proposal rather than executing it (see Step 8
  carve-out). This preserves the audit trail while respecting tree governance.
```

---

### 1C — GITHUB_TRACKER.md / github-tracker.toolguide.yaml pagination delta

**Current state:** `--paginate` appears in GITHUB_TRACKER.md only under "Reading children" (sub_issues endpoint) and the pitfall quick-table. The pagination rule is presented as sub_issues-specific.

**Gap:** `gh issue list`, `gh label list`, `gh search issues`, and `gh api` list surfaces all have a default page size of 30; any of them silently truncates on large result sets. The toolguide generalises the rule.

**Delta — GITHUB_TRACKER.md** (under Rate-limiting section, after the existing mitigations block):

```markdown
### --paginate applies to all gh list surfaces

`--paginate` is not specific to sub-issue reads. Any `gh` command that returns a
paginated list (issues, labels, search results, API list endpoints) silently
truncates at the default page size (30 for most; 100 for `gh search issues`).
Always add `--paginate` when the full result set matters:

```bash
# All forms that need --paginate:
gh api repos/{owner}/{repo}/issues/{n}/sub_issues --paginate --jq '.[].number'
gh issue list --repo {owner}/{repo} --state open --paginate --json number,title,labels
gh label list --repo {owner}/{repo} --paginate --json name,description
gh api repos/{owner}/{repo}/labels --paginate --jq '.[].name'
```

Exception: `gh search issues` returns up to 100 items per call with `--limit` but
has a separate cap; verify with `--jq 'length'` when a known large set is expected.
```

**The github-tracker.toolguide.yaml file itself** (the metadata file): no field change needed — the `guide_path` points to the `.md` file which is the live guide. The toolguide schema has no `references` field, so no DRG wiring is possible from this artifact (see Scope 3). The `last_updated` field should be bumped:

```yaml
last_updated: "2026-06-12"
```

---

## Scope 2 — Authority-Path Flip Chain Re-Verification

The ADR `2026-06-11-1-op-as-first-class-execution-artifact.md` (Adjudication 1) recorded a **deferred** flip of `DEFAULT_AUTHORITY_PATHS` from `architecture/2.x/adr/` to `architecture/3.x/adr/`, listing the enumerated chain and three extra surfaces.

### Chain as recorded in the ADR

1. `src/charter/context_renderers/authority_paths.py` `DEFAULT_AUTHORITY_PATHS` dict
2. Two source prompts: `src/doctrine/missions/mission-steps/software-dev/implement/prompt.md` and `review/prompt.md`
3. Two governance-contract tests: `tests/architectural/test_template_governance_payload_contract.py` and `tests/specify_cli/next/test_wp_prompt_governance_contract.py`
4. Three `tests/charter/` assertions: `test_context_authority_paths.py`, `test_sync_authority_paths.py`, `test_schemas_additive_fields.py`
5. `.kittify/charter/charter.md` line 317 annotation
6. Twelve-agent parity baseline regen (`PYTEST_UPDATE_SNAPSHOTS=1 pytest tests/specify_cli/regression/`)

### Post-two-rebase verification (branch: feat/doctrine-glossary-consolidation-01KTNWFC)

**1. `authority_paths.py` DEFAULT:** `architecture/2.x/adr/` confirmed at line 53. **STILL ACCURATE — no drift.**

**2. `implement/prompt.md` line 94:** `architecture/2.x/adr/` confirmed. **STILL ACCURATE.**

**3. `review/prompt.md` line 72:** `architecture/2.x/adr/` confirmed. **STILL ACCURATE.**

**4a. `test_template_governance_payload_contract.py`:** Confirmed references `architecture/2.x/adr/` at lines 131, 200, 269 (the path-existence checks). **STILL ACCURATE.**

**4b. `tests/specify_cli/next/test_wp_prompt_governance_contract.py`:** Confirmed `architecture/2.x/adr/` at line 112 and the `adr_path_present` check at line 663. **STILL ACCURATE.**

**5a. `test_context_authority_paths.py`:** `test_default_adr_path_surfaces_when_directory_present` creates `architecture/2.x/adr` and asserts `DEFAULT_AUTHORITY_PATHS["architecture/2.x/adr/"]`. **STILL ACCURATE — would break on flip.**

**5b. `test_sync_authority_paths.py`:** Inline charter string `_CHARTER_WITH_FULL_BLOCK` at line 46 contains `- architecture/2.x/adr/` and the assertion at line 62 checks `doctrine.get("authority_paths") == ["glossary/contexts/", "architecture/2.x/adr/"]`. **STILL ACCURATE — would break on flip.**

**5c. `test_schemas_additive_fields.py`:** `TestDoctrineSelectionAuthorityPathsField.test_round_trip_with_authority_paths` at lines 142–158 uses `architecture/2.x/adr/` as the fixture value (YAML text + assertion). **STILL ACCURATE — would break on flip.**

**6. `.kittify/charter/charter.md` line 317:** Confirmed `- architecture/2.x/adr/    # 2.x-era architectural decisions (historical)`. The comment already acknowledges this as historical. **STILL ACCURATE.**

**7. Parity baseline regen:** `tests/specify_cli/regression/` confirmed present; `__init__.py` documents `PYTEST_UPDATE_SNAPSHOTS=1 pytest tests/specify_cli/regression/ -v`. **PROCEDURE STILL ACCURATE.**

### Chain drift verdict: NONE

All seven links in the enumerated chain are **exactly as the ADR recorded**, post two rebases. No drift detected. The ADR deferral rationale ("not broken today, blast radius exceeds the sanctioned chain, WP02 boundary crossing") remains valid and actionable. The flip remains a well-bounded follow-up Op/mission when undertaken; no new surfaces were discovered in this verification pass.

---

## Scope 3 — #1863 DRG Extractor Walk Extension (Styleguides/Toolguides)

### Current extractor behavior

`src/doctrine/drg/migration/extractor.py` — `extract_artifact_edges()` walks: **directives, tactics, paradigms, procedures, agent_profiles**. Styleguides and toolguides are **not walked** for their `references` blocks.

`_discover_built_in_artifact_nodes()` does scan styleguide and toolguide directories to register **nodes** — but only nodes, no edges from their inline `references` fields.

### Current graph state (graph.yaml — 232 nodes, 561 edges)

- 10 styleguide nodes, 10 toolguide nodes — all present as nodes.
- **Edges INTO styleguides/toolguides: 19** (from actions, directives, procedures, tactics via their reference walks).
- **Edges FROM styleguides/toolguides: 0** — because the extractor never walks their `references` fields.
- Styleguides/toolguides with no incoming edges ("graph-orphans"): `deployable-skill-authoring`, `java-conventions`, `mutation-aware-test-design`, `reasons-canvas-writing`, `maven-review-checks`, `python-mutation-tools`, `python-review-checks`, `typescript-mutation-tools` (8 of 20 are true orphans; the other 12 have at least one incoming edge).

### References census on built-in files

| File | Format | Reference count | Format shape |
|------|--------|-----------------|--------------|
| `aggregate-design-rules.styleguide.yaml` | plain `list[str]` (file paths) | 3 | raw file paths (`src/doctrine/tactics/…`) |
| `deployable-skill-authoring.styleguide.yaml` | plain `list[str]` | 3 | raw file paths |
| `java-conventions.styleguide.yaml` | plain `list[str]` | 5 | raw file paths |
| `mutation-aware-test-design.styleguide.yaml` | none | 0 | — |
| `planning-and-tracking.styleguide.yaml` | plain `list[str]` | 2 | raw file paths |
| `python-conventions.styleguide.yaml` | plain `list[str]` | 3 | raw file paths |
| `reasons-canvas-writing.styleguide.yaml` | none | 0 | — |
| `test-desiderata-and-boundaries.styleguide.yaml` | plain `list[str]` | 8 | raw file paths |
| `testing-principles.styleguide.yaml` | plain `list[str]` | 7 | raw file paths |
| All 10 toolguide `.yaml` files | none | 0 | — |

**Critical format gap:** Styleguide `references` is a `list[str]` (raw file paths like `src/doctrine/tactics/built-in/…`), NOT the structured `{type, id, reason}` form used by procedures, tactics, and directives. The schema confirms this: `references.items.type = string`. The extractor's `_add_ref_edge` and `_kind_for_type` helpers work with structured `{type, id}` dicts — they cannot parse raw file paths.

### Extractor extension design sketch

To walk styleguide and toolguide `references`, the extractor needs a **path-to-URN resolver**:

```python
# New helper: infer kind and id from a raw file path reference
_PATH_KIND_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"src/doctrine/tactics/built-in/(.+)\.tactic\.yaml$"), "tactic"),
    (re.compile(r"src/doctrine/paradigms/built-in/(.+)\.paradigm\.yaml$"), "paradigm"),
    (re.compile(r"src/doctrine/directives/built-in/(.+)\.directive\.yaml$"), "directive"),
    (re.compile(r"src/doctrine/styleguides/built-in/(.+)\.styleguide\.yaml$"), "styleguide"),
    (re.compile(r"src/doctrine/toolguides/built-in/(.+)\.toolguide\.yaml$"), "toolguide"),
    (re.compile(r"src/doctrine/procedures/built-in/(.+)\.procedure\.yaml$"), "procedure"),
]

def _resolve_path_ref(path_str: str) -> tuple[str, str] | None:
    """Return (kind, id) for a raw path reference, or None if unrecognised."""
    for pattern, kind in _PATH_KIND_PATTERNS:
        m = pattern.search(path_str)
        if m:
            # Extract the artifact id from the filename (without the kind suffix)
            raw_id = m.group(1)  # e.g. "aggregate-boundary-design"
            # For directives the id is the numeric prefix + name; load and read it
            # For all others the stem IS the id
            return kind, raw_id
    return None
```

Then add a styleguide walk block to `extract_artifact_edges()` (after procedures, before agent profiles):

```python
# --- Styleguides ---
styleguides_dir = doctrine_root / "styleguides" / "built-in"
if styleguides_dir.is_dir():
    for path in sorted(styleguides_dir.rglob("*.styleguide.yaml")):
        data = _load_yaml(path)
        if data is None:
            continue
        sg_id: str = data.get("id", "")
        sg_title: str = data.get("title", "")
        src_urn = artifact_to_urn("styleguide", sg_id)
        _ensure_node(nodes_by_urn, src_urn, NodeKind.STYLEGUIDE, sg_title)

        for ref_raw in data.get("references", []) or []:
            if not isinstance(ref_raw, str):
                continue
            resolved = _resolve_path_ref(ref_raw)
            if resolved is None:
                continue  # non-doctrine path (e.g. glossary YAML) — skip
            ref_kind, ref_id = resolved
            tgt_kind = _KIND_MAP.get(ref_kind)
            if tgt_kind is None:
                continue
            tgt_urn = artifact_to_urn(ref_kind, ref_id)
            _ensure_node(nodes_by_urn, tgt_urn, tgt_kind)
            _add_edge(DRGEdge(source=src_urn, target=tgt_urn, relation=Relation.SUGGESTS))
```

Toolguides have **zero** `references` blocks in the current built-in set — no new edges would come from a toolguide walk today. However, the schema would need a `references` field added (currently absent from `toolguide.schema.yaml`) before toolguides could carry structured references. The toolguide schema has `additionalProperties: false`, so no references field can be added without a schema change.

### Graph delta estimate

Styleguides with references: 7 files, 31 total path references.

Filtering non-doctrine paths (glossary YAML → `.kittify/glossaries/…` — 2 paths in `planning-and-tracking.styleguide.yaml`):

| Styleguide | Resolvable refs | New edges |
|------------|-----------------|-----------|
| `aggregate-design-rules` | 3 (2 tactics + 1 paradigm) | 3 suggests |
| `deployable-skill-authoring` | ~3 (need path inspection to confirm kinds) | ~3 suggests |
| `java-conventions` | ~4 (directives + tactics pattern) | ~4 suggests |
| `planning-and-tracking` | 1 (toolguide only; glossary path skipped) | 1 suggests |
| `python-conventions` | ~3 | ~3 suggests |
| `test-desiderata-and-boundaries` | ~7 (mix of tactics + directives) | ~7 suggests |
| `testing-principles` | ~6 (tactics + directives) | ~6 suggests |

**Estimated graph delta: +27 edges, 0 new nodes** (all target nodes already exist as nodes from `_discover_built_in_artifact_nodes`). The 27 "legacy orphans" referenced in the task prompt correspond to the 27 orphan non-action/non-profile nodes in the current graph — of those, ~7 would gain incoming edges from the styleguide walk (the 7 tactics/paradigms currently referenced by styleguides but only registered as nodes with no incoming edges). The remaining ~20 orphan tactics would remain orphans until either: (a) other procedures/directives gain cross-references to them, or (b) curated edges are added to `_CURATED_ARTIFACT_EDGES`.

**Extractor walk prerequisite:** The `references` format mismatch (plain file paths vs structured dicts) is the single blocking implementation decision. The path-to-URN resolver above handles it. No schema changes are needed to add the walk; schema changes are needed only if toolguides are ever to carry `references` blocks.

---

## DIRECTIVE_018 Versioning — Overall Verdict

All three artifacts (`planning-and-tracking.styleguide.yaml`, `tracker-organisation-workflow.procedure.yaml`, `GITHUB_TRACKER.md`) use `schema_version: "1.0"`. DIRECTIVE_018 requires version notes for **breaking** changes. All deltas above are **additive** (new `patterns` entries, extended `description` text, additional `notes` content, `last_updated` bump). No fields are removed or semantically redefined. No version bump is required. The changes should be accompanied by a CHANGELOG entry or a commit message noting the additive doctrine update.

---

## Verdicts Summary

| Scope | Verdict |
|-------|---------|
| **#1865 styleguide deltas** | DELTAS READY — 3 targeted changes: triage-snapshot pattern, secondary-label-coexistence pattern, provisional-priority default naming in principle 9 |
| **#1866 procedure deltas** | DELTAS READY — Step 8 description + `notes` addendum; label-only-mutation question explicitly answered (permitted) |
| **#1867 toolguide pagination** | DELTA READY — `--paginate` generalisation block + `last_updated` bump; no toolguide YAML schema change needed |
| **Authority-path flip chain** | NO DRIFT — all 7 chain links verified accurate post two rebases; ADR deferral still valid |
| **DRG extractor extension** | SKETCH READY — path-to-URN resolver needed; +~27 suggests edges estimated; toolguide walk blocked by missing schema `references` field; styleguide walk is self-contained |
