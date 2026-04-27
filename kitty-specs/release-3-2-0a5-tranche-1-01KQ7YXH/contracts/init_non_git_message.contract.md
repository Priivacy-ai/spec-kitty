# Contract: `spec-kitty init` non-git target message

**Traces to**: FR-005 (#636)

## Stimulus

A user runs `spec-kitty init <target_dir>` in a directory whose
filesystem path is **not** inside a git work tree (i.e. neither
`<target_dir>/.git/` nor any ancestor `.git/` exists).

## Required behavior

**Canonical invariant** (Decision Moment `01KQ84P1AJ8H3FPJN9J5C12CBY`):
non-git init is allowed; silent non-git init is not.

1. The command MUST emit exactly one informational line, on stdout or
   stderr, that includes BOTH:
   - The phrase "not a git repository" (or substring "not.*git.*repo",
     case-insensitive).
   - The phrase "git init" as the suggested remediation.
2. The line MUST be styled at "info" level (not red, not bold-red). Yellow
   or cyan styling is acceptable.
3. The command MUST complete the scaffold successfully and exit code `0`
   when no other failure occurs — populating `.kittify/`, `.gitignore`,
   agent directories, etc., as it does today.
4. The command MUST NOT auto-run `git init` on the target. The "git not
   initialized" condition is informational only.
5. The command MUST NOT bail out before writing files just because the
   target is not a git work tree. Fail-fast semantics are explicitly
   rejected (see Decision Moment record).

## Forbidden behavior

- Multiple repetitions of the same message in one invocation.
- Hard-failing the command (any non-zero exit) solely because the target
  is not a git repository — Decision Moment `01KQ84P1AJ8H3FPJN9J5C12CBY`
  rejected fail-fast semantics; the "scaffold then init later" workflow
  is the canonical path.
- Skipping any normal scaffold step because the target lacks `.git/`.
- Silently writing files into the target without any indication that the
  user must run `git init` before downstream `agent` commands will work
  (the "silent non-git init" case the canonical invariant forbids).

## Implementation hint (informative, not normative)

The `git binary not detected` branch already exists at
`src/specify_cli/cli/commands/init.py:360`. Add a sibling branch that
checks whether the target dir is inside a git work tree (e.g.
`subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
cwd=target, check=False)`). When the answer is "no", print the new
informational line. Also append a single-line "next: run `git init`" item
to the post-init quick-start summary.

See [research.md R4](../research.md#r4--spec-kitty-init-non-git-target-fr-005--636).

## Verifying tests

- Unit: new `tests/specify_cli/cli/commands/test_init_non_git_message.py`
  drives `init` against a tmp dir without `.git/`, captures rich-rendered
  output (markup stripped), asserts the message appears exactly once and
  the regex `not\s+a\s+git\s+repository` matches at least once.
- E2E: extend `tests/e2e/test_cli_smoke.py` with the same assertion via
  `CliRunner`.

## Out-of-scope

- The exact wording of the message (decided during implementation).
- Localization (the project ships English-only).
