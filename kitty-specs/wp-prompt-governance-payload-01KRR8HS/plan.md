# Implementation Plan: WP-Prompt Governance Payload Completeness

**Branch**: `feat/org-doctrine-layer` | **Date**: 2026-05-16 | **Spec**: [spec.md](spec.md)
**Mission**: `wp-prompt-governance-payload-01KRR8HS` | **Merge target**: `feat/org-doctrine-layer`

---

## Summary

The WP `implement` and `review` prompts already invoke the charter/doctrine pipeline at
the correct boundary (`_governance_context` is called from `_build_wp_prompt` at
`src/specify_cli/next/prompt_builder.py:147`), but the pipeline returns a degenerate
payload: section anchors without bodies, the charter-extracted `DIR-NNN` namespace
instead of the doctrine-catalog `DIRECTIVE_NNN` namespace, zero tactics, and no glossary
or ADR pointers. The runtime `implement.md` template at
`src/specify_cli/missions/software-dev/command-templates/implement.md:68-71` then
forbids the executing agent from looking elsewhere, closing the trap.

This mission makes the `profile=` parameter of `build_charter_context` load-bearing
(today: `_ = profile` at `src/charter/context.py:92`), wires the WP frontmatter's
`agent_profile:` through `_build_wp_prompt → _governance_context →
build_charter_context`, augments the bootstrap renderer to surface charter section
bodies (verbatim or fetch + when-doing) plus authority paths plus profile-cited
directives and tactics, teaches `charter sync` to preserve `DIRECTIVE_NNN` /
tactic-id citations as a structured `references:` cross-link, and amends the runtime
templates with a `## Governance Payload Contract` section that enumerates what the
prompt guarantees. Finally it updates spec-kitty's own
`.kittify/charter/charter.md` with the `template_set` / `available_tools` /
`authority_paths` declarations the resolver now reads.

The ATDD suite at `tests/specify_cli/next/test_wp_prompt_governance_contract.py`
(9 failing / 14 passing) is the acceptance gate; all 23 tests must pass at mission
completion.

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: existing — `ruamel.yaml`, `pydantic`, `rich`, `typer`,
`pytest`. No new runtime dependency is introduced.
**Storage**: filesystem only — `.kittify/charter/{charter.md, directives.yaml,
governance.yaml}`; agent-profile YAML under `src/doctrine/agent_profiles/built-in/`
or project overrides at `.kittify/doctrine/agent_profiles/`.
**Testing**: `pytest`, ATDD acceptance suite at
`tests/specify_cli/next/test_wp_prompt_governance_contract.py`; architectural
suite at `tests/architectural/test_layer_rules.py` (must stay green).
**Target Platform**: Linux, macOS, Windows (no platform-specific code).
**Performance Goals**: NFR-002 — `_build_wp_prompt` end-to-end runtime stays within
1.5× of pre-mission baseline. NFR-001 — augmented WP prompt ≤ 32 000 characters
total (proxy for ~8 000 tokens); larger payloads auto-substitute fetch commands
for the longest sections.
**Constraints**: C-001 — `kernel ← doctrine ← charter ← specify_cli` is
non-negotiable; charter MUST NOT import from `specify_cli`. Profile resolution lives
in `doctrine.agent_profiles.AgentProfileRepository`, which IS importable from
`charter` (doctrine is below charter), so `build_charter_context(profile=<id>)`
delegates profile loading to a `doctrine`-layer helper. C-002 — the ATDD tests
are the canonical spec; assertions are not adjusted to make implementation pass.

---

## Charter Check

**Charter present**: yes (`.kittify/charter/charter.md`)
**Template set**: not yet declared (the project charter lacks the YAML block this
mission will add per FR-009).
**Active directives**: DIR-001 … DIR-N (charter-extracted) — augmented with
catalog cross-links per FR-006.

| Gate | Status | Notes |
|---|---|---|
| Layer rule `kernel ← doctrine ← charter ← specify_cli` | Pass | New profile lookup lives in `doctrine.agent_profiles`; charter imports doctrine (already allowed). No `specify_cli` import added to charter. |
| Backward compatibility | Pass | NFR-005 — charters without the new YAML blocks behave exactly as today. |
| Test coverage | Pass | 23 ATDD tests are the gate; unit tests added for token-budget logic and citation regex. |
| No new runtime deps | Pass | Pure stdlib + existing dependencies. |
| Dogfood enforcement | Pass on mission completion | FR-009 / C-005 — spec-kitty's own charter updated as part of this mission. |

