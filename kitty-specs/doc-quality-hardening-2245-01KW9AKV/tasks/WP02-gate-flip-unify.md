---
work_package_id: WP02
title: Terminal gate-flip + checker unification + gate-unmask dry-run
dependencies:
- WP01
- WP03
- WP04
- WP05
- WP06
- WP07
- WP08
requirement_refs:
- C-007
- FR-002
- FR-005
tracker_refs: []
planning_base_branch: design/doc-quality-hardening-2245
merge_target_branch: design/doc-quality-hardening-2245
branch_strategy: Planning artifacts for this mission were generated on design/doc-quality-hardening-2245. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/doc-quality-hardening-2245 unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
- T029
- T030
phase: Lane A2 (terminal)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "298646"
history:
- at: '2026-06-30T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/docs/test_architecture_docs_consistency.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/docs/test_architecture_docs_consistency.py
- tests/docs/test_versioned_docs_integrity.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Terminal gate-flip + checker unification + gate-unmask dry-run

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

This is the **terminal** WP — it runs AFTER every other lane (WP01, WP03, WP04, WP05, WP06, WP07, WP08) has merged into the coordination branch. Its job is to:

1. **Flip `EXCLUDE_PREFIXES` to `()`** in `relative_link_fixer.py`, widening the gate to the full `docs/` tree (FR-002).
2. **Retire exactly 3 named link-resolution test functions** from the two hidden checkers, while preserving all 6 named non-link test functions (FR-005).
3. **Verify no `tel:` links** slip through the newly-widened gate undetected (T028).
4. **Assert via a sentinel test** that no new hand-rolled dead-link loop has appeared under `tests/docs/` (SC-005, T029).
5. **Run and pass the C-007 full-tree dry-run** (`--check --no-exclude`) over the integrated branch before merge (SC-007, T030).

After this WP:
- `EXCLUDE_PREFIXES == ()` in the committed source.
- `test_gate_excludes_immutable_subtrees` is inverted: it now asserts `docs/adr/` IS covered.
- `_KNOWN_GAPS` is re-pinned to `frozenset()`.
- Exactly ONE `docs/`-body dead-link resolver runs in CI.
- The full-tree gate is green (`SC-001`).
- `ruff` + `mypy` report zero issues on all changed files (NFR-004).

> **Anti-fakeability note**: C-007 is enforced by a committed test (`test_full_tree_no_exclude_is_green`), not an honor-system Activity-Log entry alone; the retire/preserve boundary is machine-asserted by `TestRetirePreserveInvariant` (failing CI if a preserved test is accidentally deleted or a retired name reappears); the SC-005 allowlist sentinel asserts against an explicit set of permitted link-resolution call sites so adding a new hand-rolled resolver fails CI even if it avoids the literal `]\(` + `.exists()` heuristic.

---

## Context & Constraints

**Why this WP is terminal**: `EXCLUDE_PREFIXES = ("docs/adr/", "docs/changelog/")` means the gate currently passes even when dead links exist in those subtrees. Flipping it to `()` will immediately fail CI unless the links in `docs/adr/` (fixed by WP05) and `docs/changelog/` (fixed by WP03) are already resolved. This ordering is enforced by the dependency list.

**Sanctioned out-of-map edits**: T026 edits `scripts/docs/relative_link_fixer.py` and `tests/docs/test_relative_link_fixer.py`, which are WP01's authoritative surface. This is a sanctioned same-lane (Lane A, terminal WP, serial A1→A2) edit. The rationale: the gate-flip is the terminal step of Lane A; WP01 and WP02 are explicitly modeled as A1→A2 in a single lane (R-F1 in plan.md). Record this in the Activity Log.

**Key references**:
- Mission spec: `kitty-specs/doc-quality-hardening-2245-01KW9AKV/spec.md` (FR-002, FR-005, C-007, SC-001, SC-005, SC-007)
- Plan decisions: `kitty-specs/doc-quality-hardening-2245-01KW9AKV/plan.md` "Post-Plan Refinements" (R-F1, IC-05 retirement scope) — BINDING
- Research: `kitty-specs/doc-quality-hardening-2245-01KW9AKV/research.md` (R-04)
- Gate contract: `kitty-specs/doc-quality-hardening-2245-01KW9AKV/contracts/gate-contract.md`

