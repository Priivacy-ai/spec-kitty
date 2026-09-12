---
work_package_id: WP05
title: Render emission and built-output verifier
dependencies: []
requirement_refs:
- FR-001
- FR-005
- FR-008
- FR-010
- FR-011
- FR-012
- NFR-001
- NFR-008
tracker_refs: []
planning_base_branch: feat/docs-seo-metadata-enforcement
merge_target_branch: feat/docs-seo-metadata-enforcement
branch_strategy: Planning artifacts for this mission were generated on feat/docs-seo-metadata-enforcement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-seo-metadata-enforcement unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
- T026
- T027
- T028
agent: "claude:opus-5:reviewer-renata:reviewer"
shell_pid: "89572"
history:
- at: '2026-08-05T19:58:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: scripts/docs/seo_verify.py
create_intent:
- scripts/docs/seo_verify.py
- tests/docs/test_seo_verify.py
execution_mode: code_change
model: claude-opus-5
owned_files:
- scripts/docs/seo_verify.py
- scripts/docs/seo_postprocess.py
- tests/docs/test_seo_verify.py
- .github/workflows/docs-pages.yml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Render emission and built-output verifier

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objective

Make the render actually emit a description tag, then add a verifier that proves the shipped HTML carries correct metadata.

This is the **only** layer that can catch a render-path defect. Source-level checks read frontmatter; they cannot observe that `seo_postprocess.py` reads a description and never writes one. That is today's state: 147 pages have correct-looking pipelines and zero `<meta name="description">` tags in the shipped HTML.

## Context

**Read before starting**: [`contracts/built-output-verifier.md`](../contracts/built-output-verifier.md) is the binding contract. [`data-model.md`](../data-model.md) defines `RenderedPage`, `AuditRecord`, rules V-06…V-10, and invariants I-06/I-08/I-09. [`research.md`](../research.md) R-005 and R-009 cover the two-layer rationale and the workflow ordering.

**The defect, precisely**: `seo_postprocess.py::seo_block()` emits `og:description`, `twitter:description`, and JSON-LD `description` — but never a `<meta name="description">`. `extract_description()` falls back to a boilerplate constant when none is found. So a page with no frontmatter `description` ships with: no description tag, and a boilerplate social description shared with 146 other pages. Confirmed live: an ADR page returns `grep -c 'name="description"'` → **0**.

**Dependency correction**: `plan.md` lists IC-03 as depending on IC-01. That is wrong on closer reading — contract C-B4 requires reuse of `seo_postprocess.should_index()`, which is render-side and already exists. The source-side resolver is not needed here. This WP has **no dependencies** and can start immediately.

**Existing workflow order in `docs-pages.yml`** (do not disturb):
```
docfx build → seo_postprocess.py → glossary_linker.py
  → redirect_stub_generator.py generate → redirect_stub_generator.py coverage
  → Setup Pages → upload-pages-artifact
```
The workflow's own comments explain that SEO and glossary injection run *before* stub generation specifically so stubs never receive them. Respect that.

## Subtasks

### T022 — Emit `<meta name="description">` from `seo_postprocess.py`

**Purpose**: Close the render-path defect at its source.

**Steps**:
1. In `seo_block()`, add the description meta tag to the emitted block:
   ```html
   <meta name="description" content="{escaped_desc}">
   ```
2. **Emit conditionally**: only when the page does not already carry a `<meta name="description">`. DocFX emits one when frontmatter supplies a `description`, and that is the author's intent — this addition is a backstop, not an override. Single canonical authority: the frontmatter wins.
   - `DESCRIPTION_RE` already exists in the module for detecting this. Reuse it.
3. Keep the boilerplate fallback **detectable**, not disguised. The source gate (WP06) will flag the fallback string as equivalent to missing. Do not make the backstop indistinguishable from an authored description — that would let it mask the defect it exists to reveal.
4. Preserve idempotence. The module already strips `SEO_BLOCK_RE` before re-inserting; verify a second run produces identical output.

**Files**: `scripts/docs/seo_postprocess.py`

