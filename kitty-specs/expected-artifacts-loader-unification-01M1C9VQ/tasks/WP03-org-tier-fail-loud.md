---
work_package_id: WP03
title: Org-Tier Fail-Loud + Unreadable Widening
dependencies:
- WP01
requirement_refs:
- FR-007
- FR-008
- FR-012
- NFR-005
planning_base_branch: fix/expected-artifacts-loader-unification
merge_target_branch: fix/expected-artifacts-loader-unification
branch_strategy: Planning artifacts for this mission were generated on fix/expected-artifacts-loader-unification. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/expected-artifacts-loader-unification unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
phase: Phase 2 - Behavioral
history:
- timestamp: '2026-08-31T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/charter/activation/org_expected_artifacts.py
create_intent:
- tests/charter/activation/test_org_expected_artifacts.py
execution_mode: code_change
mission_id: 01M1C9VQZ28CFRW741WRADS6SZ
owned_files:
- src/charter/activation/org_expected_artifacts.py
- src/charter/offering/missions/repository.py
- tests/charter/activation/test_org_expected_artifacts.py
- tests/doctrine/missions/test_repository.py
tags: []
tracker_refs: []
wp_code: WP03
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

---

## Objective

Close the #3412 behavioral gap at its source readers: a **present-but-broken** org
`expected-artifacts.yaml` must raise `MalformedManifestError` instead of warning
and degrading to `None`, and the same fail-loud treatment must be symmetric across
BOTH tiers for the **present-but-unreadable** (`OSError`/`UnicodeDecodeError`)
case (FR-007, FR-012). This is the red-first WP: two genuinely-RED-on-`upstream/main`
regression scenarios drive the implementation (C-004, D8). Genuine absence still
returns `None` — corrupt and absent stay DISTINCT (Invariant I1).

## Context & Constraints

- **Org reader today swallows.** `org_expected_artifacts._read_yaml_mapping`
  (`src/charter/activation/org_expected_artifacts.py:95-118`) catches
  `(OSError, UnicodeDecodeError, YAMLError)` at `:109` and warns → returns `None`
  for a PRESENT file — the #3412 launder origin.
- **Built-in reader is asymmetric.** `MissionTemplateRepository.get_expected_artifacts`
  (`src/charter/offering/missions/repository.py:385`) already raises
  `MalformedManifestError` on `YAMLError` (`:411-412`, shipped in `1763bf2ae3`)
  but still swallows `(OSError, UnicodeDecodeError)` → `None` (`:413-414`). FR-012
  widens that swallow to fail loud too.
- **Sibling-error model.** Use `MalformedManifestError` (charter,
  `repository.py:38`) for parse-fault / non-mapping / unreadable-present on BOTH
  tiers. NEVER route these onto `ManifestSchemaError` (that is the schema/`extra=forbid`
  sibling, and its message says "schema-invalid").
- **Distinctness invariant (I1).** `not path.is_file()` (genuine absence) still
  returns `None`. Only a PRESENT file that fails to parse / is non-mapping /
  unreadable raises.
- **NFR-004:** reuse the single existing file read — add no extra I/O per load.
- **NFR-005 / I2:** `str(MalformedManifestError)` must name the source file (or a
  descriptive org-tier origin) and the underlying cause, without needing exception
  notes.
- **Red-first hygiene (C-004/D8):** T010 and T012 are `@pytest.mark.regression`,
  issue-pinned #3412, and must be verified RED on `upstream/main` through the
  pre-existing entry point BEFORE the fix. T014 distinctness tests are
  characterization.

## Subtasks & Detailed Guidance

### T010 — [RED] Regression: broken + non-mapping ORG manifest raises at the reader

**Purpose.** Pin the org-tier fail-loud gap with TWO genuinely-red scenarios
(US1-AC1 broken-YAML and US1-AC5 non-mapping) — both warn→`None` on main today.

**Steps.**
1. Author a test that points at an org root whose `expected-artifacts.yaml`
   contains a REAL YAML-syntax error — an unterminated quote or bad indentation,
   NOT a typo'd key (a typo'd key is a schema fault, not a parse fault).
