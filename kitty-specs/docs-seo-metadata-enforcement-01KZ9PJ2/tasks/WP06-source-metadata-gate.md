---
work_package_id: WP06
title: Source metadata gate hardening
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- FR-002
- FR-003
- FR-006
- FR-007
- NFR-002
- NFR-003
- NFR-004
- NFR-005
- NFR-006
- NFR-007
tracker_refs: []
planning_base_branch: feat/docs-seo-metadata-enforcement
merge_target_branch: feat/docs-seo-metadata-enforcement
branch_strategy: Planning artifacts for this mission were generated on feat/docs-seo-metadata-enforcement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-seo-metadata-enforcement unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
- T032
- T033
- T034
agent: "claude:opus-5:reviewer-renata:reviewer"
shell_pid: "78928"
history:
- at: '2026-08-05T19:58:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: scripts/docs/description_length_check.py
create_intent: []
execution_mode: code_change
model: claude-opus-5
owned_files:
- scripts/docs/description_length_check.py
- tests/docs/test_description_length_gate.py
- tests/docs/test_docs_seo.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Source metadata gate hardening

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objective

Make a missing, boilerplate, or duplicated description fail at PR time across the **whole** published tree instead of 2.4% of it.

This is the gate that stops the defect recurring. It runs in `docs-freshness.yml` without .NET, so it blocks before merge — which the built-output verifier (WP05) structurally cannot do.

## ⚠️ Dependency warning — read before starting

This WP **must not land before WP02, WP03, and WP04 have completed.**

T030 removes `docs/adr/` from the description gate's exclusion list. If the 147 ADR descriptions are not yet in place, that single change turns CI red for 147 files. The dependency is declared in frontmatter and is real, not advisory.

Verify before starting T030:
```bash
PYTHONPATH=. uv run python - <<'PY'
import re, pathlib
missing = []
for f in sorted(pathlib.Path("docs/adr").rglob("*.md")):
    t = f.read_text(encoding="utf-8")
    if not t.startswith("---"):
        missing.append(str(f)); continue
    if not re.search(r"^description:", t[:t.find("\n---", 3)], re.M):
        missing.append(str(f))
print("ADR pages still missing a description:", len(missing), "(must be 0)")
for m in missing[:10]: print(" ", m)
PY
```
If this prints anything other than 0, stop and wait for the ADR packages.

## Context

**Read before starting**: [`contracts/source-metadata-gate.md`](../contracts/source-metadata-gate.md) is the binding contract. [`research.md`](../research.md) R-002 and R-004 document the coverage measurement and the expired exemption rationale.

**The measured defect**: `tests/docs/test_docs_seo.py::_published_markdown_files` globs ten patterns describing the *pre-move* directory layout. Five of them match **nothing**. The gate resolves 16 of 674 pages and has been reporting green for the tree.

**Existing gate wiring** (unchanged by this WP): `docs-freshness.yml` already invokes `description_length_check.py --strict`. You are widening and strengthening what it checks, not changing how it runs.

## Subtasks

### T029 — Consume the resolver in `description_length_check.py`

**Purpose**: Stop the gate guessing which pages are published; make it ask the authority WP01 built.

**Steps**:
1. Replace the `docs_root.rglob("*.md")` walk in `validate_descriptions()` with a call to `resolve_published_pages()` from `scripts/docs/_published_pages.py`.
2. **Expect the checked count to change, possibly downward.** Pages under `docs/plans/`, `docs/templates/`, and other unpublished trees leave scope, because publication status is `docfx.json`'s decision, not this module's.
   - This reduction is **legitimate** and must not be confused with the silent under-collection the floor assertion guards against. The floor (T033) is what distinguishes them.
3. Keep the existing report shape (`LengthReport`, `LengthViolation`) so the CI invocation and its output format are unchanged.

**Files**: `scripts/docs/description_length_check.py`

**Validation**:
- [ ] Page set comes from the resolver, not a filesystem walk
- [ ] Report shape unchanged
- [ ] Checked count is in the hundreds, not 16

### T030 — Retire the ADR exclusion and correct its stale rationale

**Purpose**: Bring 147 pages into the gate — and leave an honest record of why the old exclusion existed.

**Steps**:
1. **Re-run the dependency check above.** Do not proceed until it prints 0.
2. Remove `docs/adr/` from:
   ```python
   _EXCLUDE_PREFIXES: Final[tuple[str, ...]] = ("docs/adr/",)
   ```