No charter violations.

---

## Architectural Design

### The C-001-clean profile-resolution path

The architectural pivot is that the resolver needs **agent-profile data** to satisfy
FR-002 (profile-cited directives in the WP prompt). The natural temptation is to have
the charter layer reach up into `specify_cli` to load profile YAML — that would
violate C-001 (ADR `2026-03-27-1`). It is unnecessary: `AgentProfileRepository` lives
at `src/doctrine/agent_profiles/repository.py`, and `doctrine` is **below** `charter`
in the layer order, so `charter` is allowed to import it.

Concrete chain:

```
specify_cli.next.prompt_builder._build_wp_prompt
  │ reads WP frontmatter agent_profile (already does)
  ▼
specify_cli.next.prompt_builder._governance_context(repo_root, action=..., profile=<id>)
  │ NEW: forwards profile=<id> to build_charter_context
  ▼
charter.context.build_charter_context(repo_root, action=..., profile=<id>)
  │ NEW: profile= becomes load-bearing
  │ NEW: imports doctrine.agent_profiles.AgentProfileRepository (allowed)
  │ NEW: walks profile.directive_references / tactic_references
  │ NEW: looks up bodies via DoctrineService (already used by bootstrap render)
  ▼
augmented CharterContextResult.text with profile-cited directives,
tactics, authority paths, and charter section bodies
```

No new `specify_cli` import is added to `charter`. The architectural test suite
(`tests/architectural/test_layer_rules.py`, 8 tests) remains green per NFR-004.

### Anatomy of the augmented `text` payload

The `CharterContextResult.text` returned to `_governance_context` becomes a
multi-section block:

```
Charter Context (Bootstrap):
  - Source: .kittify/charter/charter.md
  - This is the first load for this action. ...

Policy Summary:
  - ...

Project authority paths:
  - glossary/contexts/    (canonical terminology — when you encounter a domain
                          term in the diff, grep this directory)
  - architecture/2.x/adr/ (architectural intent — when you change a
                          structural boundary, read the relevant ADR)
  - <additional paths declared in charter authority_paths block>

Action-Critical Charter Sections (implement):
  ### Terminology Canon
  <body verbatim, when under budget>
  -- OR --
  Run: spec-kitty charter context --include section:terminology-canon
  When you rename or introduce a term in the diff, run this command and apply.

  ### Regression Vigilance
  <body verbatim, when under budget>
  -- OR --
  Run: spec-kitty charter context --include section:regression-vigilance
  When you perform a terminology cutover, run this and apply.

  ### Code Review Checklist
  <body verbatim or fetch + when-doing>

Profile-Cited Directives (python-pedro):
  - DIRECTIVE_010: Specification Fidelity Requirement
    Implementations must faithfully reflect design specifications without
    unauthorized deviations. (rationale from profile)
    -- OR --
    Run: spec-kitty charter context --include directive:DIRECTIVE_010
    When you implement code that satisfies a requirement, fetch and apply.
  - DIRECTIVE_024: Locality of Change ...
  - DIRECTIVE_025: Boy Scout Rule ...
  - DIRECTIVE_030: Test and Typecheck Quality Gate ...
  - DIRECTIVE_034: Test-First Development ...

Profile-Cited Tactics (python-pedro):
  - <tactic-id>: <title> — <rationale>
    -- OR --
    Run: spec-kitty charter context --include tactic:<id>
    When <tactic.when>, fetch and apply.

Action Doctrine (implement):
  Directives:
    - DIRECTIVE_NNN: ... (resolver-resolved set, may overlap profile)
  Tactics:
    - <id>: ...

Reference Docs:
  - ...
```

Every section follows the *verbatim OR (fetch command + when-doing rule)*
contract pinned by
`_contains_either_body_or_fetch_with_conditional` in the test file (lines 215-238).

### Component changes

