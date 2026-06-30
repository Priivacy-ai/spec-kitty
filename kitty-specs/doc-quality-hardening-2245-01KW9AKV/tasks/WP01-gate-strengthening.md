---
work_package_id: WP01
title: 'Gate strengthening: actionable output, non-vacuity, escape-guard, --no-exclude'
dependencies: []
requirement_refs:
- C-006
- FR-001
- FR-003
- FR-004
- NFR-001
- NFR-002
- NFR-003
tracker_refs: []
planning_base_branch: design/doc-quality-hardening-2245
merge_target_branch: design/doc-quality-hardening-2245
branch_strategy: Planning artifacts for this mission were generated on design/doc-quality-hardening-2245. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/doc-quality-hardening-2245 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
phase: Lane A1
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "103946"
history:
- at: '2026-06-30T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: scripts/docs/relative_link_fixer.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- scripts/docs/relative_link_fixer.py
- tests/docs/test_relative_link_fixer.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Gate strengthening: actionable output, non-vacuity, escape-guard, --no-exclude

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

This WP strengthens the existing `check_dead_body_links` gate WITHOUT changing its scope (i.e., `EXCLUDE_PREFIXES` remains `("docs/adr/", "docs/changelog/")` throughout). After this WP:

- Every `Unresolvable` record carries a `line: int` field; failure output is `file:line -> target` per offender.
- A zero-files or zero-links scan fails loudly (non-vacuity guard, FR-004).
- A link whose normalized target escapes `docs/` is reported (not silently accepted), with a regression test (D-1).
- `relative_link_fixer.py --check --no-exclude` empties `EXCLUDE_PREFIXES` at runtime (D-3), enabling the C-007 dry-run in WP02.
- Reference-style and raw-HTML link shapes are either extended or explicitly documented as out-of-scope, with a narrowness test asserting the exemption boundary (C-006).
- `_KNOWN_GAPS` stays `frozenset[tuple[str, str]]` keyed on `(file, link)` — never `(file, link, line)` — and set-difference logic projects the gate's 3-field findings to 2-tuples (D-2 correctness trap).
- Performance-regression test: full `docs/` scan completes in < 5 s (NFR-001).
- Deliberate-breakage test: ≥ 2 planted bad links are ALL reported with correct line numbers (SC-002).
- `ruff` + `mypy` report zero issues on all new and changed code (NFR-004).
- All new tests are marked `@pytest.mark.fast`.

> **Anti-fakeability note**: These four tests convert NFR-003/FR-004/D-1/D-3 from "plausibly implemented" to objectively verified: (1) the T008 frontmatter case pins line-number correctness under real ADR/changelog frontmatter; (2) the T002 live-tree links-examined floor ensures a scope-narrowing regression goes red; (3) the T004 end-to-end spy confirms `--no-exclude` actually plumbs through `main()`, not just the internal API; (4) the T003 negative case proves the escape-guard does not over-report intra-docs traversal.

**This WP does NOT flip `EXCLUDE_PREFIXES`.** That terminal step belongs to WP02.

---

## Context & Constraints

**Primary surface**: `scripts/docs/relative_link_fixer.py` (~500 LOC — near the complexity ceiling of 15; extract helpers rather than deepening nested conditionals).

**Test surface**: `tests/docs/test_relative_link_fixer.py` (marked `pytestmark = pytest.mark.fast`).

**Key references**:
- Mission spec: `kitty-specs/doc-quality-hardening-2245-01KW9AKV/spec.md` (FR-001, FR-003, FR-004, NFR-001, NFR-002, NFR-003, C-006, C-007)
- Plan decisions: `kitty-specs/doc-quality-hardening-2245-01KW9AKV/plan.md` "Post-Plan Refinements" (D-1, D-2, D-3) — BINDING
- Research: `kitty-specs/doc-quality-hardening-2245-01KW9AKV/research.md` (R-04, R-05)
- Gate contract: `kitty-specs/doc-quality-hardening-2245-01KW9AKV/contracts/gate-contract.md`