3. **Correct the comment; do not silently delete it** (DIRECTIVE_037). The current comment reads:
   > ADR bodies are byte-identical to their pre-move originals (C-002, enforced by `test_adr_content_invariance`) and carry only bare `status` frontmatter — by design they have no `description`.

   That justification **expired**. `tests/docs/test_adr_content_invariance.py`'s own docstring records: *"Retired earlier (2026-06-29): the byte-identity content-invariance proof … was a transitional gate for the move itself, self-invalidating once merged to main"* and *"With byte-invariance retired upstream (`ccd278061`)"*.

   Replace it with a note stating that the byte-invariance rationale was retired on 2026-06-29, that descriptions were backfilled by this mission, and that the surviving census gate asserts only a canonical `status` value and permits additional frontmatter keys. A future reader must learn the history, not find an unexplained deletion.
4. Scope discipline (DIRECTIVE_024, decision `01KZ9Q2DC9WX6GTJZ57GE0BZNM`): retire the exemption for **description only**. The structural-lint frontmatter contract exempts ADR bodies through a separate styleguide config — leave that alone. Do not pull 147 files into that contract's full field requirements.

**Files**: `scripts/docs/description_length_check.py`

**Validation**:
- [ ] Dependency check printed 0 before the edit
- [ ] `docs/adr/` no longer excluded
- [ ] Comment explains the expired rationale, not merely deleted
- [ ] Styleguide structural-lint config untouched

### T031 — Add boilerplate detection pinned to the render-side constant

**Purpose**: Stop fallback text masking an unwritten description (FR-006).

**Steps**:
1. Add a `boilerplate` violation reason, **distinct** from `missing`. The two call for different author actions: "you wrote nothing" versus "you inherited the default".
2. Define the known-fallback set:
   ```python
   BOILERPLATE_DESCRIPTIONS: Final[frozenset[str]] = frozenset({...})
   ```
3. **Pin it to the render-side constant.** Import the fallback from `seo_postprocess`, or add a test asserting the two are equal. Retyping the string means a future change to the fallback silently disarms this check — the same drift-between-two-copies failure the mission exists to fix.

**Files**: `scripts/docs/description_length_check.py`

**Validation**:
- [ ] `boilerplate` is a distinct reason from `missing`
- [ ] Constant pinned to `seo_postprocess`, not retyped
- [ ] A test proves the pinning

### T032 — Add duplicate detection that names the colliding peer

**Purpose**: Eliminate the specific defect under repair — 147 pages sharing one description (FR-007).

**Steps**:
1. After collecting all descriptions, group by exact value. Any group of size > 1 yields one violation per member.
2. Each violation **names its peers** (I-07). A uniqueness failure reporting only one side is not actionable — the author cannot tell what they collided with.
3. **Exact-match comparison.** Do not normalise case or whitespace: two descriptions differing only in case are still duplicates for search purposes, and exact matching keeps the rule explainable.
4. Keep output sorted by path for deterministic diffs.

**Files**: `scripts/docs/description_length_check.py`

**Validation**:
- [ ] Duplicates detected across the full published set
- [ ] Every duplicate violation names the peer path
- [ ] Output deterministic

### T033 — Add the non-vacuity coverage assertion

**Purpose**: The single assertion that makes this whole class of bug unrepresentable (FR-003, I-01/I-02).

**Steps**:
1. Before validating, assert the resolved page set is non-empty and at or above the floor.
2. **A gate that validates zero pages must fail, not pass.** That is precisely how the current defect stayed invisible.
3. On failure, the message names the observed count, the expected floor, and the globs that produced the set — enough for the reader to diagnose without instrumenting the code.

**Files**: `scripts/docs/description_length_check.py`

**Validation**:
- [ ] Empty set → failure, not a pass
- [ ] Below-floor → failure naming both counts and the globs
- [ ] The assertion runs before any per-page work

### T034 — Repoint `test_docs_seo.py` and extend the boundary proofs

**Purpose**: Delete the hardcoded glob list — the direct fix for the 2.4% defect — and prove the widened gate can fail (NFR-006).

**Steps**:
1. In `tests/docs/test_docs_seo.py`, delete `_published_markdown_files()`'s ten-pattern list and call the resolver instead.
2. Keep the per-file parametrised shape so a failure names the offending page. If scaling from 16 to ~674 parametrised cases breaks the 30-second budget (NFR-007), collapse to a single test that emits all violations at once — **do not relax the budget**.
3. Extend `tests/docs/test_description_length_gate.py`, whose docstring already states the principle: *"A length gate that cannot go RED is fake, so the Definition of Done is the boundary proof."* Add:

