# Authority-Seams Design — name-vs-authority remediation

**Profile:** architect-alphonso (read-only / design) · **Date:** 2026-06-12
**Repo:** spec-kitty · **Branch:** feat/doctrine-glossary-consolidation-01KTNWFC
**Inputs:** my own scan adjudication (`work/convention-enforcement-scan-2026-06-12.md` §"Architect adjudication"); C4 container doc (`architecture/diagrams/02_containers/runtime-execution-domain.md`); ADRs `2026-06-07-1` (canonical surface) + `2026-06-11-1` (Op artifact); operator decision 2026-06-11 (config-determined surfaces); the `doctor.py` porcelain exemplar (now at L3063, not 2957 — tree drifted); `branch_naming.py` canonical API; `test_safe_commit_import_boundary.py` ratchet template.

---

## 0. State-of-tree delta vs the scan (READ THIS FIRST — it re-scopes the slice)

The scan was taken on `upstream/main + 01KTNWFC`. On the current branch, mission **01KTG6P9 (canonical-surface, 12/12 approved) already landed two of my three "immediate fixes":**

| Scan-claimed defect | Current reality | Consequence |
|---|---|---|
| C — `surface_resolver.py:80` fabrication else `(slug.replace("-","")+"00000000")[:8]` | **ALREADY FIXED.** `_coord_mid8` (L66–100) now runs the `meta.mid8 → mission_id[:8] → mid8_from_slug` cascade and **raises `StatusReadPathNotFound`** on exhaustion. | C in surface_resolver is DONE. Do not re-spec it. |
| D — `workflow.py:781` `"canonical status not found" in str(exc).lower()` | **ALREADY FIXED.** workflow.py L796–804 is now `isinstance(exc, CanonicalStatusNotFoundError)`. | The single D site I folded in is DONE. Drop from slice. |

**But the C root cause is NOT eradicated** — the fabrication idiom `(mission_slug.replace("-","")+"00000000")[:8]` still lives in **two un-scanned sites** the original cluster missed:

| New C site | Line | Live behavior |
|---|---|---|
| `coordination/status_transition.py` | 265 | `_TransactionIdentity.effective_mid8` fabricates when `mission_id` short/absent — **drives the on-disk transaction dir name** (`_transaction_dir_name`). Lock/transaction mis-route, same class as Cluster A. |
| `cli/commands/implement.py` | 395 | `effective_mid8` fabricated in the same idiom — feeds coord-branch + identity resolution at implement time. |

So the slice's C work is **not** surface_resolver (done) but **these two transaction-identity sites** + the runtime_bridge pre-init fallback (below). This is the headline correction: the ratchet's `+"00000000"` assertion would have caught these two had it existed; they are the live regression surface.

`runtime/next/runtime_bridge.py:109` `_resolve_coordination_branch` still composes legacy `f"kitty/mission-{slug}"` on meta-absent (pre-init window) — C-cluster, but it is the *create→first-write* window the surface_resolver explicitly carves out, so it is **decision-table row "undeclared"**, not a fail-closed raise. Keep as-is; the decision table (§5) makes it explicit.

**Net re-scope:** Seam 1 (topology) unchanged — 5 A-sites + 2 G-writes. Seam 2 (branch identity) unchanged — 7 B-sites. Cluster C = the 2 transaction-identity fabrication sites (NOT surface_resolver, NOT workflow). The two ratchet tests are the durable closure.

---

## 1. Seam 1 — Topology Authority

### 1.1 Owner & rationale (C4-aligned)

Per the container doc, the Execution/Runtime module owns "status-surface resolution … fails closed" and the module that physically owns it is `coordination/surface_resolver.py` (home of `resolve_status_surface_with_anchor`). The new predicate is **co-located there** — same authority (git worktree registry + meta.json), same fail-closed posture, no new god-module. This is exactly my adjudication Q1 ("co-located with `resolve_status_surface_with_anchor`"). It must NOT merge with Seam 2: A's authority is the *git worktree registry* (process/filesystem I/O); B's is *declared meta.json identity + naming grammar* (pure strings). Combining couples git-process I/O to string grammar — rejected.

