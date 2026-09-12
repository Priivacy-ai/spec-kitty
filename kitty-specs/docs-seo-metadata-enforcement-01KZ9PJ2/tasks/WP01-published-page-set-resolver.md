---
work_package_id: WP01
title: Published-page-set resolver
dependencies: []
requirement_refs:
- FR-002
- FR-003
- FR-013
- NFR-005
tracker_refs: []
planning_base_branch: feat/docs-seo-metadata-enforcement
merge_target_branch: feat/docs-seo-metadata-enforcement
branch_strategy: Planning artifacts for this mission were generated on feat/docs-seo-metadata-enforcement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-seo-metadata-enforcement unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
agent: "claude:opus-5:reviewer-renata:reviewer"
shell_pid: "69267"
history:
- at: '2026-08-05T19:58:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: scripts/docs/_published_pages.py
create_intent:
- scripts/docs/_published_pages.py
- tests/docs/test_published_pages.py
execution_mode: code_change
model: claude-opus-5
owned_files:
- scripts/docs/_published_pages.py
- tests/docs/test_published_pages.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Published-page-set resolver

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objective

Make "which source pages are published" resolvable from **exactly one authority** — `docs/docfx.json` — so that a directory reorganisation can never again leave a quality gate guarding an empty tree.

This is the mission's root-cause fix. Today the question has two answers: `docs/docfx.json`, which the build follows, and a hardcoded glob list in `tests/docs/test_docs_seo.py`, which the gate follows. When `how-to/` → `guides/` and `reference/slash-commands` → `api/` moved, the build followed and the gate did not. The gate now resolves **16 of 674** pages and has been reporting green for the whole tree.

You are not fixing the glob list. You are removing the possibility of two lists.

## Context

**Read before starting**: [`contracts/published-page-set-resolver.md`](../contracts/published-page-set-resolver.md) is the binding contract for this WP. [`data-model.md`](../data-model.md) defines `PublishedPageSet`, `Exclusion`, and invariants I-01 through I-05. [`research.md`](../research.md) R-002 documents the measurement.

**Measured baseline** (confirm these before building on them — see T001):

| Quantity | Value |
|---|---|
| Pages published via `docfx.json` content globs | 674 |
| Pages the current gate resolves | 16 |
| Coverage | 2.4% |

**The `docfx.json` content globs** (the authority you are reading):

```
index.md, toc.yml, context/**.md, architecture/**.md, adr/**.md, plans/**.md,
api/**.md, configuration/**.md, integrations/**.md, security/**.md, guides/**.md,
development/**.md, operations/**.md, migrations/**.md, changelog/**.md,
release-goals/**.md, doctrine/**.md, core-concepts/**.md, reference/**.md, updates/**.md
```
with `"exclude": ["**/_*.md"]`.

## Subtasks

### T001 — Establish and record the green baseline

**Purpose**: Planning ran without a working Python environment (no `uv`, no `pytest` on any available interpreter), so the current green baseline was **never empirically confirmed**. Without it you cannot tell your red from pre-existing red.

**This is not optional and it comes first.**

**Steps**:
1. From the repo root:
   ```bash
   uv sync
   PYTHONPATH=. uv run python scripts/docs/related_validator.py --strict --repo-root .
   PYTHONPATH=. uv run python scripts/docs/description_length_check.py --strict --repo-root .
   PYTHONPATH=. uv run python scripts/docs/relative_link_fixer.py --check --repo-root .
   uv run python packs/built-in/assets/docs_structural_lint.py \
     --styleguide packs/built-in/styleguides/common-docs.styleguide.yaml
   PWHEADLESS=1 uv run pytest tests/docs/ -q
   ```
2. Record which of these are red **before** any edit, in the WP's notes.
3. Apply the repository's baseline-red policy: a failure is yours only if it is red on your branch **and** green on the merge base. Do not "fix" pre-existing known-P0 reds.

**Validation**:
- [ ] Baseline recorded in writing, including any pre-existing failures
- [ ] You can state which failures are not yours and why

