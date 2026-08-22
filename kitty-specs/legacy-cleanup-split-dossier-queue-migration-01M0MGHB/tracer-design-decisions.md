# Design Decisions — legacy-cleanup-split-dossier-queue-migration

Seeded at spec phase; append during plan/tasks/implementation.

## Decision: topology
`coord` topology (context-derived default on primary branch `main`), NOT explicit
`--topology`. Ledger SK-57/SK-36/SK-09 document branch-flat topologies chosen on protected
`main` scaffolding "successfully" with no branch minted and no landing spot for
`safe-commit`. `coord` mints `kitty/mission-legacy-cleanup-split-dossier-queue-migration-01M0MGHB`
and gives bookkeeping the coordination-branch destination SK-60's guard requires.
Verified post-scaffold: `git branch --list` shows the coordination branch minted; HEAD
remains on `main` (expected for `coord` — the coordination branch is a bookkeeping
destination, not necessarily the author's checkout branch); `meta.json` fields:
`"topology": "coord"`, `"target_branch": "main"`, `"coordination_branch":
"kitty/mission-legacy-cleanup-split-dossier-queue-migration-01M0MGHB"`.

## Decision: no dependency bump for spec-kitty-events
Already pinned `>=6.0.0,<7.0.0`; 6.1.0 (installed) already exports `validate_event()` and
the typed payload models. `spec-kitty-events#50` is an open, unmerged, non-draft PR adding
fixtures — not new constraints. Do not couple this mission's landing to that PR merging.

## Decision: topology — SUPERSEDED, re-scaffolded to `single_branch`

The `coord` decision above was acted on and scaffolded successfully (coordination branch
minted, ref confirmed), but proved non-viable at commit time: `safe-commit --to-branch main`
refused (protected branch); `safe-commit --to-branch <coord-branch>` refused because HEAD
was never moved onto it (and moving HEAD by hand is forbidden); `spec-kitty spec-commit`
(the tool's own documented "materialize-then-retry" escape hatch for exactly this state)
materialized a coordination worktree but did not relocate the uncommitted mission files
into it, so the retry it prescribes still failed identically — first-hand confirmation
that ledger **SK-12** is not fixed on 3.2.6rc3 (see `tracer-tooling-friction.md`).

**Operator-authorized remedy**: re-scaffold via the entry point the refusals had been
naming all along — `spec-kitty agent mission create <slug> --mission-type software-dev
--start-branch refactor/dossier-emitters-canonical-only-1058 --json` — which switches
HEAD to a fresh **non-protected** feature branch *before* topology is derived. With HEAD
off `main`, `--topology`'s context-derived default (#2581) resolves to `single_branch`
instead of `coord`. This is NOT the SK-57/SK-36 trap (an explicit branch-flat topology
chosen while HEAD sits on protected `main`): here the branch-flat shape resolves onto an
already-non-protected branch, which is exactly the safe case those entries contrast
against.

Verified post-re-scaffold: HEAD = `refactor/dossier-emitters-canonical-only-1058`
(non-protected); `meta.json`: `"topology": "single_branch"`, `"target_branch":
"refactor/dossier-emitters-canonical-only-1058"`, `"coordination_branch": null`; the
`agent mission create` command's own auto-commit (`75d707d89`, `meta.json` only) landed
directly on that branch, demonstrating plain `safe-commit` (no `--to-branch`/
`--target-branch`) now has a working destination. New mission slug/ULID:
`legacy-cleanup-split-dossier-queue-migration-01M0MGHB` (old `...-01M0MF07` scaffold was
torn down after confirming it carried no unique commits — nothing committed was lost;
all authored content was preserved and ported).

We PR into `main` and never run `spec-kitty merge`, so `target_branch` pointing at the
feature branch rather than `main` has no downstream effect on this mission's merge path.