### 1.2 Seam API (signatures)

Add to `coordination/surface_resolver.py` (or a sibling `coordination/topology_authority.py` imported by it — see ratchet allowlist note §4):

```python
class WorktreeTopology(enum.Enum):
    """How a worktree path relates to a mission's commit destination."""
    PRIMARY = "primary"            # the main checkout's kitty-specs dir
    COORDINATION = "coordination"  # a registered <slug>-<mid8>-coord worktree
    LANE = "lane"                  # a registered lane worktree (NOT coord)
    UNREGISTERED = "unregistered"  # under .worktrees but absent from git registry (husk)

def is_registered_coord_worktree(path: Path, *, repo_root: Path | None = None) -> bool:
    """True iff *path* is inside a worktree that BOTH ends in ``-coord`` AND is
    registered in ``git worktree list --porcelain`` for *repo_root*.

    The ``-coord`` suffix only *proposes* coord topology; the porcelain registry
    *disposes*. A lane worktree, or a husk (suffix present, not registered),
    returns False — killing the split-brain where a lane path silently receives
    coord write-contract routing (#1589/#1821, F-005 husks).

    repo_root defaults to the resolved canonical root of *path* when omitted.
    Fails closed: if the registry cannot be read, raises rather than guessing.
    """

def classify_worktree_topology(path: Path, *, repo_root: Path | None = None) -> WorktreeTopology:
    """Full classification used by routing/dashboard consumers that need the
    PRIMARY/LANE distinction, not just the coord boolean. Single git-registry
    read, memoized per (repo_root, call) — never per-path shell-out."""
```

**Backstop mechanics (the `doctor.py:3063` template):** one `git -C <repo_root> worktree list --porcelain` call, parse the `worktree <abs-path>` records into a set, and test `str(path.resolve()) ∈ registry AND <name>.endswith("-coord")`. Memoize the registry read within a resolution pass (the doctor caches it "so we don't shell out per lane"); expose a `registry: frozenset[Path] | None = None` injection param for callers that already hold the porcelain output (status_service routes many contracts in one pass — it must pass the cached set, not re-shell per contract).

### 1.3 Per-site migration table (Cluster A + promoted G)

| # | Site | Current predicate | Migrates to | Shape of change |
|---|---|---|---|---|
| A1 | `coordination/status_service.py:54` `_is_coordination_worktree_path` | `".worktrees" in path.parts` | `is_registered_coord_worktree(path, registry=cached)` | Routes read/write **contract** (4 call sites L143/150/222/229). Thread one cached porcelain set through the contract-routing pass; replace the 4 uses. **Highest blast radius** — this is the write-contract router. |
| A2 | `status/aggregate.py:278` `MissionStatus._is_coord_dir` | `part == _WORKTREES_SEGMENT` | `is_registered_coord_worktree(read_dir, repo_root=self.repo_root)` | Drives `topology` classification field. `repo_root` is already on `MissionStatus`. |
| A3 | `dashboard/scanner.py:328` | `name.endswith("-coord")` + name-equality | `classify_worktree_topology(...) == COORDINATION` | Scanner already iterates `.worktrees`; it holds `worktree_dir` — pass `repo_root=project_dir`. Drop the brittle `feature_dir.name == name.removesuffix("-coord")` identity equality. |
| A4 | `workspace/root_resolver.py:72` | `candidate.name.endswith("-coord")` skip | `is_registered_coord_worktree(candidate, repo_root=...)` | Guards canonicalization skip. Keep the existing `WorkspaceRootNotFound`/non-git fallthrough (ad-hoc test dirs outside a repo must still return as-is). |
| A5 | `coordination/status_transition.py:114` `_is_coord_worktree_feature_dir` | `.parts` + ancestor `-coord` walk | `is_registered_coord_worktree(feature_dir, repo_root=...)` | Status-write routing. Collapses the two-clause ancestor walk into the one authority. |
| G1 | `status/emit.py:388` `_feature_status_lock_root` | `feature_dir.parent.name == KITTY_SPECS_DIR` → `.parent.parent` | Resolve lock root via `classify_worktree_topology` → canonical root | **PROMOTED from ACCEPT.** Mis-routing a status **lock** root is a concurrency defect of the A class. The resolver lands one cluster over; absorb it. Preserve the `repo_root is not None` early return. |
| G2 | `status/work_package_lifecycle.py:58` `_repo_root_for_lock` | identical idiom | identical migration to G1 | Same lock-root mis-route risk; same cheap absorption. |

