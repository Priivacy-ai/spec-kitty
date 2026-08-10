# Closure dossier: per-project sync consent ledgers

## Scope

This dossier will collect the evidence needed to close core #3262 and to support,
but not automatically close, SaaS #585.

## Prevention evidence

- [ ] Default-deny consent resolver.
- [ ] Global environment flag cannot grant project egress consent.
- [ ] Per-project ledger/storage resolver.
- [ ] Selection/transmit/acknowledgement/purge predicates keyed by event/task project.
- [ ] Daemon and body-upload paths refuse non-consenting projects.
- [ ] Old-client/bypass seams fail closed.
- [ ] Two-project integration proof.

## Historical incident boundary

SaaS #585 recorded 1,322 events from five non-consenting projects that were already
delivered alongside the intended opted-in project data. This mission prevents the
class from recurring, but #585 remains open until those historical events receive
an approved remediation disposition.

## Evidence log

| Date | WP | Evidence | Result |
|------|----|----------|--------|
| 2026-08-10 | Planning | Mission spec/plan/tasks created | Pending implementation |
