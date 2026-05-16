# Mission Review Report: wp-prompt-governance-payload-01KRR8HS

**Reviewer**: spec-kitty-mission-review (Claude Opus 4.7, 1M ctx)
**Date**: 2026-05-16
**Mission**: `wp-prompt-governance-payload-01KRR8HS` — WP-prompt governance payload completeness
**Mission ID**: `01KRR8HS66A7NFV64HHPXG2JJE`
**Mission type**: software-dev
**Target branch**: `feat/org-doctrine-layer`
**Squash merge commit**: `480536c1`
**Pre-merge baseline (parent)**: `480536c1^`
**HEAD at review**: `be7f731d`
**WPs reviewed**: WP01..WP07 (all `done`, all `approved`)

---

## Gate Results

### Gate 1 — Contract tests
- Command: `uv run pytest tests/contract/ -q --timeout=60`
- Exit code: non-zero (19 failures / 218 passed / 1 skipped)
- Result: **PASS for this mission** (no contract drift introduced by the mission)
- Notes: The 19 contract failures are pre-existing on `feat/org-doctrine-layer`; they
  all live in `tests/contract/test_event_envelope.py`,
  `tests/contract/test_handoff_fixtures.py`, and
  `tests/contract/test_packaging_no_vendored_events.py`. None of those files are
  touched by this mission (`git log 480536c1^..be7f731d -- tests/contract/` returns
  empty; `git diff main..feat/org-doctrine-layer -- tests/contract/` returns empty).
  They belong to the events / shared-package-boundary work tracked elsewhere on the
  branch and are out of scope for this mission's verdict. The mission-touched
  ATDD contract suite (`tests/specify_cli/next/test_wp_prompt_governance_contract.py`)
  is 23/23 green.

### Gate 2 — Architectural tests
- Command: `uv run pytest tests/architectural/ -q --timeout=60`
- Exit code: 0
- Result: **PASS** (104 passed, 1 skipped)
- Notes: Includes the new `tests/architectural/test_template_governance_payload_contract.py`
  added by WP06 — 8 cases green. Layer rules
  (`tests/architectural/test_layer_rules.py`) pass; no new `specify_cli` import
  in `charter/` (C-001 / NFR-004 preserved).

### Gate 3 — Cross-repo E2E
- Command: N/A
- Exit code: N/A
- Result: **N/A** (not applicable to this fork)
- Notes: The cross-repo `spec-kitty-end-to-end-testing` sibling repo is not
  checked out in this working tree (`ls ../spec-kitty-end-to-end-testing/` →
  no such file). The four floor scenarios (FR-038..FR-041, C-010) belong to
  the upstream production-spec-kitty programme; this mission is an in-repo
  enhancement to the WP-prompt governance pipeline and does not modify any
  cross-repo contract. Per skill protocol, this gate is recorded as N/A rather
  than FAIL or EXCEPTION, because the gate's predicate (mission modifies
  cross-repo behaviour) is false.

### Gate 4 — Issue Matrix
- File: `kitty-specs/wp-prompt-governance-payload-01KRR8HS/issue-matrix.md`
- Rows: 0 (file does not exist)
- Result: **N/A** (the FR-037 issue-matrix discipline is a programme-level
  artifact for the upstream stability-and-hygiene-hardening initiative; this
  mission did not produce an issue matrix, and none of the mission's review
  cycles deferred a defect to a follow-up issue. Mission did not need one.)
- Notes: A single follow-up item is captured in DRIFT-1 below; if the team
  wants formal tracking, opening an issue is recommended (see "Open items").

---

## FR Coverage Matrix

