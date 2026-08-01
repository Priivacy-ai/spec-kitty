---
work_package_id: WP07
title: 'The token-manager verdict: both directions measured, and the verdict applied'
dependencies:
- WP01
- WP02
requirement_refs:
- FR-009
planning_base_branch: feat/verification-trust-3115
merge_target_branch: feat/verification-trust-3115
branch_strategy: Planning artifacts for this mission were generated on feat/verification-trust-3115. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verification-trust-3115 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-verification-trust-3115-01KYVYWM
base_commit: d8d0ad7eff9ddeb14e154afd82450cf2dfd5472d
created_at: '2026-07-31T12:00:00+00:00'
subtasks:
- T023
- T024
- T025
- T026
history: []
authoritative_surface: tests/cli/commands/
execution_mode: code_change
owned_files:
- tests/cli/commands/test_sync_doctor_per_project_3030.py
- tests/cli/commands/test_sync_status_per_project_3030.py
- tests/cli/commands/test_sync_migrate_backfills_h4.py
- tests/cli/commands/test_sync_purge_3030.py
- tests/cli/commands/test_sync_doctor_consent_health_3030.py
- scripts/mutants/neutralise_reset_token_manager_3115.py
create_intent:
- scripts/mutants/neutralise_reset_token_manager_3115.py
tags: []
tracker_refs: []
---

# WP07 — The token-manager verdict

`578a659162` / `4f8e4ca781` shipped as **self-declared unproven hardening**: *"Could not force a live
reproduction of the reported empty-journal CI failure locally … this is defensive hardening of a
credible process-global per the maintainer's lead, not a confirmed-necessary fix."* That is an honest
commit and a correct piece of reporting — and it is also, by this repo's own standing rule, **not a
fix**. FR-001 and FR-002 now make the claim cheap to test, and the width finding supplies a strong
prior: **the reset was aimed at a global that was never the CLI cause.**

> **Re-scoped by the cut.** WP07 previously owned **no test file** — it measured, and WP08 applied.
> **WP08 is retired, so WP07 now measures *and* applies**, and it becomes the sole owner of the five
> `578a659162` files. That is still **one live agent** in those files (C-007); it is simply the same one
> twice rather than two in sequence.

## HARD PROHIBITIONS on those five files — stated in these words

> **Edit the `reset_token_manager()` call sites' surrounding docstring/comment and nothing else. Do
> not remove, weaken, move or annotate ANY of the five `monkeypatch.setenv("COLUMNS", …)` lines in
> this WP's file set.**

**All five files set `COLUMNS`, and the list is exhaustive** — an earlier draft named only two and read
as though it were complete. Measured on the tree:

| File | `COLUMNS` site | Value |
|---|---|---|
| `tests/cli/commands/test_sync_doctor_per_project_3030.py` | `:72` | `_WIDE_TERMINAL` = **220** (`:45`) |
| `tests/cli/commands/test_sync_status_per_project_3030.py` | `:83` | `_WIDE_TERMINAL` = **220** (`:56`) |
| `tests/cli/commands/test_sync_migrate_backfills_h4.py` | `:66` | literal **`"220"`** |
| `tests/cli/commands/test_sync_doctor_consent_health_3030.py` | `:81` | `_WIDE_TERMINAL` = **220** (`:53`) |
| `tests/cli/commands/test_sync_purge_3030.py` | `:98` | `_WIDE_TERMINAL` = **240** (`:56`) |

**`test_sync_purge_3030.py` is the odd one out at 240**, and it is **corroborating evidence for WP02's
≥ 240 constraint from inside WP07's own file set** — not just from
`tests/specify_cli/cli/commands/charter/test_activation_layout.py:111`. A pin below 240 would render
narrower than a width this repo's own consent tests already found they needed. **Report the 240 site
when quoting the prohibition**; do not average it away against the four 220s.

The earlier plan called these sets "provably dead" and handed their removal to WP08. **That finding was
wrong** (post-plan F2: `COLUMNS` **is** consulted on the non-dumb path, and
`test_activation_layout.py:111` is live today), **WP08 is gone, and the removal is not reassigned to
WP07 or to anyone.** Touching them would drag the ≥ 240 render-width constraint into this WP; it
belongs to WP02, where the pin is authored.

> **Do not add, move, remove, rename or restructure any home-isolation setup in these five files —
> the `_isolated_home` fixtures and the inline `SPEC_KITTY_HOME` sets alike.**

FR-008 is **cut**. The count stays at **22** (`grep -r "def _isolated_home" tests/` = 22 before and 22
after, measured) and a diff that changes it is a **scope violation**.

**The prohibition is stated over home-isolation setup generally, not over the fixture name**, because
the name does not cover this file set. Measured: **three** of the five carry a `def _isolated_home` —
`…doctor_per_project…:49`, `…migrate_backfills_h4…:44`, `…status…:60`. The other **two** set
`SPEC_KITTY_HOME` **inline inside a differently-named fixture**: `test_sync_doctor_consent_health_3030.py`'s
`checkout` (`:57`, setting at `:77`) and `test_sync_purge_3030.py`'s `checkout` (`:65`, setting at
`:94`). An earlier draft said *"four of the five files here carry one"*; it is three, and a prohibition
keyed to the fixture **name** would have left those two inline sites outside its named scope — the exact
shape of the finding that cut FR-008 in the first place (**a name collision, not a duplicated seam**).
**All five are read-only for the purpose of this mission**, whatever they are called.

## Definition of done — measurable evidence

### T023 — the mutant, under the corrected contract in full

`scripts/mutants/neutralise_reset_token_manager_3115.py`:

