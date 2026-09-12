# Status History Errata

## Event `01M0SCH08432EXH26NF3VFZG1T`

This forced `WP06` transition from `for_review` back to `in_progress` was an
administrative handoff correction made before any reviewer verdict existed. Its
recorded reason states that the final implementation commit needed to precede
the authoritative `for_review` transition. The command version used at the time
did not attach a `review_ref`, so current status validation reports the historic
event as incomplete.

The event is intentionally not rewritten: `status.events.jsonl` is append-only
mission history. The later WP06 rejection and approval cycles are independently
recorded in `tasks/WP06-uncontended-verdict-performance/`, and the final approval
is present in the canonical event log. This erratum documents the metadata gap;
it does not waive or alter any implementation or review verdict.
