# Research — Sync CLI Degod (Wave 4)

Phase 0 consolidation. All design questions were resolved by a 4-lens research squad (decomposition ·
architectural-compat · mechanical-slices+golden-surface · scope/tracking) — full record in
[research/mission-brief.md](./research/mission-brief.md) — and hardened by a post-spec adversarial
squad ([research/squad-findings-post-spec.md](./research/squad-findings-post-spec.md)). No NEEDS
CLARIFICATION markers remain. No dependency decisions (supply-chain N/A).

## Decision 1 — Decomposition pattern: ports + pure cores + thin shells (runtime_bridge template)
- **Decision**: Follow the `runtime_bridge` (#2531) six-seam split (closest analogue — large, I/O-heavy,
  many monkeypatched privates) + the coord-authority trio (#2464/#2465/#2508) shell+core+executor
  pattern, reusing the `agent_tasks_ports.py` port protocols and `TasksPorts`/`default_ports()` shape.
- **Rationale**: proven on the exact class of module; reuses the canonical port authority (single-canonical-authority).
- **Alternatives considered**: a fresh port abstraction (rejected — forks a second authority); a pure
  mechanical smell sweep without decomposition (rejected — leaves the 3 C901 and the 6,332-LOC god-module).

## Decision 2 — Cores/ports placement: under `specify_cli.sync.*`
- **Decision**: nest new cores/ports under `specify_cli.sync.*` (with the Typer `app` + husk in `cli/commands/sync.py`).
- **Rationale**: `cli.commands.sync → specify_cli.sync.*` is a legal inbound edge (already used for `consent`);
  `runtime` is a lower layer and may not import `specify_cli` (`test_layer_rules.py`); no new top-level
  package (`test_no_unregistered_src_packages`).
- **Constraint surfaced**: placement must not add a new `status`/`dossier`→sync edge (#862 gates) — folded into C-001.

## Decision 3 — Golden-CLI-characterization FIRST; the ~60 patch-tests are the seam co-gate
- **Decision**: freeze all 22 subcommands' observable contract before any extraction; the golden test proves
  *production* behavior, the ~60 sync-monkeypatch tests prove the *seam* is preserved.
- **Rationale**: the roadmap non-negotiable (golden replaces DIR-041 ratchets); the post-spec squad proved the
  husk re-export is necessary-not-sufficient for call-time patch dispatch, so patched callees must be reached
  through the shell (C-005) and the patch-tests co-gated (NFR-001).
- **Alternatives considered**: rely on the husk re-export alone (rejected — silent patch-dispatch no-op risk).

## Decision 4 — Two-authority split guarded by an arch-test
- **Decision**: keep read-authority and write-authority as two ports; add `tests/architectural/test_sync_two_authority.py`
  asserting distinct symbols / no shared authority class.
- **Rationale**: the #2160-class invariant; the post-spec squad confirmed no existing gate guards non-unification,
  so "verifiable from the diff" was insufficient.

## Decision 5 — Deferrals: env-deletion → WS6, daemon-lifecycle → WS4
- **Decision**: census/inventory env vars (no deletion); relocate daemon read/guard code intact without changing
  reuse/kill/lifecycle behavior. Emitter/queue/daemon adapter-consolidation out of scope.
- **Rationale**: WS6 versioned-contract ADR gates safe env deletion; WS4 daemon-identity gates lifecycle change;
  scope/tracking lens confirmed the CLI-split is cleanly separable from the adapter-consolidation follow-on.

## Adversarial evidence (per contracts/adversarial-evidence-contract.md)
No security-impacting dependency decision was made (supply-chain N/A). A **post-spec adversarial squad**
(architect-alphonso, reviewer-renata, planner-priti) challenged the spec; every contested finding's
disposition is recorded in `research/squad-findings-post-spec.md` — all `changed` (folded into the spec) or
`accepted`; **none dropped**. A post-plan adversarial squad runs at the next point-cut.

## Residual / deferred (tracked)
- Emitter/transport_attempts/queue/daemon adapter-consolidation (WS4/WS6/#2173-Phase-2) — FR-008 follow-on.
- Env-var deletion of retire-candidates (`SPEC_KITTY_SYNC_READONLY_IDENTITY`, `SPEC_KITTY_NO_AUTO_CUTOVER`) → WS6.
