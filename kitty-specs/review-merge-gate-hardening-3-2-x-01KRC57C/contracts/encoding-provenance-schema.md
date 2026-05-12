# Contract: Encoding provenance schema

**WP**: WP06 | **FRs**: FR-022 | **HiC decision**: dual-storage, prefer per-mission, centralize shared

## Record schema (JSONL; one record per line)

```json
{"event_id": "01HXYZ...",
 "at": "2026-05-12T18:30:00+00:00",
 "file_path": "kitty-specs/<mission>/charter/charter.yaml",
 "source_encoding": "cp1252",
 "confidence": 0.93,
 "normalization_applied": true,
 "bypass_used": false,
 "actor": "spec-kitty charter compile",
 "mission_id": "01KRC57CNW5JCVBRV8RAQ2ARXZ"}
```

Field semantics: see `data-model.md` §3 `EncodingProvenanceRecord`.

## Routing rule

A record is appended to **exactly one** file. The chokepoint inspects `file_path`:

- **Per-mission**: if `file_path` starts with `kitty-specs/<mission-slug>/`, append to `kitty-specs/<mission-slug>/.encoding-provenance.jsonl`. Set `mission_id` to the mission's ULID (resolved from `kitty-specs/<mission-slug>/meta.json`).
- **Centralized**: otherwise, append to `.kittify/encoding-provenance/global.jsonl`. Set `mission_id` to `null`.

There is **no third destination**, and a single event is **never** appended to both files.

## File layout

```
kitty-specs/
├── <mission-slug-A>/
│   ├── charter/
│   └── .encoding-provenance.jsonl     # per-mission events for this mission
├── <mission-slug-B>/
│   ├── charter/
│   └── .encoding-provenance.jsonl     # per-mission events for this mission
└── ...

.kittify/
├── charter/                            # global charter (not mission-scoped)
└── encoding-provenance/
    └── global.jsonl                    # events for charter content outside any kitty-specs/<mission>/ tree
```

## Append semantics

- Append is `open(..., "a", encoding="utf-8")` + `f.write(json.dumps(record, sort_keys=True) + "\n")` — same pattern as the existing `status.events.jsonl` writer (see `src/specify_cli/status/store.py`).
- `event_id` is a fresh ULID per record (uses the existing ULID utility from `specify_cli.id_gen` or equivalent).
- `at` is ISO-8601 UTC with offset; same format as status events.

## Read semantics

Consumers (audit tooling, hypothetical future dashboard) may `cat` per-mission + centralized files together without coalescing logic. Each record is self-describing via `mission_id`.

## Acceptance fixtures

- Ingest a file under `kitty-specs/foo-01KQ.../charter/x.yaml` → record appears in `kitty-specs/foo-01KQ.../.encoding-provenance.jsonl`, NOT in `.kittify/encoding-provenance/global.jsonl`.
- Ingest a file under `.kittify/charter/y.yaml` → record appears in `.kittify/encoding-provenance/global.jsonl`, NOT in any mission file.
- Concurrent appenders (two `spec-kitty charter compile` invocations in parallel) → all records survive; no overwrite.

## Invariants

- Record schema is identical across both files (same keys, same types).
- No record is duplicated across files.
- The schema is JSON-stable per NFR-001; new keys may be added but existing key names and types never change without a deprecation cycle.
