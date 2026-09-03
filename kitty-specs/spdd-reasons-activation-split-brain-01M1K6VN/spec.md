# Mission Specification: SPDD/REASONS activation split-brain

**Mission Branch**: `fix/spdd-reasons-activation-split-brain-3838`
**Created**: 2026-09-03
**Status**: Specified
**Input**: GitHub issue [#3838](https://github.com/Priivacy-ai/spec-kitty/issues/3838) — "SPDD/REASONS activation split-brain: `is_spdd_reasons_active` reads `selected_*` while the compiler activates via `activated_*`"

## Summary

`is_spdd_reasons_active` (`src/charter/offering/spdd_reasons/activation.py:61`) decides
whether the SPDD/REASONS doctrine pack is active by parsing `.kittify/charter/charter.yaml`'s
**authored** `governance.charter.selected_paradigms` / `selected_tactics` /
`selected_directives` — the record of what an interview/pack selected once, at
charter-bootstrap time. The activation compiler (`compile_charter`,
`src/charter/activation/compiler.py:365-367`) explicitly does the opposite: its own
docstring states the activated-doctrine selection is sourced from `config.activated_*`
"never from `interview.selected_*`" — `selected_*` is retired as an activation source and
kept purely as an interview record. `PackContext.from_config`
(`src/charter/activation/pack_context.py:207`) is the real, current activation authority:
it resolves `.kittify/config.yaml`'s `activated_*` keys (or, when a `charter:` pointer is
present, the pointed-at `charter.yaml`'s flat `activated_*` keys — the INV-2 two-file
resolution implemented by `_load_charter_activation_source`,
`pack_context.py:557-585`) under documented three-state semantics: an absent key means "all
built-ins available," an explicit empty list means "nothing activated," and a non-empty list
is an explicit set.

Because nothing in current `main` ever refreshes `governance.charter.selected_*` after
charter-bootstrap (`write_compiled_charter` preserves the `governance:` section
byte-for-byte; `spec-kitty charter sync` is a pure staleness reporter, never a writer — both
confirmed by reading the code, not just the readiness probe), the two answers drift apart
through ordinary charter evolution — deactivating or activating a pack via
`.kittify/config.yaml` (`charter pack apply`, a manual edit, an org-pack change) after
bootstrap — with no error, no warning, and no test in the repository today that would fail if
this were "fixed" back to itself.

**This is reproduced live, on this checkout's own dogfood `.kittify/`, not merely cited.**
Running both functions against this repo's own charter (HEAD at spec-authoring time):

```
activated_paradigms has SPDD:      True   (charter.yaml:1718 "structured-prompt-driven-development")
activated_directives has 038:      True   (charter.yaml:1545 "038-structured-prompt-boundary")
activated_tactics has reasons:     True   (charter.yaml:1616-1617 "reasons-canvas-fill"/"reasons-canvas-review")
is_spdd_reasons_active(repo_root): False  (charter.yaml:20-22 governance.charter.selected_* are all [])
```

All four of `is_spdd_reasons_active`'s disjunctive selectors are true in the *actually
activated* set; the function returns `False` anyway, because it reads the empty, never-synced
`governance.charter.selected_*` section instead. **This repo's own missions are right now
silently not receiving SPDD/REASONS bootstrap guidance and having REASONS template blocks
stripped, despite the compiler treating the pack as fully active** — a live instance of the
issue, not a hypothetical.

A second reader of the same stale section is in scope per the issue's own "and anything else
currently reading `selected_*` for activation decisions" clause: `_load_action_doctrine_bundle`
(`src/charter/activation/action_doctrine_bundle.py:185`) sources its DRG traversal roots and a
directive-delivery allowlist from `_load_doctrine_selection` → `load_governance_config`
(`src/charter/activation/sync.py:321`) — the same authored `governance.charter.selected_*`
section — in the same function that separately, correctly, filters the DRG by `activated_*`
(`filter_graph_by_activation`, line 216). See Decision Record 2 below for the code-level proof
this is the same defect class, not merely a superficially similar one.

The fix makes `is_spdd_reasons_active` (and the `action_doctrine_bundle.py` reader) consume
`activated_*`-based resolution — without violating the `charter.offering → charter.activation`
one-way import ban (C-004, enforced non-vacuously by
`tests/architectural/test_charter_offering_does_not_import_activation.py`), which is exactly
why `activation.py` currently carries its own "narrow compat read" instead of calling the real
resolver in the first place.

## Clarifications

Both decisions below were made by the operator during mission readiness review (readiness
probe `_readiness/3838-spdd-reasons-activation-split-brain.md`, Q1/Q2) and are **binding** —
not reopened here. This section records them with the evidence a reviewer needs to audit them
against, per the operator's explicit instruction that R1–R6 and `sk-review` must be able to
review the decisions actually made, not re-derive them.

### Decision Record 1 — Q1: how the fix satisfies the C-004 layering gate

