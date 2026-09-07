# Plan-phase ruling — orchestrator

The plan phase HALTed correctly under the oscillation rule: severity>=3 findings went
3 -> 2 -> 1 -> 2 across four R4->R5 rounds. Rising is the stop signal, and stopping was right.

## Ruling: one targeted fix round, anchored verify only. No fresh sweep. Then proceed to tasks.

All three survivors are **prose defects about test-construction mechanics**, not defects in the
fix design. The fix design — the `resolve_primary_anchor_dir` extension, the five real FR-006
catch sites, and the `Lane.UNINITIALIZED` block — has been independently re-verified as correct
across four rounds and is not in question.

A fifth full sweep over prose that has already oscillated is how a design phase burns its budget
without converging. This programme has watched that happen. The fix is to make the three
corrections and verify *those*, not to re-derive the whole artifact.

### PLAN-FRESH4-002 (severity 4) — fix by DELETION, not by argument

Two things are wrong and only one needs writing:

1. The plan cites Call (c)/(d)'s fixture as precedent for "an asymmetric mock". That text never
   says it. **Delete the citation.** A fabricated precedent is worse than no precedent, and this
   mission exists to fix guards that claim more than they check.
2. The finding is structurally right: both calls route through the same pure
   `resolve_primary_anchor_dir(feature_dir, repo_root, mission_slug)` with byte-identical
   arguments and no mutation between them, so no fixture can differentiate them. **State plainly
   that calls (c) and (d) share fate and are covered by one test**, exactly as round 4 already
   concluded for the other call pair.

That round 4 fixed this pattern for one pair and left it unfixed for another is instance-vs-class
— the recurring failure of this programme. Fix the class: check every call pair in the plan for
the same share-fate property, not just the one named.

### PLAN-FRESH4-001 (severity 3) — add the missing patch target

The Gate Set's `patch() target validation` row does not list `_should_advance_wp_step`, which
round 4's own test design requires patching at module level. That is the one gate whose entire
purpose is catching a wrong patch target, silent about the target this plan introduces. One line.

### PLAN-FRESH4-003 (severity 1) — delete the overclaim

"grepped exhaustively" is not true when a dozen bare references remain. Delete the word, or state
what was actually searched. Do not re-grep to make the claim true; the claim was never needed.

## What this ruling REPLACES

Per the review protocol, this ruling **replaces the acceptance bar** for the plan phase. A later
verifier must check that these three corrections landed and that no new severity>=3 finding was
introduced by them — it must **not** re-derive the original findings or re-open the fix design.

## Not in scope for the fix round

The `CLAUDE.md` drift (it instructs reading `SPEC-KITTY-LEDGER.md`, which is not in this
repository — that ledger lives in the operator's workspace) is real and correctly flagged, but it
is a repository documentation defect, not this mission's work. Leave it flagged.
