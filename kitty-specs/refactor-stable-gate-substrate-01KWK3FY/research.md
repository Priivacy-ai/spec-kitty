# Phase 0 Research — refactor-stable-gate-substrate-01KWK3FY

Consolidates the pre-spec census (debugger-debbie) and the post-spec squad evidence
(reviewer-renata, paula-patterns), all command-backed on this branch, 2026-07-03.
Entry-point facts re-verified at plan time.

## D1 — Design-P over Design-S (the mission ADR)

- **Decision**: frozen tool-derived `(file, qualname, token)` comparands (Design-P);
  the live scanner re-derives and checks membership.
- **Evidence (renata's drift probe, real `_ratchet_keys.composite_key`)**:
  - Scenario A — blank line above the site, fixed seed: allow-key derives the WRONG
    token (`('f','x = 1')` vs live `('f','return primary_feature_dir_for_mission …')`)
    → MATCH False. Seed re-derivation (Design-S) is NOT drift-immune with a fixed seed.
  - Scenario B — in-place token change, same seed line: both sides re-derive the NEW
    token → MATCH True. A content change to an allowlisted site is INVISIBLE under
    Design-S.
  - Design-P satisfies both halves: drift changes nothing (frozen token still found by
    the membership scan); a content change breaks the match (staleness guard fires).
- **In-tree precedents**: Design-P = `test_no_worktree_name_guess.py`
  (`_ALLOWED_SITES_FILES` frozen composites + `test_pinned_composites_still_live`
  staleness guard + drift theater already shipping). Design-S = `_RAW_JOIN_SITES`
  (stays as-is in its own family; not propagated).
- **Alternatives considered**: Design-S everywhere (REJECTED — empirically fails
  NFR-001); hand-typed tokens (REJECTED — `_RAW_JOIN_SITES`' own rule: tool-derived
  only; hand-typing invites typos and drift).

## D2 — Gate anatomy (verified at plan time)

- `GateAllowlistKey(enclosing_qualname: str, token_line: int)` — construction sites:
  loader :217, `derive_live_key` :270, scanners :455/:597; entry points
  `check_canonicalizer_gate` :462 and `check_coord_authority_gate` :604; int-line test
  constructors ~:645/:714/:1034/:1069 (~6) — ALL convert in the same WP (mypy strict).
- Violation messages print `{rel_path}:{qualname}:{token_line}` (:475/:618) — the line
  survives as a non-authoritative locator so the jump-to ergonomics keep working.
- **Key collision facts (paula)**: qualname `implement` appears in BOTH `workflow.py`
  and `implement.py` entries; `review` twice within `workflow.py` — today disambiguated
  ONLY by line. Post-conversion: by `(file, token)`. Current tokens verified distinct
  (different LHS names), but the design documents the within-function collision rule:
  if two allowlisted sites in one function carry identical tokens, the entry covers
  N occurrences (count-qualified) — mirroring the reference implementation's handling.
- **Consumers**: zero external consumers of the YAML or the key type (grep-verified) —
  the conversion is contained in one file pair.

## D3 — Audit anatomy (paula, verified)

- The audits are **copy-paste twins** — no shared import, each defines its own frozen
  row dataclass + `key() = f"{rel_path}:{line}"` + `main()` checks:
  - `untrusted_path_audit/audit.py`: `SinkRow(rel_path, line, untrusted_source,
    sink_op)`; Check-2 (undercount, raw line) :379-398; Check-3
    (`KNOWN_CANDIDATE_FILES`, path-level — already drift-immune, untouched).
  - `surface_resolution_audit/audit.py`: `ResolutionRow(rel_path, line, call_name,
    handle_source)` + `SelectionRow(rel_path, line, name, in_seam)` — TWO checks
    (:529, :549).
  - A THIRD raw-line compare duplicated in `test_untrusted_path_containment.py:328`.
- **Line-drop non-viability (paula's collision test)**: coarse `(path, source,
  sink_op)` identity collides 7/30 (untrusted) and 6/27 (surface) — the undercount
  tripwire would be defeated by construction. STRUCK.
- **Chosen identity**: `(path, enclosing_qualname, token)` via
  `composite_key_from_file(path, line)` — derivable today from the existing row data
  (line as the one-time locator).
- **Split-brain**: the surface inventory's `line` column is ALREADY consumed as a
  composite seed by `test_single_mission_surface_resolver.py:464,498` while the same
  inventory's own audit compares raw lines — IC-03 reconciles (one identity model per
  inventory) without touching the resolver test.
- **Overcount hole**: neither audit checks that inventory rows map to live sinks —
  deleted sinks leave silent ghost rows. The NEW overcount guard closes this (modulo
  explicitly-tagged rows, e.g. rows kept for documentation of intentionally-removed
  sinks — the tag syntax is a data-model item).

## D4 — Freeze tooling (FR-003 design)

- One-time converter: read YAML seeds → `composite_key_from_file` → write `file:` +
  `token:` (+ keep `line:` as locator). Fail-closed: seed resolving to `<module>`
  scope, empty tokens, or a file that doesn't parse aborts with the offending entry
  named. The converter is a throwaway script recorded in the mission dir (not shipped
  tooling); the runtime staleness guard is the standing protection.
- Runtime semantics: frozen key not found live → gate FAILS with "evict or re-approve"
  guidance (content changed or site removed — both require a human decision, exactly
  the review moment the gate exists to force).

## D5 — CT9 mechanics (census + renata's bar)

- Bypass for verification: `SPEC_KITTY_RUN_QUARANTINE=1` (conftest skip gate,
  `tests/_support/quarantine.py`).
- 15 verified-passing node ids (census 2026-07-03; re-verify on implement day):
  1 retrospect help, 11 upgrade-ux, 1 decision-widen help, 1 decision-shape,
  1 doctor-ops usage.
- Stay-behind reasons to REWRITE: the 2 uv-tool cases are hermetic behavioral-drift
  failures (`calls[0][1] is None` — env dict no longer passed; missing
  `--python 3.13` argv suffix) — NOT "env-dependent". Upstream issue to file for the
  upgrade domain. A16 perf case (0.511s vs 0.5 budget) keeps its CI-timing rationale.
- Determinism evidence: the real CI shard invocation form per the parallel-run rules
  (`-n auto --dist loadfile`, marker-scoped; serial `-n0` for real-port/daemon
  classes), twice, plus a green CI run pre-merge.

## D6 — Doctrine mechanics (census, verified at plan time)

- File: `src/doctrine/styleguides/built-in/testing-principles.styleguide.yaml`
  (schema: `principles` list; `patterns`/`anti_patterns` with name/description/
  good_example/bad_example). Activated in `.kittify/config.yaml`; DRG edges exist.
- Regeneration: `generate_graph` (src/doctrine/drg/migration/extractor.py:767) →
  `src/doctrine/graph.yaml`; two byte-for-byte freshness gates
  (tests/doctrine/drg/migration/test_extractor.py + test_path_ref_resolver.py) enforce
  same-change regeneration.
- Completion evidence: acceptance-time parse script (≥6 named principles matching the
  US3 enumeration, non-empty good/bad examples, ≥1 citing PR #2308) — recorded in the
  acceptance matrix, NOT a standing suite test.

## D7 — Doctrine content outline (what the styleguide gains)

Principles (draft names; final wording at implement):
1. invariants-over-shape (arch/acceptance tests pin invariants; a test that reds on a
   clean refactor measured the wrong thing)
2. negative-and-behavioral-forms-first (forbidden-pattern-absent AST scans; behavioral
   pins through public surfaces — over positive literal-presence scans)
3. size-metrics-belong-to-sonar (no LOC/complexity ceilings in pytest)
4. convert-or-delete-never-re-pin (with surviving-coverage proof)
5. shrink-only-count-ratchets-are-sanctioned (exception-set bounds change only when
   cleaning)
6. transitional-shape-guards-need-a-retirement-path (e.g. seam is-identity batteries →
   named migration of patch targets)
Patterns/anti-patterns each carry a good/bad example citing the PR #2308 precedents
(LOC-gate retirement; literal-scan deletion with surviving coverage; the quarantine
graveyard as the cost of shape-coupling).

## D8 — Blockers/couplings

- PR #2308 coupling resolved by branching on its tip (rebased to `84b2eeed0` at plan
  time); C-002 covers further drift.
- The audit-twin CONSOLIDATION (a shared audit module) is a real improvement
  deliberately NOT attempted here — named in the FR-009 #2072 comment as follow-up
  material (avoids scope growth; the identity unification is the enabling step).

## D9 — Post-tasks squad errata (2026-07-03; line refs re-verified on b824111e7)

Debbie's code-truth pass after the #2308/#2312 rebases — corrections to D2/D3/D5:
- Gate file: constructor sites all EXACT (:164/:174 def+field, :217 loader, :262/:270
  derive_live_key, :433/:455 + :576/:597 scanners, :462/:604 entry points, :475/:618
  messages). Int-line TEST constructors = **10**, not ~6 (regions :645-647, :714-722,
  :1034, :1069). YAML: 3+7 entries confirmed; 5 spot-check re-derivations all PASS.
- Untrusted audit: Check-2 = :379-389 (the convert-target is the LOCATOR compare
  `f"{rel_path}:{line}"` at :383; `SinkRow.key()` is 3-part `rel:line:sink_op`);
  Check-3 starts :391 (untouched). Dup compare confirmed at containment test :328.
- Surface audit: ResolutionRow Check-2 :526-534 (raw compare :528); SelectionRow check
  is "Check 4" :549-561; SelectionRow fields are `(rel_path, line, call_name,
  in_seam_file)` (:353-356).
- **WP03 premise correction (HIGH)**: the resolver test does NOT read inventory.md —
  it imports `discover_rows` (:164) and derives keys from the LIVE scan (:457/:464/:498);
  its `_RAW_JOIN_SITES`/`_ALLOWLISTED_RAW_JOINS` seeds live in the test file. The real
  coupling = the audit module's public shape. Split-brain narrative struck (spec rev 3).
- Reference file: the staleness guard is `test_name_compose_offenders_match_pinned_baseline`
  (:420, stale_exemptions :465); drift theater `test_composite_key_survives_line_drift`
  (:936) + :991 + :1058. `test_pinned_composites_still_live` does not exist — citation fixed.
- Quarantine truth table: 31 marked total; LOCAL 16 pass / 15 fail; **CI 0 pass / 31 fail**
  (run 28643092421). Marker distribution: retrospect 1, upgrade_ux 13, decision_widen 1,
  decision_shape 1, doctor_ops_cli 1, doctor_ops 1, mid8 2, no_checklist 1, daemon_reaper 10.
- Coord fixtures path note: the two by-design YAML entries resolve at
  src/specify_cli/decisions/emit.py + src/specify_cli/widen/state.py (qualname-keyed, harmless).

## D10 — FR-010 CI-green fold mechanics

- The lane: `quarantine visibility (non-blocking)` in ci-quality.yml runs the 31 marked
  nodes with the bypass on; green = every node passes or skips on CI.
- Adjudication inputs per test: the CI failure signature (scratchpad qlane.log capture),
  the local result, the quarantine reason, git history. Judge-the-test: stale→re-pin
  for CI reality; env-fragile assertion (Rich rendering, fresh-venv version skew)→
  remediate robustly; valueless→delete; real-product-signal out of mission domain→
  skip with issue ref (daemon-reaper #2309; uv-tool upstream issue).
- Verification loop: local shard-form + differential skip evidence first; the
  authoritative gate is the lane run on the mission PR.
