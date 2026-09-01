---
work_package_id: WP02
title: Charter-freshness content-hash cache
dependencies: []
requirement_refs:
- C-005
- FR-002
- NFR-002
- NFR-004
planning_base_branch: perf/next-latency-durable-fix
merge_target_branch: perf/next-latency-durable-fix
branch_strategy: Planning artifacts for this mission were generated on perf/next-latency-durable-fix. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into perf/next-latency-durable-fix unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-next-latency-durable-fix-01M14RM3
base_commit: 30a985bda39d2f4c2de3bfa73be25838c370de48
created_at: '2026-08-28T20:59:37.277385+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
phase: Phase 1 - Implementation
history:
- timestamp: '2026-08-28T18:24:17Z'
  agent: system
  action: Prompt generated via tasks phase authoring
agent_profile: python-pedro
authoritative_surface: src/specify_cli/charter_runtime/freshness/
create_intent:
- src/specify_cli/charter_runtime/freshness/cache.py
- tests/charter_runtime/test_freshness_cache.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/charter_runtime/freshness/**
- tests/charter_runtime/test_freshness_cache.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match.

---

## Objective

Stop `spec-kitty next` from re-parsing the full (1588-line) `charter.yaml` on every invocation.
Cache the charter **freshness verdict** to a content-keyed sidecar and serve it on a hit,
skipping the ruamel parse. This is the ~0.5s real-project cold-start cost the squad measured.

**ELEVATED RISK — this caches a governance verdict.** Serving a stale *"fresh"* verdict is worse
than any stale projection. The cache MUST be content-keyed (never mtime), fail-closed on any
miss/error, and its key MUST fold in the synthesized-DRG graph file. This WP gets a mandatory
pre-merge adversarial review pass.

## Context

- Seam: keep the cache **inside** the freshness subsystem so callers are unchanged.
  `_run_charter_preflight_for_next` → `compute_freshness`
  (`src/specify_cli/charter_runtime/freshness/computer.py:793`, re-exported via `freshness/__init__.py`
  and reached from `charter_runtime/preflight/runner.py:172` too). Wrap `compute_freshness` (or add a
  cached entrypoint it delegates to) so the ruamel parse is skipped on a hit. **Do NOT edit
  `next_cmd.py`** — WP01 owns it; keep this change wholly within `charter_runtime/freshness/`. Both
  `_doctrine_graph_path` and `MANIFEST_PATH` already live in `computer.py` — you need **no** edit to
  `src/charter/bundle.py`.
- Key = `sha256(bundle_hash + ":" + graph_hash + ":" + manifest_hash)` over THREE inputs
  `_compute_synthesized_drg` (`computer.py:648-669`) reads:
  1. `compute_bundle_content_hash(repo_root)` (`src/charter/bundle.py`, existing; covers `charter.yaml`);
  2. the graph file (`graph.yaml`, via `_doctrine_graph_path`) — NOT in `BUNDLE_CONTENT_HASH_FILES`;
  3. `.kittify/charter/synthesis-manifest.yaml` (`MANIFEST_PATH`) — the verdict reads
     `manifest.built_in_only` (`:655`) and `manifest.bundle_content_hash` (`:761-767`).
  A `(charter, graph)`-only key serves a stale governance verdict when the manifest drifts (squad B1).
- Design of record: `data-model.md` (FreshnessCacheKey / FreshnessCacheEntry) and
  `contracts/freshness-cache-contract.md`. Follow them exactly.
- **Force `PYTHONPATH=src`** for measurement/tests.

## Subtasks

T006 Add `src/specify_cli/charter_runtime/freshness/cache.py`: compute the composite `FreshnessCacheKey` = `sha256(bundle_hash + ":" + graph_hash + ":" + manifest_hash)` over ALL THREE inputs per `data-model.md`; a `FreshnessCacheEntry` (schema_version, key, serialized verdict, written_at); read/write helpers to a per-repo gitignored runtime cache dir (match repo conventions — do NOT invent a new top-level dir). Content-only key; fail-closed (ANY of the three inputs missing/unreadable → treat as miss, never write a poisoned entry). (WP02)

T007 Wire the cache into the freshness computation inside `computer.py` (or a thin new cached entrypoint it delegates to): compute the key, look up; on a `key` match deserialize and return the verdict WITHOUT calling `_safe_load_yaml`/the parse; on miss/mismatch/error recompute via the existing path and persist the fresh entry. Keep `next_cmd.py` untouched. (WP02)

T008 Ensure the serialized/deserialized verdict is exactly the object `compute_freshness` returns (no semantic change) so `next` output is unaffected. Gitignore the cache dir. (WP02)

T009 Add `tests/charter_runtime/test_freshness_cache.py` implementing all SEVEN guarantees in `contracts/freshness-cache-contract.md`: hit-correctness (parse skipped — assert via a spy/patch on `_safe_load_yaml`), bundle-invalidation, **graph-invalidation** (mutate `graph.yaml` only → miss), **manifest-invalidation** (mutate `synthesis-manifest.yaml` only — flip `built_in_only` or change `bundle_content_hash` → miss; this is the B1 stale-"fresh" guard), fail-closed (ANY of the three inputs unreadable → recompute, no poisoned entry), content-only key (touch mtime only → still a hit), schema-version invalidation. Declare a `pytestmark` marker. This is the in-diff DoD. (WP02)

T010 Add a charter-path byte-identical assertion (NFR-004) within the same test file: freshly-computed vs cache-served verdict yields byte-identical `next --json` output except `timestamp`. Do NOT reuse the masked `canonical()` oracle. (WP02)

## Branch Strategy

Planning branch and final merge target: `perf/next-latency-durable-fix`. Execution worktree from
`lanes.json`; merge back into `perf/next-latency-durable-fix`.

## Definition of Done (observable in this diff)

- A profiled cache **hit** skips `_safe_load_yaml`/`compute_freshness`'s parse on a charter-bearing checkout.
- `test_freshness_cache.py` proves all seven contract guarantees, incl. **graph-invalidation**, **manifest-invalidation**, and fail-closed.
- Charter-path byte-identical `next` output (NFR-004).
- `next_cmd.py` is NOT modified by this WP. `ruff`/`mypy` clean. Cache dir gitignored.

## Risks / Reviewer guidance

- **The stale-"fresh" trap**: if the DRG graph file changes but the bundle doesn't, a bundle-only key would serve a stale governance verdict. The DRG-graph-invalidation test is the load-bearing proof — reviewer must confirm it actually mutates the graph file and observes a recompute.
- Fail-closed everywhere: a corrupt/partial sidecar must never be trusted.
- Reviewer (and the pre-merge adversarial squad): treat any path where a stale verdict could be served as a blocker, not a nit.
