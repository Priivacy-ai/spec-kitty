# Spec — Charter UX & Org-Pack Vocabulary

**Mission ID:** 01KSAF14K8FZ56MHYT45EGWHHC
**Mission slug:** charter-ux-and-org-pack-vocabulary-01KSAF14
**Mission type:** software-dev
**Target branch:** main
**Status:** Draft
**Parent epic:** [#1111](https://github.com/Priivacy-ai/spec-kitty/issues/1111)
**Linked issues:** #1099, #1100, #1101, #1104, #1291
**Mission brief:** `research/mission-brief.md` (Researcher Robbie, 2026-05-23)

---

## Overview

A user adopting Spec Kitty today can land in two distinct failure modes that this mission resolves together:

1. **"My charter says it is healthy, but my agent has no doctrine."** `charter status`, `charter lint`, and `charter synthesize` each operate on a partial slice of the freshness story. A repo with a charter but no synthesized doctrine appears `SYNCED / No decay detected` while the linter scanned zero nodes. The dashboard, governed context, and agent reasoning silently degrade.
2. **"My org pack wants to extend a built-in tactic, but the schema says no."** Tactic, styleguide, paradigm, procedure, and agent-profile schemas use `extra: forbid`, so a pack author cannot declare augment-vs-replace intent. The validator emits a generic "overrides a shipped tactic" advisory regardless of intent.

These failure modes share two code surfaces (the charter CLI and the doctrine schema/validator pipeline). Resolving them in one mission also lets us correct an accumulated vocabulary inconsistency: the canonical layer label in `src/doctrine/*/built-in/` is **`built-in`** on disk, but Python identifiers, log messages, JSON outputs, and tests still emit `shipped`. This mission unifies the term.

---

## Primary scenarios

### Scenario 1 — Fresh-clone freshness reporting (FR-001 .. FR-005)
A developer clones a project that ships only `.kittify/charter/charter.md`. They run `spec-kitty charter status` and `spec-kitty charter lint`. The tool must report deterministically that the project DRG is missing, that lint scanned the built-in DRG only (or refused to scan), and exactly which command will bring the project up to date.

### Scenario 2 — Session-start preflight (FR-006 .. FR-008)
A developer starts a governed session against a repo whose synthesized doctrine is stale (charter source has been edited since last `sync`/`synthesize`). The preflight detects the staleness, and either auto-refreshes when safe, or blocks with one exact recovery command. The preflight runs at the entry point of governed commands and never fails silently.

### Scenario 3 — Pack tactic augments a built-in (FR-009 .. FR-014)
An org-pack author writes a tactic with the same ID as a built-in tactic and declares `enhances: <built-in-id>`. `spec-kitty doctrine pack validate` accepts it without the override advisory and the DRG auto-emits the `enhances` edge. If the author writes `overrides: <built-in-id>` instead, the validator accepts the explicit replace intent and suppresses the advisory the other way.

### Scenario 4 — Vocabulary cutover (FR-015 .. FR-017)
A user reads `charter status --json` after upgrade. The provenance and layer labels read `"built-in"` consistently — in advisory messages, profile sources, status JSON, lint banners, and ADR / doc references. The word `shipped` no longer appears as a user-facing label anywhere in the public surface.

---

## Functional Requirements

| ID | Description | Status | Linked issue |
|---|---|---|---|
| **FR-001** | `LintEngine` MUST distinguish three graph states (`merged`, `built_in_only`, `missing`) and expose them in `DecayReport.graph_state`. | Draft | #1099 |
| **FR-002** | When `.kittify/doctrine/graph.yaml` is absent, `LintEngine` MUST fall back to the built-in DRG and report `graph_state="built_in_only"` rather than returning an empty report. | Draft | #1099 |
| **FR-003** | The `charter lint` human banner MUST branch on `graph_state` — emit a "No project DRG found; linted built-in only — run `spec-kitty charter synthesize`" line for the `built_in_only` case, and a "No lintable graph" line for the `missing` case. | Draft | #1099 |
| **FR-004** | `charter lint --json` output MUST include `graph_state` as a top-level field. | Draft | #1099 |
| **FR-005** | `charter status --json` MUST include separate freshness sub-objects (`charter_source`, `synced_bundle`, `synthesized_drg`), each with `state`, `last_change`, and `remediation` fields, computed by hash/timestamp comparison rather than file existence alone. | Draft | #1101 |
| **FR-006** | A new `charter preflight` command (and matching session-start hook callable from governed commands) MUST emit a deterministic JSON result describing what was checked, what was refreshed, and what blocked the session — never a silent no-op. | Draft | #1100 |
| **FR-007** | When the preflight detects a fresh-checkout repo with a charter and no synthesized doctrine, it MUST either run the safe refresh sequence (`charter sync` → `charter synthesize` → `bundle validate`) automatically or block with the exact recovery command(s); behaviour is selectable via a configuration flag whose default is documented. | Draft | #1100 |
| **FR-008** | The preflight MUST refuse to auto-refresh when there are uncommitted generated artifacts in the worktree, and MUST surface the conflict instead of overwriting work. | Draft | #1100 |
| **FR-009** | `charter synthesize` MUST guarantee a documented post-condition for fresh checkouts: either (a) `.kittify/doctrine/graph.yaml` exists and is valid, or (b) a `built_in_only: true` marker is recorded in `synthesis-manifest.yaml` and downstream commands honour it. | Draft | #1104 |
| **FR-010** | The `Tactic`, `Styleguide`, `Paradigm`, `Procedure`, and `AgentProfile` Pydantic models and matching JSON Schemas MUST accept two new optional declarative fields: `overrides: <id>` and `enhances: <id>`. | Draft | #1291 |
| **FR-011** | The two fields MUST be mutually exclusive on a single artifact; the model validator MUST emit a named error when both are present. | Draft | #1291 |
| **FR-012** | When `overrides` or `enhances` references an ID that does not exist in built-in doctrine of the same artifact kind, `spec-kitty doctrine pack validate` MUST raise a hard error (not an advisory). | Draft | #1291 |
| **FR-013** | The pack validator's shipped-ID collision advisory MUST be suppressed when `overrides` or `enhances` is declared on the colliding artifact, and reworded when neither is declared (to align with the field-merge semantics ratified in ADR `2026-05-16-1-doctrine-layer-merge-semantics.md`). | Draft | #1291 |
| **FR-014** | The DRG resolver / org-pack loader MUST auto-emit `Relation.ENHANCES` and `Relation.OVERRIDES` edges from the declared fields, so pack authors do not have to hand-write entries in `drg/fragment.yaml`. The `Relation` enum MUST be extended to include both relations. | Draft | #1291 |
| **FR-015** | The user-facing vocabulary `shipped` MUST be renamed to `built-in` across: (a) Python identifiers, parameter names, variable names; (b) log and advisory messages; (c) JSON output keys and values (e.g. `profiles_cmd.py` provenance, `_warn_project_override`); (d) docstrings and comments; (e) test assertions and fixtures; (f) doc, ADR, and schema description text. | Draft | epic body |
| **FR-016** | The rename MUST be covered by an architectural regression test that scans the public CLI surface (`charter status --json`, `charter lint --json`, `agent profile list --json`, `doctrine pack validate --json`) and asserts the absence of `"shipped"` as a layer label. | Draft | epic body |
| **FR-017** | The rename MUST be accompanied by a CHANGELOG breaking-change entry and a migration note for any external consumer that pattern-matched `"shipped"` in JSON output. | Draft | epic body |

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|---|---|---|---|
| **NFR-001** | Charter preflight runtime overhead per invocation MUST stay below 300 ms on a repo with synthesized doctrine present and below 1.0 s on a fresh checkout where refresh runs. | <300 ms warm / <1.0 s cold | Draft |
| **NFR-002** | All new fields, enum values, and JSON keys MUST be documented in user-visible reference docs before the mission merges. | 100% coverage of new public symbols | Draft |
| **NFR-003** | The `shipped → built-in` rename MUST NOT break green CI: zero failing tests after the cutover. | 0 regressions | Draft |
| **NFR-004** | The Python `extra="forbid"` schema additions for `overrides`/`enhances` MUST NOT regress loading of any existing tactic/styleguide/paradigm/procedure/agent-profile YAML in the repo. | 0 fixture failures | Draft |

## Constraints

| ID | Description | Status |
|---|---|---|
| **C-001** | Field-merge semantics ratified by ADR `2026-05-16-1-doctrine-layer-merge-semantics.md` MUST NOT change. The new fields add declarative vocabulary on top of existing merge behaviour; they do not alter it. | Locked |
| **C-002** | Mission must classify every `shipped → built-in` occurrence in `occurrence_map.yaml` before implementation begins (bulk-edit gate — `change_mode: bulk_edit` is set in `meta.json`). | Locked |
| **C-003** | Issues #1099, #1100, #1101, #1104, #1291 MUST be assigned to the Human-in-Charge at the moment a WP for that issue starts implementing (DIR-012). | Locked |
| **C-004** | Any new ADR introduced by this mission MUST live under `architecture/3.x/adr/` and cross-reference the merge-semantics ADR. | Locked |
| **C-005** | This mission does not modify epic-#1111 Slices B (#1103), C (#1102), D (#1098), E (#1007, #1013), or the Slice F composable-workflows item (#682). Those remain in their own missions. | Locked |
| **C-006** | All new Python code MUST pass `mypy --strict` and `ruff check` and ship with tests (per project charter Quality Gates). | Locked |
| **C-007** | Identifier safety / ASCII allowlist (DIR-010) applies to any generated DRG node URN or pack ID validation. | Locked |

---

## Success criteria (measurable)

1. **Freshness-UX success.** On a freshly cloned repo containing only a charter file, all three commands (`charter status`, `charter lint`, `charter preflight`) report the missing project DRG with the same remediation hint, and `synthesize` produces or explicitly skips the project DRG per FR-009.
2. **Pack-authoring success.** A pack tactic declaring `enhances: context-boundary-inference` against a known built-in passes validation without the override advisory; declaring against an unknown ID fails with a named error.
3. **Vocabulary success.** Grepping the public JSON CLI output and the source tree for `"shipped"` (as a layer label) returns zero hits after the mission merges.
4. **No regression.** The full test suite passes after the cutover. The charter freshness round-trip on the project's own repo produces a green status.

---

## Key entities

- **Charter freshness state** (new logical entity): aggregates `charter_source`, `synced_bundle`, and `synthesized_drg` sub-states; surfaced by both `charter status` and `charter preflight`.
- **Pack authoring intent declaration** (new): the `overrides` and `enhances` fields on tactic/styleguide/paradigm/procedure/agent-profile artifacts; semantically the org-layer pack author's contract with the doctrine validator.
- **Layer label** (existing, vocabulary-clarified): the user-facing string identifying a doctrine layer. Allowed values post-mission: `built-in`, `org:<pack-name>`, `project`.

## Out of scope

- Slice B (#1103), Slice C (#1102), Slice D (#1098), Slice E (#1007, #1013), Slice F composable-workflows (#682). Tracked in separate missions.
- Cross-pack augmentation (a pack tactic enhancing an artifact from another pack). The relationship is org-pack → built-in only.
- Dashboard UI changes beyond what is needed to render the new freshness fields.

## Assumptions

- The ADR-ratified field-merge behaviour is correct and stable.
- Org-pack consumers in the wild are pre-3.2.0 stable and have not externally cached `"shipped"` as a contract; CHANGELOG note is sufficient migration support.
- The bulk-edit gate produces an actionable occurrence map without manual classification of every single comment.

## Open questions (max 3)

1. Should the field name be `enhances` (per issue #1291) or `augments` (per HiC mention at handoff)? — **flagged for architect review.** Default: `enhances`, matching the canonical issue text.
2. Should `Relation.REPLACES` be renamed to `Relation.OVERRIDES`, or should both names coexist with an alias? — **flagged for architect review.**
3. Should the preflight run on every governed command or only at session-start / `next` / `implement` / `dashboard` entry points? — **flagged for architect review.**