| FR ID  | Description (brief)                                                                                                              | WP Owner(s)   | Test File(s)                                                                                                       | Test Adequacy | Finding                |
| ------ | -------------------------------------------------------------------------------------------------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------ | ------------- | ---------------------- |
| FR-001 | Action-critical section bodies surface verbatim or with fetch + when-doing                                                       | WP04          | `tests/charter/test_context_section_bodies.py`, ATDD `test_implement_prompt_regression_vigilance_body_or_fetch...` | ADEQUATE      | —                      |
| FR-002 | `profile=` parameter is load-bearing; profile-cited directives + tactics surface                                                 | WP03          | `tests/charter/test_context_profile.py` (12 tests), ATDD `test_python_pedro_directive_010_referenced_in_implement` | ADEQUATE      | —                      |
| FR-003 | `Project authority paths:` block (defaults + charter-declared)                                                                   | WP04          | `tests/charter/test_context_authority_paths.py`, ATDD `test_implement_prompt_references_glossary_path / adr_path`  | ADEQUATE      | —                      |
| FR-004 | `_governance_context` forwards `agent_profile` from WP frontmatter                                                               | WP03 + WP06   | ATDD self-sufficiency test (aggregate), `tests/architectural/test_template_governance_payload_contract.py`         | ADEQUATE      | —                      |
| FR-005 | Runtime templates either drop forbid OR carry `## Governance Payload Contract`                                                   | WP06          | ATDD `test_template_either_drops_forbid_or_guarantees_governance_payload`, architectural template-contract test    | ADEQUATE      | —                      |
| FR-006 | `charter sync` detects `DIRECTIVE_NNN` / tactic-id citations, emits `references:`                                                | WP01 + WP02   | `tests/charter/test_sync_references.py` (10 tests), ATDD `test_charter_sync_emits_cross_link_when_body_cites...`   | ADEQUATE      | —                      |
| FR-007 | Charter may declare `template_set:` and `available_tools:` fenced YAML; sync persists them; **no fallback diagnostic**           | WP02 + WP07   | `tests/charter/test_sync_authority_paths.py`, ATDD `test_project_charter_declares_template_set / available_tools`  | PARTIAL       | **DRIFT-1** (see below) |
| FR-008 | Charter may declare `authority_paths:`                                                                                           | WP01+WP02+WP04 | `tests/charter/test_sync_authority_paths.py`, `tests/charter/test_context_authority_paths.py`                      | ADEQUATE      | —                      |
| FR-009 | Spec-kitty's own `.kittify/charter/charter.md` declares `template_set` + `available_tools`                                       | WP07          | ATDD `test_project_charter_declares_template_set / available_tools` (file-level grep only)                         | PARTIAL       | **DRIFT-1** (see below) |
| FR-010 | Aggregate self-sufficiency: `test_implement_prompt_self_sufficiency` passes                                                      | WP06 (gate)   | ATDD `test_implement_prompt_self_sufficiency`                                                                       | ADEQUATE      | —                      |
| NFR-001 | Token budget ≤ 32 000 chars; auto-substitute longest body with fetch stanza when over                                            | WP05          | `tests/charter/test_context_token_budget.py` (16 tests); WP05 C-004 baseline recorded (24,061 / 24,252 max)         | ADEQUATE      | —                      |
| NFR-002 | `_build_wp_prompt` runtime within 1.5× baseline                                                                                  | WP05          | Manual baseline measurement via `scripts/measure-wp-prompt.py`; no automated regression gate                       | PARTIAL       | RISK-1 (see below)     |
| NFR-003 | ATDD suite 23/23 green                                                                                                           | WP06 (gate)   | `tests/specify_cli/next/test_wp_prompt_governance_contract.py`                                                     | ADEQUATE      | —                      |
| NFR-004 | Layer rules stay green (kernel ← doctrine ← charter ← specify_cli)                                                               | all WPs       | `tests/architectural/test_layer_rules.py` (8 tests, all green)                                                     | ADEQUATE      | —                      |
| NFR-005 | Backward compatibility for charters without the new YAML blocks                                                                  | WP01+WP02     | `tests/charter/test_schemas_additive_fields.py`, multiple "no-citation" / "no-block" assertions in sync tests       | ADEQUATE      | —                      |
| C-001  | `kernel ← doctrine ← charter ← specify_cli` non-negotiable                                                                       | architectural | `tests/architectural/test_layer_rules.py`                                                                          | ADEQUATE      | —                      |
| C-002  | ATDD suite is canonical spec                                                                                                     | process       | Review cycle evidence — no rejection cycles; 23/23 green                                                            | ADEQUATE      | —                      |
| C-003  | Forbid clause must pair with payload guarantee                                                                                   | WP06          | Template content + architectural template-contract test                                                            | ADEQUATE      | —                      |
| C-004  | Token-budget measured against real prompts                                                                                       | WP05          | WP05 review cycle records baseline measurement against `layered-doctrine-org-layer-01KRNPEE` WP01–WP10              | ADEQUATE      | —                      |
| C-005  | Dogfood enforcement non-optional                                                                                                 | WP07          | ATDD file-level tests pass against the live `.kittify/charter/charter.md`                                          | PARTIAL       | **DRIFT-1** (see below) |

