---
affected_files:
- path: src/specify_cli/cli/commands/profile_invocation.py
- path: tests/specify_cli/invocation/cli/test_complete.py
cycle_number: 1
mission_slug: annoying-bugs-sweep-01KYHQ9F
reproduction_command: 'cd .worktrees/annoying-bugs-sweep-01KYHQ9F-lane-e && python -c "import pathlib; p=pathlib.Path(''src/specify_cli/cli/commands/profile_invocation.py''); s=p.read_text(); p.write_text(s.replace(''    help=\"Manage invocation records.\",\n    epilog=_OPENER_EPILOG,\n'', ''    help=\"Manage invocation records.\\\\n\\\\n\" + _OPENER_EPILOG,\n''))" && PWHEADLESS=1 python -m pytest tests/specify_cli/invocation/cli/test_complete.py -q -k "opener or manifest or dispatch_opener or epilog"'
reviewed_at: '2026-07-27T17:40:00Z'
reviewer_agent: claude
verdict: approved
wp_id: WP05
---

# WP05 Review Cycle 1 — Invocation opener discoverability

**Verdict**: Approved

Independent adversarial review of commit `9c2c0ca35` on
`kitty/mission-annoying-bugs-sweep-01KYHQ9F-lane-e`. Reviewer did not implement this WP.

## Artifact-numbering note

