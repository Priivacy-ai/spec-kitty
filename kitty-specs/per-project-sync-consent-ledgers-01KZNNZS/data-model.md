# Data model notes: per-project sync consent ledgers

## Project consent decision

- `project_id`: stable project UUID/hash used by event journal and delivery rows.
- `project_root`: normalized checkout root for user-facing status only.
- `decision`: `allowed`, `denied`, or `disabled`.
- `source`: explicit project grant, explicit project denial, rollout disabled, missing consent, migration ambiguity, or diagnostic failure.
- `reason`: human-readable status/doctor text.
- `evaluated_at`: timestamp used for audit/status evidence.

## Ledger scope key

All event journal, offline queue, body-upload queue, delivery ledger, selection,
acknowledgement, purge, and status operations must resolve a project scope before
returning egress candidates.

## Legacy classification

- `imported`: row has provable project ownership and can move into that project's scoped ledger.
- `refused`: row belongs to a project that lacks explicit consent.
- `ambiguous`: row cannot be attributed to a project; keep local-only until ownership is proven.
- `unchanged`: row is already in a scoped/current format.