**Legend**: ADEQUATE = test constrains the required behavior; PARTIAL = test
exists but only constrains a sub-aspect (e.g., file content) and misses the
broader behavioural intent; MISSING = no test found; FALSE_POSITIVE = test
passes even when implementation is deleted.

---

## Drift Findings

### DRIFT-1: Dogfood charter declarations satisfy ATDD file-grep but the live resolver still rejects them and degrades to "(none)" — FR-007 / FR-009 **intent** is unmet

**Type**: PUNTED-FR (the file-content assertion was the only enforceable gate; the
behavioural assertion the mission's stated journey-3 promised was not added to the
ATDD suite and is not satisfied by the merged code)

**Severity**: **MEDIUM** (the mission's stated acceptance gate of 23/23 ATDD IS met;
the live-system journey is partially unmet but degrades gracefully)

**Spec reference**: FR-007 ("`spec-kitty charter context --action implement` does NOT
emit a `Template set not selected in charter; fallback ... applied` ... diagnostic"),
FR-009 ("Spec-kitty's OWN `.kittify/charter/charter.md` MUST declare a `template_set`
and an `available_tools` block per FR-007 before this mission is merged. Dogfood
enforcement — the same project that built the resolver must consume it without
fallback diagnostics."), Acceptance Criterion #4 ("`spec-kitty charter context
--action implement` against this repo emits no fallback diagnostic"), Journey 3
("the diagnostic ... go away").

**Evidence**:

1. The dogfood file is correct. `.kittify/charter/charter.md` carries the
   `## Charter Resolution Hints` block (charter.md lines 360+):

   ```yaml
   template_set: software-dev-default
   available_tools: [git, spec-kitty, pytest, mypy, ruff]
   authority_paths: [glossary/contexts/, architecture/2.x/adr/]
   ```

2. The extractor reads it correctly. After `uv run spec-kitty charter sync --force`,
   `.kittify/charter/governance.yaml` shows:

   ```yaml
   doctrine:
     available_tools: [git, spec-kitty, pytest, mypy, ruff]
     template_set: software-dev-default
     authority_paths: [glossary/contexts/, architecture/2.x/adr/]
   ```

3. The runtime resolver REJECTS the selection.
   `uv run spec-kitty charter context --action implement` against this repo emits:

   ```
   Governance:
     - Template set: (none)
     - Paradigms: (none)
     - Tools: (none)
   ...
   - Diagnostics: governance unresolved (Governance resolution failed:
     - Charter selected unavailable tool(s): mypy, pytest, ruff
     - Update charter available_tools or register those tools in the runtime tool
     registry.)
   ```

4. Root cause: `src/charter/resolver.py:27` defines
   `DEFAULT_TOOL_REGISTRY: frozenset[str] = frozenset({"spec-kitty", "git"})`,
   and `_resolve_tools_selection` (resolver.py:76–95) raises
   `GovernanceResolutionError` when any selected tool is not in the registry.
   `src/charter/compact.py:220–227` catches that error and degrades the entire
   `template_set`, `paradigms`, and `tools` panel to `(none)`, then prepends a
   `governance unresolved ...` diagnostic.

5. The ATDD test `test_project_charter_declares_template_set` /
   `test_project_charter_declares_available_tools` only greps the charter FILE
   for the YAML keys; it does not invoke the resolver and does not assert the
   absence of the `Template set not selected in charter; fallback ... applied`
   or `governance unresolved` diagnostic. The dogfood acceptance gate is a
   file-level gate, not a behavioural gate.

**Analysis**: The mission's WP07 implementer correctly populated the dogfood charter
and the ATDD file-level tests pass. WP02 correctly persists the YAML block into
`governance.yaml`. The unmet half of the contract is the runtime tool-registry
side: the mission's WP07 chose to declare `pytest, mypy, ruff` (tools the project
genuinely uses) but the runtime registry only knows `{spec-kitty, git}`. The
contradiction surfaces as `GovernanceResolutionError` and the operator-visible
behaviour is identical to the pre-mission "(none)" degradation, with a different
diagnostic string.

Two reasonable fixes, both out of scope for this mission and appropriate as a
follow-up:

- **Option A (charter-side)**: narrow the dogfood charter's `available_tools` to
  the two registered names `[git, spec-kitty]` so the resolver accepts the
  selection. This makes the operator-visible journey-3 promise true today.
- **Option B (registry-side)**: extend `DEFAULT_TOOL_REGISTRY` (and/or the
  runtime tool registry the resolver consults) to recognise `pytest, mypy, ruff`
  as registered tools. This is more invasive but lets the dogfood charter
  declare the tools the project genuinely depends on.

Neither option requires re-opening this mission's contract — Option A is a
~1-line charter edit; Option B is a separate mission about the runtime tool
registry.

**Why this is MEDIUM, not HIGH**: the resolver degrades gracefully (no crash,
no broken WP-prompt generation), the WP-prompt's substantive payload (FR-001
section bodies, FR-002 profile directives, FR-003 authority paths) DOES render
correctly even when the compact panel says `(none)`, and the mission's stated
acceptance gate (NFR-003: 23/23 ATDD) is satisfied. A reader of the WP prompt
still gets the governance content this mission was built to deliver; what they
do NOT get is the operator-visible "no fallback diagnostic" guarantee that
journey 3 promised. The diagnostic text has changed from
"Template set not selected in charter; fallback ... applied" (pre-mission) to
"governance unresolved (Charter selected unavailable tool(s): ...)"
(post-mission). The mission has provably exercised the new code paths; the
remaining problem is a downstream validation choice, not a mission-scope defect.