**Out of scope (stays ACCEPT):** `status/store.py:122` `_find_mission_specs_root` — self-acknowledged best-effort **read** fallback; bounded by enforced layout; a read mis-route degrades gracefully, a write lock mis-route does not. File a low-prio note only.

### 1.4 Effort — Seam 1
**M.** One helper module/enum + one porcelain-cache plumbing decision (the injected `registry` param is the only non-mechanical design call). 5 A-swaps + 2 G-swaps = 7 call-site edits, each a 1–3 line substitution. Blast radius: status read/write routing, dashboard resolution, status lock acquisition.

---

## 2. Seam 2 — Branch-Identity Authority

### 2.1 Owner & rationale
**No new module.** `lanes/branch_naming.py` is already the canonical compose/decompose grammar and **already handles both eras** (`_LEGACY_*` + `_NEW_*` regexes; `parse_mission_slug_from_branch` returns `BranchParseResult(slug, mid8_token, lane_id)` with `mid8_token=None` flagging legacy). The 7 B-sites simply don't call it — they hand-roll a regex or compose an f-string. The fix is routing, fed `mission_id` from `meta.json`.

### 2.2 Seam API (already exists — enumerated for migrators)

```python
mission_branch_name(mission_slug, *, mission_id: str | None = None) -> str
lane_branch_name(mission_slug, lane_id, planning_base_branch=None, *, mission_id=None) -> str
parse_mission_slug_from_branch(branch_name) -> BranchParseResult | None   # dual-era
parse_lane_id_from_branch(branch_name) -> str | None                      # dual-era
is_lane_branch(branch) -> bool ; is_mission_branch(branch) -> bool ; is_legacy_branch(branch) -> bool
mid8(mission_id) -> str            # raises ValueError if < 8 chars
mid8_from_slug(slug) -> str        # "" when no mid8 tail (contract: caller backstops with meta)
```

The only **new** helper the slice should add (thin, in `branch_naming.py`) to make compose-sites fail-closed:

```python
def mission_branch_name_required(mission_slug: str, mission_id: str | None) -> str:
    """Compose the canonical mission branch, fail-closed.
    Raises BranchIdentityUnresolved when mission_id is absent AND the slug
    carries no mid8 tail — i.e. the mid8 disambiguator is genuinely lost and a
    legacy f-string would be wrong-but-plausible. Legacy slugs (NNN- prefix,
    no mission_id, by design pre-083) resolve to the legacy form without raising."""
```

### 2.3 Dual-era handling rule (DECISION)

**Decision: both eras RESOLVE; only the *unresolvable* case is rejected.** Concretely:

- **Decompose (parsers B1/B2/B3):** route through `parse_mission_slug_from_branch` / `parse_lane_id_from_branch`. Both already accept legacy `\d{3}-` AND mid8-era names. A name matching *neither* grammar yields `None` — callers must treat `None` as a structured skip/error, **never** a silent empty slug. (Today B1's bespoke regex returns the legacy match or falls through to "no workspace"; B3 returns `None` for *all* mid8 missions — a silent signal loss on every modern mission. Routing through the canonical parser fixes both.)
- **Compose (B4/B5/B6/B7):** route through `mission_branch_name(slug, mission_id=…)` / `lane_branch_name(…, mission_id=…)` with `mission_id` read from meta. When `mission_id` is present → mid8-era name. When absent **and** the slug is a legacy `\d{3}-` slug → legacy form is correct (these missions never had a mid8). When absent **and** the slug is post-083 (no NNN- prefix, no mid8 tail) → the disambiguator is lost; **fail closed** via `mission_branch_name_required` raising `BranchIdentityUnresolved` rather than emitting `kitty/mission-<slug>` that does not exist on disk.
- **Rationale for "resolve both, reject only unresolvable":** rejecting legacy outright would break FR-052 (pre-WP02 worktrees must keep working) and the `branch_naming` module's own stated contract ("both forms accepted at read time"). Fabricating mid8-era names for legacy missions would invent branches that never existed. The single genuinely-wrong case — modern mission, mid8 lost — is the only one that earns a structured error.

### 2.4 Per-site migration table (Cluster B)

| # | Site | Current shape | Migrates to | mission_id source | Note |
|---|---|---|---|---|---|
| B1 | `cli/commands/sync.py:823` | `re.match(r"^kitty/mission-(\d{3}-…)-lane-…$")` (decompose) | `parse_mission_slug_from_branch(branch)` → use `.slug` (+ `.lane_id`) | n/a (read) | Legacy-only regex; misses every mid8 mission → wrong/empty slug. Canonical parser is dual-era. |
| B2 | `manifest.py:156` | `split("/")[-1]` + `branch[0].isdigit()` (decompose) | `parse_mission_slug_from_branch` / `is_mission_branch` filter | n/a (read) | `isdigit()` prefix test excludes all mid8 branches from discovery. |
| B3 | `core/vcs/detection.py:155` | `re.match(r"(\d{3})-", worktree_name)` (decompose) | `parse_mission_slug_from_branch` on the branch, or `mid8_from_slug(worktree_name)` for the dir-name form | n/a (read) | Returns `None` for all mid8 missions today — silent signal loss. Worktree *dir* names use `<slug>-<mid8>`; decompose with `mid8_from_slug` + slug remainder, not a `\d{3}` regex. |
| B4 | `cli/commands/merge.py:1114` | `f"kitty/mission-{mission_slug}"` (compose) | `mission_branch_name_required(slug, mission_id)` | meta.json (merge already loads mission meta) | False "missing branch" on every mid8 mission. |
| B5 | `lanes/compute.py:348,538,672` | `mission_branch=f"kitty/mission-{slug}"` (compose) | `mission_branch_name(slug, mission_id=resolved_mission_id)` | **already in scope** (`resolved_mission_id`/`mission_id` local at each site) | Writes the manifest `mission_branch` — wrong value persists into lanes.json. Lowest-risk fix (id already present). |
| B6 | `lanes/recovery.py:321,570` | fallback `f"kitty/mission-{slug}"` when `_find_mission_branch` empty (compose) | `mission_branch_name_required(slug, mission_id)` read from feature_dir meta | meta.json at `feature_dir` | The empty-`_find_mission_branch` fallback is the live wrong-compose path. |
| B7 | `merge/preflight.py:86` | `mission_branch or f"kitty/mission-{slug}"` → suggested `git switch -c` target (compose) | `mission_branch or mission_branch_name_required(slug, mission_id)` | meta.json (preflight has repo_root + slug) | This is an **actionable operator instruction** — a wrong branch here tells the operator to branch off a nonexistent ref. Highest user-visible harm of the B set. |

Note: `status/aggregate.py:669` and `runtime_bridge.py:109` also compose `f"kitty/mission-{slug}"`. aggregate.py:669 is `coordination_branch or f"…"` — **fold into B** (route the fallback through `mission_branch_name`). runtime_bridge.py:109 is the pre-init window → **decision-table "undeclared" row** (§5), left as legacy fallback by design.

### 2.5 Effort — Seam 2
**M.** Add one thin fail-closed helper (`mission_branch_name_required` + `BranchIdentityUnresolved`). 7 sites (+aggregate.py:669) routed through existing API; the only per-site work is threading `mission_id` from meta (B4/B6/B7) — B5 already has it. Blast radius: sync selector, manifest discovery, VCS detection, merge preflight (operator-facing), lanes.json manifest content.

---

## 3. Cluster C — fail-closed transaction identity (the real residual)

| Site | Migration |
|---|---|
| `coordination/status_transition.py:265` | Replace the `(mission_slug.replace("-","")+"00000000")[:8]` else with: if `mission_id` short/absent → `raise BranchIdentityUnresolved` (or reuse `StatusReadPathNotFound` if the surrounding contract expects it). The `mission_id[:8]` and `meta.mid8` branches stay. |
| `cli/commands/implement.py:395` | Same: delete the fabrication else; fail closed on exhausted cascade. `mid8` and `mission_id[:8]` branches preserved. |
| `runtime/next/runtime_bridge.py:109` | **Keep** legacy `f"kitty/mission-{slug}"` — this is the meta-absent pre-init window (decision-table "undeclared"); fail-closing here would break mission create. Document it as the carved-out window. |

Effort **S** (delete two else-branches, add one exception). These two sites are the live `+"00000000"` regressions the ratchet (§4.3) makes impossible to reintroduce.

---

## 4. Ratchet — `tests/architectural/test_topology_resolution_boundary.py`

Mirrors `test_safe_commit_import_boundary.py` exactly: `pytestmark = pytest.mark.architectural`; `_REPO_ROOT = parents[2]`; `_SRC_ROOT = _REPO_ROOT/"src"`; `_iter_src_python_files()`; `_rel()`; AST + textual scans; allowlist as `frozenset[str]` of repo-relative posix paths with rationale comments.

### 4.1 Assertion 1 — topology predicate allowlist (mirrors "exactly the blessed importers")

```python
_COORD_PREDICATE_SUBSTRS = ('".worktrees" in', "endswith(\"-coord\")", 'part == _WORKTREES_SEGMENT',
                            "_WORKTREES_DIR_NAME in", "_WORKTREES_SEGMENT for part in")
_BLESSED_TOPOLOGY_MODULES = frozenset({
    "src/specify_cli/coordination/surface_resolver.py",     # owns is_registered_coord_worktree
    "src/specify_cli/coordination/topology_authority.py",   # IF split into a sibling
    # surface_resolver legitimately uses `part == _WORKTREES_SEGMENT` for the
    # #1772 already-resolved-coord short-circuit — that read is the authority's own.
})
```
`test_coord_path_predicate_only_in_blessed_modules`: scan every `src/` file (AST `Attribute`/`Compare` walk OR textual fallback) for any `_COORD_PREDICATE_SUBSTRS` occurrence; `actual - blessed` must be empty. Assert message: "infer coord-ness from a registered-worktree check (`is_registered_coord_worktree`), not from path shape." Also assert `blessed - actual` is empty (no stale allowlist entry) — matching the safe_commit test's bidirectional check. **Migrated A1–A5 sites drop out of `actual` once they delegate.**

### 4.2 Assertion 2 — unbackstopped `kitty/mission-{slug}` compose scan (mirrors `destination_ref=` AST call-site scan)

AST scan for `JoinedStr` (f-string) nodes whose constant text contains `kitty/mission-` AND interpolates a `{mission_slug}`/`{slug}`/`{self.mission_slug}` `FormattedValue` but **not** a `{mid8}`/`{mid8_from_slug...}`/`{mission_id...}` value — i.e. a legacy-shape compose. The site passes only if it is in the allowlist:

```python
_ALLOWLISTED_LEGACY_COMPOSE_SITES = frozenset({
    "src/runtime/next/runtime_bridge.py",      # pre-init window (decision-table "undeclared")
    "src/specify_cli/missions/_create.py",     # mission-create composes the legacy human-part by design
    # branch_naming.py itself defines the grammar (the f-strings ARE the canonical form)
    "src/specify_cli/lanes/branch_naming.py",
    "src/specify_cli/lanes/models.py",         # docstring only — exclude via "is in a docstring" guard or allowlist
})
```
`actual - allowlist` empty. Assert message points at `mission_branch_name(slug, mission_id=…)`. The migrated B4–B7 + compute + recovery + aggregate sites drop out. (Guard against docstring false-positives by skipping `ast.Expr`-wrapped `Constant` strings, as models.py:122 is prose.)

### 4.3 Assertion 3 — zero fabricated-mid8 idiom (mirrors `_DELETED_CHANNEL_SYMBOLS` zero-reference test)

```python
_FABRICATION_IDIOMS = ('+ "00000000")[:8]', '+"00000000")[:8]', 'replace("-", "") + "00000000"')
```
`test_fabricated_mid8_idiom_has_zero_references`: textual scan of all `src/` files; **zero** offenders. Excludes the UUID-zero literals in `sync/diagnose.py:252` / `sync/emitter.py:2045` (those are `00000000-0000-…` project_uuid placeholders, a different shape — the idiom strings above don't match them, so no allowlist needed). Catches `status_transition.py:265` + `implement.py:395` today and any future regrowth.

**Why these three and not more:** they are the three *decision points* of the seam (topology proposal vs. registry; legacy compose vs. canonical; fabrication vs. fail-closed). Each mirrors a proven assertion in the safe_commit ratchet. mid8-caller-must-backstop-with-meta is *implied* by 4.2+4.3 together (a compose either threads mission_id or is fail-closed); a separate "every `mid8_from_slug` caller reads meta" scan would over-fire on the legitimate `branch_naming` internals, so it is intentionally omitted.

---

## 5. #1889 decision table — declared-but-not-materialized coord topology

**Problem (#1889):** `meta.json` declares `coordination_branch`, but the coord worktree may be absent, or its branch deleted (#1848 carve-out). Every consumer (status read, status write, dashboard, lock root, branch compose) must derive ONE answer. The container doc routing-invariant #4 is the governing rule: *"a materialized coord root lacking the mission dir fails closed rather than falling back to a primary surface."* The table below extends that single rule across the four observable states.

| State | coord_branch in meta | coord worktree materialized | coord branch exists in git | **Decision** | Authority / rationale |
|---|---|---|---|---|---|
| **R1 declared+materialized** | yes | yes (mission dir present) | yes | **COORDINATION.** Surface = `<coord>/kitty-specs/<dir>/status.events.jsonl`. `is_registered_coord_worktree` → True. | Normal happy path. surface_resolver short-circuit L164–170. |
| **R2 declared+branch-exists-no-worktree** | yes | no | yes | **Compose-once coord path, return as-is** (create→first-write window). Primary anchor stays primary. **No raise.** | surface_resolver L213–220: "Coord branch declared but worktree not materialized yet: compose by hand once." The aggregate's not-yet-materialized gate keeps the primary checkout authoritative one level up. Branch compose → `mission_branch_name_required` succeeds (mission_id present). |
| **R2′ declared+materialized-root-but-no-mission-dir** | yes | root exists, mission dir absent | yes | **FAIL CLOSED — `StatusReadPathNotFound`.** Never fall back to primary. | surface_resolver L227–234 (the live FR-005 guard). This is the #1589/#1821 split-brain class. |
| **R3 declared+branch-deleted** (#1848 carve-out) | yes | no | **no** | **FAIL CLOSED with a distinct, actionable error** (`CoordinationBranchDeleted` / `StatusReadPathNotFound` carrying a "branch deleted" reason) → next_step: `spec-kitty agent worktree repair` / flatten via removing `coordination_branch` (the MEMORY "flatten when coord worktree missing" recovery). **Do NOT silently fall back to primary** — a deleted coord branch with unmerged status is data loss, not a degraded read. | #1848 is an explicit carve-out: branch deletion is an *exceptional* state, surfaced loudly, not absorbed. Mirrors doctor's `COORDINATION_WORKTREE_MISSING` finding but at the resolution seam so every consumer inherits it. |
| **R4 undeclared** | no | n/a | n/a | **PRIMARY.** Surface = primary checkout; branch compose = legacy/`mission_branch_name` per era. | surface_resolver L207–211. runtime_bridge.py:109 pre-init fallback lives here (meta absent ⊂ undeclared). |

**Single-answer guarantee:** every consumer routes through `resolve_status_surface_with_anchor` (read) or `is_registered_coord_worktree` (routing) — both implement this table once. No consumer re-derives. R2 vs R2′ is the subtle split the surface_resolver already encodes; R3 is the **new** row this slice must add (today R3 collapses into R2/R2′ and can silently mis-resolve when the branch is gone). The implementation cost of R3 is one `git rev-parse --verify <coord_branch>` (or a registry-absence check) inside `_coord_mid8`/the materialization guard, raising the distinct error.

---

## 6. Work-package candidates & effort

| WP | Scope | Effort | Depends on |
|---|---|---|---|
| **WP-A** Topology authority | Add `WorktreeTopology` + `is_registered_coord_worktree` + `classify_worktree_topology` (porcelain xref, injected-registry param) in surface_resolver/sibling; migrate A1–A5 + G1–G2 (7 sites); add the cached-registry plumbing through status_service. | **M** | none (owns the new helper) |
| **WP-B** Branch-identity routing | Add `mission_branch_name_required` + `BranchIdentityUnresolved`; migrate B1–B7 + aggregate.py:669 (8 sites); thread mission_id from meta at B4/B6/B7. | **M** | none (uses existing branch_naming) |
| **WP-C** Fail-closed transaction identity | Delete fabrication else at status_transition.py:265 + implement.py:395; raise on exhausted cascade; document runtime_bridge.py:109 carve-out. | **S** | WP-B (shares `BranchIdentityUnresolved`) |
| **WP-R3** #1889/#1848 deleted-branch row | Add R3 detection (`git rev-parse --verify` the coord branch) + distinct `CoordinationBranchDeleted` error + next_step; wire into surface_resolver materialization guard. | **S–M** | WP-A (shares topology read) |
| **WP-RATCHET** Two ratchet tests | `test_topology_resolution_boundary.py` with the 3 assertions §4. Lands LAST so the migrated sites are already out of `actual`. | **S** | WP-A, WP-B, WP-C |

**Sequencing (adjudication Q3):** independent of and precedes #1802 (draft) and #1804/Op-ADR. Land on the `feat/execution-state-strangler` lineage. WP-A ∥ WP-B (different authorities, no shared files); WP-C after WP-B; WP-R3 after WP-A; WP-RATCHET last. Total ≈ M+M+S+S/M+S → one cohesive slice, ~2–3 WPs if A/RATCHET and B/C are paired.

**Tickets to file (out of slice):** Cluster D residual (worktree.py:332 marker tuple → exception hierarchy; mission_loader/validator "has no steps" → `error_code`; dashboard `PortUnavailableError`); Cluster E (Lane/DecisionKind/mission-type literal→enum sweep; promote `DecisionKind` to Enum); Cluster F (#1831 temp-path slug threading). Accepted debt: store.py:122 read fallback.

---

## 7. Alignment self-check

- **C4 ownership:** topology in `coordination/surface_resolver.py` (the container's named status-surface owner); branch identity in `lanes/branch_naming.py` (the named grammar). ✓
- **ADR 2026-06-07-1 / container invariants:** mid8 derived exactly once (WP-C kills the second derivation); raises rather than silent fallback (WP-A/C/R3); config-determined surfaces — meta.json is the authority, never path shape (operator 2026-06-11). ✓
- **Fail-closed over fallback:** R2′, R3, WP-C, `mission_branch_name_required` all raise structured errors. The only retained fallbacks are the *documented* create→first-write window (R2, R4/runtime_bridge) — carved out explicitly, ratchet-allowlisted. ✓
- **No new god-module / no A+B merge:** two named surfaces, different authorities, no coupling of git I/O to string grammar. ✓
