# Implementation Plan: Drift-Proof Architectural Ratchet Allow-lists

**Mission**: content-address-ratchet-allowlists-01KX8M4D
**Branch**: `analysis/test-change-coupling` (integration) → PR to `main`
**Spec**: [spec.md](./spec.md) · **Parent**: #2071 · **Folds** #2072 · **Coordinates** #2077

## Summary

Re-key the architectural ratchet allow-lists from **position anchors** (line
numbers, `module::Name`) onto **content descriptors** so a behaviour-preserving
refactor that only *moves* code cannot red the gates — while every gate keeps its
full bite. Three workstreams: WS1 line-drift unification (a shared content
descriptor + exactly-one resolution + a standing meta-guard), WS2 dead-code
scanner relocation-hardening (a net-new relocation-proof symbol key + auto-derived
categories), WS3 a small ratio=1.00 audit residue. Hardened by a post-spec squad.

## Technical Context

**Language/Version**: Python 3.11+ (test infrastructure; CI runs a 3.11 local /
3.12 shard split — token normalization matters)
**Primary Dependencies**: `pytest`; `ast` + `tokenize` (stdlib); the in-repo
`src/specify_cli/contracts/anchoring.py` substrate (`composite_key`,
`code_tokens_by_line`, `enclosing_qualname`, `is_file_line_anchor`,
`FORBIDDEN_POSITIONAL_FIELDS`), re-exported by `tests/architectural/_ratchet_keys.py`
**Storage**: N/A (test seeds are Python constants + two YAML allow-lists)
**Testing**: `pytest tests/architectural/` (baseline **869 passed / 0 failed**,
4 skipped); per-gate plant-and-catch self-tests; `uvx radon` is not a gate here
**Target Platform**: developer + CI (`fast-tests-*` / `arch-adversarial` jobs)
**Project Type**: single project (test-infra refactor, no runtime surface change)
**Performance Goals**: N/A (gate runtime unchanged; scan-derived keys are O(findings))
**Constraints**: behaviour-preserving (bite preserved); DIR-041 governing (C-001);
trio clause conditional on PR #2545 (C-002); `_baselines.yaml`/`anchoring.py`
single-owner (C-006); WS2 gated last behind a tripwire (C-004)
**Scale/Scope**: ~6 ratchet allow-lists migrated (5 line-seed + the dead-symbol
key) + 1 standing meta-guard + 3 small WS3 edits; ~7 WPs forecast

## Charter Check

*GATE: re-check after Phase 1.*

- **Single canonical authority**: PASS — reuses `contracts/anchoring` as the one
  key substrate; the standing meta-guard becomes the single authority banning
  positional anchors across all ratchet allow-lists (generalizes DIR-041).
- **ATDD-first / red-first**: PASS — each gate carries a plant-and-catch
  non-vacuity self-test (FR-013); the meta-guard is written red-first (C-006).
- **Terminology adherence**: PASS — no Mission/feature terminology surface.
- **Test-remediation discipline**: PASS — this mission *is* the sanctioned
  "convert refactor-fragile positive pins to content-addressed invariants"
  remediation (refactor-stable-arch-tests doctrine); no test is deleted to pass,
  and bite is provably preserved.
- **No new god-object**: PASS — WS2's new key lives in its own module.

No charter violations → Complexity Tracking empty.

## Project Structure

### Documentation (this mission)
```
kitty-specs/content-address-ratchet-allowlists-01KX8M4D/
├── spec.md            # committed
├── plan.md            # this file
├── research.md        # Phase 0 — squad-consolidated decisions
├── data-model.md      # Phase 1 — entities (descriptor, keys, staleness)
├── quickstart.md      # Phase 1 — motion + bite validation batteries
├── contracts/         # Phase 1 — descriptor-resolver + meta-guard interfaces
├── tracers/           # 3 tracer files (seeded now)
├── issue-matrix.md    # committed
└── tasks.md           # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source surfaces (repository root) — all under `tests/architectural/` + one src helper
```
tests/architectural/
  _ratchet_keys.py                          # + descriptor-resolver helper (IC-DESCRIPTOR)
  test_no_write_side_rederivation.py        # IC-WS1-WRITESIDE
  test_wp05_write_target_drain.py           # IC-WS1-WRITESIDE
  test_single_mission_surface_resolver.py   # IC-WS1-RAWJOIN
  test_trio_seam_only.py                    # IC-WS1-TRIO (conditional on #2545)
  test_ratchet_positional_anchor_ban.py     # IC-METAGUARD (NEW, standing)
  test_no_dead_symbols.py                   # IC-WS2-KEY + IC-WS2-CATEGORIES
  test_no_dead_modules.py                   # IC-WS2-MODULES
  _baselines.yaml / test_ratchet_baselines.py   # IC-WS2-CATEGORIES (SOLE owner, C-006)
  test_template_governance_payload_contract.py  # IC-WS3
  test_layer_rules.py                       # IC-WS3