**Validation**:
- [ ] A page with no description tag gains one
- [ ] A page with an existing DocFX description keeps it unchanged
- [ ] Two consecutive runs produce byte-identical output

### T023 — Create `seo_verify.py` with classification reusing `should_index`

**Purpose**: Establish the verifier skeleton and, critically, avoid creating a second definition of "indexable".

**Steps**:
1. Create `scripts/docs/seo_verify.py` with the CLI surface:
   ```
   python3 scripts/docs/seo_verify.py --site-dir docs/_site [--strict] [--json REPORT]
   ```
   Exit contract mirrors `description_length_check.py`: report-only exits 0; `--strict` exits non-zero on violations.
2. Implement classification per the state model, **importing `seo_postprocess.should_index()`**:
   | Class | Predicate |
   |---|---|
   | `ASSET` | path starts with `assets/` |
   | `TOC_PAGE` | basename is `toc.html` |
   | `REDIRECT_STUB` | markup contains `http-equiv="refresh"` |
   | `INDEXABLE` | none of the above, no existing `noindex` |
3. **Do not reimplement the predicate** (I-08). A second definition of indexability is exactly the two-authorities bug this mission exists to repair, one module over. If `should_index()` needs refactoring to be reusable, refactor it — do not copy it.
4. Define `RenderedPage` as a frozen dataclass per `data-model.md`.

**Files**: `scripts/docs/seo_verify.py` (new)

**Validation**:
- [ ] `should_index` imported, not duplicated
- [ ] All four classes produced correctly on fixtures
- [ ] `mypy` clean

### T024 — Implement rendered-page rules V-06 … V-10

**Purpose**: The actual assertions. Applied **only** to `INDEXABLE` pages.

**Steps**: Implement each rule, producing a `Violation` naming the page, the rule, and the observed value:

| Rule | Assertion |
|---|---|
| V-06 | `<meta name="description">` present — a rendered page with no description tag is a defect regardless of frontmatter |
| V-07 | Description is not the boilerplate fallback |
| V-08 | `<link rel="canonical">` equals this page's own canonical address |
| V-09 | `og:title` matches `<title>`; `og:description` matches the description |
| V-10 | Description unique across all indexable pages |

Also assert titles are non-empty and not the bare site default (NFR-001).

For V-10, a violation must name **both** colliding pages (I-07) — a uniqueness failure reporting one side is not actionable.

For V-07, import the boilerplate constant from `seo_postprocess`; do not retype the string.

**Files**: `scripts/docs/seo_verify.py`

**Validation**:
- [ ] Each rule produces a distinct, named violation reason
- [ ] Duplicate violations name the peer
- [ ] Rules skipped entirely for non-indexable classes
- [ ] Complexity of each function ≤ 15 — extract helpers rather than nesting

### T025 — Enforce stub, sitemap, and read-only invariants

**Purpose**: Protect behaviour that is currently correct (FR-012) and guarantee the verifier cannot launder its own result.

**Steps**:
1. Assert every `REDIRECT_STUB` carries `noindex`.
2. Assert no stub address appears in `sitemap.xml`.
3. Assert the sitemap's entry set equals the indexable page set.
4. **The verifier must never mutate `_site`.** Open files read-only. A tool that can fix what it checks can pass itself.
   - Add a test that hashes the input tree before and after a run and asserts equality.

**Files**: `scripts/docs/seo_verify.py`

**Validation**:
- [ ] Stub invariants asserted
- [ ] Sitemap set equality asserted
- [ ] Read-only proven by a before/after tree hash test

### T026 — Emit the audit record including the stale-URL finding

**Purpose**: Produce the reproducible evidence that lets issue #1652 be closed on evidence rather than assertion (FR-001, FR-010, FR-011).

**Steps**:
1. With `--json PATH`, write an `AuditRecord`: per-page classification, title, description, canonical, social metadata; the violation list; and counts per class.
2. **Deterministic output** (I-06): sort violations by path; two runs over identical input produce byte-identical files. This follows the inventory lockfile's established convention.
3. Include a findings section recording that the two addresses named in issue #1652 —
   `reference/slash-commands.html` and `how-to/install-spec-kitty.html` — are **pre-move addresses now served as redirect stubs**, and that the live pages at `api/slash-commands.html` and `guides/install-spec-kitty.html` carry correct metadata. This is the evidence for FR-011.

