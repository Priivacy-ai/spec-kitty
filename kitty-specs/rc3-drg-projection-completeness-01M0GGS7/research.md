# M2 — DRG projection completeness: research & grounding

**Purpose:** C-004 verify-first grounding of the operator-decided spec against
**current `main`** (spec authored 2026-08-20; main has moved since). Read-only
verification; no code changed. Findings drive the plan.

## Verdicts (file:line on current main)

### Emit seam — #3605 / #3604 (both real, net-new work)
- **`_reference_edge_kwargs(ref)`** — `src/doctrine/drg/migration/extractor.py:542`.
  Directive (`:768`), tactic top-level (`:802`), tactic step (`:823`), paradigm
  (`:875`) all route through it. **CONFIRMED.**
- **Procedures loop drops rationale** — `extractor.py:878–906`. The procedures
  branch mints `DRGEdge(source, target, relation)` **inline** (no `when`/`reason`).
  The `_reference_edge_kwargs` docstring (`:554–561`) **self-documents** this:
  *"Deliberately not yet wired through the procedure references branch: shipped
  procedure references DO author reason, which that branch has always dropped."*
  **CONFIRMED** — this is #3605.
- **No governance-profile.yaml projection exists** — `extract_action_edges`
  (`:1044–1092`) walks `actions/*/index.yaml` only. No module under
  `src/doctrine/drg/` or `src/charter/` emits `mission_type:<t> --scope--> gov`.
  **CONFIRMED net-new** — this is #3604.
- **`mission_type:<t>` node already exists** — `_discover_mission_type_nodes`
  (`:1177–1209`); `extract_mission_type_edges` (`:1289`) emits `--requires-->`
  edges only. #3604 adds `--scope-->` edges from the existing node. **CONFIRMED.**
- **Four `governance-profile.yaml` present** — documentation / plan / research /
  software-dev. `plan` authors **only** type-wide governance (1 directive
  `031-context-aware-design`, 9 tactics, 3 paradigms, 1 styleguide
  `planning-and-tracking`; empty action grains). **CONFIRMED** — this is why
  `mission_type:plan` cascades to empty today.

### `_DRG_NODE_KINDS` fold — #FR-006
- `src/charter/synthesizer/topic_resolver.py:37` — frozenset lacks
  `"mission_type"`. One-line fold. **CONFIRMED** (line exact).

### Delivery seam — #3488 (C-004: rc1 gaps **substantially already shipped**)
- **operating-procedures data-driven** — `_emit_operating_procedure_edges`
  `extractor.py:646–694` (**citation drift: spec said `:1024`; actual `:646`**);
  fail-**loud** at extraction (`ValueError` on unresolved built-in, `:689–694`).
  Fail-closed doctor check `_run_operating_procedures_check`
  `src/specify_cli/cli/commands/_doctrine_collect.py:427` (appends to
  `org_drg["errors"]`; records `operating_procedures_unresolved`). **CONFIRMED shipped.**
- **Step `description` renders** — `format_inline_named_body`
  `src/charter/context_renderers/profile_sections.py:142–177` (`:176` emits the
  indented description sub-line); used by tactic (`:611`) and procedure (`:399`).
  **CONFIRMED shipped.**
- **styleguide/toolguide pointer-only is a documented deliberate choice** —
  `_STYLEGUIDE_TOOLGUIDE_POINTER_ONLY_REASON` `profile_sections.py:98–102`
  (docstring: *"DELIBERATE NFR-001 token-budget decision … not a silent no-op"*).
  **CONFIRMED shipped.**

### The residual (what M2 actually closes on the delivery side)
**No delivery-path CODE gap survives on current main.** The residual is:
1. **Pointer-only contract is not pack-author-discoverable** — the reason constant
   is a code docstring, asserted by no test, referenced by no `docs/architecture/*`.
2. **`operating_procedures_unresolved` diagnostic is undocumented** — wired in code,
   absent from docs.
3. **No FR-008 anti-divergence structural test exists** (`grep` across
   `tests/`/`src/` = zero) — genuinely net-new.
So #3488's fold is: **surface** the pointer-only + unresolved-diagnostic contracts
(doc/schema) **and build** the FR-008 emit↔delivery bind — **not** a code re-fix.
This sharpens C-004: taking the rc1 report at face value would revert working code.

### Test anchors
- Mirror `test_directive_reference_reason_roundtrips`
  (`tests/doctrine/drg/migration/test_extractor.py:266`) and
  `test_tactic_reference_reason_roundtrips` (`:313`) as
  `test_procedure_reference_reason_roundtrips`: fixture with `references:` carrying
  `when`/`reason` → `extract_artifact_edges(doctrine_root)` → assert edge `.when`/
  `.reason`; a reference with no `reason` yields `reason is None`.
- **AC-003 target is a *named* test, not a generic set:**
  `test_cascade.py:449` `test_plan_cascade_is_empty_because_its_actions_scope_no_governance`
  asserts `result.activated == {}` for plan, with a rationale comment (`:452–459`).
  `_GOVERNANCE_BEARING_MISSION_TYPE_URNS` (`:406–410`) currently excludes plan.
  Landing #3604 **flips this test** — it must be **rewritten** (add plan to the set +
  assert non-empty cascade), not merely "added to a set."
- **Counts 31/23/160/0 are NOT pinned by any existing test** (live-verified accurate).
  M2 must **write new** count-pinned assertions, not update existing ones.

### Tooling
- `spec-kitty doctrine regenerate-graph` exists; supports `--check` (no-write
  freshness gate) and `--json`. The single golden re-ledger tool. **CONFIRMED.**

## Planning implications (deltas from the 2026-08-20 spec)
1. **Correct the `_emit_operating_procedure_edges` citation to `:646`** (spec said `:1024`).
2. **AC-003 = rewrite the named test at `test_cascade.py:449`**, revising its
   rationale comment — not a silent add-to-set.
3. **Write new count assertions** (documentation 31 / research 23 / software-dev 160 /
   plan 0→populated); none exist to update.
4. **FR-002 single-helper enforcement** needs a concrete mechanism (e.g.
   `inspect.getsource` + regex/AST over `extract_artifact_edges`), no existing
   structural-test pattern to mirror in this file.
5. **The #3488 fold is doc-surfacing + a net-new FR-008 test, not a code fix** —
   scope the delivery WP as documentation + structural test, and hold C-004
   (verify before touching shipped, correct delivery code).
6. **Golden re-ledger deferred:** the single `regenerate-graph` runs *after* both
   extractor edits land **and** after M3 (`#3617`) merges — rebase onto landed M3,
   then regenerate once, then confirm M3's cascade tests stay green against the
   re-ledgered goldens (landing-sequence note).