| Module | Change |
|---|---|
| `src/charter/context.py` | Remove `_ = profile` at line 92; thread `profile=` into `_load_action_doctrine_bundle` and into a new `_render_profile_section` helper. Add `_render_authority_paths(repo_root, charter_config)`, `_render_critical_section_bodies(charter_content, action)`, `_render_profile_directives(profile, service)`, `_render_profile_tactics(profile, service)`. Extend `_render_bootstrap_text` to call all four. |
| `src/charter/context.py` (new helper) | `_load_agent_profile(profile_id)` — imports `doctrine.agent_profiles.AgentProfileRepository.default()`, returns the profile or `None`. Centralised so the import site is single. |
| `src/charter/context.py` (token budget) | New `_apply_token_budget(text, budget=32_000)` walks the rendered sections, identifies the longest body, replaces it with a `Run: …\nWhen …, run this and apply.` stanza, and emits a warning line `# Governance payload trimmed: <section> substituted with fetch command (budget=…).` Repeats until under budget; warns once if still over. |
| `src/charter/sync.py` | Augment `Extractor._extract_directives` (extractor.py:263) to scan each `numbered_items` body for `DIRECTIVE_\d{3}` and tactic-id slug regex; collect detected IDs into a new `references:` list on the emitted `Directive`. Update `charter.schemas.Directive` to carry an optional `references: list[str] = []` field. |
| `src/charter/sync.py` (resolver-input declarations) | Extend `Extractor._merge_doctrine_selection` to scan any section's `yaml_blocks` for top-level `template_set`, `available_tools`, and `authority_paths` keys. Already partially supported for `template_set` / `available_tools` via `_apply_selection_row`; add `authority_paths` handling and ensure it lands in `GovernanceConfig.doctrine` (new `authority_paths: list[str] = []` field). |
| `src/charter/schemas.py` | Add optional `references: list[str] = []` to `Directive`. Add optional `authority_paths: list[str] = []` to `DoctrineSelectionConfig`. Both default-empty so NFR-005 holds. |
| `src/specify_cli/next/prompt_builder.py` | In `_build_wp_prompt`, after `read_wp_frontmatter`, extract `wp_meta.agent_profile` (already in frontmatter). Pass it to `_governance_context(repo_root, action=action, profile=<id>)`. In `_governance_context`, forward `profile=` to `build_charter_context`. |
| `src/specify_cli/missions/software-dev/command-templates/implement.md` | Add new top-level section `## Governance Payload Contract` (before `## Execution Steps`) enumerating the guaranteed bodies and fetch-command stanzas. Forbid clause at lines 68-71 stays; the new section makes it honest. |
| `src/specify_cli/missions/software-dev/command-templates/review.md` | Same addition for the review prompt, framed for the reviewer's surfaces (profile-cited review directives e.g. DIRECTIVE_032, glossary pointer with "when you assess a diff that renames identifiers, …" conditional). |
| `.kittify/charter/charter.md` | Add a fenced YAML block declaring `template_set: software-dev-default`, `available_tools: [git, spec-kitty, pytest, mypy, ruff]`, and `authority_paths: [glossary/contexts/, architecture/2.x/adr/]`. Placement: under a new `## Charter Resolution Hints` heading near the end. |

### Token-budget mechanism (NFR-001)

Measure `len(text)` after rendering. Threshold `BUDGET = 32_000` characters
(~8 000 tokens, consistent with NFR-001). If exceeded:

1. Rank rendered sections by character length (longest first).
2. Pop the longest, replace its body with:
   ```
   Run: spec-kitty charter context --include <selector>
   When you <action-verb derived from section>, run this command and apply the returned rule.
   ```
3. Re-measure. Repeat until under budget or only one section remains.
4. If still over budget after all body bodies have been substituted, emit a single
   `# Governance payload: <N> sections substituted with fetch commands (budget=BUDGET).`
   line.

The threshold is measured against real WP prompts from
`layered-doctrine-org-layer-01KRNPEE` WP01–WP10 per C-004; a small CLI helper
(`scripts/measure-wp-prompt.py` or an existing dev tool) records baseline character
counts before mission start so NFR-002's 1.5× regression bound has a number to
compare against.

### Backward compatibility (NFR-005)

- A charter without the new fenced YAML block produces the same fallback diagnostic
  the system emits today (the resolver still calls
  `_render_compact_governance` with empty governance config).
- A charter whose directive bodies contain no `DIRECTIVE_NNN` or tactic-id citation
  produces a `directives.yaml` whose entries have empty (or missing) `references:`
  fields. Sync MUST NOT error.