src/specify_cli/contracts/
  anchoring.py                              # IC-METAGUARD only (C-006)
  <new>_symbol_identity.py                  # IC-WS2-KEY (NEW; keeps anchoring.py single-owner)
```

## Complexity Tracking
*No charter violations — none.*

## Implementation Concern Map

Dependency spine: **IC-WS3** (free, first) · **IC-DESCRIPTOR** (keystone) →
**IC-WS1-\*** migrations → **IC-METAGUARD** (hard, after all WS1) · **IC-WS2-\***
(gated last, tripwire; no hard dep on WS1 but must not gate its merge).

### IC-DESCRIPTOR — shared content-descriptor mechanism (keystone)
**FR**: FR-001/002/003, NFR-005. **Owns**: a helper in `_ratchet_keys.py` (or a
sibling), e.g. `resolve_descriptor(source, descriptor) -> CompositeKey` +
`descriptor_still_live(source, descriptor, seeded_key) -> bool`.
**Design**: descriptor `(rel_path, qualname, token_substring, occurrence, rationale)`;
match `token_substring` against the **normalized** `code_tokens_by_line` output;
collect findings whose `enclosing_qualname == qualname` and whose token line
contains the substring; **assert exactly one** (RED on 0 or >1); return its
`composite_key`. Staleness = "resolves to exactly one whose key **equals** seeded".
**Verified**: composite_key + normalization already exist (anchoring.py). **Depends**: none.

### IC-WS1-WRITESIDE — migrate write-side + wp05 (+ campsite)
**FR**: FR-005a, FR-006, FR-007b. **Owns**: `test_no_write_side_rederivation.py`
(`_ALLOW_LIST_SEED` + `_CHECKOUT_GRAMMAR_ALLOW_LIST_SEED` + the 3 line-number
twin-guards) and `test_wp05_write_target_drain.py` (the `_ALLOW_LISTED_LINE=347`
scalar **and** the `composite_key(source,347)` call-arg; keep the 2 probes).
Delete the re-anchor changelog fossils. **Depends**: IC-DESCRIPTOR.

### IC-WS1-RAWJOIN — migrate the highest-tax gate
**FR**: FR-005b, FR-007b. **Owns**: `test_single_mission_surface_resolver.py`
(`_RAW_JOIN_SITES`, ~8 re-anchors — #3 CaaCS). Delete its 8-entry fossil.
**Depends**: IC-DESCRIPTOR.

### IC-WS1-TRIO — migrate the trio I/O allow-list (CONDITIONAL)
**FR**: FR-005c. **Owns**: `test_trio_seam_only.py` (`_IO_ALLOWLIST_SITES`).
**Conditional on PR #2545** (file absent on this branch). If #2545 unmerged at
implement time → drop to a tracked follow-up, do NOT block.
**Depends**: IC-DESCRIPTOR + #2545.

### IC-METAGUARD — standing all-suite positional-anchor ban
**FR**: FR-004, FR-014. **Owns**: `test_ratchet_positional_anchor_ban.py` (NEW) +
any `anchoring.py` helper (**sole owner**, C-006). Scans **all**
`tests/architectural/` Python seeds + the two YAMLs; bans integer line components
in **authoritative** comparands; codifies authoritative-vs-diagnostic (permit the
documented non-authoritative `line:` locator fields + count-floor baselines).
Enumerates the two deferred `path::qualname` census allow-lists (FR-014).
**Hard sequence**: lands AFTER all in-scope WS1 migrations (write red-first; green
only once no un-migrated line seed remains — else it self-reds and blows NFR-004).
**Depends**: IC-WS1-WRITESIDE + IC-WS1-RAWJOIN (+ IC-WS1-TRIO if in scope).

### IC-WS2-KEY — relocation-proof symbol identity (GATED LAST, tripwire)
**FR**: FR-007. **Owns**: a NEW `_symbol_identity` module (C-006) +
`test_no_dead_symbols.py` key migration (343 entries). **Design-spike first WP**:
a relocation-proof key that **forbids bare-name-alone** (keep a module/body
disambiguator; gate behind the existing T004 no-false-negative self-tests using
`ArtifactKind`×3 / `GateDecision`×2 / `ResolutionResult`×2 fixtures).
**Tripwire (C-004)**: >2 impl WPs or unstable body-hash → carve WS2 to standalone
#2546. **Depends**: none (independent key); must NOT gate WS1/WS3 merge.

### IC-WS2-CATEGORIES — auto-derive exempt categories
**FR**: FR-008. **Owns**: `test_no_dead_symbols.py` category logic +
`_baselines.yaml` + `test_ratchet_baselines.py` (**SOLE owner of the baseline
files across the whole mission**, C-006). Auto-derive the registered *class*
symbol exemption (`@MigrationRegistry.register`, ~96 `m_*.py` — dead helpers still
caught), docstring/`__all__`-only re-export shims, Typer sub-apps. Coordinate
#2293. **Depends**: IC-WS2-KEY.

### IC-WS2-MODULES — module scanner relocation-hardening
**FR**: FR-009. **Owns**: `test_no_dead_modules.py`. Preserve cross-module
`__all__` deadness + the 4 detectors + test-not-caller + bidirectional ratchet.
**Depends**: IC-WS2-KEY (shared identity concept).

### IC-WS3 — ratio=1.00 audit residue (free, FIRST/parallel)
**FR**: FR-010/011/012. **Owns**: `test_template_governance_payload_contract.py`
(derive promised-surface from contract/schema) + `test_layer_rules.py` (convert
the 2 `__module__` sub-tests) + the FR-012 doc-only 10-KEEP verdict.
**Depends**: none.

### Definition of Done (every migrating IC)
FR-013 plant-and-catch self-test **including a planted same-qualname sibling
offender** (proves exactly-one staleness deletes a routed allowance) + the motion
battery (NFR-001, 0 false reds) + the bite battery (NFR-002, 100% caught) + full
`tests/architectural/` 869/0 (NFR-004) + 0 authoritative line anchors
(NFR-003/SC-003). The NFR batteries are the gate, not complexity.

## Post-Plan Squad Hardening (3 lenses — folded)

### Descriptor feasibility — proven for all 17 line-seed entries; ZERO need `occurrence`
The design lens resolved every current line seed against live source. All resolve
to **exactly one** finding; `occurrence` is forward-insurance only. This table is
the direct `/tasks` authoring input (token_substrings are in **normalized** token
space):

| # | Seed list | src site | qualname | token_substring |
|---|---|---|---|---|
| WS#1 | `_ALLOW_LIST_SEED` | status_transition.py | `_resolve_write_target` | `coord_branch or _current_branch` |
| WS#2 | `_ALLOW_LIST_SEED` | agent/workflow.py | `_review_feedback_root` | `return feature_dir . parent . parent` |
| WS#3 | `_ALLOW_LIST_SEED` | implement.py | `_status_commit_destination_branch` | `get_current_branch ( repo_root ) or fallback_branch` |
| CG#1 | `_CHECKOUT_GRAMMAR` | coordination/transaction.py | `BookkeepingTransaction.commit` | `CommitTarget ( ref = self . destination_ref )` |
| CG#2 | `_CHECKOUT_GRAMMAR` | agent/tasks_map_requirements.py | `_mr_resolve_context` | `CommitTarget ( ref = st . target_branch )` |
| CG#3 | `_CHECKOUT_GRAMMAR` | agent/workflow.py | `_commit_via_legacy_safe_commit` | `CommitTarget ( ref = target_branch )` |
| CG#4 | `_CHECKOUT_GRAMMAR` | agent/tasks_move_task.py | `_mt_commit_lane_deliverables` | `CommitTarget ( ref = workspace . branch_name )` |
| RJ#1 | `_RAW_JOIN_SITES` | coordination/surface_resolver.py | `_coord_mid8` | `coord_candidate = repo_root` |
| RJ#2 | `_RAW_JOIN_SITES` | coordination/surface_resolver.py | `_coord_mid8` | `primary_candidate = repo_root / KITTY_SPECS_DIR / mission_slug` |
| RJ#3 | `_RAW_JOIN_SITES` | missions/_read_path_resolver.py | `primary_feature_dir_for_mission` | `primary_dir : Path = get_main_repo_root ( repo_root ) / KITTY_SPECS_DIR / mission_slug` |
| RJ#4 | `_RAW_JOIN_SITES` | core/mission_creation.py | `create_mission_core` | `feature_dir = resolved_root / KITTY_SPECS_DIR / mission_slug_formatted` |
| WP05 | `_ALLOW_LISTED_LINE` | status_transition.py | `_resolve_write_target` | `coord_branch or _current_branch` |
| TR#1–5 | `_IO_ALLOWLIST_SITES` (trio, post-rebase) | gates_core.py / implement_cores.py | `_workflow_evidence_missing` / `status_porcelain` / `show_blob` / `_drop_vcs_lock_only_meta` / `_files_changed_vs_ref` | `read_text (` / `subprocess . run (` ×2 (disambiguated by qualname) / `read_bytes ( )` ×2 |

Two cases prove the two-axis disambiguation: RJ#1/RJ#2 (same qualname, different
substring); TR#2/TR#3 (identical token line `subprocess . run (`, different qualname).

### Design gaps to encode (non-blocking)
- **GAP-1 (highest-risk authoring rule):** `resolve_descriptor(source, …)` scans
  ALL token lines in the qualname, not the gate's finding-set. So `/tasks` MUST
  mandate: (a) author `token_substring` from the finding's **own** normalized
  token line; (b) an import-time **unique-within-qualname** assertion; (c) the
  FR-013 self-test asserting `resolve_descriptor(...) == composite_key(source, true_finding_line)`.
- **GAP-2 (minor):** build the qualname map **once** per file, not per-line.

### Key-shape / consolidate-not-fork (brownfield lens)
`composite_key` returns a **2-tuple** `(qualname, token_line)` (no `rel_path`).
`tests/architectural/surface_resolution_audit/audit.py` already defines the
canonical **path-qualified 3-tuple** `CompositeKey = (str,str,str)` +
`_composite_from_file`. **IC-DESCRIPTOR reuses/relocates that**, it does not fork a
third key-builder. Authoritative descriptor key = the path-qualified 3-tuple.

### Meta-guard predicate (ownership + design lenses converge)
Ban = an **int reaching a line-locator sink** (NOT "positional anchor", NOT
`module::Name`). Python = AST int-to-line-sink (2nd arg of `composite_key(_from_file)`,
or a `code_tokens_by_line(...)` subscript/`.get`). YAML = field-name rule (ints
only in `line`/`count`/`*_baseline`). `module::Name`/`path::qualname` + `occurrence`
are structurally never caught → **IC-METAGUARD depends ONLY on the WS1 line-seed
migrations, never WS2**. (Reconciles the reworded spec rule + FR-004.)

### Ownership corrections (C-006, revised)
- **Single-own `test_no_dead_symbols.py` end-to-end** → fold IC-WS2-KEY + IC-WS2-CATEGORIES into ONE owner (no two concurrent lane-owners on the file).
- **Hoist `_baselines.yaml` + `test_ratchet_baselines.py` OUT of the carvable WS2 WP** onto a WS1-side / early WP; WS2 routes its deltas into it (so a carve can't orphan a WS1 count bump).
- **IC-METAGUARD also owns `tests/_arch_shard_map.py`** and enrolls the new
  `test_ratchet_positional_anchor_ban.py` in the SAME WP (else `test_arch_shard_marker_completeness` reds — the trap the trio hit).

### WS2 tripwire (revised) + WP forecast
IC-WS2-KEY mixes design-spike + 343-entry migration + T004 fixtures → **must split**
(spike vs bulk) → that split itself trips the ">2 impl WPs" arm → **WS2 will likely
CARVE to #2546**. The spike WP MUST end with an explicit **carve/continue checkpoint
(implementer proposes, operator confirms)** BEFORE the bulk migration; "unstable
body-hash" = any drift under the NFR-001 motion battery or the 3.11↔3.12
`code_tokens_by_line` normalization.
**Forecast = decision tree:** base case **5–6 WPs (WS2 carved)** — WP1 WS3 · WP2
DESCRIPTOR(+baselines-owner) · WP3 WS1-WRITESIDE · WP4 WS1-RAWJOIN · WP5 METAGUARD
(+ WP6 WS1-TRIO after #2545 rebase); ceiling **~8** if WS2 stays fully in. WPs to
watch for >10 subtasks: IC-WS2-KEY (must split), IC-WS1-WRITESIDE (2 files, borderline).

### Status: PR #2545 MERGED (2026-07-11)
IC-WS1-TRIO is **in-scope after rebase** (C-002 flipped) — rebase the mission
branch onto main-with-#2545, then migrate `test_trio_seam_only._IO_ALLOWLIST_SITES`
(+ add its shard-map entry). Do NOT default to the follow-up drop.
