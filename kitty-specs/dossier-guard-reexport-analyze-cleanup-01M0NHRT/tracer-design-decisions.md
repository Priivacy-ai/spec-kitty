# Tracer: Design Decisions — dossier-guard-reexport-analyze-cleanup

Seeded at planning (plan phase). Append during implementation; assess at close per the
`mission-tracer-files` procedure (charter Standing Order #3).

These are restatements of design decisions spec.md already made (in its Clarifications/
Decision-Record section and its four Grounding Corrections) — this plan's own design-decision
record, citing spec.md rather than re-deriving. Each entry names the spec.md source explicitly.

## DD-001 — Attribute-chain resolution goes by final-attribute-name only

**Decision**: The widened guard's attribute-chain matching (FR-001) resolves on the *final*
attribute name of the outermost `ast.Attribute` node (e.g. `.emit_artifact_indexed` in
`a.b.dossier.emit_artifact_indexed(...)`), regardless of chain depth or what object the chain
actually resolves to at runtime.

**Source**: spec.md's Edge Cases section ("What happens when an attribute-chain call is nested
more than one level deep?") and User Story 2's own framing.

**Rationale (restated, not re-derived)**: This mirrors the existing bare-`Name` detector's already-
accepted false-positive risk tradeoff — `test_detector_ignores_unrelated_same_name_free_function`
already proves the *existing* detector accepts some risk of matching an unrelated function that
happens to share a guarded name, and the spec extends that same accepted tradeoff to the
attribute-chain shape rather than inventing a new, stricter (and much more expensive) resolution
strategy that would need real type/import-graph analysis to do properly. The guard is an AST-syntax
scanner, not a type checker; matching on the final name only keeps it in that lane.

## DD-002 — No data-flow tracking for aliased-import reassignment or dynamic dispatch

**Decision**: The widened guard performs single-level, syntactic import-alias resolution only (an
`ast.ImportFrom` alias matched to its original name within the same file) — it does not track
reassignment of an aliased name after import, and it does not resolve dynamic/reflective dispatch
(`getattr(module, "emit_x")(...)`, a dispatch-dict table, `functools.partial`-wrapped emitters).

**Source**: spec.md's Edge Cases section (the alias-reassignment bullet and the dynamic-dispatch
bullet) and Acceptance Scenario 2 under User Story 2.

**Rationale (restated)**: Both boundaries are explicit scope limits already recorded in spec.md,
not gaps discovered during planning. The guard remains a syntactic AST matcher throughout — adding
data-flow or runtime-reflection tracking would be a materially different (and much heavier) tool
than the "close two named, currently-open gaps" scope #3676 defines. FR-003's docstring update
must state these boundaries explicitly (not silently assume them), per spec.md's own instruction.

## DD-003 — Charter path relativizes against `canonical_root`, not `repo_root`

**Decision**: FR-007's path relativization uses two different governing roots depending on which
`input_artifacts` entry is being recorded: `repo_root` for the three hash-input artifacts
(`spec.md`, `plan.md`, `tasks.md`), but `canonical_root` — the root `_charter_path` already
resolves via `resolve_canonical_repo_root(repo_root)` — for the `charter` entry specifically.

**Source**: spec.md Grounding Correction 3, in full.

**Rationale (restated, not re-derived)**: `_charter_path` was already deliberately written (the
#1823 fix) to resolve the charter through the canonical root rather than the passed-in `repo_root`,
specifically so a linked worktree's analysis report hashes the MAIN checkout's charter, not a
worktree-local copy. `test_charter_hash_resolves_canonical_root_from_worktree` is an existing,
currently-green test that asserts exactly this cross-root behavior in production. A single uniform
rule ("relativize every `input_artifacts` path against `repo_root`, raise if not possible") would
make that legitimate, tested, intentional cross-root case indistinguishable from the actual SK-63
leak this mission fixes, and would force a choice between breaking a green #1823 regression test or
weakening FR-007's raise-on-failure guarantee for a case that is not actually a leak. Splitting the
governing root per-entry avoids that false choice entirely: the `charter` entry raises/reports only
if it cannot be expressed relative to *its own* governing root, never against an unrelated
`repo_root` it was never meant to be measured against.

## DD-004 — `check_analysis_report_current`'s non-raising contract is preserved by construction, not by suppression

**Decision**: The new relativization-failure path (FR-007/NFR-002) is caught *inside*
`check_analysis_report_current` (or inside `collect_input_artifact_hashes`, with
`check_analysis_report_current` catching a typed exception it raises) and mapped to
`AnalysisFreshness(ok=False, reason=...)`. It is never allowed to propagate as a raised exception
out of `check_analysis_report_current`. `write_analysis_report`, by contrast, is allowed to raise —
it has no established non-raising contract.

**Source**: spec.md Grounding Correction 3 (the established-contract paragraph),
Acceptance Scenario 5 under User Story 1, and NFR-002 verbatim.

**Rationale (restated)**: `check_analysis_report_current`'s caller, `_require_current_analysis_report`
(`cli/commands/agent/workflow.py:950`), depends on `check_analysis_report_current` always returning
a typed result — every existing branch in that function already returns/consumes an
`AnalysisFreshness`, never raises. Introducing a new failure mode (relativization can now fail,
where it never could before when the code just wrote `str(path)` unconditionally) is exactly the
kind of change that silently breaks an established contract if it is not deliberately mapped at the
boundary. The design decision is explicit about *where* the catch happens (inside
`check_analysis_report_current`'s own call, not left to its caller) precisely because
`_require_current_analysis_report` was written assuming this function cannot raise, and auditing
every caller of `check_analysis_report_current` for new exception handling was correctly judged (in
spec.md) as the wrong place to absorb this risk.

## DD-005 — Commit-subject fix beats ignore-list widening

**Decision**: FR-006's fix gives the `record-analysis` commit a real conventional-commit subject
(`docs(<scope>): <subject>`, `type` pinned to `docs`) rather than widening
`commitlint.config.cjs`'s `ignores` regex to also match an `analysis` artifact-type token.

**Source**: spec.md Grounding Correction 4, in full, including its citation of ledger entry SK-64's
own prior first-hand investigation and stated fix-direction preference.

**Rationale (restated, not re-derived)**: Two independent facts converged on this in spec.md's own
grounding pass, both worth restating here since they are the actual load-bearing evidence: (1) the
mission brief's own illustrative alternative message did not even satisfy the *current* ignore
regex without also widening it — so "just adjust the message" was never actually a smaller change
than "adjust the message AND widen the regex," collapsing the apparent two-option choice into one
real comparison; (2) SK-64, investigating the identical defect independently and earlier, already
measured it directly (2 of 52 commits in a real mission's history failed commitlint, both this same
message) and already stated its own preferred fix order with option (1) — a conforming subject —
listed first, specifically because it "fixes the cause and needs no ignore-list growth." Choosing
the conforming-subject fix is therefore not a fresh preference invented in this plan; it is
adopting SK-64's own prior, evidence-backed conclusion, further reinforced by this repo's own
established practice of giving tool-authored analyze/review commits real conventional-commit types
(the cited `docs(review): commit pre-merge verification and fresh sweep for implementation diff`
example, observed directly in this checkout's own `git log`). Widening the ignore-list was rejected
because it grows a repo-wide special-case allowlist every other commit's linting also depends on,
for a cost (two files touched instead of one) that buys nothing a message fix does not already buy.