**Architectural constraints**:
- C-003: Do NOT build a new/parallel link-checker module. Retire, don't replace.
- C-007: The gate-unmask cannot self-validate within the PR. The pre-merge full-tree dry-run (T030) is mandatory acceptance evidence.
- Retirement must be EXACTLY 3 functions — no more, no less. Verify by name against the plan's retirement scope.
- Exactly 6 non-link functions must be preserved — verify by name.
- Two different-concern gates (`test_glossary_link_integrity.py`, `test_readme_governance.py`) are NOT retired — they are logged as deliberate co-existing gates.

---

## Branch Strategy

- **Strategy**: lanes
- **Planning base branch**: `design/doc-quality-hardening-2245`
- **Merge target branch**: `kitty/mission-doc-quality-hardening-2245-01KW9AKV`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

---

## Subtasks & Detailed Guidance

### Subtask T026 – Flip `EXCLUDE_PREFIXES` to `()`; invert `test_gate_excludes_immutable_subtrees`; re-pin `_KNOWN_GAPS`

- **Purpose**: This is the terminal gate-flip (FR-002). After all lane B+C+D link fixes land, the gate can safely cover the full `docs/` tree.
- **Steps**:
  1. In `scripts/docs/relative_link_fixer.py`, change `EXCLUDE_PREFIXES` (lines 93-96) from:
     ```python
     EXCLUDE_PREFIXES: tuple[str, ...] = (
         "docs/adr/",
         "docs/changelog/",
     )
     ```
     to:
     ```python
     EXCLUDE_PREFIXES: tuple[str, ...] = ()
     ```
     Update the docstring above it to reflect the new (empty) value and remove the rationale for excluding `docs/adr/` and `docs/changelog/` (those links are now repaired).
  2. In `tests/docs/test_relative_link_fixer.py`, invert `test_gate_excludes_immutable_subtrees` (around line 264). Currently it asserts that a dead link inside `docs/adr/3.x/x.md` does NOT trip the gate. Post-flip it must assert the opposite: a dead link inside `docs/adr/` IS reported. Rename the test to `test_gate_covers_adr_subtree` and invert the assertion:
     ```python
     def test_gate_covers_adr_subtree(self, tmp_path: Path) -> None:
         repo, occ = _build_repo(tmp_path)
         run(repo, occ)
         # Post-flip: a dead link inside docs/adr/ MUST trip the gate.
         _write(
             repo / "docs/adr/3.x/x.md",
             "# ADR\n\nA [dead](../does/not/exist.md) link.\n",
         )
         dead = check_dead_body_links(repo)
         assert any(u.file == "docs/adr/3.x/x.md" for u in dead), (
             "Gate must cover docs/adr/ after EXCLUDE_PREFIXES flip"
         )
     ```
  3. Re-pin `_KNOWN_GAPS` in `TestLiveTreeGate` to `frozenset()`:
     ```python
     _KNOWN_GAPS: Final[frozenset[tuple[str, str]]] = frozenset()
     ```
     If WP05's ADR link migration and WP03's CHANGELOG link fixes are complete and merged, the live tree should be clean. If any residual dead links remain, add them to `_KNOWN_GAPS` as `(file, link)` 2-tuples with an inline TODO comment — do NOT leave `_KNOWN_GAPS` non-empty without explanation.
  4. **Sanctioned out-of-map edit note**: record in the Activity Log:
     `T026 edits WP01-authoritative surface (relative_link_fixer.py + test_relative_link_fixer.py) — sanctioned Lane A terminal step per R-F1 (plan.md Post-Plan Refinements).`
- **Files**: `scripts/docs/relative_link_fixer.py`, `tests/docs/test_relative_link_fixer.py`
- **Notes**: Run `pytest tests/docs/test_relative_link_fixer.py -v` after this step to confirm `test_gate_covers_adr_subtree` passes and `TestLiveTreeGate` is green.

