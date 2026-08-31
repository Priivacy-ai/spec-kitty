---
work_package_id: WP02
title: Charter Shim Deletion + CHANGELOG
dependencies:
- WP01
requirement_refs:
- FR-012
- FR-013
- FR-014
- NFR-003
- NFR-004
- C-001
- C-006
planning_base_branch: feature/module_ownership
merge_target_branch: feature/module_ownership
branch_strategy: Planning artifacts for this feature were generated on feature/module_ownership. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/module_ownership unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
shell_pid: "1020155"
history:
- at: '2026-04-18T04:31:57Z'
  event: created
  actor: claude
authoritative_surface: src/specify_cli/charter/
execution_mode: code_change
owned_files:
- src/specify_cli/charter/__init__.py
- src/specify_cli/charter/compiler.py
- src/specify_cli/charter/interview.py
- src/specify_cli/charter/resolver.py
- tests/specify_cli/charter/test_defaults_unit.py
- tests/charter/test_sync_paths.py
- tests/charter/test_chokepoint_coverage.py
- tests/specify_cli/charter/test_no_new_legacy_modules.py
- tests/specify_cli/charter/test_shim_deprecation.py
- CHANGELOG.md
tags: []
agent: "claude"
---

# WP02 — Charter Shim Deletion + CHANGELOG

## Objective

Delete the `src/specify_cli/charter/` compatibility shim (4 files), remove the 3 associated C-005 test-fixture exceptions, add the CHANGELOG removal notice, and confirm the existing test suite passes with zero regressions.

This is the code-deletion half of Mission `functional-ownership-map-01KPDY72`. It must happen **after WP01** so the ownership map already reads the charter slice as "fully consolidated" from the moment the deletion lands.

**Acceptance marker**: After this WP, `python -c "import specify_cli.charter"` raises `ModuleNotFoundError` (NFR-004). The CHANGELOG contains the removal notice (FR-013). The merge commit message includes `Closes #611` (FR-014).

## Context

- The shim at `src/specify_cli/charter/` has been live since Mission `01KPD880`. It emits a `DeprecationWarning` with `__removal_release__ = "3.3.0"`. External importers have had this warning since spec-kitty 3.1.0.
- The canonical implementation at `src/charter/` is the sole definition site for all public API that the shim re-exports. Deleting the shim is safe at the code level (confirmed by `01KPD880` exemplar research).
- The 3 C-005 test-fixture exceptions were created by mission `01KPD880` to keep legacy-import tests passing while the shim was alive. With the shim gone, those tests have no purpose.
- **Do not modify `pyproject.toml` version** (C-001). Do not move or rename any other package (FR-015).

---

## Subtask T008 — Grep: confirm zero non-test callers of `specify_cli.charter`

**Purpose**: Run the **hard deletion gate** — confirm no CI workflow, release script, or source file outside `tests/` imports `specify_cli.charter`. If any caller is found, **stop and report** before proceeding.

> **D1 note**: WP01-T001 ran a discovery grep of the same form and recorded the result. T008 supersedes that run and is the authoritative gate: it is the last check before any file is deleted. Even if T001 found zero callers, T008 must run again — time may have passed between planning and implementation.

**Steps**:

1. Run the comprehensive grep:
   ```bash
   grep -rn "specify_cli[./]charter" \
     .github/ scripts/ src/ Makefile pyproject.toml setup.cfg \
     --include="*.yml" --include="*.yaml" --include="*.py" \
     --include="*.toml" --include="*.cfg" \
     2>/dev/null \
     | grep -v "src/specify_cli/charter/"
   ```
   Expected output: **zero lines**. If any lines appear that are not under `src/specify_cli/charter/` itself, stop and report the file paths — do not proceed to T009.

