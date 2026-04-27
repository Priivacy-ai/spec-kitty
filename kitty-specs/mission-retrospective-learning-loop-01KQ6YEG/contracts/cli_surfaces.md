# Contract: CLI Surfaces

**Status**: pinned for this tranche.
**Operator-facing surface**: `spec-kitty retrospect summary` (top-level, AD-003 / Q3-C).
**Agent-facing mutation surface**: `spec-kitty agent retrospect synthesize` (under `agent`, AD-003 / Q3-C).

The `retrospect` action and `retrospective-facilitator` profile (FR-001, FR-002) are DRG artifacts, not CLI commands. They are invoked through `spec-kitty next --agent <name> --mission <handle>` and consume DRG context like any other action.

---

## Command 1: `spec-kitty retrospect summary`

Top-level operator-facing read surface. Reads the project's mission corpus and emits a cross-mission summary.

### Usage

```
spec-kitty retrospect summary [OPTIONS]

Options:
  --project PATH            Project root (default: current working directory).
  --json                    Emit JSON to stdout instead of Rich rendering.
  --json-out PATH           Emit JSON to a file in addition to whatever rendering
                            is selected. Useful for downstream tools.
  --limit N                 Top-N for ranked sections (default: 20, max: 100).
  --since DATE              ISO-8601 date; only include missions whose
                            mission_started_at is on or after DATE.
  --include-malformed       Include malformed records' detail in output
                            (default: counts only).
  --help                    Show help and exit.
```

### Behavior

1. Discover retrospective records by globbing `<project>/.kittify/missions/*/retrospective.yaml` (NFR-003 ≤200 missions in <5 s).
2. For each, attempt schema-validating load. Malformed entries become `MalformedSummaryEntry` rows in the result. (NFR-004.)
3. Read proposal-lifecycle events from the mission's `kitty-specs/<slug>/status.events.jsonl`. Missing log → "no retrospective events" entry (no crash).
4. Reduce into a `SummarySnapshot`.
5. Render Rich output AND emit JSON if `--json` or `--json-out` is set. The Rich rendering and the JSON are informationally equivalent (CHK034). The JSON schema mirrors `SummarySnapshot` from data-model.md.

### Output sections (Rich + JSON)

- Counts: `mission_count`, `completed`, `skipped`, `failed`, `in_flight`, `legacy_no_retro`, `terminus_no_retro`, `malformed`.
- Top-N "not helpful" targets.
- Top-N "missing terms," "missing edges," "over-inclusion," "under-inclusion."
- Proposal acceptance metrics: `total / accepted / rejected / applied / pending / superseded`.
- Top-N skip reasons (HiC).
- Malformed entries (counts always; detail when `--include-malformed`).

### Exit codes

| Exit | Meaning |
|---|---|
| `0` | Summary produced (even if some missions had no retrospective). |
| `1` | Project root invalid (no `.kittify/` and no `kitty-specs/`). |
| `2` | I/O error reading the corpus (logs surfaced). |

### Examples

```bash
spec-kitty retrospect summary
spec-kitty retrospect summary --json --limit 10 > summary.json
spec-kitty retrospect summary --since 2026-01-01 --include-malformed
```

---

## Command 2: `spec-kitty agent retrospect synthesize`

Agent-facing surface that applies staged proposals from a mission's retrospective record. Default is `--dry-run`. Mutation is opt-in via `--apply` (FR-021).

### Usage

```
spec-kitty agent retrospect synthesize --mission <handle> [OPTIONS]

Required:
  --mission HANDLE          Mission handle (mission_id / mid8 / mission_slug).
                            Resolver disambiguates by mission_id.

Options:
  --dry-run                 (default) Plan + check; do not mutate.
  --apply                   Execute application after conflict + staleness checks pass.
  --proposal-id ID          Repeatable; restricts the batch to specific proposal ids.
                            Default: all proposals with state.status == "accepted",
                            plus all auto-applicable flag_not_helpful proposals.
  --json                    Emit JSON to stdout.
  --json-out PATH           Also write JSON to PATH.
  --actor-id ID             Override the actor recorded in provenance (default:
                            inferred from environment / user identity).
  --help                    Show help and exit.
```

### Behavior

1. Resolve the mission via the standard handle resolver. Ambiguous handle → structured `MISSION_AMBIGUOUS_SELECTOR` error (no silent fallback).
2. Load the retrospective record from the canonical path. Missing or malformed → exit code 3.
3. Compute the proposal batch (per `--proposal-id` or default).
4. Call `specify_cli.doctrine.synthesizer.apply_proposals(..., dry_run=<flag>)`.
5. Render `SynthesisResult` as Rich + (optional) JSON. Informationally equivalent.
6. Emit `retrospective.proposal.applied` / `.rejected` events as appropriate (only when `--apply`; dry-run emits no events).
7. Exit non-zero on conflicts/rejections when `--apply` was passed.

### Exit codes

| Exit | Meaning |
|---|---|
| `0` | Dry-run completed; or apply succeeded with no conflicts and no apply-time rejections. |
| `1` | Mission handle unresolvable (`MISSION_AMBIGUOUS_SELECTOR` or not found). |
| `2` | I/O error reading retrospective record. |
| `3` | Retrospective record malformed; refuse to operate. |
| `4` | Apply attempted with `--apply` but conflicts present; nothing applied. |
| `5` | Apply attempted with `--apply` but staleness/invalid-payload rejections present; nothing applied. |

### Examples

```bash
# Dry-run (default) for a mission, all accepted proposals
spec-kitty agent retrospect synthesize --mission 01KQ6YEG

# Apply a specific accepted proposal after dry-run looked clean
spec-kitty agent retrospect synthesize \
    --mission 01KQ6YEG --apply --proposal-id 01KQ6YE...P1

# Machine-readable plan
spec-kitty agent retrospect synthesize --mission 01KQ6YEG --json > plan.json
```

---

## Help text

Both commands ship Rich-rendered help. The help body for `retrospect summary` MUST mention:

- The data sources read (`.kittify/missions/*/retrospective.yaml` and `kitty-specs/*/status.events.jsonl`).
- The fact that no mutation is performed.

The help body for `agent retrospect synthesize` MUST mention:

- That `--dry-run` is the default and that `--apply` is required to mutate.
- That `flag_not_helpful` is the only auto-applied kind (Q2-A).
- That conflict detection is fail-closed.

---

## Output JSON shape

Both commands emit JSON whose top-level keys include a `schema_version` field (`"1"`) so downstream tools can pin. The JSON schema mirrors `SummarySnapshot` (for `summary`) or `SynthesisResult` (for `synthesize`) plus a thin envelope:

```json
{
  "schema_version": "1",
  "command": "retrospect.summary",
  "generated_at": "2026-04-27T11:35:00+00:00",
  "result": { ... }
}
```

```json
{
  "schema_version": "1",
  "command": "agent.retrospect.synthesize",
  "generated_at": "2026-04-27T11:35:00+00:00",
  "dry_run": true,
  "result": { ... }
}
```
