# Mission Specification: Stop the literal-`${…}`-filename test leak and guard it

**Status**: Draft
**Issue**: [#2169](https://github.com/Priivacy-ai/spec-kitty/issues/2169)

## User Scenarios & Testing *(mandatory)*

**Primary actor**: a contributor running the test suite locally (or CI), and the Windows CI job.

**Problem (root-caused, post-spec)**: exactly one test double leaks a junk file into the working tree. `fake_run_with_xml` in `tests/review/test_baseline.py` (lines ~807-833, `test_capture_baseline_custom_test_runner_label`) regex-parses the command string — `m = re.search(r"--output=(\S+)", cmd_text)` — then `Path(m.group(1)).write_text(...)`. The command carries the shell-safe form `--output="${SPEC_KITTY_CMD_OUTPUT_FILE}"`, so the regex captures the **literal** `"${SPEC_KITTY_CMD_OUTPUT_FILE}"` and writes a file with that exact name **as a relative path into the current working directory**. The fake **ignores** `kwargs["env"]` (where the real resolved path lives) and the `cwd` passed to `subprocess.run` — so it leaks **regardless of whether `SPEC_KITTY_CMD_OUTPUT_FILE` is set or unset**. Its sibling fakes (lines ~253/294/338) do it correctly: `Path(kwargs["env"]["SPEC_KITTY_CMD_OUTPUT_FILE"]).write_text(...)`.

The junk name contains `"`, `$`, `{`, `}` — forbidden in Windows filenames. It was swept into a commit by `git add -A` on **PR #2161**, and `git checkout` then exited 128 on Windows, breaking the **Windows critical CI job** (run 28224079685).

**What this is NOT** (corrected from the original diagnosis): it is **not** an unset-env-var issue and **not** a product bug. `configured_command.py` always couples the shell form with `env={**os.environ, **substitution_env}` (the resolved path), and a real `sh -c` with the var unset creates **no** file — so there is no "product hardening" fix. `tests/specify_cli/test_configured_command.py` is **inert** (fully mocks subprocess, 0 filesystem writes) — not an emitter.

### User Story 1 - The leaking test double writes to the real target, not the literal (Priority: P1)
As a contributor, I want `test_capture_baseline_custom_test_runner_label` to never write a `"${…}"`-named file into the working tree — regardless of the `SPEC_KITTY_CMD_OUTPUT_FILE` environment value — so `git status`/`git add -A` never pick up a junk file.

**Independent test**: run that test from a scratch cwd with the var unset **and** with it set to a valid path; the cwd stays clean in both cases (no `"${SPEC_KITTY_CMD_OUTPUT_FILE}"`).

### User Story 2 - A future invalid-name leak fails fast, before Windows CI (Priority: P1)
As a maintainer, I want a cheap architectural test that fails if **any** tracked filename contains a character forbidden in Windows paths, so this class of leak is caught on **every** PR (via the always-on arch pole) instead of exit-128 on Windows checkout.

### User Story 3 - The fix mirrors the safe siblings (Priority: P2)
As a maintainer, I want the fix to make the leaking fake read `kwargs["env"]["SPEC_KITTY_CMD_OUTPUT_FILE"]` (as sibling fakes already do) or run under a `tmp_path` cwd — a minimal, consistent correction, not a rewrite of the substitution machinery.

### Edge Cases
- Var set to a valid path vs unset — the leak (and the fix) are identical either way (env-independent).
- Another emitter parses `--output=` similarly — the architectural filename guard still catches any resulting tracked file; note it if found.
- The guard must be selected by the always-on `arch-adversarial` CI pole (not silently deselected — see NFR-001).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
| --- | --- | --- | --- | --- |
| FR-001 | Both `--output=` parsers write to the real target | As a contributor, I want **both** `--output=` parsers in `test_capture_baseline_custom_test_runner_label` — the wired `fake_run_with_xml` (~807) AND the dead-but-copy-paste-ready twin `fake_run` (~789) — to stop writing the parsed literal into cwd (write to `kwargs["env"]["SPEC_KITTY_CMD_OUTPUT_FILE"]` / a `tmp_path` cwd, or delete the dead twin), so no `"${…}"` file is created, env-independently and with no re-leak-ready copy left behind. | High | Open |
| FR-002 | Zero working-tree residue | As a contributor, I want running `tests/review/test_baseline.py` (the emitter) to leave `git status --porcelain` with no new untracked entry, whether `SPEC_KITTY_CMD_OUTPUT_FILE` is set or unset. | High | Open |
| FR-003 | Forbidden-filename guard (two named sets) | As a maintainer, I want a cheap `tests/architectural/` test over `git ls-files` failing on two **distinct, named** sets: (1) **Windows-illegal** `<>:"\|?*` (`:` off drive-prefix — the `"` is the actual #2161 CI-breaker), and (2) **shell-expansion leak telltales** `$ { }` (Windows-legal, but a leak signature). Fail listing the offender + which set matched — not conflating the two. | High | Open |
| FR-004 | Non-vacuous guard pins the real contract | As a maintainer, I want the mutation proof to include a **genuinely-Windows-illegal** tracked filename (e.g. `a"b.txt`, the CI-breaker class) turning the guard RED — not only a harmless `${}` name — plus a `${}`-telltale case, so the proof pins FR-003's Windows-illegal contract, not just the incidental arm. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| NFR-001 | Guard runs on every PR (registered in the shard map) | The arch pole is **sharded** (#2397): selector `-m '${{ matrix.shard }} and not windows_ci and (git_repo or integration or architectural)'`, `matrix.shard ∈ {arch_shard_1,2,3}` (`ci-quality.yml:1816`). A `tests/architectural/` file earns an `arch_shard_N` marker **only if registered** in `tests/_arch_shard_map.py` (`_ARCH_SHARD_N_FILES`); unregistered → `shard_for()` returns `None` → no marker → silently deselected on all 3 shards **and** `test_arch_shard_marker_completeness.py` goes RED. So the guard MUST be added to an `_ARCH_SHARD_N_FILES` tuple. Acceptance: it executes under `-m 'arch_shard_<N> and not windows_ci and (git_repo or integration or architectural)'` and the completeness gate stays green. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| C-001 | Preserve the test's intent | `test_capture_baseline_custom_test_runner_label` keeps asserting the custom-runner label behavior it was written for; only the leaking write is corrected. | Technical | High | Open |
| C-002 | No new suppressions | `ruff` + `mypy --strict` clean; no new `# type: ignore` / `# noqa`. | Technical | High | Open |
| C-003 | Bounded scope (3 files) | Change spans `tests/review/test_baseline.py` (the one leaking fake), a new `tests/architectural/` filename guard, and `tests/_arch_shard_map.py` (register the guard in an `_ARCH_SHARD_N_FILES` tuple). **Not** `test_configured_command.py` (inert) and **not** `configured_command.py` (the product is correct). Distinct from #1842/#1634 (separate mission). | Technical | High | Open |

### Key Entities
- **`fake_run_with_xml`** (`tests/review/test_baseline.py:~807-833`) — the sole leaker: parses `--output=(\S+)` and writes the literal to a relative cwd path, ignoring `kwargs["env"]`.
- **the safe sibling fakes** (`~253/294/338`) — read `kwargs["env"]["SPEC_KITTY_CMD_OUTPUT_FILE"]`; the fix pattern to mirror.
- **the invalid-Windows-char filename guard** (new `tests/architectural/` test) — the class-closing backstop.
- **`tests/_arch_shard_map.py`** — the arch-pole shard registration table (#2397); the new guard must be added to an `_ARCH_SHARD_N_FILES` tuple to earn its `arch_shard_N` marker, or it is deselected AND breaks `test_arch_shard_marker_completeness.py`.

## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-001**: Running `test_capture_baseline_custom_test_runner_label` from a scratch cwd leaves that cwd with **no** new file (no `"${…}"`), with `SPEC_KITTY_CMD_OUTPUT_FILE` both **unset** and **set** — reproduced RED before the fix, GREEN after.
- **SC-002**: The guard goes RED on a genuinely-Windows-illegal tracked filename (e.g. `a"b.txt`) **and** on a `${}`-telltale name, GREEN on the clean tree (red-first proof); it is registered in `tests/_arch_shard_map.py`, confirmed selected under the live per-shard selector `-m 'arch_shard_<N> and not windows_ci and (git_repo or integration or architectural)'`, and `test_arch_shard_marker_completeness.py` stays green.
- **SC-003**: `ruff` + `mypy --strict` clean on all touched files; `tests/review/test_baseline.py` still passes with its original assertions intact.

## Out of Scope
- The broader test-suite state-leak classes (#1842) and the `test-feature-*` scratch-mission leak (#1634) — separate mission (M2 umbrella).
- Any change to `configured_command.py` / the shell-substitution machinery (the product is correct).
- `tests/specify_cli/test_configured_command.py` (inert — no leak).

## Assumptions
- `fake_run_with_xml` is the sole active emitter (empirically confirmed post-spec: `test_configured_command.py` writes nothing; the product path always injects the env). The guard covers any other emitter by catching the resulting tracked file.
- The Windows-forbidden character set is `<>:"/\|?*` (plus the shell `${}` that appear in this specific leak); the guard targets that set for tracked paths.
