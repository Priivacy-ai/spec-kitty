# Implementation Plan: Stop the literal-`${…}`-filename test leak and guard it

**Branch**: `fix/cmd-output-file-leak-guard` | **Issue**: #2169 | **Spec**: [spec.md](./spec.md)

## Summary

Fix the one test double that leaks a `"${SPEC_KITTY_CMD_OUTPUT_FILE}"`-named junk file, and add a class-closing architectural guard so it can never reach Windows CI again. The leaker is `fake_run_with_xml` (`tests/review/test_baseline.py:~807-833`): it regex-parses `--output=(\S+)` from the command and `write_text`s the captured literal shell-form as a **relative** path into cwd, ignoring `kwargs["env"]` — so it leaks whether or not `SPEC_KITTY_CMD_OUTPUT_FILE` is set. Fix = make it write to `kwargs["env"]["SPEC_KITTY_CMD_OUTPUT_FILE"]` (mirroring its safe sibling fakes at ~253/294/338) or run under a `tmp_path` cwd (FR-001/002). Then add a cheap `tests/architectural/` guard asserting no `git ls-files` path contains a Windows-forbidden char, **registered in `tests/_arch_shard_map.py`** so the **sharded** (#2397) always-on `arch-adversarial` pole selects it — an unregistered `tests/architectural/` file gets no `arch_shard_N` marker, so it is silently deselected on all 3 shards AND turns `test_arch_shard_marker_completeness.py` RED (FR-003/004, NFR-001). The product (`configured_command.py`) is correct and untouched; `test_configured_command.py` is inert.

## Technical Context

**Language/Version**: Python 3.11 (repo pinned)
**Primary Dependencies**: `pytest`, `re`, `pathlib`; `git ls-files` for the guard
**Storage**: n/a
**Testing**: `tests/review/test_baseline.py` (the leaking fake + its assertions); a new `tests/architectural/` filename guard
**Target Platform**: CI (incl. the Windows-critical job) + local
**Project Type**: single project (test-infra fix + one architectural guard)
**Performance Goals**: guard runs well under 1s (git-ls-files/grep)
**Constraints**: no change to `configured_command.py`; `mypy --strict` + `ruff` clean; no new suppressions; guard must carry `pytest.mark.architectural`
**Scale/Scope**: 2 files — `test_baseline.py` (fix one fake) + a new `tests/architectural/test_*.py` guard

## Charter Check

*GATE: must pass before task decomposition.*

- **Evidence-first / non-vacuous (red-first)** — the leak is reproduced RED from a scratch cwd before the fix; the guard is proven to fire on a forbidden-char filename. ✅
- **Root-caused, not guessed** — post-spec squad + independent verification pinned the sole leaker (env-independent test-double bug), corrected the spec. ✅
- **Canonical sources** — mirror the existing safe sibling fakes; reuse the always-on arch selector; do not touch the correct product. ✅
- **Draft-PR-first / operator decides** — lands as a cross-fork draft; operator merges. ✅
- **Quality gates** — `ruff` + `mypy --strict` clean, no new suppressions. ✅

No violations → Complexity Tracking not required.

## Project Structure

### Documentation (this mission)
```
kitty-specs/cmd-output-file-leak-guard-01KWVZX7/
├── spec.md · plan.md · tasks.md
```

### Source / deliverables (repository root)
```
tests/review/test_baseline.py                          # fix fake_run_with_xml to write to the env path / tmp cwd; FR-001/002
tests/architectural/test_no_invalid_windows_filenames.py   # NEW: forbidden-char tracked-filename guard, arch_shard_N marker; FR-003/004
tests/_arch_shard_map.py                               # register the new guard in an _ARCH_SHARD_N_FILES tuple (#2397); NFR-001
```

**Structure Decision**: single project; fix one leaking fake + add one architectural guard (registered in the sharded arch pole).

## Implementation Concern Map

### IC-01 — Fix the leaking test double
- **Purpose**: stop `fake_run_with_xml` writing the literal `"${…}"` name into cwd.
- **Relevant requirements**: FR-001, FR-002; SC-001, SC-003; C-001.
- **Affected surfaces**: `tests/review/test_baseline.py` `fake_run_with_xml` (~807-833). Replace the `re.search(r"--output=(\S+)")` + `Path(m.group(1)).write_text(...)` with `Path(kwargs["env"]["SPEC_KITTY_CMD_OUTPUT_FILE"]).write_text(...)` (mirror the safe siblings at ~253/294/338); if the test intentionally exercises the `--output=` parse, run it under a `tmp_path` cwd so any write stays in the sandbox. Keep the custom-runner-label assertion intact (C-001).
- **Sequencing/depends-on**: none.
- **Risks**: the test asserts on the parsed `--output=` value — preserve that assertion; only redirect the write target.

### IC-02 — Architectural forbidden-char filename guard
- **Purpose**: fail any PR whose tracked tree contains a Windows-illegal filename, before Windows checkout.
- **Relevant requirements**: FR-003, FR-004; NFR-001; SC-002.
- **Affected surfaces**: NEW `tests/architectural/test_no_invalid_windows_filenames.py` — enumerate `git ls-files`, assert no path component contains `<>:"\|?*` or `${}` (drive-letter `:` excepted), fail listing the offender. **Register it in `tests/_arch_shard_map.py`** by adding its path to an `_ARCH_SHARD_N_FILES` tuple (#2397) so `shard_for()` assigns an `arch_shard_N` marker — WITHOUT this it is silently deselected on all 3 shards AND `test_arch_shard_marker_completeness.py` goes RED. Do NOT rely on a bare `architectural`/`fast`/`unit` marker.
- **Sequencing/depends-on**: independent of IC-01. The shard-map registration and the new guard file land together (registering a not-yet-existing file, or a file that isn't registered, both break the completeness gate).
- **Risks**: silent CI deselection + a RED completeness gate if unregistered (NFR-001) — verify under `-m 'arch_shard_<N> and not windows_ci and (git_repo or integration or architectural)'` and that `test_arch_shard_marker_completeness.py` is green. False positives on legitimate `:` in paths — exclude the drive-letter/URL-ish cases precisely.

### IC-03 — Non-vacuous proof + green
- **Purpose**: prove both the leak fix and the guard are real, not green-by-construction.
- **Relevant requirements**: FR-004; SC-001, SC-002, SC-003.
- **Affected surfaces**: reproduce SC-001 (scratch-cwd run leaks RED pre-fix, clean post-fix, env-independent); mutation-check the guard (a forbidden-char tracked file → RED); confirm the guard is selected by the arch selector; full `test_baseline.py` + the new guard green; ruff + mypy clean.
- **Sequencing/depends-on**: IC-01, IC-02.
- **Risks**: the guard witness must add a real tracked file (or simulate the ls-files output) so the RED is genuine.