**Files**: `scripts/docs/seo_verify.py`

**Validation**:
- [ ] JSON report written and parseable
- [ ] Two runs byte-identical
- [ ] Stale-URL finding present with both old and current addresses

### T027 — Wire the verifier into `docs-pages.yml` as the last step

**Purpose**: Make the check blocking, in the one position where it observes the true final artifact.

**Steps**:
1. Insert a step running `python3 scripts/docs/seo_verify.py --site-dir docs/_site --strict`.
2. **Position: after `redirect_stub_generator.py coverage`, before `Setup Pages`/`Upload artifact`.**
   - After stub generation so the verifier sees stubs and can confirm they are correctly excluded.
   - Before upload so a metadata regression fails the build rather than reaching the deployed site.
   - Placing it earlier leaves stub regressions unobserved. This ordering is load-bearing.
3. Add a comment explaining *why* the position matters, matching the style of the existing ordering comments in that workflow.
4. Do not reorder or modify any existing step.

**Files**: `.github/workflows/docs-pages.yml`

**Validation**:
- [ ] Step is last before Setup Pages
- [ ] Runs with `--strict`
- [ ] Existing steps unmodified
- [ ] Positional rationale documented in a comment

### T028 — Write the verifier and post-processor test suite

**Purpose**: Prove every rule can go red. A gate that cannot fail is fake.

**Steps**: Create `tests/docs/test_seo_verify.py` using synthetic `_site` fixtures under `tmp_path` — **no DocFX build required**, so these stay in the fast tier.

| Test | Asserts |
|---|---|
| `test_missing_description_is_red` | Indexable page without the tag → violation (V-06) |
| `test_boilerplate_description_is_red` | Fallback string → violation (V-07) |
| `test_wrong_canonical_is_red` | Canonical pointing elsewhere → violation (V-08) |
| `test_og_mismatch_is_red` | `og:description` diverging → violation (V-09) |
| `test_duplicate_description_is_red` | Two indexable pages sharing a description → both flagged (V-10) |
| `test_duplicate_violation_names_peer` | Violation carries the colliding path (I-07) |
| `test_stub_is_not_indexable` | Refresh-stub markup classifies as `REDIRECT_STUB`, rules skipped |
| `test_stub_absent_from_sitemap` | No stub address in the sitemap |
| `test_verifier_does_not_mutate_site` | Input tree byte-identical after a run |
| `test_clean_site_is_green` | Compliant fixture → zero violations, exit 0 |
| `test_strict_exits_nonzero` | Exit contract |
| `test_report_is_deterministic` | Two runs byte-identical |
| `test_postprocess_emits_description` | Page with no description tag gains one (T022) |
| `test_postprocess_preserves_existing_description` | Existing description not overwritten (T022) |
| `test_postprocess_is_idempotent` | Two passes identical (T022) |

**Files**: `tests/docs/test_seo_verify.py` (new)

**Validation**:
- [ ] All fifteen tests present and passing
- [ ] Every red-path test verified to actually go red (invert the assertion once to confirm)
- [ ] No test requires a DocFX build

## Branch Strategy

- **Planning base branch**: `feat/docs-seo-metadata-enforcement`
- **Final merge target**: `feat/docs-seo-metadata-enforcement`
- Execution worktrees are allocated per computed lane from `lanes.json`. Consume the resolved path.
- This mission reaches `origin/main` only through a pull request.

## Definition of Done

- [ ] `seo_postprocess.py` emits a description tag when one is absent, preserves it when present, idempotent
- [ ] `seo_verify.py` classifies via imported `should_index`, never a second definition
- [ ] Rules V-06…V-10 implemented; duplicates name both peers
- [ ] Stub and sitemap invariants asserted; verifier proven read-only
- [ ] Audit record deterministic and includes the stale-URL finding
- [ ] Verifier wired last in `docs-pages.yml` with `--strict` and a positional comment
- [ ] Fifteen tests passing, all red-paths confirmed to go red
- [ ] Existing redirect-coverage and glossary-linker steps still green
- [ ] `ruff` and `mypy` clean, no new suppressions; complexity ≤ 15

