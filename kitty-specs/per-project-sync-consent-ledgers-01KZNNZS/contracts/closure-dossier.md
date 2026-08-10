# Closure dossier: per-project sync consent ledgers

## Scope

This dossier collects the evidence needed to close the prevention class in core
#3262 and to support, but not automatically close, SaaS #585.

## Prevention evidence

- [x] Default-deny consent resolver.
- [x] Global environment flag cannot grant project egress consent.
- [x] Per-project ledger/storage resolver.
- [x] Selection/transmit/acknowledgement/purge predicates keyed by event/task project.
- [x] Daemon and body-upload paths refuse non-consenting projects.
- [x] Old-client/bypass seams fail closed.
- [x] Two-project integration proof.

## Historical incident boundary

SaaS #585 recorded 1,322 events from five non-consenting projects that were already
delivered alongside the intended opted-in project data. This mission prevents the
class from recurring, but #585 remains open until those historical events receive
an approved remediation disposition.

## Evidence log

| Date | WP | Evidence | Result |
|------|----|----------|--------|
| 2026-08-10 | Planning | Mission spec/plan/tasks/analysis created | Complete |
| 2026-08-10 | WP01 | Default-deny consent authority; env flag is arming only | 94 passed, 2 xfailed |
| 2026-08-10 | WP02 | Per-project ledger and selector resolver | 56 passed |
| 2026-08-10 | WP03 | Safe migration/backfill from shared state | 60 passed |
| 2026-08-10 | WP04 | Explicit opt-in/out/status UX | 67 passed |
| 2026-08-10 | WP05 | Daemon/body/delivery/history-import/SaaS-client enforcement | 132 passed |
| 2026-08-10 | WP06 | Closure proof and runbook | 126 passed |

## Closure verdict

- Core #3262 prevention closure: ready for PR review after the mission review
  gate confirms spec-to-artifact fidelity.
- SaaS #585 historical closure: not ready. The prevention class is addressed,
  but the already-delivered 1,322 events still require an approved remediation
  disposition before #585 can be closed.

## Runbook

See `docs/runbooks/hosted-sync-consent-incident.md` for the operator closure
procedure, focused proof command, and reopening triggers.