**Architectural constraints**:
- C-003: Do NOT build a new/parallel link-checker module. The gate IS `check_dead_body_links`.
- D-2 (correctness trap): `_KNOWN_GAPS` must stay `frozenset[tuple[str, str]]` keyed on `(file, link)`. The `line` field is display-only. The `dead - _KNOWN_GAPS` set-difference must project 3-field `Unresolvable` records to 2-tuples BEFORE the subtraction. Failure to do this will cause the live-tree gate to silently pass or fail spuriously.
- `EXCLUDE_PREFIXES` is NOT touched in this WP. Do not change it.
- NFR-002: gate output must be deterministic (sort by `(file, line, link)`).
- Complexity ceiling is 15 (Ruff C901 / Sonar S3776). The file is already ~500 LOC. Extract small pure helpers rather than deepening conditionals.

---

## Branch Strategy

- **Strategy**: lanes
- **Planning base branch**: `design/doc-quality-hardening-2245`
- **Merge target branch**: `kitty/mission-doc-quality-hardening-2245-01KW9AKV`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

---

## Subtasks & Detailed Guidance

### Subtask T001 – Add `line: int` to `Unresolvable`; update construction sites and `_print_report`

- **Purpose**: Every unresolvable finding must carry the line number of the offending link so failure output is actionable (NFR-003, R-05).
- **Steps**:
  1. Add `line: int` to the `Unresolvable` dataclass at line 339:
     ```python
     @dataclass
     class Unresolvable:
         file: str
         link: str
         line: int
     ```
  2. In `check_dead_body_links` (line 423), compute line number at each `_LINK.finditer` match using:
     ```python
     line_num = body.count("\n", 0, match.start()) + 1
     ```
     Note: `body` here is AFTER the frontmatter has been stripped by `split_frontmatter`. If you need the absolute line, account for the frontmatter line count (count `"\n"` in the frontmatter string). The contract says line-in-body is acceptable; match the approach used by `test_architecture_docs_consistency.py` (which counts newlines at match offset). Keep it consistent — body-relative lines are what reviewers see in editors after stripping frontmatter.
  3. Update BOTH `Unresolvable(...)` construction sites in `check_dead_body_links` (around current line 444) to pass `line=line_num`.
  4. Update `_print_report` (line 468) to print `un.file:un.line -> un.link` instead of `un.file: un.link`. Also update the `--check` branch in `main` (line 488) similarly.
  5. Update `rewrite_body` (line 356) if it also constructs `Unresolvable` objects (it does, at line 378): you may pass `line=0` there as a sentinel since `rewrite_body` is the fix path, not the gate path — OR compute the line there too for completeness. Document which approach you chose inline.
- **Files**: `scripts/docs/relative_link_fixer.py`
- **Notes**: After this change, existing `TestLiveTreeGate` assertions (`(u.file, u.link)`) still work because they project to 2-tuples (see T006). `TestGate.test_gate_red_on_planted_broken_link` uses `[(u.file, u.link) for u in dead]` — that still compiles. No test changes are needed for T001 beyond what T006 and T008 will add.

### Subtask T002 – Non-vacuity guard (FR-004)

