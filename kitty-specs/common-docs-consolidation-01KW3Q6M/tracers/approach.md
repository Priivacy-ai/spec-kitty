# Tracer: Approach — Mission A (Common Docs Doctrine & Reconciliation)

> What we tried, what worked, what we'd do differently. Seed at planning, append during implement, assess at close.

## Seeded at planning (2026-06-27)

- **The 3-ship split (the pivotal call).** The original single "full Common Docs adoption" mission was *structurally* wrong: C-002 (ADR-before-move), C-004 (gate + full-gate dry-run), and gate-unmask-cannot-self-validate are only honestly satisfiable across **merge boundaries**, and the spec was undersized ~4-5×. Split into **Hygiene** (ships now, #2190 — landed via PR #2195) → **Mission A** (the governed foundation: ADR + doctrine + report-only rulers) → **Mission B** (the structural move, dogfoods A). The split came from the post-spec squad; without it we'd have shipped an un-self-validatable gate.
- **Report-only-then-flip-blocking.** Mission A authors the rulers **report-only** so they *measure* the violation baseline against today's messy tree; Mission B flips them to blocking against the *cleaned* tree (paired with a full-gate dry-run). This is the only sequencing that lets a freshly-authored gate honestly police the diff it ships in.
- **Self-test IS the Definition of Done.** Every ruler WP (WP03/04/05) is "done" only when its self-test demonstrably goes **RED on a seeded violation** (and green on a good fixture), demonstrated **red-first against a no-op stub**. This converts "asserts detection" into "demonstrably bites" — the fakeability lens's core demand.
- **Dogfooding across a merge boundary.** Mission A's doctrine (directive/styleguide/tactics) + rulers merge into `main` *first*; Mission B consumes the governed, self-testing foundation. Same-mission would be parity, not dogfooding.
- **The squad cadence earned its keep, repeatedly.** 4-lens pre-spec → 5-lens post-spec (forced the split, corrected the numbers, found the 4 unimplementable mechanisms + the glossary read-path) → 3-lens post-tasks (the singular/plural dirs, the `_inventory.py` ownership, the binding-resolves fakeability, SC-006 orphan). Each pass changed the work; the post-spec split was the highest-leverage finding of the whole session.

## What worked / would-do-differently
- **Worked:** the clone-for-parallel-work (sidestepped the contested checkout); report-only rulers; the squads.
- **Watch:** the corrected ADR count (~117 unique / 191 files; 20 era-less exact) — the spec's first-pass "140" was a floor, not a measurement; always live-count.

## Appended during implement
- WP01 (ADR) implemented clean by architect-alphonso; D5 verified against live code (`load_seed_file`).