- The `profile=` parameter still accepts `None`; when `None`, the renderer skips
  the "Profile-Cited Directives" and "Profile-Cited Tactics" sections entirely.
  Existing callers that omit `profile=` see byte-identical output to today.

### Test strategy

| Test category | Coverage | Location |
|---|---|---|
| ATDD acceptance | 23 tests at `tests/specify_cli/next/test_wp_prompt_governance_contract.py`. 9 currently red → green. 14 currently green → stay green. | existing file |
| Charter sync — references extraction | New unit tests: `DIRECTIVE_NNN` detection regex, tactic-id slug detection, multi-citation per body, no citation → no error. | `tests/charter/test_sync_references.py` (new) |
| Charter context — profile path | New unit tests: profile lookup, missing profile → graceful empty section, profile with empty `directive_references` → empty section without errors. | `tests/charter/test_context_profile.py` (new) |
| Charter context — authority paths | New unit tests: default paths surface when directories present; charter-declared paths additive; missing directories silently skipped. | `tests/charter/test_context_authority_paths.py` (new) |
| Token budget | New unit tests: under-budget → unchanged; over-budget → longest section substituted; severely over → all bodies substituted; warning line emitted. | `tests/charter/test_context_token_budget.py` (new) |
| Architectural | `tests/architectural/test_layer_rules.py` (8 tests) — MUST stay green. | existing file |
| Prompt builder | Existing tests under `tests/specify_cli/next/` — MUST stay green. | existing files |

### Risk register

| ID | Risk | Mitigation |
|---|---|---|
| R-1 | Over-eager body inlining bloats prompts past the 32 k budget on real missions. | Token-budget mechanism is part of the same mission; measured against `layered-doctrine-org-layer-01KRNPEE` WPs (C-004) before mission completion. |
| R-2 | Catalog-citation regex (`DIRECTIVE_\d{3}` / tactic-id) emits false positives on a directive body that mentions IDs incidentally (e.g. an example). | The regex is intentionally permissive; false positives generate extra `references:` entries that the resolver harmlessly surfaces. The cost is a slightly bloated prompt that the token-budget mechanism trims. |
| R-3 | Profile lookup races during concurrent WP claims (multiple agents loading the same `python-pedro` profile). | `AgentProfileRepository` is read-only after construction; load is idempotent and process-local. No locking needed. |
| R-4 | `build_charter_context(profile=...)` callers in tests pass arbitrary strings; profile lookup raises. | `_load_agent_profile` returns `None` on miss; renderer skips profile sections; no exception propagates. Logged as a warning. |
| R-5 | The runtime template's `## Governance Payload Contract` section drifts from what the resolver actually emits. | A new architectural test (`tests/architectural/test_template_governance_payload_contract.py`) parses the template section and the resolver output and asserts every guaranteed surface is present. |
| R-6 | Layer-rule regression — accidental `from specify_cli` import in `charter/context.py`. | NFR-004 — `tests/architectural/test_layer_rules.py` is run in CI on every WP; any violation surfaces immediately. |
| R-7 | NFR-002 latency budget exceeded because profile lookup + bigger payload render are slow. | The `AgentProfileRepository.default()` already caches; the new render helpers are O(n) over a handful of IDs. Baseline measurement (C-004) is the contract; regression > 1.5× is treated as a defect. |

---

## Phasing

The mission decomposes into seven sequenced phases, each phase mapping to one
work package. The split keeps each WP narrow enough for a single agent to finish
in one cycle and follows the dependency order the data needs.

