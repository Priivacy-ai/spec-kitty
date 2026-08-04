# Issue matrix — egress-refusal-consolidation-3110-01KYW895

Bundle B. Verdicts as of **WP01 approval**; issue states measured against
`Priivacy-ai/spec-kitty` on 2026-08-03, not taken from the dossier.

Three of the four rows are `in-mission`: they are closed by work packages that
have not landed yet. **`in-mission` is accepted at per-WP `approved` but rejected
on the `done` transition**, so each must resolve to a terminal verdict
(`fixed` / `verified-already-fixed` / `deferred-with-followup`) before the
mission merges. That is deliberate — it is what stops the mission landing with an
unclosed headline issue.

| issue | verdict | evidence_ref | title | wp | scope |
|---|---|---|---|---|---|
| #3110 | in-mission | WP03 — `src/specify_cli/egress.py`, both `*/egress_consent.py` deleted (PB-5); MUT-1/MUT-2 | consolidate duplicated `project_egress_refusal` wrapper across saas_client/tracker | WP03 | wrapper consolidation |
| #3111 | in-mission | WP04 — `decisions/ownership.py` + `cmd_widen` refusal; red-first proof asserts bytes, not counts | harden `decision widen` consent to key on the decision's owning project | WP04 | consent laundering |
| #3109 | in-mission | WP05 — keep-and-pin `register_saas_client_factory` (D-1); docstring truth + export pin | resolve the phantom `token_manager._ws_client` | WP05 | dead seam residual |
| #3030 | verified-already-fixed | Parent mission `journal-project-consent-3030-01KYKWQS`, PR #3098, merged 2026-07-31; issue CLOSED 2026-07-28. WP01 re-verified its attribution guards are non-vacuous per class: floors 4/3, MUT-4/5/6 killed, SC-005 removal reds `assert 3 >= 4` and `assert 2 >= 3` | P0: sync drain authorizes per-checkout but delivers per-journal | WP01 | parent invariant |
| #3144 | verified-already-fixed | **Bundle A, not this mission's work.** MERGED 2026-08-02 (mission `verification-trust-3115-01KYVYWM`). Referenced only as provenance for WP03 residual R-2: `docs/development/process-global-inventory-3115.md` is its artifact and carries three pointers into the `tracker/egress_consent.py` that WP03 deletes. State measured against GitHub, not read from the dossier | make the render-width fold, egress boundary and timeout gap provable | — | Bundle A dependency |
| #3177 | fixed | Filed BY this mission, deferred, then **fixed at landing** — the deferral is reversed, not carried. `S_ISDIR(resolved.stat().st_mode)` replaces `resolved.is_dir()` in `_mission_dirs`, which is the explicit-probe remedy FU-Q itself proposed. **Divergence corrected to 3.14+, not 3.13+**: re-measured on 3.11.15 / 3.12.13 / 3.13.12 / 3.14.4 — the predicate raises on the first three and returns `False` on 3.14 alone, because 3.14 delegates `is_dir` to `os.path.isdir`, which swallows every `OSError`. FU-Q's "3.13+" came from probing `hasattr(pathlib, "_ignore_error")`, which is a namespace-layout change in 3.13 rather than a behaviour change. Verified `33 passed` on 3.11 / 3.12 / 3.14 (3.14 was `2 failed, 31 passed`); full mission set `152 passed` on 3.11. The standing AST guard is tightened in the same commit — it was GREEN with the defect live, because it permitted `is_dir` inside a `try` and a `try` around a non-raising call is inert; all four predicates are now banned outright, `stat`/`lstat` stay try-permitted. Both halves falsifiable | unstattable mission directory loses its diagnosis on Python 3.13+ (title as filed; the accurate floor is 3.14) | WP04 | regression filed AND fixed by this mission |

## Notes on the #3030 row

WP01 does not re-fix #3030 — that landed with the parent mission. What WP01
establishes is that the guards protecting its invariant **cannot pass
vacuously**: before this WP each guard asserted a bare `assert scanned`, which
reds only when *every* construction site of a class disappears. The named
per-class floors make losing **one** site red, and the SC-005 demonstration
proves it by removing one site of each class and quoting the two reds.

That is why the verdict is `verified-already-fixed` rather than `fixed`: the
defect was closed upstream, and this mission verified the guard that keeps it
closed is real rather than decorative.

## Standing limit on every row

`#3115` (shard-parallel test isolation) is **OPEN** and its sync half is
explicitly deferred to `#3136`, so only single-file isolated runs are trustworthy
greens on this mission's test surface. Every count above was measured in
isolation. `#3113` is CLOSED by **non-adoption** — the all-positional blind spot
is a named limit in the *boundary* guard's `_transmits_a_body` — and it does
**not** bound the attribution guards, which count every match regardless of call
form. No coverage claim here is credited to it.