## Risks

| Risk | Mitigation |
|---|---|
| Verifier placed before stub generation → stub regressions unobserved | T027 states the position and the reason; reviewer checks it explicitly |
| Reimplementing `should_index` creates a second authority | T023 requires import; reviewer greps for duplication |
| Unconditional description emission overwrites author intent | T022 emits only when absent; a test pins the preserve case |
| Post-processor double-injection breaks idempotence | Existing strip-then-insert cycle retained; explicit idempotence test |
| Boilerplate backstop masks the defect it reveals | T022 keeps the fallback detectable; WP06 flags it as missing |

## Reviewer Guidance

1. **Check the workflow step position first.** It must be after `redirect_stub_generator.py coverage` and before `Setup Pages`. Wrong position silently defeats the stub assertions.
2. **Grep `seo_verify.py` for a reimplemented indexability predicate.** If `should_index` is copied rather than imported, reject — that is the exact bug this mission repairs.
3. **Verify the read-only guarantee** by reading every file-open call in the verifier. Any write mode is a defect.
4. **Invert one red-path assertion** and confirm the test actually fails. Fifteen green tests prove nothing if none can go red.
5. **Confirm the description emission is conditional** — a page with an authored DocFX description must not be overwritten.
6. **Check determinism** by running the report twice and diffing.

## Activity Log

- 2026-08-05T20:18:30Z – claude:opus-5:python-pedro:implementer – shell_pid=55785 – Assigned agent via action command
- 2026-08-05T20:46:27Z – claude:opus-5:python-pedro:implementer – shell_pid=55785 – T022-T028 complete. seo_postprocess.py now emits <meta name="description"> CONDITIONALLY (only when find_description(markup) is None, after the SEO block is stripped) so DocFX frontmatter stays authoritative; fallback stays detectable so V-07 can flag it. New scripts/docs/seo_verify.py IMPORTS seo_postprocess.should_index (zero local definitions) and implements V-06..V-10 + NFR-001 titles + I-09 stub/sitemap invariants; strictly read-only (--json refused inside --site-dir). Deterministic AuditRecord with the #1652 stale-URL finding whose note reports only what was observed. Wired into docs-pages.yml AFTER 'Verify redirect coverage (NFR-002)' and BEFORE 'Setup Pages' with --strict; no existing step reordered. Fixed a latent C-B2 whitespace non-idempotence in HEAD_CLOSE_RE plus a re.sub backslash-escape hazard. 21 tests in tests/docs/test_seo_verify.py; all 18 red-paths confirmed to go red by neutralizing each production rule. tests/docs 660 passed. ruff exit 0, mypy exit 0.
- 2026-08-05T20:47:25Z – claude:opus-5:reviewer-renata:reviewer – shell_pid=74618 – Started review via action command
- 2026-08-05T20:58:41Z – user – shell_pid=74618 – Moved to planned
- 2026-08-05T20:59:22Z – claude:opus-5:python-pedro:implementer – shell_pid=76614 – Started implementation via action command
- 2026-08-06T00:54:54Z – claude:opus-5:python-pedro:implementer – shell_pid=76614 – Cycle 1 fix. R-1 closed: _replace_head_close now covered by two tests, one per corruption mode (\1 raises; C:\temp silently TABs via valid JSON escape). BOTH verified RED by reverting the callable sub to string form, then restored byte-identical. R-2 closed: _finding_note unexpected branch pinned. Also added og:title, absent-title, sitemap-orphan, non-indexable-label coverage. 33 tests in file; tests/docs/ 662 passed; ruff 0; mypy clean. Note: the implementation agent died on a network error mid-task; the orchestrator ran the inversion verification and completed the handoff.
- 2026-08-06T00:55:08Z – claude:opus-5:reviewer-renata:reviewer – shell_pid=89572 – Started review via action command
