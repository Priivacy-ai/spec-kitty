---
work_package_id: WP02
title: Intake Security & Atomic Writes
dependencies: []
requirement_refs:
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- FR-012
- NFR-003
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
agent: "claude:opus-4-7:implementer:implementer"
shell_pid: "82553"
history:
- at: 2026-04-26T07:36:00Z
  actor: claude
  note: WP scaffolded by /spec-kitty.tasks
authoritative_surface: src/specify_cli/intake/
execution_mode: code_change
mission_id: 01KQ4ARB0P4SFB0KCDMVZ6BXC8
mission_slug: stability-and-hygiene-hardening-2026-04-01KQ4ARB
owned_files:
- src/specify_cli/intake/**
- tests/unit/intake/**
- tests/integration/test_intake_size_cap.py
- tests/integration/test_intake_atomic_writes.py
tags: []
---

# WP02 — Intake Security & Atomic Writes

## Objective

`spec-kitty intake` accepts third-party plan documents and turns them into
a mission brief that downstream agent runs read. Today it has six classes of
boundary bugs: provenance lines that can break out of comments and inject
prompt content; path scanning that follows symlinks out of the intake root;
unbounded reads on oversized inputs; non-atomic brief writes; missing-vs-
corrupt errors that get swallowed; and inconsistent root selection between
scan and write. This WP closes all six.

## Context

The contract surface for intake is documented in
[`contracts/intake-source-provenance.md`](../contracts/intake-source-provenance.md).
The decisions behind these fixes are documented in `research.md` D6 and D7.

## Branch strategy

- **Planning base**: `main`.
- **Final merge target**: `main`.
- **Lane workspace**: assigned by `finalize-tasks`. Use
  `spec-kitty agent action implement WP02 --agent <name>` to enter the
  workspace.

## Subtasks

### T007 — Provenance escape helper

**Purpose**: A `source_file:` line written into a markdown comment cannot
break out of the comment, inject markdown headings, or smuggle prompt
content into downstream agent runs.

**Steps**:

1. Add `src/specify_cli/intake/provenance.py:escape_for_comment(s: str) -> str`.
   - Strips ASCII control chars (0x00-0x1F, 0x7F) except `\t`.
   - Replaces `-->` with `--&gt;`, `*/` with `*&#47;`, leading `#` (line
     start) with `\\#` when targeting Markdown context.
   - Clips to 256 bytes (UTF-8 safe truncation).
2. Wire all callers that write provenance lines through this helper.
3. Add `tests/unit/intake/test_provenance_escape.py` covering each rule
   in isolation and a property-test-style trial of random byte strings.

**Validation**:
- All test cases pass.
- `grep -nE "source_file" src/specify_cli/intake/` shows the helper in
  every code path that writes provenance.

### T008 — Path canonicalization + symlink guard

**Purpose**: Plan source scanning cannot escape the intake root via
traversal or symlinks.

**Steps**:

1. In `src/specify_cli/intake/scanner.py`, replace any direct
   `path.exists()` / `open(path)` with a guarded helper:
   - Compute `intake_root_resolved = Path(intake_root).resolve(strict=True)`.
   - For each candidate, compute `candidate.resolve(strict=True)` and
     assert `candidate_resolved.is_relative_to(intake_root_resolved)`.
   - If false, raise `INTAKE_PATH_ESCAPE` with both paths.
2. The check happens BEFORE the file is opened. Symlinks that point
   outside the root are rejected.
3. Add `tests/unit/intake/test_traversal_symlink_block.py`:
   - Direct traversal: `../etc/passwd`.
   - Absolute path traversal: `/etc/passwd`.
   - Symlink inside root pointing outside.

**Validation**:
- All cases produce `INTAKE_PATH_ESCAPE` and zero file reads.
- Legitimate paths inside the root continue to read.

### T009 — Size cap before full read

**Purpose**: Reject oversized plan files before reading them entirely
into memory.

**Steps**:

1. Read `intake.max_brief_bytes` from `.kittify/config.yaml` (default
   `5_242_880`).
2. In `src/specify_cli/intake/scanner.py:read_brief()`:
   - Try `os.stat(path).st_size`. If `> cap`, raise `INTAKE_TOO_LARGE`
     before opening.
   - Else if size unknown (e.g., piped STDIN), use `read1(cap + 1)`.
     If returned bytes > cap, raise `INTAKE_TOO_LARGE`.
3. Add `tests/integration/test_intake_size_cap.py`:
   - 50 MB random file → rejected, peak RSS ≤ 1.5 × cap (NFR-003).
   - 4 MB file → accepted.
   - STDIN of 6 MB → rejected.

**Validation**:
- Peak resident memory under 1.5 × cap during 50 MB rejection (use
  `resource.getrusage(resource.RUSAGE_SELF)`).
- All test cases pass.

### T010 — Atomic write helpers

