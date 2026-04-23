# ADR-001 — Correlation contract uses append-only JSONL events on the invocation file

**Mission**: `phase-4-closeout-host-surfaces-and-trail-01KPWA5X`
**Status**: Accepted
**Date**: 2026-04-23
**Relates to**: FR-007, SC-003, C-003, C-004
**Supersedes**: None

## Context

Phase 4 core runtime and the 3.2.0a5 closeout slice shipped the invocation trail model: every `advise`/`ask`/`do` invocation writes a `started` JSONL line, and `profile-invocation complete` appends a `completed` line. Tier 2 evidence promotion is already wired for caller-supplied evidence paths. What the shipped model does **not** provide is a deterministic lookup from `invocation_id` to every artifact and commit the invocation produced. Issue #701 calls out this correlation gap explicitly.

Without a correlation contract, reconstructing "what did this invocation touch?" requires either repo-wide grep, commit-history scanning, or operator memory. All three are fragile.

## Decision

Attach correlation data as **append-only JSONL events** on the same `.kittify/events/profile-invocations/<invocation_id>.jsonl` file that already carries the `started` and `completed` events.

Two new event shapes:

- `artifact_link`: `{event, invocation_id, kind, ref, at}` — appended one per `--artifact <path>` flag on `profile-invocation complete`. Flag is repeatable.
- `commit_link`: `{event, invocation_id, sha, at}` — appended once per `--commit <sha>` flag on `profile-invocation complete`. Flag is singular per call.

Ref normalisation: repo-relative when the resolved path is under `repo_root`; absolute otherwise. Falls back to the verbatim input on resolution failure, mirroring the existing evidence-ref handling in `executor.complete_invocation`.

Readers that encounter unknown event types skip the line (precedent: `glossary_checked`). No existing JSONL line is mutated.

## Rationale

- **Append-only respects C-004.** The existing trail already requires append-only; correlation fits the same invariant without new file types.
- **Single-file read satisfies SC-003.** One `cat`/`head` gives every correlation for an invocation.
- **No git-hook dependency.** A commit-trailer approach (alternative A below) would require a reliable `prepare-commit-msg` hook installed on every contributor's machine and every host LLM's workspace. Relying on host LLMs to install and respect a git hook is fragile.
- **Handles non-commit artifacts.** Commit trailers cannot represent evidence files, build outputs, or mission artifact references. The JSONL event can.
- **Backwards-compatible.** Omitting `--artifact` / `--commit` yields identical 3.2.0a5 behaviour.

## Alternatives considered

| Option | Outcome | Why rejected |
|--------|---------|--------------|
| **A. Git commit trailer** `Invocation-Id: <ulid>` on every commit | Rejected | Requires a git hook; unreliable across hosts; cannot represent non-commit artifacts; read path scans history. |
| **B. Append correlation events to the invocation JSONL** | **Accepted** | See Rationale. |
| **C. New sibling index file** `.kittify/events/correlation-links.jsonl` | Rejected | Second source of truth; duplicates `invocation-index.jsonl` pattern; still needs per-invocation grouping on read. |
| **D. Hybrid A + B** | Rejected | Double write, double maintenance; no operator benefit over B alone. |

## Consequences

- `InvocationWriter` gains `append_correlation_link(...)` — new, not a modification of `write_started`/`write_completed`.
- `spec-kitty profile-invocation complete` gains two new flags: `--artifact` (repeatable) and `--commit` (singular). No new top-level command (respects C-008).
- JSON response from `complete` grows two new fields: `artifact_links: list[str]` and `commit_link: str | null`. Additive (respects C-003).
- SaaS projection of correlation events is governed by `POLICY_TABLE` (see ADR-003).
- Readers written before this ADR must already skip unknown event types; if they do not, they are non-compliant with the existing `glossary_checked` contract and need to be fixed independently.

## Revisit trigger

Revisit this decision if any of the following occurs:

- A host LLM or operator workflow demonstrates that operator-supplied `--artifact` / `--commit` flags are regularly missed, and automatic derivation becomes necessary.
- The per-invocation JSONL becomes a performance bottleneck at very high invocation counts (not anticipated under NFR-002).
- A future epic introduces a canonical cross-invocation artifact index that supersedes per-file correlation reads.

## References

- `src/specify_cli/invocation/writer.py` — existing `write_started`, `write_completed`, `write_glossary_observation` (appendix events precedent)
- `src/specify_cli/invocation/executor.py:236-255` — existing ref-resolution pattern for evidence
- `docs/trail-model.md` — trail contract baseline
- Issue #701 — Minimal Viable Trail epic
- Contract: `contracts/profile-invocation-complete.md`
- Data model: `data-model.md` §3, §6