2. Also grep inside `tests/` to confirm only the three known C-005 fixtures reference the shim:
   ```bash
   grep -rn "specify_cli\.charter\|specify_cli/charter" tests/ 2>/dev/null
   ```
   Expected: lines only in:
   - `tests/specify_cli/charter/test_defaults_unit.py`
   - `tests/specify_cli/charter/test_no_new_legacy_modules.py` (may reference shim path)
   - `tests/specify_cli/charter/test_shim_deprecation.py` (may reference shim path)
   - `tests/charter/test_sync_paths.py` (C-005 exception 2)
   - `tests/charter/test_chokepoint_coverage.py` (C-005 exception 3, comments only)

   Any reference in a test file **outside** this set must be investigated. Note them and ask whether they need to be removed or updated.

**Validation**: Zero non-test callers found. All test references are in the expected files.

---

## Subtask T009 — Delete `src/specify_cli/charter/` — all 4 files

**Purpose**: Permanently remove the shim package. After deletion, `import specify_cli.charter` must raise `ModuleNotFoundError`.

**Steps**:

1. Delete all four files in the shim package:
   ```bash
   rm src/specify_cli/charter/__init__.py
   rm src/specify_cli/charter/compiler.py
   rm src/specify_cli/charter/interview.py
   rm src/specify_cli/charter/resolver.py
   ```

2. Remove the now-empty directory:
   ```bash
   rmdir src/specify_cli/charter/
   ```

3. Confirm deletion:
   ```bash
   ls src/specify_cli/charter/ 2>&1
   # Expected: "ls: cannot access 'src/specify_cli/charter/': No such file or directory"
   ```

4. Quick smoke test:
   ```bash
   python -c "import specify_cli.charter" 2>&1
   # Expected: ModuleNotFoundError: No module named 'specify_cli.charter'
   ```

5. Confirm canonical imports still work:
   ```bash
   python -c "from charter import build_charter_context; print('charter OK')"
   # Expected: "charter OK"
   ```

**Files deleted**: `src/specify_cli/charter/__init__.py`, `compiler.py`, `interview.py`, `resolver.py` (and the now-empty `src/specify_cli/charter/` directory).

**Validation**: Directory gone; `import specify_cli.charter` → `ModuleNotFoundError`; `from charter import build_charter_context` → OK.

---

## Subtask T010 — Delete/clean the 3 C-005 test-fixture exceptions

**Purpose**: Remove the test code that existed solely to verify the shim's legacy-import behaviour. With the shim gone, this code has no purpose and its continued presence would cause import errors.

**Important distinction**: Only remove legacy-path lines. Canonical `from charter import …` or `import charter` lines throughout `tests/charter/` are correct and must **not** be touched.

**Steps**:

### Exception 1: `tests/specify_cli/charter/test_defaults_unit.py`

Delete the entire file — it was kept by design as a C-005 compatibility fixture and has no purpose once the shim is deleted:
```bash
rm tests/specify_cli/charter/test_defaults_unit.py
```

Also check if `tests/specify_cli/charter/test_no_new_legacy_modules.py` and `test_shim_deprecation.py` reference `src/specify_cli/charter/`:
```bash
cat tests/specify_cli/charter/test_no_new_legacy_modules.py
cat tests/specify_cli/charter/test_shim_deprecation.py
```
These files likely assert that the shim has no new modules (a constraint that is vacuously satisfied once the directory is gone) or test the deprecation warning. Delete them entirely, or — if they test something unrelated to the shim — remove only the shim-specific lines.

If `tests/specify_cli/charter/` becomes empty (no remaining `.py` files other than `__init__.py`), remove the directory too:
```bash
rmdir tests/specify_cli/charter/ 2>/dev/null || true
```

### Exception 2: `tests/charter/test_sync_paths.py`

The C-005 exception in this file is the `import_module("specify_cli.charter")` call and the test that asserts `specify_cli.charter.sync` is the same callable as `charter.sync`. Read the file first to understand the exact scope:
```bash
grep -n "specify_cli" tests/charter/test_sync_paths.py
```

Remove:
- The docstring or comment that references `specify_cli.charter` as a backward-compatibility surface.
- The `import_module("specify_cli.charter")` line (and any surrounding fixture).
- Any test function whose sole purpose is asserting `specify_cli.charter.*` == `charter.*` parity.

Keep:
- Any test that imports `from charter import …` or `import charter` directly.
- Any test that validates sync behaviour via the canonical package.

