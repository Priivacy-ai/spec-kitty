# Residual: the exempted consoles are still narrow on the failing path

Measured by WP02's independent reviewer. **Not a WP02 defect** — FR-002 and the post-plan squad's
F1 finding both *require* those consoles to be exempted, and WP02 did exactly that. This records
what the exemption leaves uncovered, so the mission does not close reading as though FR-002 fixed
the whole CLI surface.

## What was measured

`CliConsole._instances` holds three deliberately-sized consoles, and WP02 correctly declines to
touch them:

| Console | Declared | `_height` | Effective `size` under `TERM=dumb FORCE_COLOR=1` |
|---|---|---|---|
| `charter/list_cmd.py:26` | `width=200` | `None` | **(80, 25)** |
| `glossary.py:46` | `width=120` | `None` | **(80, 25)** |
| `docs.py:43` | `width=120` | `None` | **(80, 25)** |

They are **not actually sized on the failing path**. Rich's explicit-size early return requires
`_width` **and** `_height`; with `_height=None` it never fires, so `is_dumb_terminal` wins and all
three render at 80 columns. This is the *same* width-alone trap that FR-002's own seam comment
documents — applied to the consoles the seam is required to leave alone.

## Consequence: five tests are still red in the `#3115` environment

- `tests/agent/cli/commands/test_glossary.py::TestGlossaryConflicts::test_conflicts_all`
- `…::TestGlossaryConflicts::test_conflicts_unresolved_present`
- `…::TestGlossaryConflicts::test_conflicts_mission_filter`
- `…::TestGlossaryConflicts::test_conflicts_strictness_filter`
- `tests/docs/test_docs_query_cli.py::test_human_table_renders_with_no_rich_markup_leak`

Failing as `assert 'workspace' in '   Confl…'` and
`assert 'docs/architecture/worktrees.md' in '   Doc…'` — truncation, the same defect class as the
uuid fold. **Identical with the seam on and off** (so provably not WP02's doing), and all 88 tests
in that subset pass once `TERM=dumb FORCE_COLOR=1` is removed.

## The binding consequence for WP03 (FR-003)

**The width guard must compare against effective `size.width`, not declared `_width`.**

A guard reading `_width` sees `200`, `120`, `120` — comfortably above the 36-character uuid — and
passes. The same consoles render at **80**. That guard would be vacuous on precisely the three
instances this residual is about, while reporting a healthy inspected count. That is the
"mechanism reporting success for having done nothing" shape, and it would be introduced by the very
requirement written to prevent it.

FR-003 already requires the guard to assert it saw the *named* singletons by object identity rather
than a non-zero count. This adds the second half: what it reads from each must be the **effective**
size.

## Disposition

Carried as a recorded residual, not fixed in this mission. Fixing it means giving three consoles an
explicit height, which is a production change to `src/` — outside every work package's ownership,
and outside the mission's stated scope of not changing production behaviour (C-001). The honest
statement for the PR is that **FR-002 pins the two CLI singletons and the mission's own reproducer
goes green; it does not make the entire CLI surface wide on the failing path**, and five known tests
remain red there for the same underlying reason.
