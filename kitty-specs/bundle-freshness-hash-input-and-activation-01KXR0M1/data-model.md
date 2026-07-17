# Data Model — Content-Identity Recipe

Contract for `compute_bundle_content_hash(repo_root: Path) -> str | None` after this mission.

## Inputs

| Input | Source | Notes |
|-------|--------|-------|
| `governance.yaml` digest | `.kittify/charter/governance.yaml` | per-file `hash_content`; unchanged |
| `directives.yaml` digest | `.kittify/charter/directives.yaml` | per-file `hash_content`; unchanged |
| `metadata.yaml` digest | `.kittify/charter/metadata.yaml` | per-file `hash_content`; unchanged |
| **directive-activation digest** *(new)* | shared helper `resolve_synthesis_graph_directives(repo_root)` | `hash_content("directives=" + ",".join(sorted(ids)))` |
| ~~`references.yaml` digest~~ | — | **REMOVED** (#2758) |

`BUNDLE_CONTENT_HASH_FILES = ("governance.yaml", "directives.yaml", "metadata.yaml")` (was 4).

## `resolve_synthesis_graph_directives(repo_root) -> list[str]`

The single authority (extracted from `_synthesis.py:76-79`, called by BOTH the synthesizer and the hash):

```
pack_context = PackContext.from_config(repo_root)
config_roots = resolve_config_activated_roots(repo_root=repo_root)   # compiler.py:212 (bare canonical ids)
return [] if pack_context.activated_directives is None else config_roots.directives   # #2577 absent→[]
```

Digest: `hash_content("directives=" + ",".join(sorted(ids)))` (sorted → order-independent). Paradigms are
**not** included (inert for `graph.yaml`).

## Combine

`hash_content("\n".join([gov_digest, dir_digest, meta_digest, directive_digest]))` → `"sha256:<hex>"`.

## Fail-posture (OQ-4) — never-raise

| Condition | Result | Recoverable? |
|-----------|--------|--------------|
| triad file missing/unreadable | `None` → `stale` | yes (`synced_bundle` gate; `charter sync`) |
| `config.yaml` malformed / non-mapping (`CharterPackConfigError`) | caught → `None` → `stale` | yes: `synthesize` surfaces actionable config error → fix → synthesize |
| **drifted activated *directive* stem** (activated_directives present) → resolver raises `UnknownArtifactIdError` (`ValueError`) | **caught → `None` → `stale`** (must NOT crash) | yes: `synthesize` surfaces the resolution error → fix → synthesize |
| absent `activated_directives` + a drifted *other-kind* stem | short-circuits to `[]` **before** resolving → real hash (not `None`) | n/a — unreachable via normal promotion (which always writes `activated_directives`, even `[]`); a non-directive drift does not change `graph.yaml`, and `synthesize` on such a hand-edited config would itself fail on the drift |
| `activated_directives` absent | resolves to `[]` (mirrors the graph, #2577) — NOT `None` | n/a, stable |
| `references.yaml` missing | **no effect** (removed) | — (#2758 closed) |

`compute_bundle_content_hash` catches `(UnknownArtifactIdError, CharterPackConfigError, ValueError, OSError,
UnicodeDecodeError)` around the resolver read → `None`. Never raises.

## Behavior + remediation matrix (acceptance anchors)

| Scenario | Pre-fix | Post-fix | remediation (post-fix) |
|----------|---------|----------|------------------------|
| non-`built_in_only` graph, `references.yaml` absent | permanent `stale` | not stale on that account (SC-001) | `None` |
| activate a **directive** changing the resolved set | `fresh` (false) | `stale` (SC-002) | `spec-kitty charter synthesize` |
| deactivate an active directive | `fresh` (false) | `stale` | `spec-kitty charter synthesize` |
| activate a **paradigm** or **tactic** (non-graph-varying) | `fresh` | `fresh` — CORRECT (NOT false-fresh) | `None` |
| no-op for the resolved directive set (re-activate resolved id / validation fail / deactivate no-op) | `fresh` | `fresh` (SC-003) | `None` |
| directive activate, then `charter synthesize` | — | `fresh` (FR-006) | `None` |
| **drifted activated stem** (config drift) | (crash risk under naive re-base) | recoverable `stale`, `charter status` does NOT crash (NFR-003) | `spec-kitty charter synthesize` (after fixing the stem) |
| **legacy-`None`** (pre-#2732, schema-"2", `bundle_content_hash=None`) | `stale` | `stale` → `fresh` after generate→synthesize (FR-003, distinct anchor) | `spec-kitty charter synthesize` |
| **#2732-era** (schema-"3", real 4-file hash) mismatching new recipe | — | one-time `stale` → `fresh` after 1 synthesize (FR-007) | `spec-kitty charter synthesize` |

FR-003 (schema-"2" `None`) and FR-007 (schema-"3" recipe mismatch) are **distinct** starting states with
distinct anchors. Tests derive directive ids from the resolver / monkeypatch the seam — never hardcode
`default.yaml` content.

## Propagation & performance

Consumers of the recipe: reader `_compute_synthesized_drg` (computer.py:426), `promote()`
(write_pipeline.py:685), `resynthesize` (resynthesize_pipeline.py:205). `project_drg.py:311` **preserves**
via `model_copy` (does not recompute — correct; only on the `built_in_only` toggle, which the reader
short-circuits before the hash compare). IC-03 proves the bake. The `bundle→compiler` import is
**function-local** (NFR-001); the per-`charter status` `load_doctrine_catalog()` cost is bounded by the < 2s
envelope test reaching the graph-hash branch (NFR-002).

## Non-touch (C-003)

`computer._BUNDLE_FILES` (computer.py:137) drives the **separate** `synced_bundle` signal — NOT edited.