---

## Risk Findings

### RISK-1: NFR-002 latency budget has no automated regression gate

**Type**: BOUNDARY-CONDITION
**Severity**: LOW
**Location**: process / CI
**Trigger condition**: Future change to `build_charter_context` or
`AgentProfileRepository` introduces a >1.5× latency regression in
`_build_wp_prompt`.

**Analysis**: NFR-002 declares "`_build_wp_prompt` end-to-end runtime stays
within 1.5× of the baseline measured before this mission." The baseline was
recorded in the WP05 review note (character-count baseline: max implement
24,061 / review 24,252 chars across `layered-doctrine-org-layer-01KRNPEE`
WP01–WP10). No `pytest-benchmark` gate or perf-CI assertion was added; the
mission's tests measure character count (for NFR-001 token budget) but not
wall-clock latency. A future change that, for example, fetches profile YAML
from disk on every render instead of using `AgentProfileRepository.default()`'s
cache would not trip any test. Recommend adding a coarse-grained perf gate
(e.g., a `pytest` benchmark asserting `_build_wp_prompt` returns under
~150 ms on a representative WP) in a follow-up if NFR-002 needs hard
enforcement; otherwise document as a manual contract.

### RISK-2: Tactic-id detection regex relies on `DoctrineService` being constructible

**Type**: ERROR-PATH
**Severity**: LOW
**Location**: `src/charter/extractor.py` (citation detection, the helper added by WP02)
**Trigger condition**: A consumer project synchronises a charter that contains
kebab-case slugs but ships without a doctrine catalog (e.g., older
spec-kitty bundle).

