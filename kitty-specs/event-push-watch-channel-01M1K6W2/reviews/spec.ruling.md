# Operator ruling — spec phase HALT, mission `event-push-watch-channel-01M1K6W2`

Date: 2026-09-03. Issued by the operator (Human-in-Charge) via the mission orchestrator.

The spec phase HALTed under the R6 early-stop rule after two full R4→R5 rounds: the severity≥3
count did not fall between round 1's and round 2's fresh sweeps (2 → 2), so the loop stopped rather
than sampling for a lucky pass. Three findings survived, recorded in `reviews/spec-fresh-2.yaml`.

**This ruling REPLACES the acceptance bar for SPEC-FRESH2-001.** A verifier handed the original bar
would re-derive the original verdict and HALT the mission a second time on a question already answered.

## Ruling on SPEC-FRESH2-001 (severity 4) — the content invariant is a HASH

The spec defines the resume "content invariant" as *"a hash of, **or the raw bytes of**"* the last
consumed line. That unresolved either/or became load-bearing once it fed a `--from-invariant` CLI flag
and an envelope field.

**Decision: commit to a hash. Delete the "or the raw bytes of" branch** from FR-005, FR-004 and the
Tail-cursor definition, and anywhere else the either/or appears.

Rationale, so a plan-phase author need not re-derive it:

1. **The spec's own evidence falsifies the raw-bytes branch.** It cites 610KB event lines (ledger
   SK-131). Embedding 610KB in every envelope, or passing it back as a CLI argument on restart,
   breaks `ARG_MAX` and contradicts the streaming design the same document specifies.
2. **Equality is the only operation a resume cursor performs.** A hash supports it exactly. Nothing
   the invariant is used for requires reading the original bytes back.
3. **Fixed size regardless of event size** is precisely the property an envelope field and a CLI
   argument need.
4. **Two alternatives were considered and rejected.** *Keep both, bounded by a size threshold*: adds
   a mode switch, a threshold to justify and tune, a boundary to test, and an envelope field whose
   type varies with event size — more surface for a consumer to get wrong, in a mission whose whole
   purpose is not silently misleading consumers. *Drop the invariant, resume on offset alone*:
   reopens the exact defect the invariant closes — a rollback-then-regrow leaves the same offset
   pointing at different content, so a resuming consumer silently reads the wrong events. That is the
   plausible-but-wrong-answer class that got a sibling mission's equivalent verb rejected at severity
   4 today.

The spec must name the hash algorithm and state what the consumer does when the invariant does not
match on resume — raise, report, or refuse, never a silent re-read from the wrong position.

## SPEC-FRESH2-002 (severity 3) and SPEC-FRESH2-003 (severity 2)

No operator ruling required — both carry concrete, uncontested remediations and are to be fixed as
written:

- **002**: add a dedicated Success Criterion clause for FR-013's resume-time content-mismatch path
  (User Story 3 AC4), or cross-reference AC4 inside SC-002. It is currently measured only by the
  generic NFR-003 blanket clause.
- **003**: require the CLI to reject `--from-invariant` supplied without `--from-offset` as a usage
  error, consistent with FR-009's existing pattern.

## How the phase closes

One final targeted R4 fix round covering all three findings, then a single R5a anchored verification
against the bar set by this ruling. No further fresh sweep, no further rounds. All resolved → the
phase passes and the whole `reviews/` trail is committed with the phase. Anything still unresolved →
HALT again, back to the operator.