- **Purpose**: A zero-files or zero-links scan must fail loudly; a silent pass on an empty tree masks misconfiguration.
- **Parallel**: Yes (independent of T001's data-model change, but commit after T001 to avoid merge conflicts on `check_dead_body_links`).
- **Steps**:
  1. In `check_dead_body_links`, after the loop, add counters for files visited and links examined:
     ```python
     files_visited = 0
     links_examined = 0
     for path in iter_doc_files(repo_root):
         files_visited += 1
         ...
         for match in _LINK.finditer(body):
             parsed = parse_link_payload(match.group(1))
             if parsed is None or not is_bare_relative(parsed.path):
                 continue
             links_examined += 1
             ...
     if files_visited == 0:
         raise RuntimeError("check_dead_body_links: no doc files found under docs/")
     if links_examined == 0:
         raise RuntimeError("check_dead_body_links: zero inline body links examined — possible misconfiguration")
     ```
  2. Expose this guard so tests can exercise it. One approach: make the thresholds configurable via optional params with `min_files: int = 1, min_links: int = 1`.
  3. Add a `@pytest.mark.fast` test that passes an empty tmp_path tree and asserts the guard fires (raises or exits non-zero).
  4. **FR-004 non-vacuity live-tree floor**: Add (or extend) a test in `TestLiveTreeGate` (or a sibling live-tree test class) that asserts `links_examined >= 200` when `check_dead_body_links` is called against the real `_REPO_ROOT`. The exact threshold should be tuned to the current live tree (run the scan once and set the floor at ≈80 % of the observed count to allow organic growth without being trivially defeatable). This ensures that a future scope-narrowing — whether via an overly broad `exclude_prefixes`, a broken `iter_doc_files`, or a regex change that silently stops matching links — goes RED immediately rather than passing vacuously. A synthetic empty-tree test alone cannot detect this class of regression.
     ```python
     def test_live_tree_links_examined_meets_non_vacuity_floor(self) -> None:
         # FR-004: ensure the scan is not vacuously empty on the real docs/ tree.
         # Floor is set at ≥ 200 inline bare-relative links; adjust upward as the
         # doc set grows — never downward without a documented scope change.
         examined: list[int] = []
         # Instrument via the min_links guard: a call that raises means we went
         # below the floor; a call that passes means we met it.
         # Alternative: expose links_examined as a return value or counter attribute
         # and assert it directly — prefer that if T002's implementation supports it.
         result = check_dead_body_links(_REPO_ROOT)
         # If the guard did not raise, links_examined >= min_links threshold was met.
         # Add a direct assertion on the exposed counter if available:
         # assert check_dead_body_links.last_links_examined >= 200
         _ = result  # gate passed; non-vacuity is satisfied by absence of RuntimeError
     ```
     The preferred implementation exposes `links_examined` as part of the return value or a named counter so the floor can be asserted directly. The exact form is left to the implementer; the REQUIREMENT is that a scan examining zero or near-zero links goes RED, not green.
- **Files**: `scripts/docs/relative_link_fixer.py`, `tests/docs/test_relative_link_fixer.py`
- **Notes**: In `TestLiveTreeGate`, the live tree trivially satisfies both thresholds.

### Subtask T003 – Port the repo-escape guard (D-1)

- **Purpose**: The three retired hand-rolled checkers (to be removed in WP02) each guard against a link whose normalized target escapes the repo or `docs/`. This invariant must NOT be silently lost — it must be ported into `check_dead_body_links` (D-1: "porting wins over silent loss").
- **Steps**:
  1. In `check_dead_body_links`, after computing `current = posixpath.normpath(posixpath.join(file_dir, parsed.path))` (line 442), add an escape check BEFORE the `exists()` call:
     ```python
     # D-1: report links whose normalized target escapes docs/ rather than
     # silently accepting them via bare exists().
     if not current.startswith(DOCS_ROOT + "/") and current != DOCS_ROOT:
         dead.append(Unresolvable(file=rel, link=parsed.path, line=line_num))
         continue
     ```
  2. Add a `@pytest.mark.fast` regression test (`test_escape_guard_reports_link_escaping_docs_root`) that plants a link like `../../outside.md` in a synthetic `docs/` file and asserts it appears in the dead list even when the target happens to exist on disk.
  3. **D-1 negative (no over-reporting)**: Add a complementary `@pytest.mark.fast` test (`test_escape_guard_does_not_flag_intra_docs_traversal`) that verifies the escape-guard does NOT over-report. Specifically, a link that normalizes to a path still INSIDE `docs/` — e.g. `docs/sub/../other.md` from a file at `docs/sub/page.md` — must NOT appear in the dead list when the target file actually exists. Example:
     ```python
     def test_escape_guard_does_not_flag_intra_docs_traversal(self, tmp_path: Path) -> None:
         repo = tmp_path / "repo"
         # Create both files; the link traverses up one level but stays inside docs/.
         _write(repo / "docs/other.md", "# Other\n")
         _write(
             repo / "docs/sub/page.md",
             "# Sub\n\nSee [other](../other.md) for details.\n",
         )
         dead = check_dead_body_links(repo)
         assert not any(u.link == "../other.md" for u in dead), (
             "Intra-docs traversal (docs/sub/../other.md → docs/other.md) "
             "must NOT be flagged as an escape — over-reporting guard"
         )
     ```
     This negative case is the complement of the positive escape test and prevents the guard from becoming a false-positive source as the doc tree grows.
- **Files**: `scripts/docs/relative_link_fixer.py`, `tests/docs/test_relative_link_fixer.py`
- **Notes**: The guard runs on the normalized POSIX path, so `../../anything` from a file at `docs/adr/3.x/x.md` normalizes to something outside `docs/` and is caught. This is a correctness guard, not an exclusion — it reports, never silently accepts.

### Subtask T004 – Add `--no-exclude` CLI flag (D-3)

- **Purpose**: Enable the C-007 pre-merge full-tree dry-run (`relative_link_fixer.py --check --no-exclude`) without modifying `EXCLUDE_PREFIXES` in source. Also enables a `@pytest.mark.fast` test that exercises the flag.
- **Steps**:
  1. In `_parse_args`, add:
     ```python
     parser.add_argument(
         "--no-exclude",
         action="store_true",
         help="Run with EXCLUDE_PREFIXES=() — covers the full docs/ tree. "
              "Use for the C-007 gate-unmask dry-run.",
     )
     ```
  2. In `main`, when `args.no_exclude` is true, temporarily override `EXCLUDE_PREFIXES` before calling `check_dead_body_links`. Because `iter_doc_files` reads the module-level `EXCLUDE_PREFIXES`, the cleanest approach is to pass the effective prefixes as a parameter. Refactor `iter_doc_files` to accept an optional `exclude_prefixes: tuple[str, ...] | None = None` parameter (defaulting to the module-level constant), and thread it through `check_dead_body_links` as well.
  3. In `check_dead_body_links`, add a matching optional parameter:
     ```python
     def check_dead_body_links(
         repo_root: Path,
         *,
         exclude_prefixes: tuple[str, ...] | None = None,
     ) -> list[Unresolvable]:
         effective = EXCLUDE_PREFIXES if exclude_prefixes is None else exclude_prefixes
         ...
     ```
  4. Add a `@pytest.mark.fast` test that calls `check_dead_body_links(repo, exclude_prefixes=())` on a synthetic tree containing a dead link under `docs/adr/` and asserts the link IS reported (previously excluded, now covered).
  5. **D-3 end-to-end plumbing test**: Add a `@pytest.mark.fast` test that verifies `--no-exclude` plumbs through `main()` end-to-end — not only a direct `check_dead_body_links(exclude_prefixes=())` call (which would pass even if `main` ignores the flag). Use a spy or mock to assert that when `main(["--check", "--no-exclude", "--repo-root", str(repo)])` is called, `iter_doc_files` (or `check_dead_body_links`) is invoked with `exclude_prefixes=()`. Example pattern:
     ```python
     def test_no_exclude_flag_plumbs_through_main(self, tmp_path: Path, monkeypatch) -> None:
         repo = tmp_path / "repo"
         _write(repo / "docs/index.md", "# Hello\n")
         captured: list[tuple[str, ...]] = []
         original = check_dead_body_links
         def spy(root, *, exclude_prefixes=None):
             captured.append(exclude_prefixes if exclude_prefixes is not None else ("sentinel",))
             return original(root, exclude_prefixes=exclude_prefixes)
         monkeypatch.setattr(
             "scripts.docs.relative_link_fixer.check_dead_body_links", spy
         )
         main(["--check", "--no-exclude", "--repo-root", str(repo)])
         assert len(captured) == 1
         assert captured[0] == (), (
             f"--no-exclude must pass exclude_prefixes=() to check_dead_body_links, got {captured[0]!r}"
         )
     ```
     Adjust module path and spy target to match the actual import structure. The requirement is that the test FAILS if `main` ignores the flag and falls back to the default `EXCLUDE_PREFIXES`.
- **Files**: `scripts/docs/relative_link_fixer.py`, `tests/docs/test_relative_link_fixer.py`
- **Notes**: `TestLiveTreeGate` continues to call `check_dead_body_links(_REPO_ROOT)` without the parameter — the default behaviour is unchanged.

### Subtask T005 – Reference-style / raw-HTML link-shape coverage or documented exclusion (FR-003, C-006)

- **Purpose**: `is_bare_relative` and `_LINK` (lines 105, 157-166) currently skip reference-style links (`[text][ref]`) and raw-HTML `<a href="...">` links. FR-003 requires either extending coverage or explicitly documenting these as out-of-scope shapes with a narrowness test.
- **Steps**:
  1. Examine the live `docs/` tree to determine whether reference-style or raw-HTML links are in use. Run: `grep -r '\]\[' docs/ | head -20` and `grep -r '<a href=' docs/ | head -20`.
  2. If neither shape is used: document the exclusion in the `is_bare_relative` and `_LINK` docstrings with explicit "out-of-scope" notes. Then add a `@pytest.mark.fast` narrowness test (`test_reference_style_and_raw_html_are_documented_out_of_scope`) that: (a) asserts a string like `[text][ref]` is NOT matched by `_LINK`, and (b) asserts a string like `<a href="../foo.md">` is NOT matched by `_LINK` — confirming the boundary is intentional and pinned.
  3. If either shape IS used in the live tree: extend `_LINK` or add a second pattern and integrate it into `check_dead_body_links`. Add corresponding tests.
  4. C-006 narrowness: add a test that asserts a "too-broad" exemption would fail. For example, if you add `tel:` to the skip set in T028, verify that `is_bare_relative("tel:+1234")` returns `False` and that `is_bare_relative("telemetry/guide.md")` returns `True` (ensuring the prefix check is not over-broad).
- **Files**: `scripts/docs/relative_link_fixer.py`, `tests/docs/test_relative_link_fixer.py`
- **Parallel**: Yes (pure test/doc work, no data-model conflict with T001).
- **Notes**: The narrowness test mirrors `test_docs_adr_exemption_is_narrow` pattern referenced in the plan.

### Subtask T006 – Keep `_KNOWN_GAPS` as `(file, link)` 2-tuple; fix set-difference projection (D-2)

- **Purpose**: D-2 is a correctness trap. After T001, `Unresolvable` has 3 fields. The `dead - _KNOWN_GAPS` set-difference in `TestLiveTreeGate` would break if `_KNOWN_GAPS` stays as 2-tuples but `dead` is a set of 3-field dataclasses. Fix the projection so the gate remains correct.
- **Steps**:
  1. In `TestLiveTreeGate.test_assembled_tree_has_no_unexpected_dead_links`, update the comprehension to project explicitly:
     ```python
     dead = {
         (u.file, u.link) for u in check_dead_body_links(_REPO_ROOT)
     }
     unexpected = dead - self._KNOWN_GAPS
     ```
     The set already uses a comprehension that projects to `(file, link)` — verify this is the form after T001 (the existing code at line 306 does this). If it already projects to 2-tuples, confirm it still works after the dataclass gains `line`. This subtask is a correctness audit: read the current code, verify projection, update if needed.
  2. Confirm `_KNOWN_GAPS: Final[frozenset[tuple[str, str]]] = frozenset()` stays typed as 2-tuples. Add a type annotation comment if it helps future readers: `# (file, link) — line is display-only (D-2)`.
  3. Add a focused `@pytest.mark.fast` unit test `test_known_gaps_projection_is_2_tuple` that creates two `Unresolvable` instances with different line numbers but the same `(file, link)`, and asserts both map to the SAME 2-tuple in the set-comprehension — confirming line is correctly excluded from gap-matching.
- **Files**: `tests/docs/test_relative_link_fixer.py`
- **Notes**: This subtask must be done AFTER T001 (data-model change is a prerequisite). It is not parallel with T001.

### Subtask T007 – Performance-regression test (NFR-001)

- **Purpose**: The gate must complete < 5 s over the full `docs/` tree. Pin this as a `@pytest.mark.fast` test so it runs in every fast-shard CI run.
- **Parallel**: Yes (no code changes to the gate, pure test).
- **Steps**:
  1. Add a test class `TestGatePerformance` with a single test:
     ```python
     import time

     class TestGatePerformance:
         def test_full_docs_scan_under_5_seconds(self) -> None:
             start = time.monotonic()
             check_dead_body_links(_REPO_ROOT)
             elapsed = time.monotonic() - start
             assert elapsed < 5.0, (
                 f"Gate scan took {elapsed:.2f}s — exceeds the 5 s NFR-001 budget"
             )
     ```
  2. Mark the class or test with `@pytest.mark.fast` (the module-level `pytestmark` already applies it).
  3. The current live-tree scan is ~0.10 s, so the 5 s threshold gives ~50× headroom. This is a generous regression guard, not a tight benchmark.
- **Files**: `tests/docs/test_relative_link_fixer.py`
- **Notes**: If this test is flaky on slow CI machines, raise to 10 s — the NFR says "< 5 s" but "materially slow" is the real constraint. Document any adjustment inline.

### Subtask T008 – Actionable `(file, line, target)` failure output + deliberate-breakage test (NFR-003, SC-002)

- **Purpose**: Verify that when the gate fails, ALL offending links are reported with correct line numbers. This is the SC-002 acceptance criterion and the key output guarantee of this WP.
- **Steps**:
  1. Ensure `main` (the `--check` branch) prints one line per dead link as `file:line -> target`. After T001 updates `_print_report` and the `--check` branch, the format is `{un.file}:{un.line} -> {un.link}`.
  2. Add a `@pytest.mark.fast` test class `TestDeliberateBreakage`:
     ```python
     class TestDeliberateBreakage:
         def test_all_dead_links_reported_with_line_numbers(self, tmp_path: Path) -> None:
             repo = tmp_path / "repo"
             # Plant two bad links at known line positions in the body.
             _write(
                 repo / "docs/section/a.md",
                 "# Title\n"
                 "\n"
                 "See [first broken](../ghost/one.md) here.\n"   # line 3 in body
                 "Some prose.\n"
                 "See [second broken](../ghost/two.md) here.\n", # line 5 in body
             )
             dead = check_dead_body_links(repo)
             assert len(dead) == 2, f"Expected 2 dead links, got {len(dead)}: {dead}"
             findings = {(u.file, u.line, u.link) for u in dead}
             assert ("docs/section/a.md", 3, "../ghost/one.md") in findings
             assert ("docs/section/a.md", 5, "../ghost/two.md") in findings
     ```
  3. The exact line numbers depend on whether `line` is body-relative (after frontmatter strip) or file-absolute. Make the test consistent with the implementation choice documented in T001. Use a file with NO frontmatter so both conventions agree.
  4. Verify `≥ 2` distinct offenders are all reported (the SC-002 requirement is ≥ 2, not exactly 2).
  5. **SC-002 frontmatter case (line-number correctness under real ADR/changelog format)**: Add a SECOND test in `TestDeliberateBreakage` that uses a Markdown file WITH YAML frontmatter. Plant a bad link at a known line AFTER the frontmatter block and assert `u.line` equals the correct editor line number of the offending link (i.e., the absolute file line, accounting for the frontmatter). This pins line-number correctness under the real ADR/changelog frontmatter case — a frontmatter-free test alone cannot catch an off-by-N error introduced by the frontmatter line-count offset. Example:
     ```python
     def test_dead_link_line_reported_correctly_with_frontmatter(self, tmp_path: Path) -> None:
         repo = tmp_path / "repo"
         _write(
             repo / "docs/adr/3.x/example.md",
             "---\n"                                      # line 1
             "title: Example ADR\n"                       # line 2
             "status: accepted\n"                         # line 3
             "---\n"                                      # line 4
             "\n"                                         # line 5
             "See [dead](../ghost/missing.md) here.\n",   # line 6 — offending link
         )
         dead = check_dead_body_links(repo)
         assert len(dead) == 1
         assert dead[0].line == 6, (
             f"Expected line 6 (editor-absolute), got {dead[0].line} — "
             "frontmatter offset not accounted for correctly"
         )
     ```
     Adjust the expected line number to match the implementation's convention (body-relative vs file-absolute) as documented in T001 — the key requirement is that the value is consistent and corresponds to what an editor shows.
- **Files**: `tests/docs/test_relative_link_fixer.py`
- **Notes**: This test is NOT in parallel with T001 — it depends on the `line` field existing on `Unresolvable`. Implement after T001.

---

## Test Strategy

Run after each subtask:

```bash
pytest tests/docs/test_relative_link_fixer.py -v --tb=short
```

Run the full fast shard to catch regressions:

```bash
PWHEADLESS=1 pytest tests/ -m fast -n auto --dist loadfile -p no:cacheprovider
```

Run ruff and mypy on changed files:

```bash
ruff check scripts/docs/relative_link_fixer.py tests/docs/test_relative_link_fixer.py
mypy scripts/docs/relative_link_fixer.py tests/docs/test_relative_link_fixer.py
```

**Commit order discipline (LOC guard from plan)**:
- T001 first (data-model change — all other subtasks depend on the new `line` field).
- T006 and T008 immediately after T001 (they consume the new field).
- T002, T003, T004, T005, T007 can land in any order after T001.
- Do NOT co-land T001 with the `EXCLUDE_PREFIXES` flip — that belongs to WP02.

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| D-2 correctness trap: `_KNOWN_GAPS` set-difference silently fails after T001 adds `line` | T006 explicitly audits and pins the 2-tuple projection with a focused test. |
| Complexity ceiling: `check_dead_body_links` is already in a 500-LOC file | Extract the escape-guard check and non-vacuity logic as named helpers; keep functions ≤ 15 cyclomatic complexity (Ruff C901). |
| Line-number off-by-one: frontmatter offset | Decide body-relative vs file-absolute ONCE in T001 and document it; T008's test uses a frontmatter-free file so both conventions agree. |
| `--no-exclude` breaks `TestLiveTreeGate` if the live tree has dead links under excluded subtrees | T004 adds a synthetic test; `TestLiveTreeGate` is unaffected because it does not use `--no-exclude`. WP02's T030 is the live-tree dry-run. |
| `rewrite_body` also constructs `Unresolvable` — missed construction site | T001 explicitly enumerates both construction sites (line 378 in `rewrite_body`; line 444 in `check_dead_body_links`). |

---

## Review Guidance

The reviewer (`reviewer-renata`) should check:

1. **T001**: Both `Unresolvable` construction sites updated; `_print_report` and `main --check` branch both emit `file:line -> target` format.
2. **T002**: Non-vacuity guard fires on an empty tree (test proves it); live tree trivially passes.
3. **T003**: Escape-guard regression test uses a synthetic tree where the escaped target EXISTS on disk — verifying that existence is not the only check.
4. **T006**: `_KNOWN_GAPS` type annotation remains `frozenset[tuple[str, str]]`; projection comprehension is `{(u.file, u.link) for u in ...}` — not `{u for u in ...}` or any 3-field form.
5. **T007**: Performance test threshold is documented; any adjustment from 5 s is explained.
6. **T008**: Deliberate-breakage test asserts ≥ 2 offenders, each with a specific `line` number, and the assertion is not vacuous (the file actually has no frontmatter so the line numbers are unambiguous).
7. **`EXCLUDE_PREFIXES` unchanged**: confirm the constant at lines 93-96 is identical to the pre-WP01 value `("docs/adr/", "docs/changelog/")`.
8. **ruff + mypy clean**: zero issues on changed files.

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
- 2026-06-30T17:39:41Z – claude:sonnet:python-pedro:implementer – shell_pid=8739 – Assigned agent via action command
- 2026-06-30T17:58:06Z – claude:sonnet:python-pedro:implementer – shell_pid=8739 – Ready for review. Implemented T001-T008: Unresolvable.line field (file-absolute, frontmatter-offset-aware); non-vacuity guard (min_files/min_links params + FR-004 live-tree floor at 1000); D-1 escape guard (_is_link_intra_docs helper, synthetic + negative tests); --no-exclude flag plumbed through main() with end-to-end spy test; C-006 narrowness class (reference-style/raw-HTML out-of-scope pins); D-2 2-tuple projection audit + focused test; performance test <5s; deliberate-breakage tests (≥2 offenders + frontmatter-offset test). _KNOWN_GAPS populated with 54 pre-existing cross-section references surfaced by D-1. ruff exit 0, mypy --explicit-package-bases exit 0 (path-resolution issue is pre-existing). 42 tests all pass in 27s.
- 2026-06-30T17:59:44Z – claude:opus:reviewer-renata:reviewer – shell_pid=103946 – Started review via action command
- 2026-06-30T18:03:50Z – user – shell_pid=103946 – Review passed (reviewer-renata). T001-T008 all met. T001: line:int added (file-absolute, frontmatter-offset-aware via fm_lines); both construction sites updated (check=line_num, rewrite_body=0 sentinel, documented); _print_report + main --check emit 'file:line -> link'. T002: non-vacuity guard raises on zero files/links; live floor min_links=1000 vs observed 1360 (~73%, meaningful not vacuous). T003: D-1 escape guard via _is_link_intra_docs, fires before exists(); positive (escaped target EXISTS on disk) + negative (intra-docs ../traversal NOT flagged) tests both present. T004: --no-exclude plumbed main->check_dead_body_links->iter_doc_files; end-to-end spy proves exclude_prefixes=() passed via main(). T005: TestLinkShapeCoverage pins ref-style/raw-HTML out-of-scope + is_bare_relative over-exclude narrowness. T006: _KNOWN_GAPS stays frozenset[tuple[str,str]]; projection {(u.file,u.link)}; focused test proves two Unresolvable differing only in line collapse to one 2-tuple. T007: perf <5s. T008: deliberate-breakage (2 offenders, lines 3/5) + frontmatter case asserts editor-absolute line 6. EXCLUDE_PREFIXES unchanged ('docs/adr/','docs/changelog/'). _KNOWN_GAPS ASSESSMENT: 54 entries are LEGITIMATE escapes-that-exist — verified all 54 resolve on disk (0 genuinely dead/masked), and allowlist is exactly tight (54==live dead set, 0 over-broad, 0 unexpected). No intra-docs dead link is masked (escape guard only flags cross-section escapes; exists()-check failures would surface in unexpected). ruff+mypy --explicit-package-bases clean; 42/42 tests pass.
