# Tracer: Tooling Friction — custom-mission-type-second-class-citizens-01M1FQXD

Mission: Custom mission types are second-class citizens (#3830, #3831, #3832)
Phase: spec

Seeded at spec authoring per charter standing order #3 (mission tracer files).
Append friction encountered during plan/tasks/implement/review here; assess at
mission close.

## Spec phase

- No tooling friction encountered authoring this spec. All code citations
  (file paths, symbol names, line numbers) in the operator's brief were
  re-verified directly against the checkout via grep/sed rather than trusted
  on faith, per charter guidance to cite by symbol and verify every line
  number. All citations held up; only one detail needed correction (see
  tracer-design-decisions.md: `mission_setup_plan.py`'s three `is_substantive`
  call sites are not uniformly `kind="plan"` — line 553 is `kind="spec"`).
- GitHub issues #3830, #3831, #3832, #2660, and #3284 were all independently
  re-verified live via `gh issue view` rather than trusted from the brief;
  all matched.

## Plan phase

- `spec-kitty plan --mission custom-mission-type-second-class-citizens-01M1FQXD --json`
  ran cleanly non-interactively on the first attempt, scaffolding `plan.md` from this
  mission's own `software-dev` plan-template.md (this mission's own `meta.json` declares
  `mission_type: "software-dev"`) with `scaffold_only: true` in the JSON result. No
  friction.
- Verified plan.md itself passes its own `is_substantive(plan_file, "plan")` check
  post-authoring (`True`) — a useful, cheap self-check given this plan.md's Technical
  Context section is real content (Python 3.11+, etc.), not a proxy for the mission's own
  substantive-gate work (which targets four DIFFERENT mission types' templates, not
  software-dev's own).
- One citation from the task brief did not hold up under direct verification: the
  suggested gate-set list asserted "mission-loader coverage ≥90% ... mission.py is
  touched by FR-005 — this applies." Reading `.github/workflows/ci-quality.yml`
  directly showed the `mission-loader-coverage` job covers a different package
  (`src/specify_cli/mission_loader/`) that does not contain the functions FR-005
  touches. This is recorded as a correction, not silently dropped — see
  tracer-design-decisions.md and `plan.md` §Gate Set / `research.md` §R5.
- All other load-bearing citations in the task brief (template line numbers/shapes,
  `_substantive.py` function spans, `mission_setup_plan.py` call-site line numbers,
  `MissionConfig`/`MissionTypeProfile` field lists, the `runtime_bridge_composition.py`
  early-return bug) were independently re-verified against live source this session and
  held up exactly as described.

## Plan-phase fix round (post plan.confirmed.yaml)

- Confirmed-findings citations drift fast even within the same session: the findings
  file's own citation for the CI `critical_paths` array ("ci-quality.yml ~L3370-3396")
  was already one line short of the array's real close-paren (L3399) by the time this
  fix round re-verified it — re-read the live source rather than trusting a citation
  one round old, even a "confirmed" one.
- No tooling breakage encountered fixing the 9 findings — all edits were plain
  markdown changes to `plan.md`/`research.md`; no CLI command was needed for this
  fix-round pass beyond source-file reads for re-verification (`grep`, direct file
  reads of `mission.py`, `runtime_bridge_composition.py`, `runtime_bridge.py`,
  `mission_type.py`, `.github/workflows/ci-quality.yml`, and both research/plan
  templates).

## Tasks phase

- `spec-kitty agent mission finalize-tasks --validate-only --json` surfaced a real
  mechanical gap on the first attempt: `unmapped_functional_requirements: ["FR-004"]`.
  Reading `_read_spec_requirement_ids`/`parse_requirement_ids_from_spec_md`
  (`src/specify_cli/requirement_mapping.py`) directly showed the requirement-mapping
  validator has **no notion of a conditionally-descoped FR** — it requires every
  FR-prefixed id declared in spec.md's own table (any of the four recognized declared
  shapes) to appear in some WP's `requirement_refs`, full stop. spec.md's own FR-004 row
  is written conditionally ("IF... schema compatible... If incompatible, this FR is
  descoped"), and `plan.md`/`research.md` §R3 already resolved that condition to
  "incompatible, descoped" — but the tool has no "descoped" status column or marker it
  reads; a `~~FR-004~~` strikethrough was checked too (the table-row regex's comment
  explicitly mentions strikethrough as a "retired requirement" convention) and confirmed,
  by reading the regex itself, to still capture the id into the declared set — it does
  NOT exempt it from the unmapped-FR gate.
- **Resolution**: mapped `FR-004` into WP02's `requirement_refs` for traceability only,
  with an explicit documentation-only subtask (WP02 T006) recording that this is not an
  implementation and citing `research.md` §R3's tracked-follow-up description, per the
  operator brief's own resolution instruction. This keeps FR-coverage honest (no WP
  silently implements or silently drops FR-004) without editing spec.md, which is an
  approved artifact from an earlier phase and out of this WP-authoring task's ambit.
  Re-running `--validate-only` after this change passed cleanly.