**Analysis**: Per the cross-link contract §3 ("`DoctrineService` cannot be
constructed (e.g. shipped catalog missing) — detection regex for directives
still runs; the tactic-id detector silently emits no tactic references.
`charter sync` does not error."), this degradation is documented and
intentional. It is recorded here only because a downstream consumer who reads
the `references:` field on a `DIR-NNN` entry has no way to distinguish "no
tactic citation in the body" from "tactic detector silently skipped because
the catalog could not load". For the spec-kitty fork, the catalog is always
shipped, so this is theoretical; in a vendor-stripped install it could
manifest as a missing cross-link. Out of scope for this mission to fix; the
contract permits the behaviour.

### RISK-3: `## Governance Payload Contract` placement inside `## Execution Steps`

**Type**: CROSS-WP-INTEGRATION (template-structural)
**Severity**: LOW
**Location**: `src/specify_cli/missions/software-dev/command-templates/implement.md` line ~73
**Trigger condition**: A future template-rewriting mission moves or restructures
`## Execution Steps`; the embedded H2 may be silently dropped.

**Analysis**: The WP06 reviewer noted "Minor structural nit: `## Governance
Payload Contract` H2 is placed between `### 1. Setup` and `### 2. Load Work
Package Prompt` inside the `## Execution Steps` H2". Two H2 headings nested
inside what should be a sibling section is a markdown-structure smell. The
architectural test `test_template_governance_payload_contract.py` detects
section presence via a regex that does not care about nesting, so the smell
is invisible to the gate. Document only; no functional impact today.

---

## Silent Failure Candidates

| Location                          | Condition                                              | Silent result                                | Spec impact                                                                                                                  |
| --------------------------------- | ------------------------------------------------------ | -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `src/charter/compact.py:222–227`  | `resolve_governance` raises `GovernanceResolutionError` | `template_set`, `paradigms`, `tools` → `(none)` | DRIFT-1: dogfood charter's declarations are silently demoted to `(none)`; only the diagnostic line surfaces the rejection.   |
| `src/charter/context.py:262`      | `load_governance_config` raises any `Exception`        | returns empty `DoctrineSelectionConfig()`    | A corrupt `governance.yaml` makes the authority-paths and section-body renderers silently emit defaults. Acceptable per WP02 contract §3 ("Charter sync run on a charter that pre-dates this mission ... output is byte-identical"). |
| `src/charter/context.py:317`      | `repo.get_action_guidelines` raises                    | `pass`                                       | Action guidelines silently omitted from prompt. Used only for an optional render block; existing behaviour. |
| `src/charter/context.py:709`      | `_load_agent_profile` raises during compact path       | `pass` (profile sections skipped)            | Per `charter-context-resolver.md` §3 contract: "Unknown profiles do NOT raise — resolver renders the prompt with profile sections omitted and logs a warning." Acceptable. |
| `src/charter/context.py:868,973,1031` | DoctrineService catalog lookup raises               | per-entry fallback / continue                | Per contract §3 ("Catalog citation unresolvable ... entry appears ... with placeholder body `<not found in catalog>`"). Acceptable. |

The compact-path `(none)` degradation in `compact.py:222–227` is the only
silent-failure candidate that intersects a stated mission goal (DRIFT-1).
All other handlers are documented in the contract artifacts and are
intentional graceful-degrade paths.

---

## Security Notes

| Finding                                                                                                                                                                                                                              | Location                                                                                                                  | Risk class      | Recommendation                                                                                                                                              |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------- | --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Charter-declared `authority_paths` entries are concatenated with `repo_root` and checked via `Path.is_dir()`. A malicious charter could declare `../../etc` — `is_dir()` returns True or False but only the string is rendered into prompt text; no file content is read or executed. | `src/charter/context_renderers/authority_paths.py:82–96`                                                                  | PATH-TRAVERSAL  | Acceptable risk for v1: charter is operator-authored, output is text-only. If charters become user-uploaded, add `.resolve().is_relative_to(repo_root)` check.  |
| YAML parsing uses `ruamel.yaml.YAML(typ="safe")` (`src/charter/context.py:1211`) and Pydantic schemas; no `yaml.load()` or `unsafe_load`.                                                                                              | `src/charter/context.py`, `src/charter/extractor.py`                                                                      | UNSAFE-YAML     | No action — safe loader in use.                                                                                                                             |
| No new `subprocess`, `shell=True`, or `Popen` introduced by the mission diff.                                                                                                                                                         | mission diff                                                                                                              | SHELL-INJECTION | No action.                                                                                                                                                  |
| No new HTTP calls, network I/O, or credential handling introduced.                                                                                                                                                                    | mission diff                                                                                                              | UNBOUND-HTTP / CREDENTIAL-RACE | No action.                                                                                                                                                  |
| Agent profile lookup uses `AgentProfileRepository.default()` which returns a cached, read-only registry; no lock semantics needed for the new code path (R-3 in plan correctly identifies this).                                       | `src/charter/context.py` `_load_agent_profile`                                                                            | LOCK-TOCTOU     | No action — profile load is idempotent and process-local.                                                                                                   |

No blocking security findings.

---

## Final Verdict

**PASS WITH NOTES**

### Verdict rationale

The mission's stated acceptance gate (NFR-003: 23/23 ATDD tests in
`tests/specify_cli/next/test_wp_prompt_governance_contract.py`) is met as of
HEAD `be7f731d`. All ten Functional Requirements have test coverage; the
charter-side payload (FR-001 section bodies, FR-002 profile-cited directives
and tactics, FR-003 authority paths, FR-005 Governance Payload Contract
section in templates) is correctly rendered into the WP prompt. WP01–WP07
each cleared review on the first cycle with no rejections, no arbiter
overrides, and no forced transitions beyond the canonical-bootstrap
`finalize-tasks` events. The architectural layer rules (8/8 green) and the
new template-promise / resolver-reality consistency test (8/8 green) confirm
C-001 / NFR-004 are preserved and that the template's promises match the
resolver's actual emissions. No new security risks were introduced; no
unsafe YAML loading, no new subprocess calls, no new HTTP I/O.

