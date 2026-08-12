# Data Model: Test Sanitation Evidence

## RunEnvironment

Hash-addressed identity for a collection, execution, or timing observation.

| Field | Type | Rule |
|-------|------|------|
| `id` | string | SHA-256 over normalized fields below |
| `os` / `runner_image` / `cpu_class` | string | exact platform/runner identity |
| `python` | string | implementation + full version |
| `event` | string | local, PR, push, schedule, or manual |
| `env` | map[string,string] | explicit allowlist; secrets redacted |
| `lock_hash` | string | `uv.lock` hash |
| `install_command` / `install_state` | list[string] / string | exact setup and cache state |
| `workers` / `cache_policy` | string | exact topology and cache behavior |
| `harness_patch_hash` | string/null | exact #3283 replay artifact hash |

## CandidateObservation

Environment-specific observation; one candidate may have several.

| Field | Type | Rule |
|-------|------|------|
| `environment_id` | RunEnvironment ref | required |
| `nodeid` | string/null | null only for source-only/zero-node unit |
| `collection_state` | enum | `collected`, `ignored`, `deselected`, `error`, `zero_node` |
| `outcome` | enum/null | `passed`, `failed`, `error`, `skipped`, `xfailed`, `xpassed`, `not_run` |
| `skip_reason` | string/null | required for skipped/xfail/quarantine behavior |
| `markers` | list[string] | effective inherited markers |
| `duration` | object | collection/setup/call seconds and cost class |
| `artifact_hash` | string | raw observation artifact |

## RouteMembership

| Field | Type | Rule |
|-------|------|------|
| `route_id` | string | stable frozen route ID |
| `role` | enum | `owner`, `coverage`, `platform`, `hard_gate` |
| `required` | boolean | branch/release requirement |
| `events` | list[string] | triggering event set |
| `selector` | object | exact paths, markers, ignores, environment |

Changed narrow classes require exactly one `owner`. Documented secondary execution is allowed through other roles.

## TestCandidateUnit

| Field | Type | Rule |
|-------|------|------|
| `id` | string | stable unique slug |
| `members` | list[string] | source functions or nodeids; nonempty |
| `granularity` | enum | `function`, `family`, `duplicate_cluster`, `node` |
| `source_paths` | list[path] | repository-relative |
| `production_paths` | list[path/symbol] | alleged source targets/live seams |
| `oracle` | string/null | intended observable assertion |
| `contract_claim` | string/null | named observable contract |
| `authority` | list[reference] | active spec, ADR, contract, matrix, or issue |
| `duplicate_group` | string/null | normalized body/semantic group |
| `route_memberships` | list[RouteMembership] | owner and secondary roles |
| `platforms` | list[string] | supported scope |
| `observations` | list[CandidateObservation] | at least one for deep rows |

A family/cluster must share production path, oracle, outcome class, route role, cost class, platform scope, and disposition. Any divergence creates child node records. A ledgered `KEEP` requires non-null contract claim, authority, production path, and oracle.

## EvidenceBundle

Evidence is class-specific, not universally maximal.

| Field | Type | Used by |
|-------|------|---------|
| `profile` | enum | `inert`, `duplicate`, `structural`, `contract`, `slow`, `flake`, `dead_symbol`, `route`, `environmental_platform` |
| `caller_evidence` | list[command/result] | contract, dead symbol |
| `authority_evidence` | list[reference/result] | all except mechanically inert placeholder where issue/absence is enough |
| `routing_evidence` | list[RouteMembership/result] | inert, regression, route |
| `base_evidence` | object | red/flake/bootstrap/timing claims |
| `causal_probe` | object | structural, contract, duplicate survivor, changed survivor |
| `overlap_evidence` | list[comparison] | duplicate/consolidate |
| `cost_evidence` | object | slow/route and duplicate preference |

`causal_probe` explicitly includes `kind`, `fault`, `authority_violated`, `act_reached`, `intended_oracle`, `intended_oracle_failed`, command, environment, and raw artifact hash. Collection/import/setup failures never satisfy it.

## DispositionRecord

| Field | Type | Rule |
|-------|------|------|
| `candidate` | TestCandidateUnit | exactly one deep candidate |
| `evidence` | EvidenceBundle | satisfies profile requirements |
| `verdict` | enum | `KEEP`, `CONSOLIDATE`, `FIX_TEST`, `FIX_PRODUCT`, `DELETE`, `TEMPORARY` |
| `state` | enum | `pending`, `terminal` |
| `action` / `survivor` | string / string|null | concrete result; survivor required for consolidation |
| `issue` / `owner` / `expires` | nullable | all required for temporary |
| `hic_approval` | string/null | required for temporary |
| `review` | object | implementer, independent reviewer, verdict, timestamp |

`FIX_*` is never terminal. `TEMPORARY` is one-time/non-renewable, maximum 30 days, and valid only for profile `environmental_platform`; inert, correctness, and timing candidates cannot use it.

## FrozenWorkloadDAG

| Field | Type | Rule |
|-------|------|------|
| `routes` | list[object] | stable ID, exact argv/selectors, environment ID, base/HEAD mapping |
| `edges` | list[object] | dependency `from` → `to`; acyclic |
| `repetitions` | integer | at least 3 |
| `measurements` | list[object] | collection/setup/call, wall, compute, outcome, artifact hash |

Summed compute is the sum of route measurements. Critical path is derived from the frozen dependency DAG; deleted/renamed routes remain mapped rather than disappearing.

## BootstrapLease

| Field | Type | Rule |
|-------|------|------|
| `state` | enum | `ABSENT`, `BUILDING`, `VALIDATED`, `PUBLISHED` |
| `owner_pid` / `process_start_token` | integer / string | distinguishes PID reuse |
| `heartbeat_at` / `lease_seconds` | timestamp / number | live-owner vs abandoned decision |
| `temp_path` | path | unique sibling on same filesystem |
| `source_version` / `environment_hash` | string | validation inputs |

Only the recorded live owner may transition `BUILDING → VALIDATED → PUBLISHED`. Publication validates the temp environment then renames it to an absent final path while state is locked. Recovery cleans only the recorded abandoned temp path.

## AggregateReport

Generated from global machine census, non-overlapping `evidence/dispositions/WP##.yaml` shards, raw artifact hashes, frozen workload DAG, issue matrix, and hard-gate results. It is never an independent hand-maintained evidence source.