**Chosen: Option A — caller-resolves, callee-consumes; `is_spdd_reasons_active` keeps its
signature but is rewritten to a raw, INV-2-aware `activated_*` read.**

`charter.offering.spdd_reasons.activation` cannot import
`charter.activation.pack_context.PackContext` — the thing that actually knows `activated_*` —
without violating the hard-enforced C-004 boundary (`charter.offering → charter.activation` is
FORBIDDEN; `charter.activation → charter.offering` is the only allowed direction). Rejected
alternatives, per the readiness probe:

- **Option B (relocation)** — move the detection logic into `charter.activation` so it can call
  `PackContext` directly, leaving `charter.offering.spdd_reasons` with only pure
  content/rendering helpers. Rejected as the bigger move: a public-import-path change for
  `is_spdd_reasons_active` (currently re-exported from `charter.offering.spdd_reasons.__init__`),
  a `contracts/activation.md` rewrite, and it touches the module boundary the
  `charter-code-topology` mission (#3664) only just finished establishing days before this issue
  was filed.
- **Option C (leave self-contained, hand-roll the full org-overlay resolution)** — rejected:
  this is the same "narrow compat read" shape that produced today's bug; a second independent
  reimplementation of activation resolution invites the exact defect class recurring.

**What Option A actually requires, confirmed by reading `pack_context.py` in full (not assumed
from the issue title):** `PackContext.from_config`'s real resolution is **not** "parse
`.kittify/config.yaml`'s `activated_*` keys" in isolation. It is a two-file, pointer-following
resolution (INV-2, `_load_charter_activation_source`, `pack_context.py:557-585`):

1. Load `.kittify/config.yaml`. If it has no `charter:` pointer key (legacy/un-migrated
   project), read `activated_*` directly from `config.yaml` itself.
2. If `config.yaml` HAS a `charter:` pointer (this repo's own case —
   `.kittify/config.yaml:17` → `.kittify/charter/charter.yaml`), the `activated_*` keys are
   read from the **pointed-at charter.yaml's top level** instead — `config.yaml`'s own
   `activated_*` mirror, if any, is **never consulted** once the pointer resolves.
3. A dangling/unreadable pointer is a fail-loud `CharterPackConfigError`, never a silent
   fallback (`pack_context.py:571-578`).
4. Each per-kind key (`activated_directives`, `activated_tactics`, `activated_paradigms`, …) is
   independently three-state: absent key → `None` ("all built-ins available"); present as `[]`
   → explicit empty set; present non-empty → explicit set (`_read_list_key`,
   `pack_context.py:609-615`).

**This is why the parity test is load-bearing, not decorative.** A rewrite that only reads
`config.yaml`'s own `activated_*` keys, ignoring the `charter:` pointer, would silently return
the wrong answer on exactly this repo's own dogfood charter (where the real `activated_*` keys
live in the pointed-at `charter.yaml`, not `config.yaml`) — reproducing a **new** instance of
the split-brain this mission exists to close, on the mission's own home repository. FR-001/AC-1
below require the rewritten body to replicate step 1–4 verbatim (without importing
`charter.activation`'s Python classes — only stdlib YAML parsing of the two files, mirroring
the "narrow compat read" idiom the module already uses for the old `governance:` section), and
FR-002 requires a parity test asserting agreement with the real `PackContext.from_config()`
across fixtures covering both the pointer-present and pointer-absent shapes.

**Precedent for the caller-resolves idiom**: `template_renderer.process_spdd_blocks` already
takes `active` as a caller-supplied keyword-only parameter and never resolves activation
itself (module docstring: "Activation is decided by the caller (single source of truth,
C-002)"); `charter_context.append_spdd_reasons_guidance` follows the same rule. Only the
convenience wrapper `apply_spdd_blocks_for_project` (`template_renderer.py:179-202`) and
`bootstrap_text.py:332` still resolve internally via `is_spdd_reasons_active(repo_root)` — and
because `is_spdd_reasons_active` keeps its signature, neither of those two call sites, nor the
`charter.spdd_reasons` facade re-export, nor `command_renderer.py`/`asset_generator.py`
(both `specify_cli`-layer, permitted to import `charter.activation` directly but not required
to for this fix) need to change their call shape — only `activation.py`'s body changes.

### Decision Record 2 — Q2: does this mission also fix `action_doctrine_bundle.py`'s reader?

