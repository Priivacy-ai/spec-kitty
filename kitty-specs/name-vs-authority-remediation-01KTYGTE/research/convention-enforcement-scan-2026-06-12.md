# Convention-Enforcement Scan — Root-Cause Reduction

**Op:** 01KTY6AN · **Profile:** randy-reducer · **Date:** 2026-06-12
**Repo:** spec-kitty (upstream/main + mission 01KTNWFC) · **Inputs:** 5 bounded scans (worktree-paths, branch-names, file-names, string-signals, tmp-paths)

Reduces ~44 CONVENTION-ONLY findings to **7 root-cause clusters**. Each finding spot-verified at file:line before inclusion; backstopped/display rows dropped. The defect class is identical everywhere: **a name/string shape is treated as declared authority with no cross-check against the real authority (meta.json topology, `git worktree list`, the `Lane` enum, structured `error_code` fields, or `resolve_*` resolvers).**

---

## Cluster Ranking (risk × frequency)

| Rank | Cluster | Sites | Risk | Disposition |
|------|---------|-------|------|-------------|
| 1 | A — "is coord?" from path shape | 5 | CRITICAL (split-brain) | **NEXT-SLICE** |
| 2 | B — legacy-shape-only parsers blind to mid8 | 7 | HIGH (silent signal loss on all modern missions) | **NEXT-SLICE** |
| 3 | C — fabricated / empty mid8 fallback | 4 | HIGH (wrong-but-plausible routing) | **NEXT-SLICE** |
| 4 | D — error-substring control flow | 4 | MEDIUM (latent on message reword) | **TICKET-ONLY** |
| 5 | E — raw lane / mission-type / decision-kind literals | 6 | MEDIUM (enum-bypass, rename-fragile) | **TICKET-ONLY** |
| 6 | F — /tmp identity naming (WP-only) | 3 | MEDIUM (cross-mission collision #1831) | **TICKET-ONLY** |
| 7 | G — `parent.name == KITTY_SPECS_DIR` write discriminator | 3 | LOW–MEDIUM (lock mis-route) | **ACCEPT** (documented debt) |

---

## Cluster A — "is coord?" inferred from path shape  ·  NEXT-SLICE

**Root cause:** Five predicates classify a worktree as *coordination* purely from `".worktrees" in path.parts`, with no `-coord` suffix check and no git/meta verification. A **lane** worktree path silently receives coord-topology treatment → write-contract / topology mis-routing.

| Site | Predicate |
|------|-----------|
| `coordination/status_service.py:54-56` | `_is_coordination_worktree_path` — `".worktrees" in path.parts` (routes write contract) |
| `status/aggregate.py:278-280` | `MissionStatus._is_coord_dir` — `part == _WORKTREES_SEGMENT` (drives `topology` classification) |
| `dashboard/scanner.py:328-332` | `name.endswith("-coord")` + `feature_dir.name == name.removesuffix("-coord")` identity equality (PR #1859 / F-005 exemplar) |
| `workspace/root_resolver.py:72` | `name.endswith("-coord")` skips canonicalization (routing) |
| `coordination/status_transition.py:114-125` | `_is_coord_worktree_feature_dir` — `ancestor.name.endswith("-coord")` for status write routing |

**Declared authority:** `git worktree list --porcelain` registry + `meta.json` coordination-branch topology, exactly as `doctor.py:2957` already does (cross-checks lane dir against the porcelain list). The `-coord` suffix may *propose* a surface; the registry must *confirm* it.
**Effort:** M (one shared `is_registered_coord_worktree(path)` helper + 5 call-site swaps). **Blast radius:** status read/write routing, dashboard resolution.
**Would have prevented:** F-005 husks, #1589 / #1821 split-brain.

---

## Cluster B — legacy-shape-only parsers blind to mid8-era names  ·  NEXT-SLICE

**Root cause:** Parsers/composers hard-code the pre-083 `NNN-slug` shape. Modern `<slug>-<mid8>[-lane-<id>]` names produce **no match → silent `None`/skip** (decompose) or a **legacy-form name that does not exist** (compose). No `meta.json` backstop.

| Site | Shape assumed |
|------|----------------|
| `cli/commands/sync.py:823` | `re.match(r"^kitty/mission-(\d{3}-[a-zA-Z0-9-]+)-lane-[a-z]+$")` → returns wrong/empty slug (decompose) |
| `manifest.py:156-158` | `line.split("/")[-1]` + `branch[0].isdigit()` — numeric-prefix only (decompose) |
| `core/vcs/detection.py:155` | `re.match(r"(\d{3})-", worktree_name)` → `None` for all mid8 missions (decompose) |
| `cli/commands/merge.py:1116-1118` | builds `f"kitty/mission-{slug}"` (no mid8) → false "missing branch" (compose) |
| `lanes/compute.py:348,538,672` | `mission_branch=f"kitty/mission-{slug}"` (no mid8) though `mission_id` is in scope (compose) |
| `lanes/recovery.py:321-322,570-571` | fallback `f"kitty/mission-{slug}"` when `_find_mission_branch` empty (compose) |
| `merge/preflight.py:86` | `mission_branch or f"kitty/mission-{slug}"` — suggested as actionable `git switch -c` target (compose) |

**Declared authority:** canonical `lanes/branch_naming.py` API — `mission_branch_name(slug, mission_id, …)` for compose, `parse_mission_slug_from_branch` / `is_lane_branch` for decompose — fed `mission_id`/`mid8` from `meta.json`. The canonical regex set already handles both shapes; these sites simply don't call it.
**Effort:** M (route every site through `branch_naming` + thread `mission_id`). **Blast radius:** sync selector, manifest discovery, VCS detection, merge preflight.
**Would have prevented:** mid8='' regression, #1860 handle-as-path, fulle2e0-class selector misses.

---

## Cluster C — fabricated / empty-mid8 fallback signal loss  ·  NEXT-SLICE

**Root cause:** When `mid8_from_slug()` returns `""`, surfaces either fabricate a plausible-but-wrong mid8 or compose a legacy branch silently — no exception, no warning. The disambiguator is lost exactly when it matters.

| Site | Behavior |
|------|----------|
| `coordination/surface_resolver.py:80` | `(slug.replace("-","")+"00000000")[:8]` — fabricated mid8; comment "F-001: never compose a wrong-but-plausible coord path" yet the fabrication is the live else-branch |
| `lanes/recovery.py:321,570` | legacy-form branch composed on empty mid8 (also Cluster B) |
| `lanes/compute.py:348,538,672` | manifest `mission_branch` lacks mid8 (also Cluster B) |
| `runtime/next/runtime_bridge.py:104-108` | `_resolve_coordination_branch` legacy fallback when meta absent (pre-init window) |

**Declared authority:** `meta.json` `mission_id`/`mid8` are mandatory post-083. When the cascade exhausts declared sources, **fail closed (raise)** — never fabricate. `surface_resolver._coord_mid8` lines 68-77 already implement the correct cascade; only the final `return` must become a raise.
**Effort:** S (delete fabrication branch, raise structured error; recovery/compute overlap with B). **Blast radius:** coord-path resolution, recovery context, decision-log commit target.
**Would have prevented:** mid8='' regression, F-005 husk routing.

---

## Cluster D — error-substring control flow vs structured error_codes  ·  TICKET-ONLY

**Root cause:** Branch decisions made by `substring in str(exc)` even when a typed exception (or a structured `error_code` field) exists. A message reword silently flips the branch.

| Site | Substring | Typed alternative |
|------|-----------|-------------------|
| `cli/commands/agent/workflow.py:781` | `"canonical status not found" in str(exc).lower()` (used L1122, L2029) | `isinstance(exc, CanonicalStatusNotFoundError)` — class already exists |
| `core/worktree.py:332-337` | 3 preflight-marker substrings vs `str(e)` | structured preflight exception hierarchy |
| `mission_loader/validator.py:166,419` | `"has no steps" in str(exc)` | `error_code` on `MissionRuntimeError` (none today) |
| `dashboard/lifecycle.py:431` | `"Could not find free port" in str(e)` | typed `PortUnavailableError` |

**Declared authority:** structured `error_code` fields / `isinstance` checks — the BACKSTOPPED pattern already used in `coordination/transaction.py:731` (`caller_verdict.error_code == "PROTECTED_BRANCH_REFUSED"`).
**Effort:** S–M per site (workflow.py:781 is trivial — class exists). **Blast radius:** implement/review hard-fail path, worktree fallback. Independent, fixable standalone.

---

## Cluster E — raw lane / mission-type / decision-kind literals  ·  TICKET-ONLY

**Root cause:** Existing enums/constants are bypassed by inline string literals; the same file often mixes both forms — rename-fragile and type-unchecked.

| Site | Literal | Canonical |
|------|---------|-----------|
| `status/emit.py:528-530` | `from_lane == "in_progress"` / `"for_review"` (batch path uses `Lane.IN_PROGRESS`/`Lane.FOR_REVIEW`) | `Lane` enum |
| `status/lifecycle_events.py:781` | `from_lane == "genesis"` | `Lane.GENESIS` |
| `status/aggregate.py:607` | `str(from_lane_enum) == "uninitialized"` (stringify-then-compare smell) | `Lane` member |
| `retrospective/generator.py:415` + `migration/rebuild_state.py:338,345` | raw `"planned"/"claimed"/…` | `Lane` enum |
| `…/workflow.py`,`tasks.py`,`mission.py` + `runtime_bridge.py:2043` | `mission_type == "research"/"software-dev"/…` | shared `_BUILTIN_MISSION_TYPES` constant (defined once in migration, not imported) |
| `runtime_bridge.py` (1810,2832,3029-31,…) + `_internal_runtime/engine.py` | `decision.kind == "terminal"/"blocked"/…` (mixes `DecisionKind.x` and inline) | `DecisionKind` (promote to `Enum`; `Decision.kind: str` → typed) |

**Declared authority:** `Lane` enum, `DecisionKind`, a shared mission-type constant. **Effort:** S–M (mechanical swaps; promote `DecisionKind` to enum is the only design step). **Blast radius:** wide but low-severity; type-checker would then catch regressions. Glossary event-type literals (string-scan #11) fold in as the same anti-pattern.

---

## Cluster F — /tmp identity naming (WP-only, no mission scope)  ·  TICKET-ONLY

**Root cause:** Temp prompt files keyed on `wp_id` alone; `mission_slug` in scope but unused → cross-mission `WP01` collision.

| Site | Name |
|------|------|
| `cli/commands/agent/workflow.py:613` | `spec-kitty-{command_type}-{wp_id}.md` (#1831 exemplar; call sites L1440, L1670) |
| `doctrine/skills/spec-kitty-implement-review/SKILL.md:367-380` | `/tmp/review-prompt-WP##.md` (doc-layer; propagates to 13 agent dirs + 4 skill copies on upgrade) |
| same SKILL.md:374 | `/tmp/review-result-WP##.md` |

**Declared authority:** the backstopped `review/prompt_metadata.py` scheme (`<repo-hash>/<slug>/<wp>/<uuid>.md`) — collision-impossible. The SKILL.md already exposes the correct `$REVIEW_PROMPT` variable two lines away; the inline `/tmp/...WP##` paths are a regression against the file's own better pattern.
**Effort:** S (thread `mission_slug` into `_write_prompt_to_file`; point SKILL.md at `$REVIEW_PROMPT`, re-upgrade). **Blast radius:** concurrent-mission prompt isolation.
**Would have prevented:** #1831.

---

## Cluster G — `parent.name == KITTY_SPECS_DIR` write-path discriminator  ·  ACCEPT

**Root cause:** Three sites use the parent dir name as the *sole* topology discriminator (no structural validation) to pick lock-root / lifecycle handling.

| Site | Use |
|------|-----|
| `status/emit.py:388` | `_feature_status_lock_root` — picks status-lock root (write-safety) |
| `status/work_package_lifecycle.py:58` | managed-mission lifecycle gate |
| `status/store.py:122-128` | `_find_mission_specs_root` ("best effort" fallback, self-acknowledged) |

**Disposition:** ACCEPT as documented debt. Practical risk is bounded by enforced project layout; a same-named directory elsewhere is the only failure mode and is not observed in any incident. Revisit only if a real topology resolver lands for Clusters A/B (it would absorb these). File a low-priority note, do not block the slice.

---

## Appendix — BACKSTOPPED pattern catalog (convention WITH verification; copy these)

The right way to use a name/string as a *proposal* that is then *confirmed* against declared state:

- `cli/commands/doctor.py:2957` — `name.startswith(f"{slug}-lane-")` **then** cross-checked against `git worktree list --porcelain`. (Cluster A's fix template.)
- `lanes/branch_naming.py:105-340` — canonical `mid8_from_slug` + `parse_*`/`is_*` regex API; empty-return is a contract callers backstop with meta. (Cluster B's fix template.)
- `coordination/surface_resolver.py:66-77` — `meta.mid8 → meta.mission_id[:8] → mid8_from_slug` cascade (correct until the fabrication else, Cluster C).
- `coordination/workspace.py:156-159` — composes branch from declared parts **then** `git symbolic-ref HEAD` verifies the worktree.
- `mission_runtime/resolution.py:108-118` — `mid8_from_slug` then `_mid8_from_primary_meta` (double-backstop).
- `context/resolver.py:178-182` — re-canonicalises `slug = feature_dir.name` (resolved dir, "never the raw handle") before composing.
- `coordination/transaction.py:731,76-133` — structured `error_code` ClassVar + catch-by-type. (Cluster D's fix template.)
- `core/dependency_graph.py:143-155` — filename `WP\d{2}` cross-checked against frontmatter `work_package_id`, `ValueError` on mismatch.
- `doctrine/missions/mission_type_repository.py:118` — `yaml_file.stem == mission_type.id` enforced with reject-on-mismatch (strongest backstop in tree).
- `doctrine/artifact_kinds.py:55-64` — suffix routes the loader; Pydantic `model_validate` confirms content matches the kind.
- `status/validate.py:219-225` ↔ `lane_reader.py:25` — `status.events.jsonl` presence is the finalization flag, backstopped by paired-presence consistency guard.
- `review/prompt_metadata.py:114-121` — repo-hash + slug + WP + UUID temp path, frontmatter-validated. (Cluster F's fix template.)
- `core/paths.py:354` / `status/views.py:190` — `.git` file-vs-dir and `worktrees/` are git-protocol invariants, content-validated before use.

**Common shape of every good row:** *name proposes → declared authority (git registry / meta.json / enum / typed error_code / Pydantic) disposes.* Future convention-bearing code must include the second half.

---

## Architect adjudication (alphonso, 2026-06-12)

**Frame.** Clusters A–C are not new findings — they are *violations of already-declared invariants* of the 3.x Execution/Runtime module. The container doc (`architecture/diagrams/02_containers/runtime-execution-domain.md`) already states: inv #2 "raises rather than silently falling back on unresolvable context"; inv #4 "mid8 is derived **exactly once** as `mission_id[:8]`"; routing inv #4 "a materialized coord root lacking the mission dir **fails closed**". A/B/C are the residual sites where code predates or bypasses these invariants. So this is a *strangle to the declared seam*, not a greenfield design.

**Q1 — Slice shape & seam. ONE mission, working title "name-vs-authority remediation" (next #1666 slice). Do NOT split C out.** C is the same root cause as B (empty-mid8 → fabricate vs. fail-closed) and shares two of its four sites (recovery.py, compute.py) verbatim; splitting it spawns a merge-conflict race against B on identical lines for an illusory "S" win. The right seam is **two cohesive surfaces, not one new `topology` god-module and not 12 per-site patches**:
- **Topology authority (Cluster A)** belongs in the **Execution/Runtime** bounded context, as a single `is_registered_coord_worktree(path) -> bool` (and its `classify_worktree_topology`) helper co-located with `resolve_status_surface_with_anchor` in `coordination/surface_resolver.py` (the module that already owns "fails closed" surface resolution). It wraps the `git worktree list --porcelain` cross-check that `doctor.py:2957` already proves works. All 5 A-sites delegate to it; none re-derives from `path.parts`.
- **Branch identity authority (Clusters B+C)** is the **already-canonical** `lanes/branch_naming.py` compose/decompose API fed `mission_id`/`mid8` from `meta.json`. There is no missing module — B/C sites simply don't call it. The fix is to route every compose site through `mission_branch_name(slug, mission_id)` and make the `mid8_from_slug()=="" ` cascade-exhaustion path **raise a structured error** (the `surface_resolver._coord_mid8` fabrication else at line 80 becomes a raise), per inv #4.

Do **not** merge A and B into one `topology` module: A's authority is the *git worktree registry* (runtime/filesystem), B/C's authority is *declared meta.json identity + the naming grammar*. Different authorities, different bounded responsibilities — a combined module would couple git-process I/O to pure string grammar. Keep them as the two named surfaces above.

**Ratchet (keeps the seam closed), in the spirit of `test_safe_commit_import_boundary`:** add `tests/architectural/test_topology_resolution_boundary.py` asserting (1) the predicate `".worktrees" in path.parts` / `name.endswith("-coord")` appears in `src/` **only** inside an allowlisted set = {`coordination/surface_resolver.py`, the new helper module} — every other occurrence is a regression (mirrors the "exactly the blessed importers" assertion); and (2) `mid8_from_slug` callers in `src/` either backstop with a meta read or are in an allowlist — no site composes `f"kitty/mission-{slug}"` without `mission_id` in scope (AST scan for the f-string literal, mirroring the `destination_ref=` call-site scan). The C-side ratchet: the fabrication idiom `(…replace("-","")+"00000000")[:8]` must have **zero** occurrences in `src/` (string scan, exactly like the deleted-privilege-channel test).

**Q2 — Ranking sanity.** Two adjustments:
- **G (parent.name==KITTY_SPECS_DIR on WRITE paths): PROMOTE the write-path sites (emit.py:388 lock-root; work_package_lifecycle.py:58) from ACCEPT to fold-into-slice; KEEP store.py:122 (self-acknowledged best-effort read fallback) as ACCEPT.** Randy's "bounded by enforced layout" reasoning holds for a *read* fallback but not for a *lock-root selection* — mis-routing a write lock is a concurrency-safety defect of the same class as A (split-brain), and the slice already lands a topology authority that absorbs it cheaply. Write-path mis-routing is not acceptable debt when the resolver that fixes it is being built one cluster over.
- **D (error-substring control flow): keep TICKET-ONLY, but pull the ONE workflow.py:781 site into the slice.** It already caused #1860's confusion, the typed class `CanonicalStatusNotFoundError` *already exists*, and the change is a one-line `isinstance`. Folding the single trivial-and-incident-linked site in is right-sized; the other three D sites (worktree.py marker tuple, validator "has no steps", dashboard port) need *new* exception types — that is genuine design scope, correctly TICKET-ONLY. E and F rankings stand (mechanical enum/path debt, no architecture decision).

**Q3 — Sequencing vs in-flight work.** The slice is **independent of and should precede** both the pre/post-mission-lifecycle spec (`270b95004`, #1802 — still a draft spec, no code) and the WP06 Op-as-execution-artifact ADR (`2026-06-11-1`, naming the Op primitive). Neither owns the name-vs-authority resolver; both *consume* execution-state resolution and would inherit the split-brain hazard if built on the un-hardened surface. Landing A/B/C first means #1802's intake/correction flows and #1804's Op queue compose against a topology/identity authority that already fails closed — they should not re-derive coord-ness or mid8. Recommend the slice lands on the same `feat/execution-state-strangler` lineage as #1666 slice 2, *before* #1802 leaves draft.

**Returns.**
- **(a) Immediate fixes (in-slice, no ticket needed):** C fabrication else → structured raise (surface_resolver.py:80); workflow.py:781 substring → `isinstance(CanonicalStatusNotFoundError)`.
- **(b) Mission-slice scope ("name-vs-authority remediation"):** Cluster A (5 sites → `is_registered_coord_worktree` in surface_resolver) + Cluster B (7 compose/decompose sites → route through `branch_naming` + thread `mission_id`) + Cluster C (4 sites → fail-closed on exhausted mid8 cascade) + **G write-path sites** (emit.py:388, work_package_lifecycle.py:58) + workflow.py:781 (the single D site) + the two architectural ratchet tests.
- **(c) Tickets to file:** Cluster D residual (worktree.py:332 marker tuple, mission_loader/validator "has no steps" → add `error_code`, dashboard `PortUnavailableError`); Cluster E (Lane/DecisionKind/mission-type literal→enum sweep; promoting `DecisionKind` to `Enum` is the one design item); Cluster F (#1831 — thread `mission_slug` into `_write_prompt_to_file` + point SKILL.md at `$REVIEW_PROMPT`, propagate via upgrade).
- **(d) Accepted debt:** Cluster G read-fallback only (store.py:122 `_find_mission_specs_root` best-effort); E/F glossary event-type literal split (folds into E ticket); git-protocol conventions in the BACKSTOPPED catalog (correctly owned by git).