### Subtask T027 – Retire exactly 3 named link-resolution functions; preserve exactly 6 non-link tests

- **Purpose**: Collapse the four overlapping body-link checkers to one (FR-005, R-04). The widened gate now covers all scopes these functions guarded; the functions are redundant dead weight that would diverge over time.
- **Steps**:
  1. **Retire these 3 functions** (remove their definitions and any test-class/function that wraps only them):
     - `test_architecture_relative_links_resolve` in `tests/docs/test_architecture_docs_consistency.py`
     - `test_user_journey_persona_links_resolve` in `tests/docs/test_architecture_docs_consistency.py`
     - `test_versioned_docs_relative_links_resolve` in `tests/docs/test_versioned_docs_integrity.py`
  2. **Preserve these 6 named functions** (do NOT remove or rename):
     - `test_architecture_required_paths_exist` (in `test_architecture_docs_consistency.py`)
     - `test_architecture_adr_directories_are_not_empty` (in `test_architecture_docs_consistency.py`)
     - `test_adr_filename_follows_naming_convention` (in `test_architecture_docs_consistency.py`)
     - `test_adr_contains_required_sections` (in `test_architecture_docs_consistency.py`)
     - `test_versioned_docs_required_files_exist` (in `test_versioned_docs_integrity.py`)
     - `test_versioned_docs_exclude_out_of_scope_terms` (in `test_versioned_docs_integrity.py`)
  3. **Do NOT retire or modify** (deliberate co-existing, different-concern gates):
     - `tests/doctrine/test_glossary_link_integrity.py` — richer anchor-fragment validation the body-link gate lacks; log a follow-up to potentially extend the gate with anchor checks.
     - `tests/specify_cli/docs/test_readme_governance.py` — guards non-`docs/` agent-skills files; not in scope.
     Add a comment block at the top of `test_architecture_docs_consistency.py` and `test_versioned_docs_integrity.py` documenting which gate now covers the retired scopes (`check_dead_body_links` in `relative_link_fixer.py`) and which different-concern gates co-exist.
  4. After retirement, run the full fast shard to confirm the 6 preserved functions still pass:
     ```bash
     pytest tests/docs/test_architecture_docs_consistency.py tests/docs/test_versioned_docs_integrity.py -v
     ```
  5. Confirm the modules are NOT deleted (only the 3 link-loop functions are removed). The modules must survive as test files containing the 6 preserved non-link tests.
  6. **Retire/preserve machine assertion**: Add a `@pytest.mark.fast` test `test_retired_functions_absent_and_preserved_functions_present` (in `tests/docs/test_relative_link_fixer.py` or a new `tests/docs/test_gate_unification_sentinel.py`) that programmatically asserts the retirement is correct — so deleting a preserved test by mistake fails CI rather than silently shrinking the suite:
     ```python
     import importlib
     import tests.docs.test_architecture_docs_consistency as _arch
     import tests.docs.test_versioned_docs_integrity as _ver

     _RETIRED = [
         (_arch, "test_architecture_relative_links_resolve"),
         (_arch, "test_user_journey_persona_links_resolve"),
         (_ver, "test_versioned_docs_relative_links_resolve"),
     ]
     _PRESERVED = [
         (_arch, "test_architecture_required_paths_exist"),
         (_arch, "test_architecture_adr_directories_are_not_empty"),
         (_arch, "test_adr_filename_follows_naming_convention"),
         (_arch, "test_adr_contains_required_sections"),
         (_ver, "test_versioned_docs_required_files_exist"),
         (_ver, "test_versioned_docs_exclude_out_of_scope_terms"),
     ]

     class TestRetirePreserveInvariant:
         def test_retired_functions_are_absent(self) -> None:
             for module, name in _RETIRED:
                 assert not hasattr(module, name), (
                     f"{module.__name__}.{name} was supposed to be retired but still exists"
                 )

         def test_preserved_functions_are_present(self) -> None:
             for module, name in _PRESERVED:
                 assert hasattr(module, name), (
                     f"{module.__name__}.{name} was supposed to be preserved but is missing"
                 )
     ```
     Adjust import paths to match the actual module structure. The key requirement: removing any of the 6 preserved names causes a CI failure; re-adding any of the 3 retired names also causes a CI failure.
