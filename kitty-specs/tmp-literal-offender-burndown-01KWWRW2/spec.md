# Mission Specification: Burn down the 99 grandfathered /tmp-literal test offenders + retire the ratchet baseline

**Status**: Draft
**Issues**: Closes [#1842](https://github.com/Priivacy-ai/spec-kitty/issues/1842) (the existing-offender sweep #2181 explicitly deferred to #1842)

## User Scenarios & Testing *(mandatory)*

**Primary actor**: a contributor whose local test run disagrees with CI because a test reads/writes shared `/tmp` and is poisoned by what an earlier run (or another repo's run) left there.

**Grounding**: PR #2181 landed the frozen `/tmp` ratchet (`tests/architectural/test_no_tmp_paths_in_tests.py`) — it blocks *new* literal `/tmp/` paths in tests but **grandfathered ~99 existing offenders** into `tmp_ratchet_baseline.txt` and **explicitly deferred their remediation to #1842** (ratchet docstring: *"their sweep belongs to issue #1842, out of scope here"*; maintainer #1842 comment: *"this issue remains open pending the full existing-offender sweep"*). This mission is that sweep. The structural prevention (session reaper + `/tmp` prompt namespacing + workspace-context tombstone) ships separately in #2429 ("Part of #1842").

**Two offender categories (census of the 99 on-disk baseline files)**:
- **A — genuine write-to-`/tmp` leaks (~68)**: tests `mkdir`/`open`/`write_text`/`makedirs` under a literal `/tmp/...` path → residue survives the run, poisons later runs. **Fix**: route through `tmp_path`/a fixture with teardown.
- **B — path-literal-only (~31)**: `/tmp/...` used as an *arbitrary absolute path* in test data, mocks, or assertions that **never touch disk** (e.g. `AttackVector("absolute_path", "/tmp/research/", ...)`, `Path("/tmp/config.toml")` as a mocked `config_file`, `mock_cwd.return_value = Path("/tmp/external-worktree")`). **Fix**: replace with a non-`/tmp` absolute sentinel (or a `tmp_path`-derived value) that preserves exactly what the test asserts (absolute-path handling, mock identity) — **not** a blind `tmp_path` swap that would change the test's meaning.

### User Story 1 - No test poisons shared /tmp (Priority: P1)
As a contributor, I want every grandfathered test off literal `/tmp` — real leaks isolated to `tmp_path`, path-literals to non-`/tmp` sentinels — so no test leaves residue or depends on shared `/tmp` state, and local runs match CI.

**Independent test**: after conversion, `grep -rn '/tmp/' tests/ --include=*.py` matches nothing outside the (now-empty) baseline; every converted test still passes with its original assertions intact.

### User Story 2 - The ratchet becomes a hard gate (Priority: P1)
As a maintainer, I want the baseline emptied and the ratchet flipped from "frozen baseline (>50 grandfathered)" to a **hard gate**: *no* literal `/tmp/` in any test file. The anti-vacuity `>50` floor (which an empty baseline would fail) is replaced by a **positive self-test** proving the gate flags a synthetic offender.

### Edge Cases
- A category-B literal that tests **Windows** absolute paths (`C:\...`) alongside `/tmp/` — keep the cross-platform intent; the POSIX literal becomes a POSIX sentinel, not a `tmp_path`.
- A literal that is a **substring in an assertion message** — convert the source path AND the expected string together so the assertion still matches.
- A file where `/tmp/` appears only in a **comment/docstring** — still trips the grep-based ratchet; must be removed/reworded.
- Converting must never **weaken** a test (no `xfail`/skip/delete/assertion-loosening to satisfy the gate — that is the anti-pattern the ratchet exists to prevent).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
| --- | --- | --- | --- | --- |
| FR-001 | Convert category-A write-leaks to tmp_path/fixtures | As a contributor, I want the ~68 offenders that create filesystem state under `/tmp/` routed through `tmp_path`/fixtures with teardown, preserving each test's behavior. | High | Open |
| FR-002 | Convert category-B path-literals to non-/tmp sentinels | As a contributor, I want the ~31 offenders using `/tmp/...` as an arbitrary absolute path (mocks/test-data/assertions, never written) replaced with a non-`/tmp` absolute sentinel or `tmp_path`-derived value that preserves the exact assertion/mock semantics. | High | Open |
| FR-003 | Empty the ratchet baseline | As a maintainer, I want all 99 entries removed from `tmp_ratchet_baseline.txt` (baseline → empty). **Census correction (disk-verified):** only **98** entries still contain a live `/tmp/` literal; **1 is stale** — `tests/specify_cli/cli/commands/test_review.py` no longer contains `/tmp/`, so it needs no conversion, just removal from the baseline. **Automated guard (not a manual checkbox):** a test MUST assert `_load_baseline()` is **empty** (or ≤ the C-003-documented residual set with rationale) — otherwise a converted-but-still-baselined file yields 0 violations and every gate passes green while the baseline silently re-grandfathers files, recreating the exact false-green class this mission closes. | High | Open |
| FR-004 | Flip the ratchet to a hard gate (self-consistent) | As a maintainer, I want `test_no_tmp_paths_in_tests.py` changed so an empty baseline is the healthy state (no literal `/tmp/` in `tests/`); replace `test_baseline_is_non_empty_anti_vacuous` (the `>50` floor) with a **positive self-test** that a synthetic `/tmp/` file IS flagged by `_collect_violations`. **Self-reference fix (blocking) — make the gate file GENUINELY literal-free (all 14 lines):** the gate file is itself one of the baseline's own entries and carries **14** literal `/tmp/` lines: the `_TMP_LITERAL` needle (:73), the self-test payload (:182), **plus 12 in docstrings/comments (lines 4,13,22,83,110,133,143,147,170) and assertion-message strings (:157,:158,:185)**. Fragment-constructing only the needle keeps `_collect_violations` green but leaves SC-001's raw grep matching the other 13 (a split-brain false-green). Mirror the precedent `test_no_legacy_terminology.py` fully: (a) **string-fragment-construct** the needle AND the self-test payload; (b) **reword** every docstring/comment/assertion-message occurrence so no literal `/tmp/` remains; (c) **ADD** a `Path(__file__).resolve()` self-exclude to `_collect_violations` (it does **not** exist today — the gate currently avoids self-flagging only via its baseline membership, which disappears when the baseline empties) as belt-and-suspenders (secondary — literal-freedom is primary). Acceptance MUST run SC-001's exact grep against the gate file itself and assert **0** — not a grep `--exclude` (the C-003 gaming path). | High | Open |
| FR-005 | Every converted test stays green; full gate green | As a maintainer, I want each touched test to still pass with intact assertions, and the ratchet to report **0 violations** across `tests/`. | High | Open |
| FR-006 | Non-vacuous proof (via the real gate path) | As a maintainer, I want the positive self-test to exercise the **empty-baseline `_collect_violations` path**, not a shortcut. `_collect_violations` walks the repo `tests/` root, so a `tmp_path` offender is invisible to it — the test must make the root/baseline **injectable** (add a `tests_root`/`baseline` param, cleanest) or `monkeypatch` `_TESTS_ROOT` + `_REPO_ROOT` + `_BASELINE_FILE` to a seeded tmp dir; then assert `_collect_violations(<empty baseline>)` returns **exactly** the synthetic offender AND returns `[]` once it's removed. **Forbidden**: proving non-vacuity via `scan_file_for_tmp_literal` (it bypasses the baseline-skip logic the floor-replacement exists to cover). Plus: category-A conversions leave no `/tmp` residue. | High | Open |
| FR-007 | Category-A fix is real isolation, not evasion | As a maintainer, I want every category-A converted file to demonstrably route through `tmp_path`/a teardown fixture — verified by a check that the touched cat-A set *adopts* `tmp_path`/fixtures (grep/AST), not merely that the `/tmp/` substring is gone. **Explicitly forbidden** (all evade the substring ratchet while still leaking): swapping `/tmp/` → `/dev/shm/`, `/scratch/`, `/var/tmp/`, etc.; an uncleaned `tempfile.mkdtemp()`/`gettempdir()` with no teardown. A converted cat-A test must leave zero filesystem residue outside its `tmp_path`. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| NFR-001 | No masking / no weakening | No test is `xfail`ed, skipped, deleted, or has an assertion loosened to pass the gate. Every conversion preserves the test's original intent and coverage. | Integrity | High | Open |
| NFR-002 | Deterministic + isolated | Converted tests use per-test isolation (`tmp_path`) or pure in-memory literals — no shared mutable path, no cross-run dependence. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| C-001 | Preserve category-B intent | A category-B literal that tests absolute-path rejection / mock identity must still test exactly that (a POSIX absolute sentinel, not a fixture path that could be relative or change meaning). | Technical | High | Open |
| C-002 | No new suppressions | `ruff` + `mypy --strict` clean on every touched file; no new `# noqa`/`# type: ignore`. | Technical | High | Open |
| C-003 | Baseline stays sorted/authoritative | If any entries genuinely cannot be converted this pass, they remain in the (documented) baseline with a rationale — the goal is empty, but the gate must never be gamed. | Technical | Medium | Open |

### Key Entities
- **`tests/architectural/tmp_ratchet_baseline.txt`** — the 99-entry frozen baseline (98 live + 1 stale `test_review.py`) → empty.
- **`tests/architectural/test_no_tmp_paths_in_tests.py`** — the ratchet; `_collect_violations`, `_BASELINE_FLOOR=50`, `test_baseline_is_non_empty_anti_vacuous` (→ positive self-test); `_TMP_LITERAL` needle (→ fragment-constructed) + `__file__` self-exclude. Itself a baseline entry.
- **The 98 live offender files** — 22 dirs: `specify_cli` (30), `sync` (13), `charter` (7), `doctrine` (6), `agent` (6), `status` (4), long tail (~32).

## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-001**: `grep -rn '/tmp/' tests/ --include='*.py'` returns **0** matches (including the gate file, whose needle is now fragment-constructed — no grep `--exclude`); `tmp_ratchet_baseline.txt` is empty.
- **SC-002**: The ratchet gate reports 0 violations; the new positive self-test flags a synthetic offender (red-first proven); the gate does not flag itself (fragment needle + `__file__` self-exclude).
- **SC-003**: Every touched test file passes with original assertions intact (no xfail/skip/delete/loosening).
- **SC-004**: `ruff` + `mypy --strict` clean; no new suppressions.
- **SC-005**: Category-A conversions leave no filesystem residue outside `tmp_path` — verified across the cat-A set (tmp_path/fixture adoption check per FR-007), not a single sample; none evade via `/dev/shm`, `/scratch`, or uncleaned `mkdtemp`.

## Out of Scope
- The structural prevention — session reaper, `/tmp` prompt-writer namespacing, workspace-context tombstone — ships in **#2429** ("Part of #1842").
- Non-`/tmp` test-hygiene classes (already fixed per the #1842 re-audit).

## Assumptions
- The category split (A ~68 / B ~31) is a heuristic; each file's true category is determined at conversion time.
- Emptying the baseline + a hard gate is the intended end state (per #2181's "frozen ratchet → full remediation" design and the maintainer's #1842 comment).