- `wps_manifest.py`'s `check_concern_refs_coverage` emitted non-blocking
  `ownership_warnings` for all three WPs ("missing plan_concern_refs and cross_cutting is
  not set") on both the validate-only and mutating runs. This is expected, not friction:
  `plan.md` uses no `IC-##` concern-heading convention (confirmed via
  `_plan_contains_implementation_concerns`'s own regex against the live `plan.md` — zero
  matches), so `plan_concern_refs` was correctly omitted from every WP per the operator
  brief; the warning is advisory only and did not block either run.
- `finalize-tasks`'s mutating run wrote a `branch_strategy` string shaped for a
  multi-lane/dependency-specific-base topology ("this WP may branch from a
  dependency-specific base... unless the human explicitly redirects the landing branch")
  into all three WPs' frontmatter, even though `meta.json` declares
  `topology: "single_branch"` and `planning_base_branch`/`merge_target_branch` were
  already correctly written. Corrected in a small follow-up commit
  (`f68510687`, `tasks(3830): correct WP branch frontmatter for single_branch topology`)
  per the operator brief's own anticipation of this exact drift — the sanctioned one
  hand-edit of finalized frontmatter.

### Tasks-phase review fix round (post tasks.confirmed.yaml, 2026-09-02)

- Confirmed a real, permanent gap in `generate_tasks_md_from_manifest`
  (`src/specify_cli/core/wps_manifest.py:170-218`) while fixing TASKS-COVER-001: the
  function joins `wp.requirement_refs` verbatim into the rendered
  `**Requirement Refs**: ...` line with no per-ref status field, so a genuinely-implemented
  FR (e.g. WP02's FR-005) and one a WP explicitly declines to implement (WP02's FR-004,
  traceability-only per the #3831 SPLIT verdict) render identically in `tasks.md`. Added an
  inline YAML comment beside `wps.yaml`'s WP02 `FR-004` entry and mirrored it in
  `tasks/WP02-loud-fallback.md`'s frontmatter — confirmed via direct read of
  `load_wps_manifest` (`wps_manifest.py:83-86`, `ruamel.yaml` `YAML(typ="safe")`) that
  comments are parser-stripped, so this does not change `compute_coverage`'s mechanical
  behavior, and re-ran `finalize-tasks --validate-only --json` afterward to confirm the
  mission still validates cleanly. The comment necessarily does not survive into the
  generated `tasks.md` table row (the renderer has no field to carry it into) — this is
  out of scope to fix here (renderer code is outside this mission's C-003 file sets) and is
  recorded as a spec-kitty tooling gap: `SPEC-KITTY-LEDGER.md` SK-132.
- Added a sequencing-reconciliation note to WP02's and WP03's "Why this WP exists"
  sections for TASKS-ORDER-001: `plan.md` §Suggested Work Package Sequencing's mission-wide
  "campsite-clean precedes all three" intent is satisfied by WP01's T001 alone (no
  qualifying campsite-clean debt exists in WP02's or WP03's own file sets per §Campsite-Clean
  Scope), so no `dependencies: ["WP01"]` edge was added to `wps.yaml` — that would force
  WP02/WP03 to wait on all of WP01's T001-T007, contradicting plan.md's explicit
  independent/parallelizable framing. Placed in the WP `.md` prose rather than `wps.yaml`'s
  structured fields, confirmed by reading `mission_finalize.py`'s `_run_bootstrap_loop`
  (`~L1585-1651`): it reads each WP's frontmatter/body via `_read_wp_frontmatter`, only
  rewrites the file when frontmatter fields change, and always writes the original `body`
  back unchanged — so hand-authored prose in the WP body is not regenerated or clobbered by
  `finalize-tasks`, unlike `wps.yaml`/frontmatter's structured fields.

### Tasks-phase fresh-sweep fix round (post tasks.confirmed-3.yaml, 2026-09-02)

- Confirmed a second, related permanent gap while fixing TASKS-FRESH2-002:
  `_branch_strategy_text()` (`src/specify_cli/cli/commands/agent/mission_finalize.py:1432-1440`)
  is topology-blind — it takes only `target_branch`/`merge_target_branch`, never the
  mission's own resolved coordination topology (`single_branch` here, per `meta.json`),
  and unconditionally emits "...this WP may branch from a dependency-specific base... unless
  the human explicitly redirects the landing branch" for every mission regardless of
  topology. All three WP files' `branch_strategy` frontmatter was hand-corrected in commit
  `f68510687` for this mission's `single_branch` topology ("never a dependency-specific or
  per-WP branch") — the sanctioned one hand-edit noted in the Tasks phase section above. But
  because the generator itself was never fixed, this hand-correction diverges from the
  canonical source rather than fixing it: running
  `./.venv/bin/spec-kitty agent mission finalize-tasks --mission custom-mission-type-second-class-citizens-01M1FQXD --validate-only --json`
  confirms `would_modify` still proposes overwriting all three WPs' `branch_strategy` back
  to the dependency-specific-base wording. Any future non-`--validate-only` `finalize-tasks`
  re-run on this mission (a normal recovery/re-entry operation, not a hypothetical one)
  would silently regress the hand-fix and reintroduce topology-contradicting text. Recorded
  as a spec-kitty tooling gap: `SPEC-KITTY-LEDGER.md` SK-133. As an immediate in-mission
  safeguard, added a YAML comment directly above `branch_strategy:` in each of the three WP
  frontmatter blocks warning against a non-`--validate-only` `finalize-tasks` re-run on this
  mission; re-ran `--validate-only --json` afterward to confirm the comment placement does
  not break frontmatter parsing.
