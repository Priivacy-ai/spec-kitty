---
affected_files:
- path: docs/api/environment-variables.md
- path: docs/api/upgrade-lifecycle.md
- path: docs/architecture/launch-readiness-future.md
- path: docs/guides/install-and-upgrade.md
- path: src/doctrine/styleguides/built-in/plain-language.styleguide.yaml
- path: tests/architectural/test_status_command_guidance.py
cycle_number: 3
mission_slug: annoying-bugs-sweep-01KYHQ9F
reproduction_command: "PWHEADLESS=1 pytest tests/architectural/test_status_command_guidance.py\
  \ -m 'arch_shard_1 and not windows_ci and (git_repo or integration or architectural)\
  \ and not timing' --collect-only -q  # -> 5 deselected; and: PWHEADLESS=1 pytest\
  \ tests/architectural/test_gate_coverage.py::test_no_new_orphan_surfaces -q"
reviewed_at: '2026-07-27T15:28:36Z'
reviewer_agent: claude
verdict: rejected
wp_id: WP04
---

# WP04 Review — cycle-2 commit `a647b5d44`

**Verdict: changes requested (one blocker).**

The four cycle-1 corrections are all genuinely fixed — verified against the code,
not the narrative. One new, independently-reproduced blocker replaces them: the
guard is deselected by the CI marker expression and will never execute in CI.

## BLOCKER

**`tests/architectural/test_status_command_guidance.py:1` — the file carries no
`pytestmark`, so the arch-adversarial CI job deselects all 5 tests. The guard
never runs in CI, and it turns `test_gate_coverage.py::test_no_new_orphan_surfaces`
red.**

`.github/workflows/ci-quality.yml` runs the arch pole with:

```text
-m '${{ matrix.shard }} and not windows_ci and (git_repo or integration or architectural) and not timing'
```

The `arch_shard_1` marker *is* applied (via the `default_fallback=True`
hash-bucket in `tests/_arch_shard_map.py`), but the
`and (git_repo or integration or architectural)` clause then drops the file
because it declares none of those three markers.

Reproduction — the exact CI expression, plus a sibling control:

```text
$ pytest tests/architectural/test_status_command_guidance.py \
    -m 'arch_shard_1 and not windows_ci and (git_repo or integration or architectural) and not timing' \
    --collect-only -q
no tests collected (5 deselected) in 36.66s

$ pytest tests/architectural/test_docs_cli_reference_parity.py \
    -m 'not windows_ci and (git_repo or integration or architectural) and not timing' \
    --collect-only -q
6 tests collected in 34.95s

$ grep -n "pytestmark\|@pytest.mark" tests/architectural/test_status_command_guidance.py
(no matches)
```

The repo's own orphan-surface ratchet catches this independently:

```text
$ pytest tests/architectural/test_gate_coverage.py::test_no_new_orphan_surfaces -q
E   AssertionError: 1 test file(s) are selected by ZERO CI gates and are not in
E   the recorded baseline — they will never run in CI:
E       tests/architectural/test_status_command_guidance.py
1 failed in 111.82s
```

**Attribution (baseline-red gotcha checked, this red is yours):**

- `tests/architectural/_gate_coverage_baseline.json` has `orphan_files: []`,
  `orphan_test_count: 0` — the backlog is empty by design.
- `git cat-file -e kitty/mission-annoying-bugs-sweep-01KYHQ9F:tests/architectural/test_status_command_guidance.py`
  → **absent on the mission base**, so the gate is green there.
- The failure names exactly one file: the one this WP created.

This is not the `<gate-coverage-junit>` item in the WP's baseline-tests record
(that is "no JUnit XML artifact produced by the scoped run" — a different,
infrastructural item). This is a concrete, named, newly-introduced red.

### Fix

Declare the markers the arch gate selects. Match the closest sibling — 
`test_docs_cli_reference_parity.py`, which is likewise a docs-guidance guard:

```python
import pytest

pytestmark = [pytest.mark.architectural, pytest.mark.docs_scoped]
```

`architectural` is what gets the file selected by the arch-adversarial job.
`docs_scoped` additionally puts it in the docs-only PR leg
(`-m '<shard> and docs_scoped and not windows_ci'`), which is the right home for
a guard whose entire corpus is four Markdown pages and one YAML file — a
docs-only PR is exactly when this guard most needs to fire.

Then re-run `tests/architectural/test_gate_coverage.py::test_no_new_orphan_surfaces`
and confirm it is green (do **not** reach for `--update-baseline`; the baseline
is empty by design and the coverage gap here is accidental, not intentional).

## Cycle-1 Corrections — all four independently verified as FIXED

Do not redo these; they are correct.

1. **Concrete invocations only — PASS.** `code_segments()` yields only fenced
   code-block lines and inline code-span bodies; `command_position_path()`
   requires `spec-kitty` in executable position after optional prompt markers
   and `FOO=bar` prefixes. Of 115 lines mentioning `spec-kitty` across the five
   scoped sources, 79 produce invocations and 37 produce none — I inspected all
   37 and every one is an env-var name, a package name (`spec-kitty-cli`), a
   sibling repo (`spec-kitty-saas`), a URL, a config path, a skills path, or a
   doc title. No real invocation is dropped.