| Phase | WP | Scope | Depends on | Acceptance |
|---|---|---|---|---|
| 1 | WP01 — Schema extensions | Extend `Directive` with optional `references: list[str]`; extend `DoctrineSelectionConfig` with optional `authority_paths: list[str]`. Pure schema change; zero behavioural impact. Tests: schema round-trip; backward-compat with existing YAML. | — | All existing schema tests green; new schema tests green. |
| 2 | WP02 — Charter sync references + authority_paths extraction | Extend `Extractor._extract_directives` to detect `DIRECTIVE_\d{3}` / tactic-id citations and emit `references:` field. Extend `_merge_doctrine_selection` to read `authority_paths:` from fenced YAML blocks. Tests: `test_charter_sync_emits_cross_link_when_body_cites_catalog_id` (failing → green). | WP01 | ATDD test 6 (Contract 7) green; `charter sync` unit tests green; existing sync tests green. |
| 3 | WP03 — `build_charter_context(profile=)` becomes load-bearing | Replace `_ = profile` with profile lookup via `doctrine.agent_profiles.AgentProfileRepository`. Add `_render_profile_directives` and `_render_profile_tactics`. Tests: `test_implement_action_context_includes_profile_directive_references_when_profile_known` and the four `TestProfileDirectivesSurfacedInWpPrompt` tests that today pass only by fixture-charter coincidence (test 2 explicitly fails — `test_python_pedro_directive_010_referenced_in_implement_prompt`). | WP01 | ATDD test 2 green; layer-rule tests still green; new unit tests green. |
| 4 | WP04 — Authority paths + charter section bodies in bootstrap render | Add `_render_authority_paths` (defaults + charter-declared); add `_render_critical_section_bodies` for the action-critical sections (Terminology Canon, Code Review Checklist, Regression Vigilance, +mission-configurable). Tests: tests 1, 3, 4 (Regression Vigilance body, glossary pointer, ADR pointer). | WP02, WP03 | ATDD tests 1, 3, 4 green; authority-path and section-body unit tests green. |
| 5 | WP05 — Token-budget mechanism | Implement `_apply_token_budget` with substitution rule. Measure baseline on `layered-doctrine-org-layer-01KRNPEE` WP prompts (C-004). | WP04 | Token-budget unit tests green; measured baseline recorded in WP notes; aggregate ATDD `test_implement_prompt_self_sufficiency` green (test 7). |
| 6 | WP06 — Prompt builder wiring + template Governance Payload Contract sections | In `_build_wp_prompt` extract `agent_profile` from WP frontmatter and forward through `_governance_context` to `build_charter_context`. Add `## Governance Payload Contract` section to `implement.md` and `review.md` templates. Tests: test 5 (`TestImplementTemplateForbidClauseIsHonest`); also the new architectural template-contract test. | WP05 | ATDD test 5 green; all 23 ATDD tests now green; architectural template-contract test green. |
| 7 | WP07 — Dogfood: spec-kitty charter declares resolver inputs | Add the `template_set`, `available_tools`, and `authority_paths` block to `.kittify/charter/charter.md`. Re-run `spec-kitty charter sync`; verify no fallback diagnostic. | WP02 (sync must read the block) | ATDD tests 8, 9 green; `spec-kitty charter context --action implement` produces no `Template set not selected in charter; fallback ... applied` line. |

WP07 is decoupled from WP06 in the dependency graph and can run in parallel with
WP06 once WP02 lands. All other WPs are strictly sequential.

---

## References

- `tests/specify_cli/next/test_wp_prompt_governance_contract.py` — 23 ATDD tests (the executable spec).
- `docs/development/wp-prompt-governance-atdd-findings.md` — per-test failure-to-FR mapping.
- `docs/development/org-doctrine-layer-architecture-review.md` — root-cause analysis.
- `src/charter/context.py:70-92` — `build_charter_context` signature with the discarded `profile=` parameter.
- `src/charter/context.py:282-332` — `_render_bootstrap_text` that needs augmentation.
- `src/charter/sync.py:128-200` — `sync()` orchestration.
- `src/charter/extractor.py:263-299` — `_extract_directives` (gains `references:` detection).
- `src/charter/extractor.py:198-261` — `_merge_doctrine_selection` / `_apply_selection_row` (gains `authority_paths` handling).
- `src/specify_cli/next/prompt_builder.py:110-148` — `_build_wp_prompt`.
- `src/specify_cli/next/prompt_builder.py:265-280` — `_governance_context`.
- `src/specify_cli/missions/software-dev/command-templates/implement.md:68-71` — forbid clause to be paired with payload contract.
- `src/doctrine/agent_profiles/repository.py` — `AgentProfileRepository.default()`.
- `src/doctrine/agent_profiles/profile.py:240-241` — `directive_references` / `tactic_references`.
- `.kittify/charter/charter.md` — project charter requiring FR-009 update.
- `architecture/2.x/adr/2026-03-27-1-pytestarch-architectural-dependency-testing.md` — C-001 layer rule.
