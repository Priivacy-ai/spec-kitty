# `.kittify/memory/` — Team-Memory Store

**Curation convention for the git-tracked, worktree-shared "learned facts" store.**

Origin and rationale: [`docs/plans/engineering-notes/agent-knowledge-canonical-homes.md`](../../docs/plans/engineering-notes/agent-knowledge-canonical-homes.md).
That note traces this directory's lineage — it originally held the constitution (forked
from GitHub spec-kit), which the constitution → charter rename relocated to
`.kittify/charter/`. This directory kept its wiring (every worktree symlinks it back to
the main repo, per `src/specify_cli/core/worktree.py`) but lost its curator, and rotted
into an uncurated grab-bag. This README re-establishes the convention.

## Purpose

A git-tracked, team-shared, harness-neutral store for **durable learned facts** —
decisions, gotchas, and cross-cutting notes that are **not derivable from the repo** by
other means. It exists so that a fact learned once (by a maintainer or an agent) does not
have to be re-learned by the next session, the next agent, or the next harness.

It is shared across every Mission worktree by symlink (or copy on Windows — see
`src/specify_cli/core/worktree.py`), so a note written on one branch is immediately
visible on all others.

## What belongs here

A durable fact an agent or maintainer would otherwise have to re-discover:

- A non-obvious decision, plus its "why" (the reasoning wouldn't survive if only the
  decision's *outcome* were recorded elsewhere).
- A recurring gotcha (a footgun that has bitten more than once and has no better home).
- A cross-cutting convention that is real and followed, but not yet formalized as
  doctrine.

Each note should be short, self-contained, and readable without other context.

## What does NOT belong here (route elsewhere)

This store is for facts with no other canonical home. If a note fits one of the rows
below, it belongs there instead — **point to the source, never copy it** (no-duplication
rule; this is the exact failure mode that let this store rot last time).

| Kind of knowledge | Canonical home | Do NOT put it here because |
|---|---|---|
| Rules (what must/must-not be true) | Charter (`.kittify/charter/`) — read via `spec-kitty charter context --action <name>` | The charter already carries binding rules; a copy here goes stale the moment the charter changes. |
| Repeatable practices / "how we work here" | Doctrine (a toolguide or tactic under `src/doctrine/`) | Doctrine is served action-scoped via `charter context --json`; a practice noted only here is invisible to that retrieval path. |
| Reference / explanatory prose | Common Docs (`docs/`) | `docs/` is the indexed, Divio-typed home for explanation and reference; this store has no query surface. |
| Mission status | `status.events.jsonl` (via the status model) | The event log is the sole authority for WP lane state — a status note here would immediately drift. |
| Code structure / behavior | The code itself | Code is the only thing that can't lie about what the code does. |
| Past fixes / historical decisions | git history / ADRs (`docs/adr/`) | Git and ADRs are already the durable, timestamped record; duplicating them here just adds a second copy to keep in sync. |

If you're unsure whether something is a durable fact or belongs in one of the rows above,
default to routing it to the canonical home and leaving a one-line pointer here only if
that pointer itself is non-obvious.

## Discipline

- **No PII or secrets.** No IP addresses, hostnames, usernames, machine IDs, credentials,
  or other unique identifiers.
- **Self-contained.** Each note states its own one-line "why it's here" — a reader should
  not need this README plus tribal knowledge to understand why the note exists.
- **Retire, don't accumulate.** A stale note (superseded decision, resolved gotcha, fact
  that migrated to its canonical home) is deleted or moved, not left to rot. This store
  lost its curator once already and became an uncurated grab-bag — that is the failure
  mode this convention exists to prevent.

## Index

Tracked files as of this writing (confirm with `git ls-files .kittify/memory`):

| File | Classification | Migration recommendation |
|---|---|---|
| `available_tooling.md` | A single past session's tool-availability snapshot (timestamped decision log for one session's toolchain check). Not a durable cross-cutting fact — it describes one session's state, not a standing decision or recurring gotcha. | Mis-filed by nature rather than by location: nothing to migrate it *to*. Recommend retiring (deleting) it in a follow-up rather than moving it — a fresh session's tooling check should not be judged against a frozen 2026-03-09 snapshot. |
| `058-architectural-review.md` | An architect's review findings for one merged mission (058, mission-repository-encapsulation), including a HiC decision and rationale. This is a point-in-time review artifact, not a cross-cutting fact for ongoing work. | Recommend moving to `docs/plans/engineering-notes/architectural-review/` (an engineering-notes subdirectory already exists for exactly this kind of artifact — see `2026-05-25-deep-dive-architectural-review.md` there). |
| `templates/POWERSHELL_SYNTAX.md` | A how-to guide teaching agents correct PowerShell syntax versus Bash for spec-kitty workflows — a repeatable practice, not a one-off fact. | Recommend moving to `src/doctrine/toolguides/built-in/` as a toolguide (precedent: `EFFICIENT_LOCAL_TOOLING.md`), which makes it retrievable action-scoped via `charter context --json` instead of a flat file read. |

**None of the above have been moved yet** — this pass (Move 1) only establishes the
convention and corrects stale references; migrating the three existing files is left for
a follow-up pass so each move can be reviewed on its own.

## See also

- [`docs/plans/engineering-notes/agent-knowledge-canonical-homes.md`](../../docs/plans/engineering-notes/agent-knowledge-canonical-homes.md) — the design finding this README implements.
- `.kittify/charter/` — the project charter (rules), read via `spec-kitty charter context --action <name>`.
- `src/doctrine/` — doctrine layers (directives, tactics, styleguides, toolguides, paradigms).