2. Add a SECOND regression assertion (US1-AC5): a PRESENT org
   `expected-artifacts.yaml` that parses to a **non-mapping** (a scalar or a
   sequence where a mapping is required) also raises `MalformedManifestError` —
   this is likewise RED on main (`_read_yaml_mapping` warns→`None` for a
   non-mapping present file).
3. Drive both through the pre-existing entry point (`resolve_org_expected_artifacts`
   → `_read_yaml_mapping`). Assert each raises `MalformedManifestError` naming the
   file + parse/shape failure.
4. Mark `@pytest.mark.regression`; reference #3412 in the test docstring.
5. **Verify RED on `upstream/main`** for BOTH cases (today `_read_yaml_mapping`
   warns → `None`).

**Files.** `tests/charter/activation/test_org_expected_artifacts.py` (new).

**Validation.** RED on base, GREEN after T011. Docstring cites #3412.

### T011 — Implement org-tier fail-loud (FR-007)

**Purpose.** Make the org reader raise on a present-but-broken file.

**Steps.**
1. In `_read_yaml_mapping` (`org_expected_artifacts.py:95-118`), for a PRESENT
   file (`path.is_file()` is true), raise `MalformedManifestError(path, exc)` on
   `YAMLError` and on a non-mapping parse result — do not warn→None.
2. Keep genuine absence: `if not path.is_file(): return None` (FR-007, I1).
3. Reuse the existing single read (NFR-004) — do not re-open the file.
4. Update the `resolve_org_expected_artifacts` docstring to the shipped semantics.

**Files.** `src/charter/activation/org_expected_artifacts.py`.

**Validation.** T010 goes green; absence path still returns `None`.

### T012 — [RED] Regression: present-but-UNREADABLE built-in manifest raises (FR-012)

**Purpose.** Pin the unreadable-present gap on the built-in tier.

**Steps.**
1. Author a test where an EXISTING built-in manifest raises `OSError` or
   `UnicodeDecodeError` on read, asserting `MalformedManifestError`. The real
   `packs/built-in` tree is read-only, so use a concrete injection: **monkeypatch
   `pathlib.Path.read_text` to raise `OSError`/`UnicodeDecodeError` for the target
   manifest path** (pass through for all other paths). (Alternative if you prefer a
   filesystem fixture: write undecodable bytes — e.g. a lone `b"\xff\xfe"` — into a
   temp repo built-in tree and point the repository at it. Pick one; monkeypatch is
   the lighter default.)
2. Drive through the pre-existing entry point
   (`MissionTemplateRepository.get_expected_artifacts`).
3. Mark `@pytest.mark.regression`, reference #3412 (unreadable slice).
4. **Verify RED on `upstream/main`** (today `repository.py:413-414` swallows to
   `None`).

**Files.** `tests/doctrine/missions/test_repository.py`.

**Validation.** RED on base, GREEN after T013.

### T013 — Implement FR-012 on BOTH tiers

**Purpose.** Widen present-but-unreadable to fail loud symmetrically.

**Steps.**
1. Built-in: in `get_expected_artifacts` (`repository.py:407-414`), for a PRESENT
   file change `except (OSError, UnicodeDecodeError): return None` to raise
   `MalformedManifestError(path, exc)`. Keep `if path is None: return None` (genuine
   absence, `:405-406`).