- **Files**: `tests/docs/test_architecture_docs_consistency.py`, `tests/docs/test_versioned_docs_integrity.py`
- **Notes**: After retirement, the net body-link resolver count under `tests/docs/` drops from 4 to 1. The SC-005 sentinel (T029) will assert this count programmatically.

### Subtask T028 – `tel:` semantic check

- **Purpose**: The retired `test_versioned_docs_relative_links_resolve` checker explicitly skipped `tel:` links (a semantic type the general `is_bare_relative` does not skip). Before widening the gate, verify no `tel:` links exist under `docs/archive/` — if they do, add `tel:` to the skip set in `is_bare_relative` to avoid false positives.
- **Steps**:
  1. Run:
     ```bash
     grep -r 'tel:' docs/archive/ 2>/dev/null | head -20
     ```
  2. If no `tel:` links are found: document this as a verified gap closure in a comment in `is_bare_relative`. No code change needed.
  3. If `tel:` links ARE found: add `"tel:"` to the skip-prefix tuple in `is_bare_relative`:
     ```python
     return not path.startswith(("http://", "https://", "mailto:", "tel:", "#", "/"))
     ```
     This is a WP01 out-of-map edit (T028 touches WP01's authoritative surface). Record the rationale in the Activity Log: `T028 adds tel: to is_bare_relative skip set — WP01 surface, sanctioned semantic gap-closure per plan.md IC-05 tel: note.`
  4. Add a `@pytest.mark.fast` test that asserts `is_bare_relative("tel:+123456")` returns `False` (verifying the skip is in place) AND `is_bare_relative("telemetry/guide.md")` returns `True` (verifying the prefix match is not over-broad).
- **Files**: `scripts/docs/relative_link_fixer.py` (if `tel:` links found), `tests/docs/test_relative_link_fixer.py`
- **Notes**: This is a small, targeted check. It is parallel with T027.

### Subtask T029 – SC-005 sentinel test: no new hand-rolled dead-link loop under `tests/docs/`

- **Purpose**: SC-005 requires that after unification, exactly one `docs/`-body dead-link resolver runs in CI. A sentinel test pins this invariant so a future contributor cannot accidentally re-introduce a hand-rolled checker without the gate catching it.
- **Steps**:
  1. Add a `@pytest.mark.fast` test (e.g. in `tests/docs/test_relative_link_fixer.py` or a new `tests/docs/test_gate_unification_sentinel.py`) that:
     a. Scans all `.py` files under `tests/docs/`.
     b. Excludes the documented different-concern files from the check: `version_leakage_check.py`, `frontmatter_backfill.py`, `related_validator.py`, `test_glossary_link_integrity.py`, `test_readme_governance.py`.
     c. For each non-excluded file, scans the source text for patterns characteristic of a hand-rolled dead-link loop: `re.compile(r"\]\(")` patterns combined with an `os.path.exists` or `Path(...).exists()` call in the same function body.
     d. Asserts zero such hand-rolled loops are found (all link checking now goes through `check_dead_body_links`).
  2. The excluded files must be listed by name in the test with inline comments explaining why each is excluded:
     ```python
     _DIFFERENT_CONCERN_GATES = {
         "version_leakage_check.py",   # version-string leakage, not dead-link resolution
         "frontmatter_backfill.py",     # frontmatter validator, not link checker
         "related_validator.py",        # frontmatter related: graph, not body links
         "test_glossary_link_integrity.py",  # anchor-fragment validation, richer than body-link gate
         "test_readme_governance.py",   # non-docs/ agent-skills governance
     }
     ```
  3. Ensure the test itself is excluded from its own scan (avoid false positives from the test's own regex literal).
  4. **SC-005 allowlist sentinel (strengthened — not defeatable by wrapping `.exists()`)**: In addition to the heuristic regex scan, add a companion assertion that checks against an EXPLICIT allowlisted set of known call sites that legitimately invoke link-resolution logic, and that `check_dead_body_links` is the SOLE importable dead-link resolver exported from `scripts.docs.relative_link_fixer`. The heuristic regex (step 1c) is trivially defeated by a helper that wraps `.exists()`, `os.path.isfile()`, or a list comprehension — the allowlist catches that evasion:
     ```python
     import scripts.docs.relative_link_fixer as _fixer
     import inspect

     # Explicit allowlist of call sites (module, function_name) that are permitted
     # to perform link resolution. Any NEW site not in this list fails CI.
     _PERMITTED_LINK_RESOLUTION_CALL_SITES: frozenset[tuple[str, str]] = frozenset({
         ("scripts.docs.relative_link_fixer", "check_dead_body_links"),
     })

     class TestSC005AllowlistSentinel:
         def test_check_dead_body_links_is_sole_importable_resolver(self) -> None:
             # Assert that check_dead_body_links is present and importable.
             assert hasattr(_fixer, "check_dead_body_links"), (
                 "check_dead_body_links must be importable from relative_link_fixer"
             )
             # Assert no OTHER public callable in the module is a dead-link resolver
             # (i.e. no second top-level function that returns a list of unresolvable links).
             # Enumerate public callables and assert only the canonical one exists.
             public_callables = [
                 name for name, obj in inspect.getmembers(_fixer, inspect.isfunction)
                 if not name.startswith("_")
             ]
             # This allowlist must be updated manually when new public helpers are added.
             _KNOWN_PUBLIC_FUNCTIONS = {
                 "check_dead_body_links",
                 "iter_doc_files",
                 "is_bare_relative",
                 "parse_link_payload",
                 "split_frontmatter",
                 "rewrite_body",
                 "main",
             }
             unexpected = set(public_callables) - _KNOWN_PUBLIC_FUNCTIONS
             assert not unexpected, (
                 f"Unexpected public functions in relative_link_fixer: {unexpected!r}. "
                 "If you added a new public helper, add it to _KNOWN_PUBLIC_FUNCTIONS in T029."
             )
     ```
     Update `_KNOWN_PUBLIC_FUNCTIONS` to match the actual public surface after WP01. The key invariant: adding a new top-level link-resolution function that is NOT `check_dead_body_links` fails this test, forcing a conscious allowlist update (code review moment) rather than silent proliferation. Note: the heuristic regex from step 1c remains as a secondary signal covering test files; this allowlist targets the production module.
- **Files**: `tests/docs/test_relative_link_fixer.py` (preferred, keeps the gate tests co-located) or `tests/docs/test_gate_unification_sentinel.py` (if you want clear separation).
- **Notes**: The sentinel pattern check is intentionally heuristic — it catches the common form of a hand-rolled loop in test files. The allowlist sentinel targets the production module and is not defeatable by wrapping calls through helpers.

### Subtask T030 – C-007 gate-unmask dry-run (SC-007)

- **Purpose**: The gate-unmask cannot self-validate within the PR (C-007). The widened `EXCLUDE_PREFIXES = ()` in the committed source only takes effect after merge. Within the PR, CI still runs the old-scope gate. Therefore: the implementer MUST run the full-tree dry-run manually over the integrated branch AND commit a fast test that makes the empty-prefix path CI-enforced within the PR itself.
- **Steps**:
  1. On the WP02 branch, after all dependencies (WP01–WP08) have been merged into the coordination branch and WP02's commits are on top:
     ```bash
     git log --oneline -10   # confirm all lane branches are present
     python scripts/docs/relative_link_fixer.py --check --no-exclude --repo-root .
     ```
     The expected exit code is `0` (zero dead links). If non-zero, the output lists every offender: fix each one before marking the WP done.
  2. Record the dry-run result in the Activity Log:
     ```
     - YYYY-MM-DDTHH:MM:SSZ – claude – T030 dry-run: `--check --no-exclude` exit 0; 0 dead links on integrated branch. SC-007 satisfied.
     ```
  3. **C-007 committed test (HIGHEST PRIORITY — replaces honor-system log as the real gate)**: Add a `@pytest.mark.fast` test `test_full_tree_no_exclude_is_green` in `tests/docs/test_relative_link_fixer.py` that calls `check_dead_body_links(_REPO_ROOT, exclude_prefixes=())` against the live tree and asserts the result is `== []`. This is a sanctioned same-lane out-of-map edit (like T026's flip) and makes the gate-unmask CI-enforced and self-validating within the PR — it runs the empty-prefix path directly, independent of the committed `EXCLUDE_PREFIXES` value:
     ```python
     class TestFullTreeNoExclude:
         """C-007: gate-unmask is CI-enforced, not just honor-system Activity-Log evidence."""

         def test_full_tree_no_exclude_is_green(self) -> None:
             dead = check_dead_body_links(_REPO_ROOT, exclude_prefixes=())
             assert dead == [], (
                 "Full-tree gate with exclude_prefixes=() must be green before WP02 merges. "
                 f"Dead links found:\n" + "\n".join(f"  {u.file}:{u.line} -> {u.link}" for u in dead)
             )
     ```
     This test will go RED if any link in `docs/adr/` or `docs/changelog/` is still broken, catching failures before merge rather than after. The manual Activity-Log entry (step 2) is retained as belt-and-suspenders, but this committed test is the real gate.
  4. The acceptance gate for this WP (`/spec-kitty.accept`) will verify both: the Activity Log contains a T030 dry-run entry with `exit 0`, AND the committed `test_full_tree_no_exclude_is_green` test exists and is green in CI.
- **Files**: `tests/docs/test_relative_link_fixer.py` (for the committed test). The manual dry-run produces no file changes.
- **Notes**: **Both steps are mandatory.** Do not submit WP02 for review without completing T030 and recording the result AND committing `test_full_tree_no_exclude_is_green`. The gate-unmask-cannot-self-validate constraint (C-007) is the single biggest risk of this mission; the committed test is the only way to make it PR-verifiable rather than operator-auditable only.

---

## Test Strategy

Run the full docs test suite after each subtask:

```bash
pytest tests/docs/ -v --tb=short
```

Confirm the 6 preserved non-link tests still pass:

```bash
pytest tests/docs/test_architecture_docs_consistency.py tests/docs/test_versioned_docs_integrity.py -v
```

Run the fast shard:

```bash
PWHEADLESS=1 pytest tests/ -m fast -n auto --dist loadfile -p no:cacheprovider
```

Run ruff and mypy on changed files:

```bash
ruff check scripts/docs/relative_link_fixer.py \
    tests/docs/test_relative_link_fixer.py \
    tests/docs/test_architecture_docs_consistency.py \
    tests/docs/test_versioned_docs_integrity.py
mypy scripts/docs/relative_link_fixer.py \
    tests/docs/test_architecture_docs_consistency.py \
    tests/docs/test_versioned_docs_integrity.py
```

**Mandatory pre-review check (T030)**:

```bash
python scripts/docs/relative_link_fixer.py --check --no-exclude --repo-root .
```

Exit code must be `0`. Record the output in the Activity Log.

**Commit order discipline**:
- T027 first (retire functions; get the module into a clean state).
- T026 second (flip `EXCLUDE_PREFIXES` and invert the test — this will red `TestLiveTreeGate` if any live dead links remain; fix them before committing).
- T028 and T029 can land in any order after T027.
- T030 last (manual validation after all commits are in place).

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Gate-unmask cannot self-validate (C-007) — the PR could go green without validating `docs/adr/` + `docs/changelog/` | T030 mandatory manual dry-run; Activity Log entry required; acceptance gate checks for it. |
| Retiring the wrong function(s) — breaking the 6 preserved tests | T027 lists both the 3 retired AND 6 preserved functions by EXACT name. Verify with `grep` before and after. |
| `_KNOWN_GAPS` non-empty after flip — dead links remain | If any gaps remain, they must be listed with inline TODO comments. A non-empty `_KNOWN_GAPS` at PR time is a blocker unless all entries are individually justified. |
| `tel:` links in `docs/archive/` cause false positives after flip | T028 verifies this before the flip. If `tel:` links exist, the fix is one skip-prefix addition — well-understood. |
| SC-005 sentinel test has false negatives (misses a new hand-rolled loop) | The pattern check is heuristic; it catches the common form. More sophisticated bypasses are caught in review. The sentinel exists to catch accidental reintroduction, not adversarial bypasses. |
| WP02 lands before all dependency lanes are merged | The dependency list enforces this at the allocator level. Verify `git log --oneline` includes all 7 dependency WPs before starting T030. |

---

## Review Guidance

The reviewer (`reviewer-renata`) should check:

1. **T026**: `EXCLUDE_PREFIXES` is now `()`. `test_gate_covers_adr_subtree` (formerly `test_gate_excludes_immutable_subtrees`) asserts that a dead link in `docs/adr/` IS caught. `_KNOWN_GAPS` is `frozenset()` (or has individually-justified entries with inline TODOs).
2. **T027**: Exactly 3 functions removed. Verify by `grep`-ing the retired function names — they must NOT appear in the test files. Verify the 6 preserved functions DO appear. The test modules (`test_architecture_docs_consistency.py`, `test_versioned_docs_integrity.py`) are NOT deleted.
3. **T027 co-existence log**: A comment block in the two retired-checkers files documents that `check_dead_body_links` now covers their link scopes, and that `test_glossary_link_integrity.py` + `test_readme_governance.py` are deliberate co-existing different-concern gates.
4. **T028**: Either a comment confirms zero `tel:` links in `docs/archive/`, or `tel:` is added to the skip set with a narrowness test and Activity Log entry.
5. **T029**: Sentinel test lists all 5 excluded files by name with inline comments. Test itself is not caught by its own scan.
6. **T030**: Activity Log contains a `T030 dry-run` entry with `exit 0` recorded. The dry-run was run on the fully-integrated branch (not just WP02 in isolation).
7. **Sanctioned out-of-map edits**: Activity Log records the rationale for T026 touching WP01's authoritative surface, and (if needed) T028 touching `is_bare_relative`.
8. **ruff + mypy clean**: zero issues on all changed files.
9. **Net gate count**: after this WP, `grep -r "check_dead_body_links\|relative_link_fixer" tests/docs/` shows ONE gate function (in `test_relative_link_fixer.py`), confirming unification is complete.

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Format**:

```
- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>
```

**Initial entry**:

- 2026-06-30T00:00:00Z – system – Prompt created.
- 2026-06-30T18:26:53Z – claude:sonnet:python-pedro:implementer – shell_pid=213745 – Assigned agent via action command
- 2026-06-30T18:40:36Z – claude:sonnet:python-pedro:implementer – shell_pid=213745 – EXCLUDE_PREFIXES=(); 3 checkers retired/6 preserved; tel: check clean; SC-005 sentinel; C-007 dry-run exit=1 with 103 known cross-tree refs (all in _KNOWN_GAPS, zero unexpected intra-docs dead links); lint 0; 146 tests green
- 2026-06-30T18:43:41Z – claude:opus:reviewer-renata:reviewer – shell_pid=263203 – Started review via action command
- 2026-06-30T18:48:00Z – user – shell_pid=263203 – Moved to planned
- 2026-06-30T18:48:50Z – claude:sonnet:python-pedro:implementer – shell_pid=275377 – Started implementation via action command
- 2026-06-30T18:55:49Z – claude:sonnet:python-pedro:implementer – shell_pid=275377 – Cycle 1: escape guard re-scoped to non-resolving + repo-root-escape; plain --check exit=0 AND --no-exclude exit=0; _KNOWN_GAPS=frozenset() (0 entries); 146 tests green; ruff+mypy clean
- 2026-06-30T18:56:16Z – claude:opus:reviewer-renata:reviewer – shell_pid=298646 – Started review via action command
