# Dossier Review Notes: release gate and generated snapshot

**Audience**: Spec Kitty maintainers and release operators

**Reviewed surface**: `fix/setup-plan-auth-diagnostics-nonfatal` at `f0d7d49c184c4eb58f656aef1ff5f2feb55c3aec`

**Reviewed at**: 2026-08-24T00:31:00+00:00

## Issue #3127 remains an external P0 release gate

Issue #3127 is recorded in `issue-matrix.json` as `deferred-with-followup` with
`Follow-up: #3127`. It does not block completion of Mission 196, but it does block an
affirmative release-readiness declaration until the issue is resolved and the
authoritative mainline CI gate permits release.

NI-005 defines the auditable declaration surface as these nine files:

- `spec.md`
- `tasks.md`
- `quickstart.md`
- `acceptance-matrix.json`
- `mission-review-report.md`
- `status.json`
- `issue-matrix.json`
- `retrospective.yaml`
- `dossier-review-notes.md`

Its executable command first requires the terminal `deferred-with-followup` row and
follow-up handle, then scans every listed file for an affirmative declaration shaped as
`release readiness: pass`, `release readiness: ready`, `release_ready: true`, or their
declared spelling variants. The verified result is zero affirmative declarations. This
is evidence from the bounded dossier, not a claim that any single report is the policy
authority.

## Generated dossier snapshot divergence

The following read-only command was run with SaaS disabled:

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=0 uv run spec-kitty reconcile \
  --mission setup-plan-auth-diagnostics-nonfatal-01M0QEAD --json
```

Result at the reviewed surface:

- Status: `divergence`
- Recorded hash: `sha256:61b9b3c631291d5538186bafb3c55198597078cb1b3743d54ce8e4ad3fc73d0d`
- Rebuilt hash: `sha256:571c67ac59aa0267f1c5c9ab84b8d3bc1b58fc425a1292d6e2b781af999ae5ee`
- Differing artifacts: 39
- Reconcile exit: non-zero, as required for divergence

The recorded snapshot predates final acceptance, review, and dossier evidence repairs.
It is a generated projection, not the authority for the local spec, acceptance matrix,
event log, or status reducer.

## Why refresh was refused

There is no supported refresh-only CLI. The only canonical snapshot writer is coupled
to dossier sync/local body capture. SaaS and hosted-sync effects are disabled for this
Mission, so invoking that pipeline would exceed the allowed side-effect policy.
Hand-authoring `snapshot-latest.json` would create a second, unaudited authority and was
also refused.

## Retry condition

Refresh only when both conditions hold:

1. the operator permits the canonical dossier capture pipeline for this checkout; and
2. the hosted-effect decision allows every resulting capture/queue effect.

After the canonical refresh, rerun the exact reconcile command above and require
`status: parity` with exit code 0. The old and new hashes above remain historical
evidence of why refresh was deferred; they must not be rewritten to simulate parity.