### T002 — Define `PublishedPageSet` and `Exclusion` value objects

**Purpose**: Give the resolver a return type that carries its own provenance and its own exclusion rationale, so a consumer can explain *why* a page is absent.

**Steps**:
1. Create `scripts/docs/_published_pages.py`. The leading underscore matches the existing convention for shared internal helpers (`_inventory.py`, `_render.py`) and signals this is a library, not an entry point.
2. Define frozen dataclasses:
   ```python
   @dataclass(frozen=True)
   class Exclusion:
       pattern: str
       reason: str

   @dataclass(frozen=True)
   class PublishedPageSet:
       pages: frozenset[Path]
       source_globs: tuple[str, ...]
       exclusions: tuple[Exclusion, ...]
   ```
3. `source_globs` is retained purely for diagnostics — when the gate reports a coverage failure it must be able to say which globs produced the set.

**Files**: `scripts/docs/_published_pages.py` (new)

**Validation**:
- [ ] Both dataclasses frozen (they are values, not state)
- [ ] Type annotations complete; `mypy` clean

### T003 — Implement `resolve_published_pages` reading `docfx.json`

**Purpose**: Read the build's own declaration at call time, so the resolver cannot drift from the build.

**Steps**:
1. Signature:
   ```python
   def resolve_published_pages(
       *, docs_root: Path, docfx_config: Path | None = None,
   ) -> PublishedPageSet: ...
   ```
   `docfx_config` defaults to `docs_root / "docfx.json"`.
2. Parse `build.content[].files` for the glob patterns and `build.content[].exclude` for exclusions.
3. **Read at call time. Do not cache into a module constant.** A test in T006 proves the read is live by mutating a temp `docfx.json` and asserting the result changes.
4. Only `.md` entries are page candidates — `toc.yml` appears in the content list but is not a page.

**Files**: `scripts/docs/_published_pages.py`

**Validation**:
- [ ] Globs come from the parsed file, never a literal in this module
- [ ] `toc.yml` is not returned as a page
- [ ] Underscore-prefixed files excluded per `**/_*.md`

### T004 — Translate DocFX glob semantics with membership validation

**Purpose**: This is the highest-risk detail in the entire mission.

DocFX glob semantics are **not** Python `pathlib` semantics. DocFX's `context/**.md` matches `context/foo.md`; the naive translation `context/**/*.md` does **not**. Getting this wrong silently under-collects — which is precisely the bug you are fixing, wearing a new hat.

**Steps**:
1. Implement the translation. `<dir>/**.md` must match `.md` files at *every* depth under `<dir>`, including directly inside it.
2. **Do not accept reasoning about glob semantics as proof.** Validate empirically against known members.
3. Canary pages that MUST be in the resolved set:
   - `docs/api/slash-commands.md`
   - `docs/guides/install-spec-kitty.md`
   - `docs/adr/3.x/2026-07-08-1-mission-resolver-port.md`
   - `docs/index.md`
4. If your count lands far from 674, the translation is wrong. Debug the translation, do not lower the floor.

**Files**: `scripts/docs/_published_pages.py`

**Validation**:
- [ ] All four canary pages are members
- [ ] Resolved count within a sane tolerance of 674
- [ ] `context/foo.md`-shaped paths (file directly in a globbed dir) are matched

### T005 — Add fail-closed error paths, non-vacuity floor, enumerated exclusions

**Purpose**: Make a degraded resolution impossible. A silently-partial set is the defect under repair; there must be no code path that returns one.

**Steps**:
1. Raise, never degrade:
   | Condition | Raise |
   |---|---|
   | `docfx.json` missing | `FileNotFoundError` |
   | `docfx.json` unparseable | `ValueError` naming the parse failure |
   | Resolved set empty | `ValueError` (violates I-01) |
   | Resolved set below floor | `ValueError` naming observed **and** expected counts |