2. Org: ensure `_read_yaml_mapping` also raises `MalformedManifestError` on
   `OSError`/`UnicodeDecodeError` for a present file (fold into T011's branch).
3. Both tiers: genuine absence still returns `None`.

**Files.** `src/charter/offering/missions/repository.py`,
`src/charter/activation/org_expected_artifacts.py`.

**Validation.** T012 green; built-in and org readers now agree; the shipped
YAML-syntax case (`1763bf2ae3`) is not regressed.

### T014 — After-fix distinctness + C-006 acceptance

**Purpose.** Prove absent-vs-malformed stay distinct on each tier after the fix,
that error text is operator-actionable (NFR-005), and cover the C-006 edge case
(the promised acceptance scenario for a corrupt org override on a REGISTERED
built-in family). Note: the non-mapping case is NOT characterized here — it is a
RED regression pinned in T010.

**Steps.**
1. Add after-fix distinctness tests on each tier: a malformed present file ⇒
   raises `MalformedManifestError`; a genuinely absent file ⇒ returns `None`. These
   are characterization (green-stays-green post-fix), NOT `@regression`.
2. Assert `str(MalformedManifestError)` names the file + cause (NFR-005 / I2).
3. Note in a docstring the symmetry with the built-in `YAMLError` case already
   shipped in `1763bf2ae3`.
4. **C-006 acceptance:** add an explicit test that a corrupt ORG override
   `expected-artifacts.yaml` for a REGISTERED built-in family (`software-dev`)
   makes **gather raise `MalformedManifestError`** — the raise fires at gather time
   even though the guard-table short-circuits (`cores.py:721-723`) later, so the
   corrupt override hard-blocks the whole family. This fulfils spec Edge-Case
   bullet 1 and C-006's promised acceptance scenario. Assert the raise, not a green
   guard. (This exercises the gather-time raise, not the `:504` seam — that seam is
   WP04's integration proof.)
5. Tag the distinctness + C-006 tests characterization (NOT `@regression`) — they
   are green after WP03's reader fix.

**Files.** `tests/charter/activation/test_org_expected_artifacts.py`,
`tests/doctrine/missions/test_repository.py`.

**Validation.** Distinctness tests green; error-text assertions pass; the C-006
`software-dev` corrupt-override test raises `MalformedManifestError` at gather.

## Branch Strategy

Planning artifacts were generated on `fix/expected-artifacts-loader-unification`.
During `/spec-kitty.implement` the execution workspace (worktree) is allocated
per-lane from `lanes.json` by `resolve_workspace_for_wp` — do not reconstruct the
path. Completed changes merge back into `fix/expected-artifacts-loader-unification`
unless the human redirects. WP03 is the peer parallel stream to WP02 after WP01;
its org-raise feeds WP04's launder-seam integration. Final PR targets upstream as
a DRAFT — the operator merges.

## Definition of Done

- Org reader raises `MalformedManifestError` for present-but-broken (YAML-syntax
  and non-mapping); genuine absence still returns `None`.
- Both tiers raise on present-but-unreadable (`OSError`/`UnicodeDecodeError`);
  genuine absence returns `None`.
- T010 (broken-YAML + non-mapping) + T012 (unreadable) were RED on `upstream/main`
  and are GREEN after; all carry `@pytest.mark.regression` and cite #3412.
- T014 after-fix distinctness tests are characterization and green; error text
  names file + cause (NFR-005); the C-006 `software-dev` corrupt-override test
  raises `MalformedManifestError` at gather time.
- No extra per-load I/O (NFR-004); `ruff` + `mypy` zero-new; ≤15 complexity.

## Risks

- **False regression tag.** If T010/T012 are green on base, they are mis-scoped
  (probably a schema fault, not a parse/unreadable fault) — a green `@regression`
  is a landing defect. Re-verify RED on `upstream/main` first.
- **Absence conflation.** Raising on `not path.is_file()` would break graceful
  degradation (I1) — guard the raise behind presence.
- **Wrong sibling.** Routing malformation onto `ManifestSchemaError` violates D2 —
  use `MalformedManifestError`.
- **C-006 blast radius.** A corrupt org override for a registered built-in family
  now hard-blocks the whole family (documented, acceptance-covered) — expected,
  not a bug.

## Reviewer Guidance

- Independently confirm T010 and T012 are RED on the merge-base / `upstream/main`
  through the named entry points before accepting them.
- Verify the raised type is `MalformedManifestError`, never `ManifestSchemaError`,
  for parse/non-mapping/unreadable.
- Confirm `not path.is_file()` still returns `None` on both tiers.
- Check the reader reuses the single existing read (NFR-004) and the error string
  names file + cause (NFR-005).