**Purpose**: A killed writer never strands a half-written brief on disk.

**Steps**:

1. In `src/specify_cli/intake/brief_writer.py`, route brief writes
   through `safe_commit` from `specify_cli.git`:
   ```python
   with open(target_tmp, "wb") as f:
       f.write(payload)
       f.flush()
       os.fsync(f.fileno())
   os.replace(target_tmp, target)
   ```
2. Pre-condition: `target_tmp` and `target` share a filesystem (same
   directory). If they do not (cross-fs intake_root), fail loudly with
   structured error unless `intake.allow_cross_fs=True` is set.
3. Add `tests/integration/test_intake_atomic_writes.py`:
   - 100 trials: write a 1 MB payload. After each, simulate kill-9
     mid-write by forking the writer and killing it after a random
     small delay. Assert: target file either does not exist OR is
     fully-written and validates.

**Validation**:
- 0 partial files in 100 trials (NFR-004).
- Same-fs writes succeed; cross-fs intake_root fails loudly.

### T011 — Missing vs corrupt distinction

**Purpose**: Operator can tell why intake failed.

**Steps**:

1. In `src/specify_cli/intake/scanner.py:read_brief()`, distinguish:
   - `FileNotFoundError` → raise `INTAKE_FILE_MISSING(path=...)`.
   - Any other `OSError` (permission, I/O error, decode failure) →
     raise `INTAKE_FILE_UNREADABLE(path=..., cause=<exc>)`.
2. Add `tests/unit/intake/test_missing_vs_corrupt.py` exercising both
   surfaces with a mocked filesystem (use `unittest.mock` patches on
   `os.stat`, `open`).

**Validation**:
- Missing produces `INTAKE_FILE_MISSING` with the path in the message.
- Permission-denied / corrupt produces `INTAKE_FILE_UNREADABLE` with
  the cause chain preserved.

### T012 — Root consistency between scan and write

**Purpose**: The directory used for source scanning must equal the
directory used for brief writes.

**Steps**:

1. In the intake entry point (likely `src/specify_cli/intake/__init__.py`
   or a top-level command in `src/specify_cli/cli/commands/intake.py`),
   resolve `intake_root` exactly once at the top and pass it into both
   the scanner and the writer.
2. The scanner and writer must take `intake_root` as a parameter; they
   must NOT recompute it from `os.getcwd()` or environment.
3. Add `tests/unit/intake/test_root_consistency.py`:
   - Set up two candidate roots; pass one to scanner, the other to
     writer; assert the helper detects the mismatch and raises
     `INTAKE_ROOT_INCONSISTENT`.

**Validation**:
- Mismatched roots raise structured error.
- Single-root happy path continues to work.

## Definition of Done

- All six subtasks complete with listed validation passing.
- `pytest tests/unit/intake/` green.
- `pytest tests/integration/test_intake_*.py` green.
- All callers in `spec-kitty` that write provenance lines route through
  `escape_for_comment()`.
- Documentation update in `docs/explanation/intake-security.md` (or
  similar) noting the escape rules and size cap.

## Risks

- T009 cap default of 5 MB may be too small for some operators; document
  the override and surface the cap value in the error message.
- T010 atomic-rename across filesystems is the silent-degradation risk;
  the code MUST detect and fail loudly.
- T011 corrupt-vs-missing must not collapse into a single error type at
  the CLI surface; verify with the integration test in WP07's
  fail-loud-uninitialized-repo scenario, which depends on intake errors
  being clear.

## Reviewer guidance

1. Provenance escape (T007): test with adversarial input including
   `\n# Inject heading\n--> visible\n*/ visible`. The output must not
   contain the unescaped sequences.
2. Path escape (T008): the symlink test is the load-bearing one; ensure
   the symlink is created via `os.symlink` in the test fixture.
3. Atomic write (T010): the kill-9 trial must run with `os.fork()` and
   `os.kill(pid, signal.SIGKILL)`, not Python-level cancellation.
4. Memory ceiling (T009 / NFR-003): the assertion must measure peak
   RSS, not arbitrary heap counters.

## Activity Log

- 2026-04-26T08:07:29Z – claude:opus-4-7:implementer:implementer – shell_pid=82553 – Started implementation via action command
- 2026-04-26T08:18:39Z – claude:opus-4-7:implementer:implementer – shell_pid=82553 – WP02 ready for review: T007 escape_for_comment helper wired into mission_brief; T008 assert_under_root with strict resolve + symlink guard; T009 size cap via os.stat pre-open + read_stdin_capped(cap+1) for STDIN; T010 atomic_write_bytes (open+fsync+replace) with 100-trial fork-SIGKILL harness proving 0 partial files; T011 IntakeFileMissingError vs IntakeFileUnreadableError distinction with cause-chain preservation; T012 root-consistency validation in write_brief_atomic raising IntakeRootInconsistentError before any I/O.