2. Add the floor:
   ```python
   MINIMUM_EXPECTED_PAGES: Final[int] = 500
   ```
   Chosen below the measured 674 so ordinary churn does not false-fail, and far above the broken gate's 16 so today's defect trips it immediately.

   > A **floor**, not an exact count. The repository already retired a hardcoded exact ADR census constant on the grounds that it "guards little and merely fails on every legitimate add/remove — pure future friction." A floor captures the real invariant (the set must not collapse) without that friction.
3. Enumerate exclusions with a reason each (FR-013, I-04/I-05):
   | Pattern | Reason |
   |---|---|
   | `archive/**` | Immutable legacy snapshot; not rewritten for search (C-005) |
   | `kitty-specs/**` | Generated mission-run pages; no human author for a description |
   An exclusion with an empty reason must be impossible — assert it.

**Files**: `scripts/docs/_published_pages.py`

**Validation**:
- [ ] Every failure path raises; none returns a partial set
- [ ] Floor violation message names both counts
- [ ] Every `Exclusion.reason` non-empty

### T006 — Write the resolver test suite including the regression proof

**Purpose**: Prove the resolver works and, critically, prove it would have caught *this specific bug*.

**Steps**: Create `tests/docs/test_published_pages.py` with markers `unit`/`fast`:

| Test | Asserts |
|---|---|
| `test_resolves_from_docfx_not_a_constant` | Mutating a temp `docfx.json` changes the result |
| `test_underscore_prefixed_pages_excluded` | `_draft.md` absent |
| `test_every_exclusion_carries_a_reason` | All reasons non-empty |
| `test_empty_resolution_raises` | Empty set raises, not returns |
| `test_below_floor_raises` | Under-collection raises, naming both counts |
| `test_missing_docfx_raises` | `FileNotFoundError` |
| `test_toc_yml_is_not_a_page` | `toc.yml` absent |
| `test_live_tree_membership` | All four canary pages present |
| `test_live_tree_count_is_realistic` | Live count ≥ floor, near 674 |
| `test_would_have_caught_the_original_regression` | **The one that matters** |

**The regression proof**, in detail: build a page set from the *retired pre-move glob list* — `["index.md", "tutorials/*.md", "how-to/*.md", "how-to/harnesses/*.md", "reference/*.md", "explanation/*.md", "recovery/*.md", "3x/**/*.md", "archive/**/*.md", "migration/**/*.md"]` — and assert it fails the floor. That list resolves 16 pages today. This test encodes the actual historical failure so a future reorganisation cannot reproduce it silently.

**Files**: `tests/docs/test_published_pages.py` (new)

**Validation**:
- [ ] All ten tests present and passing
- [ ] The regression proof genuinely fails against the retired list (verify by temporarily inverting the assertion)
- [ ] Suite runs well inside the 30-second budget

## Branch Strategy

- **Planning base branch**: `feat/docs-seo-metadata-enforcement`
- **Final merge target**: `feat/docs-seo-metadata-enforcement`
- Execution worktrees are allocated per computed lane from `lanes.json`. Do not construct worktree paths by hand — consume the path the resolver gives you.
- This mission reaches `origin/main` only through a pull request. Never `git push origin main`.

## Definition of Done

- [ ] Baseline recorded before any edit (T001)
- [ ] `scripts/docs/_published_pages.py` resolves from `docs/docfx.json` at call time
- [ ] All four canary pages are members; count near 674
- [ ] Every error path raises; no path returns a degraded set
- [ ] Floor constant present with a written rationale
- [ ] Every exclusion carries a non-empty reason
- [ ] Ten tests passing, including the regression proof
- [ ] `ruff` and `mypy` clean, no new suppressions
- [ ] Complexity of every function ≤ 15

## Risks

| Risk | Mitigation |
|---|---|
| DocFX vs `pathlib` glob semantics — silent under-collection | Empirical canary membership assertions; never trust reasoning about translation |
| Floor set too high, false-failing on legitimate page removal | 500 against a measured 674 leaves 174 pages of headroom |
| Resolver caches globs and re-creates the two-authorities bug | `test_resolves_from_docfx_not_a_constant` proves the read is live |

