# Data Model: Classification Ledger

No new persisted runtime schema. The mission's spine is a **classification
ledger** over the ~60 bypass call sites, plus the gate's allow-list.

## Classification ledger (per bypass site)

| Field | Values | Meaning |
|-------|--------|---------|
| `file` | repo-rel path | the module |
| `symbol` | `candidate_feature_dir_for_mission` \| `resolve_planning_read_dir` | which primitive |
| `sites` | int | call-count in the file |
| `family` | `kind-blind` \| `kind-aware` | migration cost bucket |
| `verdict` | `migrate-fail-loud` \| `stay-lenient` \| `sanction-infra` | disposition |
| `kind` | `MissionArtifactKind` \| n/a | for kind-blind migrate sites: the declared artifact kind |
| `rationale` | text | required for `stay-lenient` and `sanction-infra` |

Verdict rules:
- **sanction-infra**: the read-primitive authority + resolution infra
  (`_read_path_resolver.py`, `surface_resolver.py`, `write_target_degrade.py`).
- **stay-lenient**: diagnostic/audit/corpus-walk readers that must tolerate
  half-materialized/deleted coord branches (doctor, dashboard, cutover audit,
  status aggregation). Recorded as allow-list entries with rationale.
- **migrate-fail-loud**: everything else — routed to `PlacementSeam.read_dir(kind)`.

## Read seam contract (target of migration)

`PlacementSeam.read_dir(kind: MissionArtifactKind) -> Path`
- `RETROSPECTIVE` → `resolve_retrospective_home`.
- else → `resolve_artifact_surface(repo_root, mission_slug, kind).path`.
- PRIMARY-partition kind → primary dir (all topologies).
- coord-partition kind, coord topology: `MATERIALIZED`→coord; `EMPTY`/`UNMATERIALIZED`→primary (sanctioned degrade); **`DELETED`→raises `CoordinationBranchDeleted`** (the fail-loud the lenient primitive lacks).
- CWD-invariant (derives from `repo_root` + stored `meta.json` topology).

## Migration equivalence (NFR-002)

For a healthy (materialized) mission, `read_dir(kind)` MUST resolve the identical
`Path` the bypassed primitive returned. The only intended difference is the
DELETED-coord case (silent primary → raise), which is exactly the fail-loud
hardening — and only for `migrate-fail-loud` sites.

## Gate allow-list entry (shrink-only)

Content-descriptor `(rel_path, qualname, token_substring)` resolved live via
`_ratchet_keys.resolve_descriptor` → `(rel_path, qualname, token_line)`. A
staleness twin-guard asserts each entry is still a live bypass; routing a site
forces its entry's deletion (shrink-only; never vacuous).
