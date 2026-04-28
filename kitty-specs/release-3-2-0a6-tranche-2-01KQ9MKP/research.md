# Phase 0 Research: 3.2.0a6 Tranche 2

**Mission**: `release-3-2-0a6-tranche-2-01KQ9MKP`
**Date**: 2026-04-28

This document records the per-issue decisions, rationales, and rejected alternatives for the seven defects in scope. There are no `[NEEDS CLARIFICATION]` items — the two product forks were resolved at spec time and are restated here as decisions.

---

## D1 — Issue #840: `init` stamps `schema_version` and `schema_capabilities`

**Decision**: Have `spec-kitty init` write `schema_version` (current value driven by the migration runner's known capability table) and a `schema_capabilities` block into `.kittify/metadata.yaml` at project creation time. The stamp is **additive only**: if the file already exists with operator-authored fields, those fields are preserved unchanged; the schema fields are merged in if absent and reconciled (without value mutation) if present.

**Rationale**: Fresh-project flows downstream (`charter setup`, `next`, anything calling the migration runner) currently assume these fields exist. Without them, fresh projects fail with a "missing schema" error and operators must hand-edit `.kittify/metadata.yaml` to proceed. Stamping at `init` time eliminates the manual step and matches the documented golden path. The migration runner already knows the canonical capability set; this fix wires that knowledge into `init`.

**Alternatives considered**:
- *Implicit defaults at read time*: have consumers tolerate missing schema fields. Rejected — pushes the contract into every reader and hides drift between project state and runtime expectations.
- *Run a migration as part of `init`*: piggyback on the migration runner. Rejected as heavier than necessary; a one-shot stamp is sufficient and keeps `init` semantics simple.
- *Document the manual edit*: rejected by the tranche acceptance criterion — fresh paths must not require manual metadata editing.

**Test strategy**:
- Unit test: `init` on an empty directory yields a `metadata.yaml` containing `schema_version` (matching migration runner's current target) and the expected `schema_capabilities` map.
- Integration test: `init` on a directory with a pre-existing `metadata.yaml` (with operator-authored keys) preserves those keys byte-identical and only adds missing schema fields.
- Idempotency test: running `init` twice produces the same final file content (excluding any unrelated timestamps).

---

## D2 — Issue #842: `--json` commands emit strict JSON

**Decision**: Audit every `--json` command's stdout path. Sync, auth, tracker, and any other diagnostic prints get routed to **stderr** by default. If a diagnostic must surface to the JSON consumer (e.g., partial-success cases), nest it inside the JSON envelope under a top-level key (proposed: `diagnostics`) — never as a bare line on stdout outside the envelope. The contract is enforced by a parametrised integration test that runs every covered `--json` command across the four SaaS states (`disabled`, `unauthorized`, `network-failed`, `authorized-success`) and asserts `json.loads(stdout)` succeeds.

**Rationale**: External scripts and CI consumers cannot tolerate non-JSON noise on stdout. Today, lines like `Not authenticated, skipping sync` are printed unconditionally to stdout, breaking strict parsing. Routing diagnostics to stderr is the standard Unix convention; it preserves the strict-JSON contract and remains visible to humans reading terminal output.

**Alternatives considered**:
- *Always silently swallow sync diagnostics*: rejected — debuggability matters; users need a signal when sync is unreachable.
- *Always nest diagnostics in the envelope*: rejected as a default — adds churn for consumers that don't care about sync state. Reserved for explicit partial-success cases.
- *Add a separate `--quiet` flag*: rejected — the `--json` flag already signals a programmatic consumer; the right contract is "stdout is parseable JSON" without further opt-in.

**Test strategy**:
- Parametrised integration test across the four SaaS states for each covered `--json` command.
- Assert `json.loads(stdout)` succeeds and that any diagnostic content appears on stderr or under the documented envelope key.
- Spec contract documented in `contracts/json-envelope.md`.

---

## D3 — Issue #833: `WPMetadata.resolved_agent()` parses `tool:model:profile_id:role`

**Decision**: Update the `resolved_agent()` parser to handle four colon-separated arities (1, 2, 3, 4 segments) and return a 4-tuple `(tool, model, profile_id, role)`. Missing trailing fields fall back to documented defaults. No silent discard — any non-empty supplied segment is preserved verbatim. The implement and review prompt-rendering layers consume the 4-tuple and surface `model`, `profile_id`, and `role` in the rendered context.

**Defaults for missing trailing fields** (documented in `data-model.md`):
- `model`: agent's default model (existing behavior).
- `profile_id`: agent's default profile id (existing behavior).
- `role`: `implementer` (existing behavior).

**Rationale**: The current parser silently truncates to `tool` only when it sees colons it didn't expect, so an operator passing `claude:opus-4-7:reviewer-default:reviewer` ends up with the default model and the default role at runtime — invisible data loss with high cost in the review loop. The fix is a small parser change in `status/wp_metadata.py` plus a wiring change in the prompt renderer. Backward compatibility is preserved by keeping the same default fall-throughs.

**Alternatives considered**:
- *Reject unknown colon counts*: rejected — breaks today's bare-`tool` and `tool:model` callers.
- *Move to a JSON-encoded `--agent` flag*: rejected — out of scope for this tranche; would be a public CLI change.
- *Preserve only `tool` and `model`, drop `profile_id` / `role` from runtime*: rejected — the prompt layer already consumes them.

**Test strategy** (NFR-004):
- Unit: one test per arity (`tool`, `tool:model`, `tool:model:profile_id`, `tool:model:profile_id:role`) asserting 4-tuple values.
- Unit: empty-segment cases (e.g., `tool::profile_id:role`) — empty positional segments fall back to defaults.
- Integration: a rendered implement prompt for a 4-arity input contains the supplied `model`, `profile_id`, and `role` strings.

---

## D4 — Issue #676: review-cycle counter only advances on real rejections

**Decision**: Decouple the review-cycle counter from the implement command. The counter advances **only** on a real `rejection` event from the reviewer pipeline. The reclaim/regenerate-prompt code path becomes idempotent: it does not increment, does not write a new `review-cycle-N.md`, and does not touch the counter file. The counter location and the on-disk `review-cycle-N.md` artifacts remain authoritative for inspection.

**Rationale**: Today, re-running `agent action implement` to regenerate the implement prompt also bumps the review-cycle counter and writes a fresh `review-cycle-N.md`, even when no reviewer rejection occurred. This corrupts review state and inflates the counter, masking the true number of rejection rounds. The fix is to gate counter advancement on the rejection event handler, not the implement command.

**Alternatives considered**:
- *Make the counter purely derived from artifacts*: rejected — cycles can be re-emitted manually under operator pressure; an explicit, event-gated counter is more auditable.
- *Add an `--idempotent` flag to implement*: rejected — idempotency should be the default, not a flag.
- *Delete `review-cycle-N.md` artifacts on regenerate*: rejected as destructive; the right fix is not to create them spuriously.

**Test strategy** (NFR-005):
- Unit: re-run `implement` ≥ 3 times against a `for_review` WP and assert counter unchanged and no new `review-cycle-N.md` files created.
- Integration: simulate a real rejection event and assert the counter advances by exactly one and exactly one new artifact appears with `N` matching the post-increment value.
- Property: counter is monotonic non-decreasing across the full WP lifecycle.

---

## D5 — Issue #843: `next` writes paired profile-invocation lifecycle records

**Decision**: When `spec-kitty next --agent <name>` issues a public action, write a `started` profile-invocation lifecycle record to the existing local invocation store. When the same action subsequently advances (success or explicit failure), write a paired `completed` (or `failed`) record. Both records share the same canonical action identifier — derived from the mission step/action issued by `next`. A validation step on lifecycle pairs detects orphans and surfaces them via the existing doctor surface.

**Rationale**: Public `next` cycles currently write no observable lifecycle trace, so it's impossible to reconcile what `next` issued against what an agent actually executed. Pair records close that observability loop and make it possible to detect agent crashes mid-cycle. The canonical action identifier guarantees pairs can be correlated even when the local store has many concurrent records.

**Alternatives considered**:
- *Write only `completed` records*: rejected — without `started`, orphans are invisible and pair-matching is impossible.
- *Use a UUIDv4 for pair identity*: rejected — the canonical mission step/action identifier is already deterministic and human-readable; reusing it makes traces self-describing.
- *Write to SaaS only*: rejected — local-first is non-negotiable per `SPEC_KITTY_ENABLE_SAAS_SYNC` policy and offline correctness.

**Test strategy** (NFR-006):
- Unit: `next` emits `started` with the issued canonical action identifier; advance emits matching `completed`.
- Unit: simulated mid-cycle crash leaves an orphan `started` that the doctor surface lists.
- Integration: ≥ 5 issued actions with all pairs matched yields ≥ 95% pairing rate.

---

## D6 — Issue #841: `charter generate` and `charter bundle validate` agree

**Decision** (resolves Spec Assumption A1): `charter generate` **auto-tracks** the produced `charter.md` so that `charter bundle validate` accepts the result without a manual `git add`. In a non-git environment, `generate` fails with an actionable error naming the remediation (e.g., "initialize a git repository, or use the documented offline path"). The user-facing governance setup documentation (FR-017) is updated to remove any redundant `git add` step.

**Rationale**: The acceptance criterion "fresh `init → charter setup/generate/synthesize → next` paths do not require manual metadata or doctrine seeding" demands that the operator can chain `generate` and `bundle validate` without intervening git intervention. Auto-tracking is the minimal change that achieves parity. Failing fast in non-git environments avoids the silent inconsistency that triggered the bug in the first place.

**Alternatives considered**:
- *Loosen `bundle validate` to accept untracked `charter.md`*: rejected — `bundle validate` exists precisely to verify what's in the bundle from git's perspective; weakening it weakens the governance guarantee.
- *Defer auto-track to a separate command (`charter track`)*: rejected — adds a documented step the user must remember; defeats the goal.
- *Always auto-commit*: rejected as too aggressive; tracking (staging) is enough for `validate` to succeed.

**Test strategy**:
- Integration: in a fresh git repo, `generate` followed by `bundle validate` succeeds with no intervening git command. Assert `charter.md` is present and tracked (staged) but not necessarily committed.
- Integration: in a non-git directory, `generate` exits non-zero with a specific error string naming the remediation.
- Documentation diff: any `git add charter.md` step is removed from the governance setup docs.

---

## D7 — Issue #839: public CLI `charter synthesize` works on a fresh project

**Decision** (resolves Spec Assumption A2): The public CLI path `spec-kitty charter synthesize` runs successfully on a fresh project that has never had `.kittify/doctrine/` hand-seeded. The fix is bounded: synthesize must produce whatever doctrine artifacts the runtime needs from the canonical inputs already available on a fresh project (charter.md after #841 lands, plus the in-package canonical doctrine seed). The consolidated golden-path E2E (`tests/e2e/test_charter_epic_golden_path.py`) is updated to no longer hand-seed `.kittify/doctrine/` and to no longer hand-edit `.kittify/metadata.yaml`.

**Rationale**: A test-only adapter would create a divergence between what tests exercise and what users hit. Fixing the public CLI is the only path that satisfies the spec's acceptance criteria (SC-001, SC-007) without introducing a parallel code path. The change is bounded by Risk Map mitigation — if scope expands beyond making the existing public surface succeed on a fresh project, escalate before merging.

**Alternatives considered**:
- *Test-only adapter*: rejected per Assumption A2; code path divergence is a future bug factory.
- *Ship doctrine seeds with `init`*: rejected — bloats `init` output and conflates init and synthesize responsibilities.
- *Block fresh-project synthesize until charter doctrine is hand-authored*: rejected — that is exactly the bug.

**Test strategy** (NFR-007, SC-001, SC-007):
- E2E: golden-path test runs `init → charter setup → charter generate → charter synthesize → next` against a fresh tmpdir, with no hand seeding and no manual git operations. Assert under-120s runtime budget and final state matches the documented golden path.
- Integration: synthesize on a fresh project (post-#840, post-#841) writes the expected doctrine artifact set; running synthesize twice is idempotent.

---

## Cross-cutting decisions

**Decision X1 — No new dependencies**. Confirmed: every fix above is achievable inside the existing dependency set (`typer`, `rich`, `ruamel.yaml`, `pytest`, `mypy`). If implementation reveals a hard dependency need, escalate before adding it (SC-008).

**Decision X2 — Shared package boundary preserved**. Continue to consume `spec_kitty_events.*` and `spec_kitty_tracker.*` only via their public imports. No vendoring, no new boundary crossings (C-007).

**Decision X3 — Mission identity model preserved**. No code in this tranche reads `mission_number` as identity; all selectors continue to flow through `mission_id` / `mid8` / `mission_slug` (C-004, A5).

**Decision X4 — Local SaaS toggle**. Test commands that touch SaaS, tracker, or hosted auth surfaces set `SPEC_KITTY_ENABLE_SAAS_SYNC=1` per the machine-level AGENTS.md (C-003, A4).