2. **Compiled command tree — PASS.** `compiled_command_tree()` returns
   `typer.main.get_command(_build_live_app())`; verified live to be a
   `BannerGroup` with `isinstance(..., click.Command) is True`. No
   `_typer_walker` / `scripts.docs` reference remains in the file.

3. **No callback-derived names — PASS.** `test_resolution_uses_click_names_not_callback_names`
   asserts both directions, as claimed, and both hold live:
   `('verify-setup',) -> True`, `('verify_setup',) -> False`.

4. **Prose excluded, real invocations kept — PASS.**
   `docs/api/upgrade-lifecycle.md:129` (the "prints a single banner" sentence) is
   not extracted; `pipx upgrade spec-kitty-cli` and
   `~/.config/spec-kitty/upgrade.yaml` are not extracted;
   `SPEC_KITTY_NO_NAG=1 spec-kitty upgrade --cli` **is** kept and resolves to
   `('upgrade',)`.

## Denominator and mutation proof — both honest

- **79 is honest.** Independently reproduced:
  `sum(len(extract_invocations(s)) for s in _scoped_sources()) == 79`
  (3 / 16 / 21 / 12 / 27). The extractor was not narrowed to dodge failures —
  the excluded lines contain no invocation of any kind. Source denominator is
  pinned at 5 with an `is_file()` inventory check.
- **Mutation proof reproduces on the real file.** I planted `spec-kitty status`
  into the real `src/doctrine/styleguides/built-in/plain-language.styleguide.yaml`
  and ran the shipping gate:

  ```text
  E   AssertionError: #2983 scoped guidance names a command the CLI does not expose:
  E       - plain-language.styleguide.yaml:55: spec-kitty status
  2 failed, 3 passed in 36.57s
  ```

  Clean tree: `unresolved_invocations(_scoped_sources()) == []`, `5 passed`.
  Styleguide restored; `git status --short` empty.
- `test_top_level_status_command_is_still_absent` genuinely blocks the cheat
  path via `assert not resolves_in_command_tree(("status",))`.

## Other gates (all green, re-run by the reviewer)

```text
PWHEADLESS=1 pytest tests/architectural/test_status_command_guidance.py -q   -> 5 passed in 37.53s
PWHEADLESS=1 pytest tests/architectural/test_docs_cli_reference_parity.py -q -> 4 passed, 2 skipped in 38.14s
PWHEADLESS=1 pytest tests/architectural/test_no_legacy_terminology.py -q     -> 4 passed in 39.81s
PWHEADLESS=1 pytest tests/architectural/test_arch_shard_marker_completeness.py -q -> 7 passed in 92.80s
ruff check tests/architectural/test_status_command_guidance.py               -> All checks passed!
python -m mypy tests/architectural/test_status_command_guidance.py           -> Success: no issues found
npx markdownlint-cli2@0.18.1 (4 scoped docs)                                 -> Summary: 0 error(s)
```

## Replacement correctness — PASS

Option spelling checked against the compiled tree, not assumed: `spec-kitty
upgrade` exposes `--cli`, `--no-nag`, `--dry-run`; `spec-kitty agent tasks
status` exposes `--mission` (Terminology-Canon compliant). Replacements are
intent-matched rather than uniform — nag/upgrade contexts became
`spec-kitty upgrade --cli`, work-package-status contexts became
`spec-kitty agent tasks status`, and generic "a status command" prose is
preserved.

## Anti-pattern checklist

1. Dead code — **FAIL**. The guard is selected by zero CI gates (the blocker).
2. Synthetic-fixture test — PASS (real-file mutation proof reproduces).
3. Silent empty return — PASS (`command_position_path` returns `None` as an
   explicit documented "not in command position" signal).
4. FR coverage — PASS in content, but FR-012's regression gate does not execute
   in CI until the blocker is fixed.
5. Frozen surface — PASS. `git log <base>..HEAD -- docs/changelog/CHANGELOG.md`
   empty; the implementer's own commits (`6285b3e23`, `a647b5d44`) touch no
   `kitty-specs/**` (the only delta there arrives via merge commits).
6. Locked decision — PASS. No top-level `status` command added.
7. Shared-file ownership — PASS. Lanes a/b/c/e diffed against the mission
   branch: none touches a WP04-owned file. C-005 disjointness holds.
8. Production fragility — N/A. No production code path changed.

## Non-blocking observations (optional, for the same edit)

1. Commented invocations inside fences are not extracted —
   `docs/guides/install-and-upgrade.md:154-155` carry `# Run: spec-kitty upgrade`
   and `# Preview first: spec-kitty upgrade --dry-run`. Both name real commands,
   so nothing is concealed today, but a phantom planted in a shell comment would
   evade the guard.
2. Once a non-`Group` leaf is reached, `resolves_in_command_tree` returns `True`
   for all trailing segments (`spec-kitty upgrade bogus` passes). This is the
   deliberate, documented allowance for positional arguments.
3. Flag-first forms (`spec-kitty --verbose status`) break the subcommand walk at
   the flag and resolve as the root. Not present in the scoped corpus.

Fixing the blocker is a one-line `pytestmark` addition plus a re-run of the
orphan-surface gate; nothing else in the WP needs to change.