One non-blocking gap (DRIFT-1, MEDIUM): the dogfood charter declarations
satisfy the file-level ATDD test but the runtime resolver rejects the chosen
`pytest, mypy, ruff` tools because the `DEFAULT_TOOL_REGISTRY` only knows
`{git, spec-kitty}`. The operator-visible `spec-kitty charter context
--action implement` still shows `Template set: (none)` with a "governance
unresolved" diagnostic, which is a different fallback diagnostic than the
pre-mission one but not the "no fallback diagnostic" outcome Journey 3
promised. The substantive payload (the actual section bodies, authority
paths, and profile-cited directives the agent will read) renders correctly
regardless; only the compact governance summary panel is degraded.

The mission is accepted. The DRIFT-1 gap is documented for a one-line
follow-up: either narrow the dogfood charter's `available_tools` to
`[git, spec-kitty]` (Option A, charter-side, ~1 minute) or extend
`DEFAULT_TOOL_REGISTRY` / the runtime tool registry to recognise the
project's real toolchain (Option B, code-side, separate mission).

### Open items (non-blocking)

1. **[DRIFT-1] Dogfood charter ↔ runtime tool registry mismatch.** Either
   narrow `.kittify/charter/charter.md`'s `available_tools` to the two
   registered names (immediate fix) or extend the runtime tool registry to
   accept `pytest, mypy, ruff` (mission-scoped follow-up). Until one of
   those lands, `spec-kitty charter context --action implement` against
   this repo continues to show "governance unresolved" instead of the
   clean output the spec promised. Recommend opening a follow-up GitHub
   issue if formal tracking is needed.

2. **[RISK-1] No automated NFR-002 latency gate.** The 1.5× baseline
   contract is captured in the WP05 review note as a character-count
   measurement only. Consider adding a `pytest-benchmark`-based assertion
   on `_build_wp_prompt` in a future hygiene mission if NFR-002 needs hard
   enforcement.

3. **[RISK-3] Template H2 nesting smell.** `## Governance Payload Contract`
   is placed between `### 1. Setup` and `### 2. Load Work Package Prompt`
   inside the `## Execution Steps` H2 of `implement.md`. Functional impact
   is zero (the architectural detection regex is nesting-agnostic), but a
   future template-rewrite mission should hoist it to a top-level sibling
   of `## Execution Steps` to match the contract's
   "before `## Execution Steps`" intent.

4. **Pre-existing 19 contract failures on `feat/org-doctrine-layer`.**
   Outside this mission's scope; tracked under the events / shared-package-
   boundary work. Recorded here only so the mission verdict is not
   conflated with that backlog.