`review-cycle-1.md` was free in this WP's directory (only `baseline-tests.json` was
present). This is a genuine cycle-1 review recorded at its natural number. Because the
verdict is **approved**, the runtime writes no verdict artifact of its own
(`create_rejected_review_cycle` only fires on rejection — tracker #2996), so this
hand-written artifact is the sole record and keeps the highest-numbered artifact honest
for the `done`/merge gate. `--skip-review-artifact-check` was not used.

## Environment caveat that shaped the evidence

The editable install in this environment resolves `specify_cli` to a **different
checkout** (`/home/stijn/Documents/_code/SDD/fork/spec-kitty/src/specify_cli`). A naive
`python -m specify_cli profile-invocation --help` therefore exercises the wrong code and
shows **no epilog**. All manual CLI evidence below was re-taken with
`PYTHONPATH=<lane-e>/src`. `pytest.ini` sets `pythonpath = src` relative to rootdir, so
the pytest gates do import the lane's source — verified via
`specify_cli.__file__`.

## Claim-by-claim verification

### Claim 1 — epilog added, `help=`/group name untouched, no command or alias

**Verified.** `src/specify_cli/cli/commands/profile_invocation.py` adds module constant
`_OPENER_EPILOG` and passes it as `epilog=` to the existing `typer.Typer(...)`. `name=`
and `help="Manage invocation records."` are byte-identical to base.

**The epilog is genuinely rendered** (this was checked against the live CLI, not just the
constant):

```text
$ PYTHONPATH=<lane-e>/src python -m specify_cli profile-invocation --help
 Manage invocation records.
 ...
 Open:  spec-kitty dispatch "<request>"
 Close: spec-kitty profile-invocation complete --invocation-id <id> --outcome
 <outcome>
```

Not dead code: `_OPENER_EPILOG` has one live production reference at the Typer
constructor. `list_commands` still returns exactly `["complete"]` — no
`profile-invocation dispatch` alias (SC-005 / C-007).

### Claim 2 — completion manifest byte-identical

**Verified.** `git diff <base>..<head> --name-only` returns exactly two paths; a
pathspec-scoped diff on `src/specify_cli/_completion_manifest.json` is empty. The
epilog is invisible to the manifest node schema `{help, hidden, deprecated, commands}`
(confirmed by reading `completion.build_manifest_from_command`, which never reads
`epilog`).

### Claim 3 — the "metadata unchanged" proof is real, not circular

**Verified.** `test_completion_manifest_entry_unchanged_by_epilog` compares
`completion.build_manifest_from_command(_resolve_group())` — the **live** CLI group
resolved from `specify_cli.app`, walked by the same function `generate_manifest()` uses
in production — against `completion._load_manifest()[...]`, which reads the **committed**
JSON from disk. Two independent sources; not a file compared to itself. The canonical
drift guard `tests/specify_cli/cli/commands/test_completion_fast_path.py::test_manifest_matches_live_cli`
was also run standalone and passes.

Minor, non-blocking: the test reaches for the private `completion._load_manifest()`. It
is a same-repo test against a stable private helper, so this is a style nit only.

## Independent mutation results (both reproduced by the reviewer, then restored)

The implementer's non-vacuity claims were not accepted on trust. Both mutations were
applied to the working tree and reverted; `git diff` was confirmed empty afterward.

**Mutation A — move the pointer from `epilog=` into `help=`** (the exact regression C-007
forbids):

```text
FAILED test_opener_pointer_lives_in_the_epilog_not_in_help
        assert info.help == "Manage invocation records."
FAILED test_completion_manifest_entry_unchanged_by_epilog
        assert live_node == committed_node
2 failed, 2 passed
```

The manifest pin genuinely goes red, and it goes red on the live-vs-committed comparison
— confirming the guard is real.

**Mutation B — delete the `epilog=` argument entirely**:

```text
FAILED test_group_help_names_the_dispatch_opener
FAILED test_opener_pointer_lives_in_the_epilog_not_in_help
2 failed, 2 passed
```

The manifest pin correctly stays green here (removing an epilog cannot change the
manifest), which is the right sensitivity profile rather than a blanket failure.

## mypy attribution — verified against the base, not accepted on trust

A detached worktree was created at the base ref
`kitty/mission-annoying-bugs-sweep-01KYHQ9F` and mypy was run on the same two files.

| Ref | mypy errors |
|-----|-------------|
| base `2311a3b32` | **4** (`test_complete.py:32` `[override]` ×2, `:69` `[no-any-return]`, `:80` `[no-untyped-call]`) |
| branch `9c2c0ca35` | **1** (`test_complete.py:89` `[no-any-return]`) |

The single remaining error is the *same* diagnostic on the *same* pre-existing helper
(`_open_invocation` → `return payload.invocation_id`), shifted from line 69 to 89 by the
lines the WP added above it. The "pre-existing, net −3" attribution is **correct**.

## Judgement on the `# type: ignore[override]` suppression

**Justified; keep it.** The base-ref mypy output above is itself the proof: mypy reports
`ArgvCliRunner.invoke` incompatible with *both* supertypes — `typer.testing.CliRunner`
(first param `app: Typer`) *and* `click.testing.CliRunner` (first param `cli: Command`).
Typer renames click's parameter, so no single parameter name satisfies both, and making
the parameter positional-only would narrow it further rather than fix it. The check is
genuinely wrong about correct code.

The suppression also meets CLAUDE.md's bar on every axis: it is **narrower than what it
replaced** (the base carried a blanket `# type: ignore[no-untyped-def]` that did not even
cover the errors mypy was raising), it names a single error code, it carries a two-line
inline rationale, real annotations were added alongside it, and it lives in a test file,
not a production path. Net effect is −3 mypy errors and a correctly typed signature.

## Scope discipline (C-005)

Changed-file set is exactly the two owned files. Cross-checked against every sibling
lane: `git diff <base>..<lane-{a,b,c,d}> -- <the two files>` is empty for all four, so
the WP05 file set is disjoint from every other work package. No shared-file coordination
note is required.

## Anti-pattern checklist

| # | Item | Result |
|---|------|--------|
| 1 | Dead code | **PASS** — `_OPENER_EPILOG` has a live production reference; rendering confirmed against the real CLI |
| 2 | Synthetic-fixture test | **PASS** — proven by two reviewer-run mutations; tests invoke the real app and the real manifest generator |
| 3 | Silent empty return | **PASS** — no new `except`/empty-return paths |
| 4 | FR coverage | **PASS** — FR-013/SC-005 (`test_group_help_names_the_dispatch_opener`), C-007 (`test_opener_pointer_lives_in_the_epilog_not_in_help`, `test_no_profile_invocation_dispatch_subcommand`, `test_completion_manifest_entry_unchanged_by_epilog`), C-005 (disjointness verified above + `test_close_metadata_unchanged_by_epilog`) |
| 5 | Frozen surface | **PASS** — `_completion_manifest.json` has zero commits in `<base>..HEAD` |
| 6 | Locked decision | **PASS** — no alias command; spec C-007's `MUST NOT` respected |
| 7 | Shared-file ownership | **PASS** — no overlap with lanes a–d |
| 8 | Production fragility | **PASS** — no new `raise` in a production path |

Terminology canon: the diff adds no `--feature` flag, alias, or prose; `grep` over added
lines is clean.

T031 process check: #2984 is assigned to the Human-in-Charge and carries a WP05 comment
naming this mission and lane (posted 2026-07-27T15:06:45Z).

## Gates re-run by the reviewer (verbatim)

```text
$ PWHEADLESS=1 python -m pytest tests/specify_cli/invocation/cli/test_complete.py -q
16 passed, 68 warnings in 69.11s (0:01:09)

$ PWHEADLESS=1 python -m pytest tests/specify_cli/cli/commands/test_completion_fast_path.py \
    tests/specify_cli/invocation/cli/test_dispatch.py \
    tests/architectural/test_no_legacy_terminology.py -q
34 passed, 22 warnings in 61.50s (0:01:01)

$ python -m ruff check src/specify_cli/cli/commands/profile_invocation.py \
    tests/specify_cli/invocation/cli/test_complete.py
All checks passed!

$ python -m mypy src/specify_cli/cli/commands/profile_invocation.py \
    tests/specify_cli/invocation/cli/test_complete.py
tests/specify_cli/invocation/cli/test_complete.py:89: error: Returning Any from function declared to return "str"  [no-any-return]
Found 1 error in 1 file (checked 2 source files)   # pre-existing, see attribution table
```

Broader regression sweep — every test file in the repo that mentions
`profile-invocation`, `profile_invocation_app`, or `epilog`, plus the whole invocation
and session-presence packages:

```text
$ PWHEADLESS=1 python -m pytest tests/contract/test_example_round_trip.py \
    tests/doctrine/test_spec_kitty_skill_content.py \
    tests/integration/test_next_lifecycle_records.py \
    tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py \
    tests/specify_cli/invocation/ tests/specify_cli/session_presence/ \
    -q -n auto --dist loadfile -p no:cacheprovider
619 passed, 3 skipped, 246 warnings in 90.86s (0:01:30)
```

No regressions. The only pre-existing baseline item for this WP
(`<gate-coverage-junit>`) is unrelated to the diff.

## Conclusion

The defect is fixed at the surface the spec names, by the mechanism the spec mandates,
with tests that were independently proven to fail when the mechanism is subverted in
either direction. Scope is exactly the owned file set. The one type suppression is
narrow, inline-justified, and strictly reduces the suppression surface. Approved with no
required changes.
