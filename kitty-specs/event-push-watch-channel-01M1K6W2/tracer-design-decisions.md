# Tracer: Design Decisions — events-tail (`event-push-watch-channel-01M1K6W2`)

Seeded at plan phase (charter Standing Order #3). Appended during implementation; assessed at
close.

## Closed by the operator ruling (do not re-derive — `reviews/spec.ruling.md`)

The content invariant is a **SHA-256 hex digest, never raw bytes**. Rationale (from the ruling,
recapped so a later reader doesn't have to chase the review trail): raw bytes were falsified by
the spec's own evidence (a measured 610KB event line — embedding that in every envelope or CLI
argument breaks `ARG_MAX` and the streaming design); equality is the only operation the invariant
performs, which a hash supports exactly; a fixed-size digest is what an envelope field and a CLI
argument actually need regardless of event size; and the two alternatives considered (size-
thresholded dual-mode, or dropping the invariant entirely) were both rejected — the latter reopens
the exact defect (a rollback-then-regrow leaving the same offset pointing at different content)
that got a sibling mission's equivalent verb rejected at severity 4.

## Decided at plan phase (this mission's own resolutions, within the spec's declared open space)

1. **What exactly gets hashed.** The SHA-256 digest of the single most-recently-consumed complete
   line's bytes, **including its trailing `\n`**, over the byte range `[start_of_last_line, O)`
   where `O` is always a verified line boundary. `start_of_last_line` is re-derivable purely from
   the file and `O` (backward-scan for the previous `\n`, or beginning-of-file) — no persisted
   line-length is needed on the external `--from-offset`/`--from-invariant` contract. `EMPTY_DIGEST
   = sha256(b"")` is the sentinel for `O == 0` (nothing consumed yet), needed to make
   `--from-offset 0 --from-invariant <x>` well-defined rather than silently ignored.

2. **Live-resync (FR-005) and cold-resume-refusal (FR-013) are genuinely different code paths, not
   just different outcomes on the same check.** A live, already-running poll has the last-consumed
   line's length in memory — no backward scan needed. A cold resume only has `--from-offset` +
   `--from-invariant` from the consumer, with no line-length, so it MUST backward-scan the file
   before it can even compute a digest to compare. `validate_resume_cursor()` exists as its own
   function for this reason, not for stylistic separation.

3. **Resolve-failure / usage-error / resume-refused signals are stderr-only, never on the stdout
   Tail-envelope stream.** The spec's Key Entities section loosely groups a "resolve-failure/error
   signal" under "Tail envelope" shapes, but every FR (FR-004, FR-009, FR-013) and every related
   acceptance scenario says, literally and repeatedly, "a structured error on stderr... no Tail
   envelope emitted." This plan resolves that soft imprecision in favor of the FR/AC language, not
   the Key Entities' looser framing.

4. **`hashlib.sha256` needs an inline `# noqa: TID251` at every call site** (production AND test) —
   it is a repo-wide banned import (`pyproject.toml:317`), enforced with no directory-level
   exemption for `tests/`. The banned-API message names "file-integrity checksums" as exactly the
   sanctioned non-charter use this mission's content invariant is. Must NOT call
   `charter.hasher.hash_content()` instead — different algorithm (BOM/newline-normalized charter
   markdown text, `"sha256:"`-prefixed output), wrong semantics for a raw log-line digest.

5. **`--json` is accepted but currently a no-op.** JSON is the command's only supported output mode
   for MVP (spec Edge Cases, explicit "do not build" instruction for a human mode) — no speculative
   `if not json_output` branch exists for a mode this mission does not implement.

6. **New sibling module (`tail_reader.py`), not an edit to `store.py`.** Keeps `store.py`'s
   existing one-shot/hard-fail-on-corruption contract for its current callers (materialize, doctor,
   migrate) untouched — those callers legitimately want "fail loud on any corruption," which this
   mission's tolerant/resumable reader must NOT weaken by sharing code.