### Exception 3: `tests/charter/test_chokepoint_coverage.py`

The C-005 exception in this file is limited to comments that list `src/specify_cli/charter/extractor.py` etc. as "chokepoint" files. Read the file first:
```bash
grep -n "specify_cli/charter\|specify_cli\.charter" tests/charter/test_chokepoint_coverage.py
```

Around lines 29–34 and 72 (per R-004 in research.md), remove the `src/specify_cli/charter/` path entries from the chokepoint file list. The canonical `src/charter/` counterparts in those same lists must remain.

Example: if the list reads:
```python
CHOKEPOINT_FILES = [
    "src/charter/extractor.py",
    "src/specify_cli/charter/extractor.py",   # ← DELETE this line
    "src/charter/hasher.py",
    "src/specify_cli/charter/hasher.py",       # ← DELETE this line
    ...
]
```
Remove the `src/specify_cli/charter/` entries; keep the `src/charter/` entries.

**Files modified**: `tests/specify_cli/charter/test_defaults_unit.py` (deleted), `tests/specify_cli/charter/test_no_new_legacy_modules.py` (deleted or cleaned), `tests/specify_cli/charter/test_shim_deprecation.py` (deleted), `tests/charter/test_sync_paths.py` (edited), `tests/charter/test_chokepoint_coverage.py` (edited).

**Validation**: No file in the repo imports `specify_cli.charter` — verify with `grep -rn "specify_cli\.charter\|specify_cli/charter" tests/ src/`.

---

## Subtask T011 — Add CHANGELOG entry (FR-013)

**Purpose**: Inform external users and downstream importers of `specify_cli.charter` that the shim has been removed and the canonical import path is `charter.*`.

**Steps**:

1. Open `CHANGELOG.md` and locate the `## [Unreleased]` section (or create it at the top if absent).

2. Under `## [Unreleased]`, find or create a `### Removed` subsection. Add this entry:

   ```markdown
   ### Removed

   - **`specify_cli.charter` compatibility shim** — The re-export shim at `src/specify_cli/charter/` has been
     removed as announced in 3.1.0 (`__removal_release__ = "3.3.0"`). External code importing
     `specify_cli.charter.*` must migrate to the canonical package: `from charter import <name>`.
     See [architecture/2.x/05_ownership_map.md](architecture/2.x/05_ownership_map.md) for the full
     charter slice entry and the reference exemplar pattern. Closes #611.
   ```

3. Confirm the entry is placed **above** any existing `### Changed`, `### Fixed`, or `### Added` subsections within `[Unreleased]` (conventional changelog ordering: Removed > Changed > Deprecated > Fixed > Added > Security).

**Files**: `CHANGELOG.md` (edited — one new entry under Unreleased/Removed).

**Validation**: `grep -A5 "Unreleased" CHANGELOG.md` shows the "Removed" subsection with the `specify_cli.charter` entry.

4. **Active FR-014 check (U3)**: Before committing, verify the planned commit message draft includes `Closes #611`. The merge commit message is the sole mechanism for auto-closing issue #611 (FR-014). Run:
   ```bash
   echo "Verify your commit message will include: Closes #611"
   # Template:
   # chore: delete specify_cli.charter compatibility shim
   #
   # Removes src/specify_cli/charter/ (4 files) and the 3 C-005 test-fixture
   # exceptions. External importers must migrate to `from charter import <name>`.
   # Closes #611
   ```
   Do not merge WP02 without this line in the commit message.

---

## Subtask T012 — Run existing test suite; confirm zero regressions (NFR-003)

**Purpose**: Gate the WP on a green test run. The shim deletion and fixture cleanup must not break any existing test.

**Steps**:

1. Run the test suite, excluding the `tests/architecture/` directory (which WP03 populates):
   ```bash
   cd /path/to/repo/src && python -m pytest ../tests/ --ignore=../tests/architecture -x -q 2>&1 | tail -20
   ```
   or from repo root:
   ```bash
   python -m pytest tests/ --ignore=tests/architecture -x -q 2>&1 | tail -20
   ```

