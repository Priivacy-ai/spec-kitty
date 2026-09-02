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