## Reviewer Guidance

Verify in this order:

1. **Is there exactly one authority?** Grep the module for any hardcoded glob list. If one exists, the WP has failed its purpose regardless of passing tests.
2. **Does the regression proof actually fail?** Temporarily invert its assertion and confirm it goes red. A regression proof that cannot fail is decoration.
3. **Can any code path return a partial set?** Read every `return` in the module. Each must be the fully-validated set.
4. **Are the canary assertions real page paths?** Confirm the four files exist on disk; a typo'd canary passes vacuously.
5. **Is the floor justified in a comment**, not just asserted?

## Activity Log

- 2026-08-05T20:17:32Z – claude:opus-5:python-pedro:implementer – shell_pid=55785 – Assigned agent via action command
- 2026-08-05T20:29:37Z – claude:opus-5:python-pedro:implementer – shell_pid=55785 – Resolver landed: scripts/docs/_published_pages.py reads docs/docfx.json at call time (no hardcoded glob list). Live tree resolves exactly 674 pages (matches the measured baseline); all four canaries are members: docs/api/slash-commands.md, docs/guides/install-spec-kitty.md, docs/adr/3.x/2026-07-08-1-mission-resolver-port.md, docs/index.md. Regression proof verified by inversion: the retired pre-move glob list resolves 2 pages (16 before the archive exclusion) and raises ValueError naming both counts against the floor of 500. Fail-closed: missing config -> FileNotFoundError, unparseable -> ValueError, empty -> ValueError (I-01), below floor -> ValueError naming observed and expected (I-02); no path returns a partial set. Exclusions enumerated with non-empty reasons enforced in Exclusion.__post_init__ (I-05). 10 tests in tests/docs/test_published_pages.py all pass (~0.2s of test time). ruff exit=0; mypy exit=0 per file. Note: running mypy on a scripts/docs + tests/docs pair in one invocation emits a pre-existing 'Source file found twice' module-resolution error, reproduced with the untouched description_length_check.py/test_description_length_gate.py pair -- not from this diff. Full tests/docs/ + terminology guard: 649 passed (baseline 639 + 10 new).
- 2026-08-05T20:30:26Z – claude:opus-5:reviewer-renata:reviewer – shell_pid=69267 – Started review via action command
- 2026-08-05T20:38:15Z – user – shell_pid=69267 – Review passed: single authority confirmed (no hardcoded published-glob list; docfx.json read at call time, no cached set; only literals are the two contract-mandated DEFAULT_EXCLUSIONS per C-R3). Reviewer independently re-resolved the live tree: 674 pages from 20 docfx globs, all four canaries exist on disk AND are members, zero archive/underscore survivors. Regression proof independently inverted by the reviewer and confirmed RED (ValueError: observed 2 page(s), expected at least 500, naming the retired globs); file restored byte-identical. Fail-closed audited across every return: public function has exactly one return, after _assert_non_vacuous; sole except re-raises as ValueError from exc; no swallow, no partial-set path. Exclusion reasons enforced at construction in __post_init__ (I-05), stronger than asserted. Floor carries written rationale incl. why-a-floor-not-a-census. C-R6 headroom: 0.011s per live resolution. 10/10 tests, ruff 0, mypy 0 per file, tests/docs+terminology 649 (639 baseline + 10), all four docs gates exit 0. Scope clean: only _published_pages.py + test_published_pages.py; WP06 files untouched. Both implementer claims verified sound: mypy dual-module error REPRODUCED on the untouched description_length_check/test_description_length_gate pair (scripts/ lacks __init__.py while scripts/docs/ has one - pre-existing repo config); omitting a minimum_pages override is correct, since such a parameter would be precisely the degraded-set code path the contract forbids. Pages render repo-relative as docs/... matching description_length_check._EXCLUDE_PREFIXES ('docs/adr/') for WP06 consumption.