1. **Loading**: `PYTHONPATH=scripts/mutants pytest -p neutralise_reset_token_manager_3115 …` — **the
   `-p` flag is quoted in the evidence**, because `PYTHONPATH` alone loads no plugin and a
   `PYTHONPATH`-only mutant binds nothing while its run reads as a passing gate.
2. **Neutralisation site**: **hook level, in `pytest_configure`** — **never** as a same-named fixture, which
   loses to a conftest fixture for items under that conftest's directory.
3. **Self-proof**: it **asserts its own binding** and fails loudly at `pytest_configure` if the symbol
   it intends to patch is absent, renamed or relocated; it **reports the per-site split**; and it
   **fails loudly if the symbol it patched was never called** during the session.
4. **Reporting**: every run under the mutant quotes the mutant's own binding/suppression report
   **beside** its count line and collected count.

### T024 — four count lines, four assertion texts

With `reset_token_manager()` neutralised by the plugin, run **(a)** WP01's falsifier
(`TERM=dumb FORCE_COLOR=1`) and **(b)** the same file at the pinned width. **All four count lines, each
beside its file's collected count, and all four assertion texts, are quoted.**

### T025 — the per-site split is mandatory, and its shape is already measured

All five `578a659162` files import `reset_token_manager` **function-locally, inside the fixture body,
from the defining module** `specify_cli.auth.manager`:

| File | Import site |
|---|---|
| `tests/cli/commands/test_sync_doctor_per_project_3030.py` | `:62` |
| `tests/cli/commands/test_sync_status_per_project_3030.py` | `:73` |
| `tests/cli/commands/test_sync_migrate_backfills_h4.py` | `:57` |
| `tests/cli/commands/test_sync_purge_3030.py` | `:83` |
| `tests/cli/commands/test_sync_doctor_consent_health_3030.py` | `:70` |

So a plugin patching `specify_cli.auth.manager.reset_token_manager` **does** bind at all five, and the
fifth rot mode (`from X import f` rebinding by value) does **not** bite there.

**Two other sites bind eagerly by value via the package name** at module import —
`tests/auth/integration/conftest.py:22` and `tests/auth/test_websocket_provisioning.py:28`, both
`from specify_cli.auth import reset_token_manager`. They are **deliberately unpatched** (outside this
WP's cone) and **the plugin's report must name them as deliberately-unpatched, not report them as
zero.** **An aggregate suppressed count is rejected** — it cannot distinguish *"all five mutated"* from
*"one mutated, four inert"*.

### T025 — the null verdict needs a non-zero suppressed count

The reset is **load-bearing only if case (b) turns red with a named assertion**; a red that is a
`TypeError` or a fixture error **satisfies nothing** (NFR-007). **An unchanged colour in both cases is
the finding** — recorded as *"not load-bearing"*, not explained away — **but only from a run whose
plugin reports a non-zero suppressed count across the five patched sites.** *A null verdict drawn from a
run that suppressed zero calls is a finding about the mutant, and it is void.*

### T026 — WP07 lands the verdict itself

The corrected docstring for the retained reset — **defence-in-depth, not the fix** — is written **at
each of the five sites**, in the voice `tests/sync/tracker/test_saas_client.py`'s `_advancing_clock`
docstring already uses (`:32-50`), **quoting the measurement that produced the verdict**. *A comment
that describes a fix that never fired is the same shape as a gate that prints like a pass.*

**Deletion is acceptable only if** the reset is shown inert **and** WP04's inventory shows nothing reads
the singleton on that path.

**Collected counts before and after, for each of the five files, quoted.** The change is a docstring
edit, so **any moved count is a defect in the edit and is reconciled, not absorbed**.

### Expected gate no-op, stated in advance

WP07's changed files are docstring edits in test files with no new test targets, so the pre-review
regression gate may print `no_coverage — skipping the gate cheaply`. **That line is expected and is not
evidence of anything.** The `for_review` transition note says so **in those words** and **names the
manual evidence standing in for the gate**: the four count lines with their collected counts and
assertion texts, the plugin's non-zero suppressed-site report with its per-site split, and the
before/after collected counts for all five files.

### Cross-cutting

**NFR-009**: merge the mission branch into the worktree before the first measurement; state the commit
and merge-base. **NFR-003**: output to a file, tail of the file read; **an empty output file is no
measurement**. **NFR-004**: never run `tests/sync` and `tests/cli` sessions concurrently on one machine.
**NFR-002**: state the worktree import path — conclusions of sameness taken without it are void, and
*"unchanged colour in both cases"* is exactly a sameness conclusion.

## This WP closes `#3030`'s matrix row

`#3030`'s consent fix merged; what was **unproven** was the token-manager hardening. WP07 measures it in
both directions and records the verdict **at the site itself** — kept with a corrected docstring if
inert, or kept as load-bearing with the measurement quoted. Either way the claim **stops being
unproven**, which is what the terminal verdict `verified-already-fixed` asserts. **Only if WP07 cannot
obtain a discriminating measurement** does that row fall back to `deferred-with-followup` with a
successor number — it may **not** sit at `in-mission`, which is rejected at mission `done`.

## Files other agents hold

`tests/conftest.py` and `scripts/mutants/disable_render_seam_3115.py` are **WP02's**.
`scripts/repro_3115_render_width.sh` is **WP01's** — this WP *runs* the falsifier, it does not edit the
script. `tests/architectural/test_cli_console_render_width.py`,
`tests/cli/commands/test_render_fold_not_repairable_3115.py`,
`tests/cli/commands/fixtures/render_width_3115/**` and `tests/_arch_shard_map.py` are **WP03's** — note
WP03 and WP07 are **co-equal branches of the critical path running concurrently**, both under
`tests/cli/commands/`, with disjoint files. `tests/auth/**` is **nobody's** — those two sites are named
in the report, never patched. `src/**` is nobody's.