**Chosen: Option A — fold it in.** The readiness probe flagged this as unresolved
("`_load_doctrine_selection`'s org-`required_*`-union purpose for prompt-content selection MAY
be a genuinely separate concept from activation gating — not yet confirmed") and required this
spec phase to settle it with code evidence, not a repeated guess. Read directly, in full, for
this spec: `src/charter/activation/action_doctrine_bundle.py`,
`src/charter/activation/org_pack_discovery.py`, `src/charter/activation/sync.py`.

**Finding: this is the same defect class, proven by two independent mechanisms in
`_load_action_doctrine_bundle` (`action_doctrine_bundle.py:142-260`), not one.**

`doctrine_selection = _load_doctrine_selection(repo_root)` (line 185) resolves through
`org_pack_discovery.py:178-222` → `sync.py:321` `load_governance_config`, which reads
`charter.yaml`'s `governance.charter.selected_*` — **the identical section**
`is_spdd_reasons_active` reads, confirmed byte-for-byte the same schema field
(`charter.activation.schemas.CharterYaml.governance.charter`). `_load_doctrine_selection` then
UNIONs each org pack's `required_<kind>` into the matching `selected_<kind>` field
(`org_pack_discovery.py:188-194`, "Org-required artifacts therefore reach the prompt without
the operator having to mirror them"). **This union purpose is real and IS legitimately
separate from activation gating** — it lets an org pack force delivery of artifacts the
project itself never selected. That part of the readiness probe's caution is confirmed
correct and is preserved, not removed (see FR-006).

But the *project-authored* half of `doctrine_selection` — the part sourced from the stale
`governance.charter.selected_*`, before the org-required union — is used in two places that
**are** activation decisions, both read directly off `action_doctrine_bundle.py`:

1. **A silent, incorrect exclusion filter (the sharper of the two).**
   `_classify_artifact_urns` (`context_renderers/delivery_table.py:238`):
   ```python
   if node.kind is NodeKind.DIRECTIVE and project_directives and artifact_id not in project_directives:
       continue
   ```
   `project_directives` (line 189) is built from the stale `selected_directives`. When it is
   **non-empty** — the ordinary case for any project that selected even one directive at
   bootstrap — this line drops **any** directive from delivery that is not in that stale set,
   **even a directive the current `activated_*` set genuinely activates and that the DRG walk
   legitimately reached**. Concretely: a project bootstrapped selecting only `DIRECTIVE_010`,
   then later activates `DIRECTIVE_038` via `.kittify/config.yaml` without a charter rebuild —
   `filter_graph_by_activation` correctly keeps the `DIRECTIVE_038` node in the graph
   (it checks `activated_*`), `resolve_context` correctly reaches it, and this line then
   silently throws it away anyway because `"DIRECTIVE_038" not in {"DIRECTIVE_010"}`. This is
   activation-adjacent, silent, and reachable through ordinary charter evolution — the exact
   shape the issue describes, not a hypothetical.
2. **A silent under-seeding of traversal roots (the softer failure, confirmed live on this
   repo's own dogfood state).** `project_directives`/`selected_tactics`/`selected_paradigms`
   (lines 189-191) also seed `roots` (lines 230-234, consumed by progressive disclosure) and
   the `start_urns` `_classify_artifact_urns` uses to widen delivery via
   `resolve_transitive_refs`'s requires/suggests closure (`delivery_table.py:211-220`). On
   this repo's own charter, `selected_directives`/`selected_tactics`/`selected_paradigms` are
   all `[]` — so `start_urns` is **empty** and the closure-widening these fields exist to
   provide contributes nothing at all, despite ~9 directives, dozens of tactics, and several
   paradigms being genuinely activated. Read `resolve_transitive_refs`
   (`src/charter/offering/drg/query.py:331-380`) and `walk_edges`: a start URN whose node is
   absent from the (already activation-filtered) graph is recorded in an `unresolved` list
   and silently dropped — never raised — so the reverse case (a stale `selected_*` entry
   naming something since deactivated) degrades gracefully rather than crashing, but still
   silently produces a narrower delivered set than `activated_*` alone would.

Both mechanisms read the same stale section for a decision that gates what an agent is told is
active/required doctrine — squarely inside the issue's "anything else currently reading
`selected_*` for activation decisions" clause. **Conclusion: fold in.** FR-006 requires
`project_directives`/`selected_tactics`/`selected_paradigms` to be re-derived from
`pack_context.activated_*` (already threaded into `_load_action_doctrine_bundle` as a
parameter — no new plumbing needed to reach it) instead of `_load_doctrine_selection`'s
authored `selected_*`, while the org-required union (the confirmed-legitimate, separate
purpose) is preserved by unioning org-pack `required_<kind>` onto the `activated_*`-derived set
rather than onto the retired `selected_*` set. The exact mechanics of that re-derivation
(a new helper vs. inline `pack_context` reads) are a plan-phase design choice; this spec fixes
the *what*, not the *how*.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A tooling consumer gets one trustworthy answer to "is SPDD/REASONS active here?" (Priority: P1)

As a maintainer of `is_spdd_reasons_active`'s callers (`bootstrap_text.py`'s charter-context
renderer, `apply_spdd_blocks_for_project`'s template gate, and any downstream tool — e.g. a
Kitty Desktop governance panel — that renders "is this doctrine pack active"), I want
`is_spdd_reasons_active(repo_root)` to agree with the compiler's real `activated_*` authority
in every case, so that bootstrap guidance, REASONS template blocks, and any panel built on top
of this function all describe the same project state instead of two that can silently
disagree.

**Why this priority**: this is the literal defect named in issue #3838 and the mission's
primary deliverable — without it, the issue is not closed, and this repo's own dogfood
charter continues to under-deliver SPDD guidance to every mission run against it.

**Independent Test**: construct a `tmp_path` charter (or use this repo's own dogfood
`.kittify/` as a ready-made fixture) where `.kittify/config.yaml` points to a `charter.yaml`
whose top-level `activated_paradigms` includes `structured-prompt-driven-development` and
whose `governance.charter.selected_paradigms` is `[]`. Confirm `is_spdd_reasons_active`
returns `True` (today it returns `False`).

**Acceptance Scenarios**:

1. **Given** a charter whose `activated_paradigms`/`activated_directives`/`activated_tactics`
   include at least one of the four SPDD selectors AND whose
   `governance.charter.selected_paradigms`/`selected_directives`/`selected_tactics` are empty
   (this repo's own live dogfood shape), **When** `is_spdd_reasons_active(repo_root)` is
   called, **Then** it returns `True` — a red-first regression test using exactly this shape
   must fail on `main` before the fix and pass after.
2. **Given** the reverse disagreement — `governance.charter.selected_paradigms` names the SPDD
   paradigm but `.kittify/config.yaml`'s (or the pointed `charter.yaml`'s) `activated_paradigms`
   is an explicit `[]` or omits it via a narrower `activated_kinds` — **When**
   `is_spdd_reasons_active(repo_root)` is called, **Then** it returns `False` (the compiler's
   `activated_*` wins in both directions, not just the direction this repo happens to exhibit).
3. **Given** a charter where `activated_*` and `governance.charter.selected_*` FULLY AGREE
   (both select SPDD, or both select nothing), **When** `is_spdd_reasons_active(repo_root)` is
   called, **Then** the answer is unchanged from today's behavior — this mission does not flip
   any project whose two sources already agree.
4. **Given** `PackContext.from_config(repo_root)` and the rewritten `is_spdd_reasons_active`
   are run against the same set of representative fixtures spanning all three per-kind states
   (absent key / explicit empty list / explicit non-empty list) for each of paradigms,
   directives, and tactics, and both the `charter:`-pointer-present and pointer-absent
   `config.yaml` shapes, **When** the parity test runs, **Then** every fixture's boolean
   agrees between the two implementations — this is the mandatory parity test required by
   Decision Record 1, without which the two can drift apart again silently.

---

### User Story 2 - Action-doctrine delivery agrees with pack activation, not a stale bootstrap snapshot (Priority: P1)

As an agent consuming charter-context/bootstrap output for a mission action, I want the
directive/tactic/paradigm doctrine `_load_action_doctrine_bundle` delivers to reflect what is
currently `activated_*`, not what was selected once at charter-bootstrap time, so that a
directive genuinely activated after bootstrap is not silently withheld from me, and closure
widening is not silently starved to zero on a project (like this repo's own) whose
`selected_*` was never populated.

**Why this priority**: this is Decision Record 2's fold-in — the issue's own "anything else"
clause — and without it the mission leaves a second, code-proven instance of the same defect
class unfixed, in the same PR that closes the first.

**Independent Test**: construct a fixture DRG + charter where `activated_directives` includes
`DIRECTIVE_038` and the graph's `requires`/`suggests` walk from the action node reaches its
node, but `governance.charter.selected_directives` is `["DIRECTIVE_010"]` (a different,
also-activated directive). Confirm `_load_action_doctrine_bundle`'s resulting
`directive_ids` includes `DIRECTIVE_038` (today it is silently dropped by the
`project_directives`-allowlist check at `delivery_table.py:238`).

**Acceptance Scenarios**:

1. **Given** a directive that is genuinely `activated_*` and reached by the DRG walk from the
   action node, but is NOT a member of the stale, non-empty `governance.charter.selected_directives`,
   **When** `_load_action_doctrine_bundle` resolves the action bundle, **Then** the directive
   appears in `directive_ids` — a red-first test pinning today's silent drop must fail on
   `main` before the fix and pass after.
2. **Given** this repo's own dogfood charter (`selected_tactics`/`selected_paradigms`/
   `selected_directives` all `[]`, `activated_*` non-empty), **When** the action bundle is
   resolved for any software-dev action, **Then** the requires/suggests closure-widening
   traversal roots are seeded from the currently-`activated_*` tactics/paradigms/directives
   (not an empty stale set) — a test must assert the roots/closure are non-trivially
   populated for this exact shape, not merely that the function does not crash.
3. **Given** an org pack declaring `required_directives: [DIRECTIVE_099]` where the project's
   `activated_directives` does not include `DIRECTIVE_099`, **When** the action bundle is
   resolved, **Then** `DIRECTIVE_099` is still delivered (the org-required-union purpose,
   confirmed legitimate and separate from activation gating in Decision Record 2, is
   preserved verbatim — this scenario must not regress).

---

### Edge Cases

- **`.kittify/config.yaml` is entirely absent (no charter has ever been bootstrapped).**
  `PackContext.from_config`'s own documented default for this case ("all built-in kinds"
  active, and each three-state per-kind field `None` = "all IDs allowed") means a *blind*
  parity rewrite would flip `is_spdd_reasons_active` to `True` for every un-bootstrapped
  project — including mid-`spec-kitty init` template rendering, before any charter has ever
  been authored, when SPDD is explicitly opt-in doctrine (per the `spec-kitty-spdd-reasons`
  skill's own scope statement: "Does NOT handle: enforcing SPDD on projects whose charter has
  not selected the doctrine pack"). This is a real risk found by reading `pack_context.py`
  directly (see Decision Record 1), not a hypothetical: FR-004 requires the mission to
  explicitly verify, at implementation time, whether any real call site invokes
  `is_spdd_reasons_active`/`apply_spdd_blocks_for_project` before `.kittify/config.yaml`
  exists on disk, and to PIN the absent-config-file behavior to `False` (today's safe
  default) regardless of what a literal `PackContext.from_config` parity read would produce
  for that one case — with the divergence and its rationale stated explicitly in the code
  comment and the parity test (which scopes its "must agree" fixtures to
  "`.kittify/config.yaml` exists," not "no charter at all"). This is a deliberate,
  documented, evidence-based carve-out from Decision Record 1's parity mandate, not a silent
  exception.
- **Malformed `.kittify/config.yaml` or a `charter:` pointer naming a file that does not
  exist.** `PackContext.from_config` fails loud (`CharterPackConfigError`) for both. The
  rewritten `is_spdd_reasons_active` must not silently degrade to `False`/`True` here either
  — it must raise, matching the contract's existing "malformed YAML propagates" rule
  (`activation.py`'s current module docstring) and `PackContext`'s own fail-loud discipline.
  This is this mission's own silent-success obligation: the bug being fixed IS a silent
  disagreement with no error signal; the fix must not introduce a new quiet corner.
- **A directive ID matches `DIRECTIVE_038` via the numeric-hint slug form** (e.g.
  `038-structured-prompt-boundary`, this repo's own live case) rather than the canonical
  `DIRECTIVE_038` string. The existing `_is_directive_038` matching logic (numeric-hint +
  case-insensitive compare, `activation.py:175-185`) must be preserved verbatim against the
  new `activated_directives` source — this is matching logic, not a source-of-truth question,
  and is out of scope to change.
- **A project migrated to the `charter:` pointer form vs. a legacy project with no pointer**
  (INV-2's two shapes). Both must be covered by the parity test fixtures (Decision Record 1) —
  a rewrite that only handles one shape correctly reproduces the exact class of bug this
  mission fixes, on whichever shape it missed.
- **The `_load_doctrine_selection` org-required union with an EMPTY `activated_*` result for
  a kind** (explicit `activated_directives: []`). FR-006's re-derivation must still union
  org-required directives onto that explicitly-empty activated set (per Decision Record 2,
  Scenario 3) — an empty `activated_*` must not be conflated with "the union step itself is
  skipped."

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Rewrite `is_spdd_reasons_active` to read `activated_*` via INV-2 resolution | `_compute_active`/`_governance_selects_pack`/`_directives_select_pack` (`activation.py:96-185`) currently parse `charter.yaml`'s authored `governance:`/`directives:` sections. As a maintainer, I want the function's body replaced with a raw, `charter.activation`-import-free read that: (a) loads `.kittify/config.yaml`; (b) if it carries a `charter:` pointer, follows it to the pointed `charter.yaml` and reads that file's top-level `activated_paradigms`/`activated_directives`/`activated_tactics` instead; (c) if no pointer, reads those same keys directly from `config.yaml` (the legacy shape); (d) applies the existing three-state per-kind semantics (absent key = all built-ins available, `[]` = none, explicit list = that list) verbatim, matching `PackContext._read_list_key`'s contract — so the function's public signature (`is_spdd_reasons_active(repo_root) -> bool`) is unchanged but its answer is sourced from the same authority the compiler uses (User Story 1). | P1 | Open |
| FR-002 | Mandatory parity test against `PackContext.from_config()` | As a reviewer, I want a committed test asserting `is_spdd_reasons_active`'s three-state resolution agrees with `PackContext.from_config(repo_root)`'s `activated_paradigms`/`activated_directives`/`activated_tactics` fields across a fixture matrix covering: each of the three states (absent key / empty list / explicit list) for each of the three kinds, AND both the `charter:`-pointer-present and pointer-absent `config.yaml` shapes — so the two implementations cannot silently drift apart again, per Decision Record 1's explicit mandate (User Story 1, Scenario 4). | P1 | Open |
| FR-003 | `__all__` for `activation.py` (C-007) | `src/charter/offering/spdd_reasons/activation.py` currently declares no `__all__` — a pre-existing C-007 gap on a module this mission rewrites. As this mission touches the file's body, I want it to also declare `__all__` (at minimum `is_spdd_reasons_active`, `clear_activation_cache`) so the symbol-level dead-code gate (`tests/architectural/test_no_dead_symbols.py`) covers it, with every listed symbol already having a real caller in `src/` (the existing `__init__.py` re-export and `bootstrap_text.py`/`template_renderer.py` call sites). | P2 | Open |
| FR-004 | Pin the absent-`.kittify/config.yaml` behavior explicitly | Per Edge Cases, I want the rewritten function's absent-config-file path to return `False` explicitly (preserving today's safe default), with a code comment stating this is a deliberate, evidence-based carve-out from full `PackContext` parity (not an oversight), and I want the implementation to first verify at the real call sites (`bootstrap_text.py:332`, `apply_spdd_blocks_for_project`, `command_renderer.py`, `asset_generator.py`) whether any of them can be reached before `.kittify/config.yaml` exists on disk (e.g. during `spec-kitty init` template rendering) — recording the finding either way. | P1 | Open |
| FR-005 | Fail-loud on malformed config, not silent False/True | As a maintainer, I want the rewritten function to raise (matching `PackContext.from_config`'s `CharterPackConfigError`/YAML-loader-exception behavior) when `.kittify/config.yaml` is malformed, or its `charter:` pointer names a file that does not exist or is malformed — never silently returning `False` or `True` for these cases. This is the mission's own silent-success obligation (charter binding: "Silent success is this repo's dominant failure mode"). | P1 | Open |
| FR-006 | Re-derive `_load_action_doctrine_bundle`'s directive allowlist and traversal roots from `activated_*` | Per Decision Record 2: `project_directives`/`selected_tactics`/`selected_paradigms` (`action_doctrine_bundle.py:189-191`), which currently source the `NodeKind.DIRECTIVE` delivery-allowlist check (`delivery_table.py:238`) and the closure-widening `start_urns`/`roots` (`action_doctrine_bundle.py:230-234`), must instead be derived from `pack_context.activated_directives`/`activated_tactics`/`activated_paradigms` (`pack_context` is already a parameter of `_load_action_doctrine_bundle` — no new plumbing required to reach it). The org-pack `required_<kind>` union currently performed by `_load_doctrine_selection` (confirmed a legitimate, separate concept in Decision Record 2) must be preserved by unioning it onto the `activated_*`-derived set rather than onto the retired `selected_*` set (User Story 2). | P1 | Open |
| FR-007 | Red-first regression test: directive-allowlist silent drop | As a reviewer, I want a test reproducing User Story 2 Scenario 1 verbatim — a directive that is `activated_*` and DRG-reachable but absent from a non-empty stale `selected_directives` — asserting it IS delivered, failing on `main` today (the `project_directives` allowlist at `delivery_table.py:238` currently drops it) and passing after FR-006. | P1 | Open |
| FR-008 | Red-first regression test: this repo's own dogfood-shape closure starvation | As a reviewer, I want a test reproducing User Story 2 Scenario 2 — the exact live shape of this repo's own `.kittify/` (`selected_*` all empty, `activated_*` non-empty) — asserting the closure-widening roots/`start_urns` are populated from `activated_*` rather than empty, failing on `main` today and passing after FR-006. | P1 | Open |
| FR-009 | Update `contracts/activation.md` and `contracts/charter-context.md` | `kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/activation.md` currently documents the OLD source of truth (it names `governance.yaml`/`directives.yaml`, files already retired by the IC-04 triad-retirement — the doc has been stale independent of this mission). As part of closing this issue, I want both contract docs updated to state the new source of truth (`activated_*` via INV-2 resolution) and the new failure modes (FR-004/FR-005), so a future reader of the formal contract is not misled the way `is_spdd_reasons_active`'s own implementer was in 2026-04. | P2 | Open |
| FR-010 | Review and update the three pinning test files | `tests/charter/test_charter_context_spdd_reasons.py`, `tests/charter/test_activate_resolves_no_answers_edit.py` (`TestSpddActivationDoesNotFlip`), and `tests/charter/test_answers_inert_and_org_union.py` (`TestThirdLedgerUntouched`) currently pin the CURRENT (buggy, per this issue) `governance.charter.selected_*` read as intended behavior — some via fixtures that manually reconstruct a synced `governance:` section from `config_roots` to simulate a "governance section stays in sync" world `write_compiled_charter` does not actually implement. As part of this mission, I want each assertion in these three files triaged: assertions whose *intent* survives the fix (e.g. `TestThirdLedgerUntouched`'s "answers are inert, only `.kittify/config.yaml` is written" claim) are kept, updated only where their literal mechanics changed; assertions that encode the bug itself (asserting `governance.charter.selected_*` as the activation source) are flipped, with the diff itself serving as the record of which is which — not silently dropped. | P1 | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No new silent-success path | Every new/changed code path this mission adds (the rewritten `is_spdd_reasons_active` body, the re-derived `_load_action_doctrine_bundle` roots/allowlist) must, when it cannot determine activation, either raise (malformed/dangling-pointer config, FR-005) or return the explicitly-pinned safe default (absent config file, FR-004) — never an unexplained silent `False`/`True`/empty result. **Fails if**: any new path returns a default value for an error condition without the choice being named in a code comment and covered by a test. | Reliability | High | Open |
| NFR-002 | `__all__` / dead-code gate stays green | `tests/architectural/test_no_dead_symbols.py` must pass for every module this mission edits (`activation.py`, `compiler.py`, `bootstrap_text.py`, `action_doctrine_bundle.py`, `org_pack_discovery.py`, `sync.py`, `template_renderer.py`) — any new helper symbol introduced (e.g. a parity-check helper, an INV-2-read helper) must have a real `src/` caller or be scoped test-only (not added to a module's `__all__`). | Reliability | High | Open |
| NFR-003 | C-004 architectural gate stays green with non-vacuous coverage | `tests/architectural/test_charter_offering_does_not_import_activation.py` must continue to pass with zero violations after FR-001/FR-003 — no import of `charter.activation` (absolute or relative, any form the gate's full-AST walk catches) is introduced anywhere under `src/charter/offering/`. **Fails if**: the gate fires on this mission's own diff. | Compatibility | High | Open |
| NFR-004 | Reflexivity — this repo's own SPDD/REASONS status changes | This mission's fix changes this repo's OWN dogfood `.kittify/`'s `is_spdd_reasons_active` answer from `False` to `True` (per the Summary's live reproduction) the moment it merges to `main`. State explicitly: no charter.yaml/config.yaml schema or write-path change occurs (this is a pure read-path fix — confirmed by reading `write_compiled_charter`'s docstring and `sync.py`'s "pure staleness reporter" behavior), so **no migration is required** for this repo's own charter or any other on-disk charter. The behavioral consequence for THIS repo specifically: subsequent mission runs against this checkout will receive SPDD/REASONS bootstrap guidance and REASONS template blocks that are currently silently stripped — this is the fix working as intended, not a side effect to mitigate, but must be stated in the PR body so it is not mistaken for scope creep. | Compatibility | High | Open |
| NFR-005 | Test-run scope | Verify test-verified requirements (FR-002, FR-007, FR-008, FR-010) by running scoped to `tests/charter/` (`test_charter_context_spdd_reasons.py`, `test_activate_resolves_no_answers_edit.py`, `test_answers_inert_and_org_union.py`, plus the new parity test) and `tests/architectural/test_charter_offering_does_not_import_activation.py` and `test_no_dead_symbols.py`, not a full-repo `pytest` sweep. `main` carries a known-red baseline tracked as issue #3284 (per this repo's CLAUDE.md / charter Standing Order #9) — classify any red observed against that baseline before attributing it to this mission; do not open a new issue for pre-existing failures. | Process | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | C-004 layering is never violated | No code change under `src/charter/offering/` may import `charter.activation` in any form (absolute, relative, `from . import`) — this is the entire reason the fix takes the "caller-resolves, narrow-compat-read" shape (Decision Record 1) instead of importing `PackContext` directly. | Technical | High | Open |
| C-002 | No charter.yaml/config.yaml schema or write-path change | This mission is a pure read-path fix. No new field is added to `CharterYaml`, `GovernanceConfig`, or `config.yaml`'s schema; `write_compiled_charter`'s byte-preservation of the `governance:` section is not touched; `spec-kitty charter sync` remains a pure staleness reporter. Confirmed no migration is required (NFR-004). | Technical | High | Open |
| C-003 | Parity test is mandatory, not optional | FR-002's parity test against `PackContext.from_config()` is a required deliverable of this mission, not a nice-to-have — per the operator's explicit instruction, its absence would let the two implementations drift apart again silently, reproducing the exact defect class this mission exists to close. | Process | High | Open |
| C-004 | PR body must cite `Closes #3838` | Per the charter's Issue Closure Linkage requirement, the eventual PR body must carry `Closes #3838`. | Process | High | Open |
| C-005 | Pre-existing red baseline is not this mission's to fix | `main` carries known-red tests tracked as issue #3284. This mission does not attempt to fix them and does not open a new issue for them; any red observed during this mission's own test runs is classified against that baseline first. | Process | Medium | Open |
| C-006 | No relocation of `charter.offering.spdd_reasons` (Option B, out of scope) | The module boundary the `charter-code-topology` mission established is not reopened by this mission. `is_spdd_reasons_active`'s public import path (`charter.offering.spdd_reasons.is_spdd_reasons_active`, and the `charter.spdd_reasons` facade for `apply_spdd_blocks_for_project`) is unchanged. | Technical | Medium | Open |

### Key Entities

- **`activated_*` keys** (`.kittify/config.yaml` or, when a `charter:` pointer resolves, the
  pointed `charter.yaml`'s top level): the compiler's real, current, three-state activation
  authority. Existing concept (`PackContext`); not new. This mission does not add new keys.
- **`governance.charter.selected_*`** (`charter.yaml`'s authored `governance:` section):
  the interview/bootstrap-time authoring record. Existing concept, explicitly retired as an
  activation source by the compiler (per its own docstring) but still read for activation by
  `is_spdd_reasons_active` (the bug) and, partially, by `_load_action_doctrine_bundle`
  (Decision Record 2's fold-in). After this mission, no code path treats it as an activation
  source; it remains readable as a historical/authoring record.
- **`PackContext`** (`src/charter/activation/pack_context.py`, existing, unchanged by this
  mission): the frozen dataclass the parity test (FR-002) compares against.
- **`_ActionDoctrineBundle.roots`/directive-allowlist** (`action_doctrine_bundle.py`,
  existing dataclass, field semantics changed by FR-006 to source from `activated_*` instead
  of the stale `selected_*`-derived `doctrine_selection`).

## Non-Goals / Out of Scope

The following are explicitly OUT OF SCOPE for this mission:

- **Option B — relocating `is_spdd_reasons_active`/`charter.offering.spdd_reasons` into
  `charter.activation`.** Decision Record 1 chose Option A explicitly; the module boundary
  stays as-is. See C-006.
- **Any `charter.yaml`/`config.yaml` schema or write-path change**, including making
  `governance.charter.selected_*` auto-sync to `activated_*` on write. This mission changes
  only what is *read* for activation decisions, not what is written or how `write_compiled_charter`/
  `spec-kitty charter sync` behave. See C-002, NFR-004.
- **Fixing the pre-existing #3284 red baseline.** Not this mission's responsibility; classify,
  don't fix, don't re-file. See C-005.
- **SK-76-class URN-minting divergence** (ledger; a distinct defect in DRG fragment-id vs.
  body-id URN keying, unrelated to the `selected_*`/`activated_*` authority question this
  mission fixes). Checked `SPEC-KITTY-LEDGER.md` for an existing entry on this specific
  `selected_*`/`activated_*` split-brain class — none found; this mission does not contradict
  any ledger entry and may itself become the reference entry for the class after merge (a
  post-merge ledger sweep is `sk-review`'s responsibility, not this spec's).
- **Any new CLI command, flag, or user-facing surface.** This is a pure internal read-path
  correction; no new `spec-kitty` subcommand or flag is introduced.
- **A general audit of every other consumer of `governance.charter.selected_*` in the
  codebase beyond the two named in the issue and confirmed here** (`is_spdd_reasons_active`
  and `_load_action_doctrine_bundle`). `load_governance_config`/`DoctrineSelectionConfig`
  have other, non-activation-decision consumers (e.g. rendering the charter-level "Global
  Selections" block in `_render_selection_block`) that display the authored selection as
  authored — that is a legitimate, distinct use (showing what was selected, not gating what
  is active) and is not touched by this mission.

## Success Criteria *(mandatory)*

**Test-run scope note**: see NFR-005 — verify SC-001 through SC-005 scoped to `tests/charter/`
and the two named `tests/architectural/` files, not a full-repo sweep; classify any other red
against the #3284 baseline before attributing it to this mission.

### Measurable Outcomes

- **SC-001**: `is_spdd_reasons_active` run against this repo's own dogfood `.kittify/` (or an
  equivalent committed fixture reproducing its exact shape: `activated_*` non-empty,
  `governance.charter.selected_*` all `[]`) returns `True` — verified by a red-first test that
  fails on `main` and passes after the fix (User Story 1, Scenario 1). **Fails if** it still
  returns `False`.
- **SC-002**: The FR-002 parity test passes — `is_spdd_reasons_active` agrees with
  `PackContext.from_config()` across the full fixture matrix (three states × three kinds ×
  pointer-present/absent). **Fails if** any fixture disagrees, or if the test's fixture matrix
  does not actually cover all the named combinations.
- **SC-003**: The FR-007/FR-008 regression tests for `_load_action_doctrine_bundle` pass —
  a genuinely-`activated_*` directive absent from a stale non-empty `selected_directives` is
  delivered (SC-003a), and this repo's own dogfood-shape closure-widening roots are populated
  from `activated_*` rather than empty (SC-003b). **Fails if** either regresses to today's
  silent-drop/silent-starvation behavior.
- **SC-004**: `tests/architectural/test_charter_offering_does_not_import_activation.py` and
  `tests/architectural/test_no_dead_symbols.py` both pass against this mission's full diff.
  **Fails if** either fires.
- **SC-005**: `contracts/activation.md` and `contracts/charter-context.md` are updated to
  state the new source of truth — verified by review at PR time (not a test; per the
  established precedent for PR-body/doc-citation requirements, no red-first ATDD test should
  be manufactured for this under C-011, and the plan/tasks phase should not decompose it into
  a WP+test — a specific reviewer step at mission close owns this).