| Test | Asserts |
|---|---|
| `test_missing_description_is_red` | Absent → reason `missing` |
| `test_boilerplate_description_is_red` | Fallback string → reason `boilerplate` |
| `test_boilerplate_set_matches_seo_postprocess` | Constant pinned to render side |
| `test_duplicate_descriptions_are_red` | Two pages, same description → both flagged |
| `test_duplicate_violation_names_the_peer` | Violation carries the colliding path |
| `test_empty_page_set_is_red` | Zero pages → failure, not pass |
| `test_adr_pages_are_now_in_scope` | An ADR without a description is flagged |
| `test_live_tree_is_clean` | The real tree yields zero violations |

Preserve the existing 49/181-red and 50/180-green boundary proofs unchanged.

4. `test_live_tree_is_clean` is the acceptance test for the ADR packages. It will be red until they land — that is the intended red-first signal.

**Files**: `tests/docs/test_docs_seo.py`, `tests/docs/test_description_length_gate.py`

**Validation**:
- [ ] Hardcoded glob list deleted
- [ ] Gate covers ~674 pages
- [ ] Eight new boundary proofs, each verified to actually go red
- [ ] Existing boundary proofs preserved
- [ ] Suite within the 30-second budget

## Branch Strategy

- **Planning base branch**: `feat/docs-seo-metadata-enforcement`
- **Final merge target**: `feat/docs-seo-metadata-enforcement`
- This WP depends on WP01–WP04; `spec-kitty agent action implement WP06 --agent <name>` resolves the correct base. Do not branch manually.
- Execution worktrees are allocated per computed lane from `lanes.json`. Consume the resolved path.
- This mission reaches `origin/main` only through a pull request.

## Definition of Done

- [ ] Dependency check confirmed 0 undescribed ADR pages before T030
- [ ] Gate consumes the resolver; hardcoded glob list deleted
- [ ] `docs/adr/` exclusion removed; stale rationale corrected in place
- [ ] Boilerplate detection present and pinned to the render-side constant
- [ ] Duplicate detection names both peers
- [ ] Non-vacuity assertion fails on an empty set
- [ ] Six distinct red-proofs: missing, 49, 181, boilerplate, duplicate, empty set
- [ ] `test_live_tree_is_clean` green
- [ ] Suite within 30 seconds
- [ ] `ruff` and `mypy` clean, no new suppressions; complexity ≤ 15

## Risks

| Risk | Mitigation |
|---|---|
| **T030 lands before the ADR backfill → CI red for 147 files** | Hard dependency declared; explicit pre-flight check at the top of this prompt |
| Legitimate scope reduction mistaken for under-collection | T029 explains the distinction; the floor assertion is what separates them |
| Boilerplate constant retyped and later drifts | T031 requires pinning plus a test |
| 674 parametrised cases exceed the runtime budget | T034 offers the collapse-to-one-test escape; budget is not negotiable |
| Silently widening scope to the full structural-lint contract | T030 restricts to description only per DIRECTIVE_024 |

## Reviewer Guidance

1. **Verify the dependency actually held.** Check that WP02–WP04 are merged and that no ADR lacks a description. If T030 landed early, CI is red for 147 files and the WP must be reverted, not patched.
2. **Read the replacement comment on `_EXCLUDE_PREFIXES`.** A bare deletion is a DIRECTIVE_037 failure — the expired rationale must be explained, not erased.
3. **Confirm the hardcoded glob list is gone**, not merely updated. An updated list is the same bug with fresh paint.
4. **Invert each of the six red-proofs once** and confirm it fails. This is the WP whose entire purpose is being able to fail.
5. **Check the boilerplate constant is pinned**, not retyped.
6. **Confirm the structural-lint styleguide config is untouched** — scope was deliberately narrow.

## Activity Log

- 2026-08-05T20:39:42Z – claude:opus-5:python-pedro:implementer – shell_pid=72721 – Assigned agent via action command
- 2026-08-05T21:02:43Z – claude:opus-5:python-pedro:implementer – shell_pid=72721 – Gate widened 547 -> 674 pages: resolver consumed, docs/adr/ exclusion retired (rationale corrected in place), boilerplate detection pinned to seo_postprocess.extract_description, exact-match duplicate detection naming every peer, non-vacuity coverage assertion (exit 2). All 7 red-proofs verified red by inversion. BLOCKER for orchestrator: test_live_tree_is_clean is RED on 2 pre-existing byte-identical page pairs under docs/plans/{,initiatives/}next-mission-mappings/issue-{documentation,plan}-mission-next-mapping.md - unowned by any WP, NOT from the ADR backfill. Needs a content decision before the mission can merge.
- 2026-08-05T21:15:52Z – claude:opus-5:reviewer-renata:reviewer – shell_pid=78928 – Started review via action command