2. Expected result: all tests pass, zero failures, zero errors.

3. If any test fails with `ModuleNotFoundError: No module named 'specify_cli.charter'`, that test references the shim and must be cleaned up (return to T010).

4. If any test fails with a different error, investigate before proceeding. Do not suppress failures with `pytest.ini` or `pyproject.toml` ignore patterns (NFR-003 forbids introducing new exceptions).

5. Record the final test run summary (e.g., "347 passed in 42.3s") in a comment in the WP progress notes.

**Validation**: `pytest` exits 0; zero new `filterwarnings` ignore entries added to `pyproject.toml` or `pytest.ini`.

---

## Branch Strategy

- **Planning/base branch**: `feature/module_ownership`
- **Merge target**: `feature/module_ownership`
- **Execution workspace**: allocated by `spec-kitty agent action implement WP02 --agent <name>` via `lanes.json`.
- **Ordering requirement**: WP01 must be merged before WP02 starts. The ownership map must exist and read "charter fully consolidated" before the deletion commits land.
- **Commit message**: Must include `Closes #611` per FR-014.

---

## Definition of Done

- [ ] `src/specify_cli/charter/` directory and all 4 files are deleted.
- [ ] `python -c "import specify_cli.charter"` raises `ModuleNotFoundError`.
- [ ] `python -c "from charter import build_charter_context; print('OK')"` exits 0.
- [ ] `tests/specify_cli/charter/test_defaults_unit.py` is deleted.
- [ ] `tests/specify_cli/charter/test_no_new_legacy_modules.py` and `test_shim_deprecation.py` are deleted or cleaned of all shim references.
- [ ] No remaining `specify_cli.charter` import in any test file (confirmed by grep).
- [ ] `CHANGELOG.md` contains the removal entry under `## [Unreleased]` / `### Removed`.
- [ ] Full test suite passes with zero failures: `pytest tests/ --ignore=tests/architecture -q`.
- [ ] No new `filterwarnings` or `ignore` patterns added to `pyproject.toml` or `pytest.ini`.
- [ ] `pyproject.toml` version unchanged at `3.1.6` (C-001).

---

## Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Unexpected non-test caller found at T008 | Low | Hard stop at T008 grep gate; report and investigate before any deletion |
| T010 removes too many lines from test_chokepoint_coverage.py | Medium | Read the file carefully; only remove `specify_cli/charter/` path entries; canonical `charter/` entries stay |
| `test_sync_paths.py` has canonical content mixed with legacy content | Medium | Read the full test function before deleting; keep any test that validates canonical `charter.sync` behaviour |
| Shim deletion breaks `tests/specify_cli/charter/test_no_new_legacy_modules.py` | Low | Delete the file if its sole purpose is shim-directory enumeration; check first |

---

## Reviewer Guidance

- Confirm the 4 shim files are deleted and the directory is gone.
- Confirm `tests/specify_cli/charter/test_defaults_unit.py` is deleted.
- Spot-check `tests/charter/test_sync_paths.py` to verify only the `specify_cli.charter` lines were removed; canonical imports are intact.
- Confirm the CHANGELOG entry is correctly placed under `[Unreleased]` / `Removed` and mentions `Closes #611`.
- Verify the test suite was run (T012 evidence) and passed.
- Check commit message includes `Closes #611`.

## Activity Log

- 2026-04-18T05:25:49Z – claude – shell_pid=980993 – Started implementation via action command
- 2026-04-18T06:45:38Z – claude – shell_pid=980993 – Ready: shim deleted, C-005 fixtures removed, CHANGELOG entry added (Closes #611), 3220 tests pass
- 2026-04-18T06:51:01Z – claude – shell_pid=1020155 – Started review via action command
- 2026-04-18T06:53:05Z – claude – shell_pid=1020155 – Review passed: shim directory deleted, all 4 files gone, C-005 fixture dir fully removed, CHANGELOG entry correctly placed under [Unreleased]/Removed with Closes #611, commit message includes Closes #611, version unchanged at 3.1.6, no new filterwarnings. Boyscout pytest marker additions are clean and in scope.
