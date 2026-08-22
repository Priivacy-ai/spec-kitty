# M2 tracer — tooling friction

Append friction encountered running this mission (CLI, gates, environment).

- 2026-08-21 (planning): runtime `next` reports the pre-authored, committed spec as
  `not_started`/`discovery` — the spec-now batch wrote artifacts without advancing
  runtime state, so the workflow must be stepped through discovery→specify with the
  existing spec confirmed rather than re-derived.
