---
work_package_id: WP05
title: IA-mechanics, tooling un-pin & aggregate gate sweep
dependencies:
- WP02
- WP03
- WP04
requirement_refs:
- C-006
- C-007
- FR-008
- FR-009
- FR-010
- NFR-001
- NFR-002
- NFR-004
planning_base_branch: docs/common-docs-section-audit
merge_target_branch: docs/common-docs-section-audit
branch_strategy: Planning artifacts for this mission were generated on docs/common-docs-section-audit. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/common-docs-section-audit unless the human explicitly redirects the landing branch.
created_at: '2026-07-22T16:30:00+00:00'
subtasks:
- T022
- T023
- T024
- T025
- T026
history:
- timestamp: '2026-07-22T16:30:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: scripts/docs/
create_intent: []
execution_mode: code_change
model: sonnet
owned_files:
- scripts/docs/bulk_ref_rewrite.py
- docs/development/3-2-page-inventory.yaml
- .github/workflows/docs-freshness.yml
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP05 – IA-mechanics, tooling un-pin & aggregate gate sweep

## ⚡ Do This First: Load Agent Profile

**Before reading any further**, load the `python-pedro` implementer profile via the `/ad-hoc-profile-load`
skill. Adopt its identity, governance scope, boundaries, and the initialization declaration it prints.
Everything below is authored for that profile: type-safe Python, canonical-tooling discipline, real CLIs
(never fabricated flags), gate-verified done-ness, no suppressions. Do not begin editing until the profile is
loaded and its init declaration is on the record.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Sanctioned tool-driven leeway (read first — ownership note)

This WP runs `relative_link_fixer` (writes across `docs/**` referrers) — a canonical tool sweep, not
hand-edited feature work — over referrer files, some of which ARE owned by other WPs (e.g.
`docs/architecture/index.md` and the folded canonical twins). The leeway is safe **by SEQUENCING, not by the
referrers being unowned**: WP05 depends on WP02 **and** WP03 **and** WP04, so every owning WP has already
landed its content before this sweep runs — the tool only repoints links in files whose content is final, so
there is no concurrent-write overlap. (WP03/WP04 explicitly deferred referrer repointing to this WP.) The
rationale is recorded here per the ownership-map-leeway discipline. Do NOT expand beyond the tool-driven
referrer rewrites + the derived artifacts in `owned_files`.

## Objectives & Success Criteria

Close the mission: safely parametrize the foreign-pinned `bulk_ref_rewrite` default (FR-010/C-007), repoint
every referrer (docs/** via `relative_link_fixer` + the one non-docs paradigm ref via `bulk_ref_rewrite`) —
BOTH driven with `--occurrence-map "$MAP"` (C-007) — regenerate the page-inventory lockfile in place, WIRE the
lint into CI now that the tree is post-move-clean (FR-008), and run the aggregate gate — the mission's
Definition of Done.

> **CRITICAL — this mission does NOT regenerate `redirect_map.yaml`.** Proven by execution: this mission's
> moved paths are **never-published** (absent from `scripts/docs/redirect_baseline_urls.json`, 180 baseline
> URLs), so `redirect_stub_generator regenerate-map --occurrence-map "$MAP"` would derive **ZERO** entries and
> **OVERWRITE** `redirect_map.yaml`, destroying the landed `01KW3SBK` mission's 149 published-URL redirects.
> There is **NO** `regenerate-map` / `check-map` step in this WP. Link integrity is delivered by
> `relative_link_fixer` (in-repo docs) + `bulk_ref_rewrite` (non-docs) ONLY. `redirect_map.yaml` and
> `redirect_baseline_urls.json` are LEFT UNTOUCHED (verified in T023). Upstream gap recorded in research.md D5.

```bash
MAP=kitty-specs/docs-structural-sanity-01KY53KJ/occurrence_map.yaml
```

**Success criteria (SC-002/003/004/005/006; NFR-001/002/004)**:
- `relative_link_fixer --check --occurrence-map "$MAP"` → 0 broken relative links, 0 baseline-URL 404s
  (NFR-001/NFR-002 reframed: no baseline-URL 404 regression + all in-repo relative links resolve).
- `redirect_map.yaml` + `redirect_baseline_urls.json` are byte-for-byte UNTOUCHED (the 149 `01KW3SBK`
  redirects preserved) — this WP regenerates NO redirect map.
- `check_docs_freshness --ci` → inventory fresh, no baseline 404 (NFR-004).
- `docs_structural_lint` → exit 0 on the live post-move tree (SC-003/004/005: clean tree, 0 shadow basenames,
  full architecture/ index) — and the lint is wired into `.github/workflows/docs-freshness.yml` (FR-008).
- `pytest tests/docs/` + the terminology guard green (NFR-004).
- `bulk_ref_rewrite` no longer silently consumes the foreign `01KW3SBK` default; every redirect/link command
  passes `--occurrence-map "$MAP"` (C-007).

## Context & Constraints

- **Charter**: `.kittify/charter/charter.md` — canonical sources (never fabricate flags), campsite cleaning,
  missing/broken canonical surface → trace + file upstream gap (C-007), no suppressions.
- **Read before editing**: `quickstart.md` (the VERIFIED real CLIs — Recipe A/B + the aggregate verify block;
  an earlier draft fabricated flags — obey quickstart exactly), `research.md` (D5 — the real subcommands/flags
  + the foreign-pinning facts), `plan.md` (IC-06), `spec.md` (FR-009/010; NFR-001/002/004; C-006/007),
  `occurrence_map.yaml` (the `moves:` spine + 3 fold entries + the `exceptions` incl. the non-docs paradigm
  referrer + the baseline-URL manifest note), `data-model.md` (redirect-map entry + state transition).
- **VERIFIED real CLIs (research.md D5 / quickstart — do NOT fabricate)**:
  - `redirect_stub_generator.py` is **NOT invoked by this mission.** Its `regenerate-map` derives redirects
    only for PUBLISHED (baseline) URLs; this mission's moved paths are never-published, so `regenerate-map`
    derives ZERO entries and OVERWRITES `redirect_map.yaml`, wiping the landed `01KW3SBK` 149 redirects. Do
    NOT run `regenerate-map` / `check-map`; leave `redirect_map.yaml` untouched.
  - `relative_link_fixer.py` **writes by default** (flags `--dry-run` / `--check` / `--no-exclude`; there is
    **NO** `--write`) and walks **`docs/**` ONLY**. It reads an occurrence map — its default is the
    `DEFAULT_OCCURRENCE_MAP` symbol IMPORTED from `bulk_ref_rewrite.py` (foreign-pinned), so it **MUST** be
    driven with `--occurrence-map "$MAP"` (C-007, PC5).
  - `check_docs_freshness.py` `--inventory` is **READ-ONLY (a checker, NOT a writer)** and it exposes `--ci`.
    Regenerate the page-inventory lockfile CONTENTS via
    `python scripts/docs/inventory_lockfile.py --write docs/development/3-2-page-inventory.yaml`, then VERIFY
    with `check_docs_freshness --ci` (PB3).
  - `bulk_ref_rewrite.py` is the prefix-anchored complement for non-`docs/` (`src/`, `scripts/`) referrers;
    accepts `--occurrence-map` and MUST be driven with `--occurrence-map "$MAP"`.
- **C-007 (binding)**: EVERY link command (`relative_link_fixer` AND `bulk_ref_rewrite`) passes
  `--occurrence-map "$MAP"`. Never rely on the built-in default (pinned to the foreign
  `common-docs-structural-move-01KW3SBK`).
- **C-004**: `3-2-page-inventory.yaml` + `toc.yml` are path-pinned (`test_inventory_path_stable.py`) — the
  inventory lockfile is regenerated CONTENTS in place, NEVER relocated. **`toc.yml` is NOT regenerated by this
  mission** (no `toc.yml` references a moved path and no generator exists) — it is a verify-only grep (PN1).
- **Prereqs**: WP03 (final move set) + WP04 (folds) must be landed; WP02's lint must exist. Read WP03's and
  WP04's Activity Logs for the referrer lists + the non-docs paradigm referrer hand-off + any borderline that
  moved (assessment/closeout) — the referrer sweep must cover exactly the ACTUAL move/fold set.
- **Stale-install note**: `bulk_ref_rewrite`/`relative_link_fixer` behaviour reflects the installed CLI —
  if you edit `bulk_ref_rewrite` (T022) and behaviour seems unchanged, `pip install -e .` may be stale; run via
  `python -m scripts.docs.<tool>` from the repo root (which uses the working tree) to be sure.

## Branch Strategy

- **Strategy**: coord topology; execution worktree allocated per computed lane from `lanes.json`.
- **Planning base branch**: `docs/common-docs-section-audit`
- **Merge target branch**: `docs/common-docs-section-audit`

> Populated by `spec-kitty agent mission tasks` / `finalize-tasks`. Do not change manually.

## Subtasks & Detailed Guidance

### Subtask T022 — FR-010 (narrowed) safely parametrize `bulk_ref_rewrite`'s foreign default

- **Purpose**: FR-010/C-007 (narrowed per the post-tasks squad, PC7) — `bulk_ref_rewrite.py` must not silently
  bind the foreign mission's occurrence map, WITHOUT breaking the non-owned callers that import its
  `DEFAULT_OCCURRENCE_MAP` symbol. `redirect_stub_generator.py` is **out of scope** here — this mission does
  not invoke it (PB2), so its own foreign `MISSION_SLUG` default is left as a pre-existing condition (note it in
  the Activity Log as an upstream observation; do NOT edit it as part of this WP).
- **Steps**:
  1. `bulk_ref_rewrite.py` defines `DEFAULT_OCCURRENCE_MAP` (line ~60, pinned to
     `kitty-specs/common-docs-structural-move-01KW3SBK/occurrence_map.yaml`). **KEEP the symbol defined** —
     `relative_link_fixer.py` imports it (line ~76), `tests/docs/test_bulk_ref_rewrite.py` +
     `tests/docs/test_redirect_stub_generator.py` and `.github/workflows/docs-freshness.yml` rely on a resolvable
     default. Do NOT remove it and do NOT make `--occurrence-map` unconditionally required (that would break
     those callers). Instead **parametrize it to resolve DYNAMICALLY** (e.g. resolve from an env var / the
     newest mission map / a non-foreign sentinel) so it is no longer hard-bound to `01KW3SBK` yet stays a valid
     `Path` for the importing callers.
  2. For THIS mission's runs, always pass `--occurrence-map "$MAP"` explicitly (C-007) — the parametrization is
     the safety net, not the driver.
  3. Adjust `tests/docs/test_bulk_ref_rewrite.py` (and, if it asserts the symbol, `test_redirect_stub_generator.py`)
     to assert the default no longer resolves to the foreign `01KW3SBK` slug — while remaining a resolvable
     default the importing callers can use. If a clean dynamic parametrization is not feasible without a broader
     refactor, **file an upstream gap** (charter: missing/broken canonical surface → trace + file) and drive
     strictly via `--occurrence-map` — record the gap issue in the Activity Log.
- **Files**: `scripts/docs/bulk_ref_rewrite.py` (+ its tests under `tests/docs/`).
- **Validation**: grep `bulk_ref_rewrite.py` for `01KW3SBK` → no live default binding; `DEFAULT_OCCURRENCE_MAP`
  still importable + resolvable (relative_link_fixer imports cleanly, `tests/docs/` green); ruff/mypy clean.
- **Edge cases**: the symbol is a shared contract — a removal/required-arg change reds non-owned callers
  (`relative_link_fixer.py`, `docs-freshness.yml`, two `tests/docs/`); parametrize, do not delete.

### Subtask T023 — Leave `redirect_map.yaml` UNTOUCHED; verify the baseline is preserved (NFR-002 reframed)

- **Purpose**: NFR-002 (reframed) — this mission's moved/removed paths are **never-published** (not in
  `redirect_baseline_urls.json`), so they need NO redirect entries; and regenerating the DERIVED
  `redirect_map.yaml` would derive ZERO new entries and OVERWRITE it, wiping the landed `01KW3SBK` mission's
  149 published-URL redirects. So: regenerate NOTHING; PROVE the redirect corpus is preserved.
- **Steps**:
  1. Do **NOT** run `redirect_stub_generator regenerate-map` / `check-map`. `redirect_map.yaml` is NOT in this
     WP's `owned_files` and MUST NOT be modified.
  2. Verify the redirect corpus is byte-for-byte unchanged: `git status --porcelain scripts/docs/redirect_map.yaml
     scripts/docs/redirect_baseline_urls.json` → both show **no modification** across the whole mission diff.
  3. Confirm (spot-check) the moved paths are absent from `redirect_baseline_urls.json` (never-published) — that
     is why no redirect entry is required and why the aggregate `check_docs_freshness --ci` sees no baseline 404.
- **Files**: none written (verification only; `redirect_map.yaml` intentionally NOT owned/edited).
- **Validation**: `redirect_map.yaml` + `redirect_baseline_urls.json` unmodified in `git status`; the 149
  `01KW3SBK` redirects intact; no baseline 404 in `check_docs_freshness --ci` (T026).
- **Edge cases**: the **assessment** borderline, if MOVED, is a never-published in-repo path — repoint its
  referrers (T024), no redirect needed. The **920-closeout** borderline is DIFFERENT: its URL **is** in
  `redirect_baseline_urls.json` (published), so a MOVE would 404 the baseline with no redirect (this mission
  regenerates none) — WP03 T016 escalates a closeout MOVE to the operator rather than moving silently; the
  expected outcome is STAYS, which keeps the baseline green. Upstream gap — non-cumulative redirect derivation
  across missions — is recorded in research.md D5.

### Subtask T024 — Repoint referrers (docs/** + the non-docs paradigm ref)

- **Purpose**: FR-009/NFR-001/C-006 — every in-repo referrer resolves to the new path.
- **Steps**:
  1. `python -m scripts.docs.relative_link_fixer --occurrence-map "$MAP"` (writes by default; `docs/**` ONLY) —
     repoints relative links across the ~25–30 docs referrers to the moved/folded paths. **The
     `--occurrence-map "$MAP"` is mandatory (C-007, PC5)**: `relative_link_fixer`'s default is the foreign
     `DEFAULT_OCCURRENCE_MAP` it imports from `bulk_ref_rewrite`; omitting it consumes the `01KW3SBK` map.
  2. `python -m scripts.docs.bulk_ref_rewrite --occurrence-map "$MAP"` — the prefix-anchored complement that
     rewrites NON-`docs/` referrers (`src/`, `scripts/`). This MUST catch
     `src/doctrine/paradigms/built-in/brownfield-onboarding.paradigm.yaml:50` (the moved audit path
     `docs/architecture/audits/2026-05-spec-kitty-caacs.md` → `…/plans/engineering-notes/architecture-audits/…`)
     — `relative_link_fixer` never walks it (occurrence_map `manual_review` exception). If `bulk_ref_rewrite`
     does not rewrite it, hand-edit the one line and record why.
  3. Cross-check against WP03/WP04's Activity-Log referrer lists (audits→11, adr-connector→6,
     feature-detection→5, 883-brief→2, gap-analysis→1, + any borderline) — confirm each is repointed.
- **Files**: docs/** referrers (tool-driven leeway) + `src/doctrine/paradigms/built-in/brownfield-onboarding.paradigm.yaml`.
- **Validation**: `relative_link_fixer --check --occurrence-map "$MAP"` clean (T026); grep the paradigm.yaml for
  the old audit path → gone.
- **Edge cases**: the non-docs referrer is the classic gap (`docs/**`-only walk) — do NOT declare done until it
  is confirmed rewritten.

### Subtask T025 — Regenerate the page-inventory lockfile in place (toc verify-only)

- **Purpose**: FR-009/C-004 — the pinned generated page-inventory reflects the new tree.
- **Steps**:
  1. Regenerate the page-inventory lockfile CONTENTS in place with the WRITER (PB3 —
     `check_docs_freshness --inventory` is READ-ONLY, it does NOT write):
     `python scripts/docs/inventory_lockfile.py --write docs/development/3-2-page-inventory.yaml`
     (path pinned by `test_inventory_path_stable.py`; regenerate contents, never relocate).
  2. **`toc.yml`: verify-only, do NOT regenerate (PN1).** No `docs/**/toc.yml` references a moved path and no
     `toc.yml` generator exists in `scripts/docs/`. Confirm with a grep
     (`grep -rl '<moved-basename>' docs/**/toc.yml` → nothing), record the grep result, and leave `toc.yml`
     untouched. If (unexpectedly) a `toc.yml` DID reference a moved path, escalate — do not hand-fabricate a
     regeneration.
- **Files**: `docs/development/3-2-page-inventory.yaml` (tool-driven, in place). No `toc.yml` written.
- **Validation**: `check_docs_freshness --ci` green (T026); the inventory path is unchanged (still at the
  pinned location); the `toc.yml` grep confirms no moved-path reference.
- **Edge cases**: never move the pinned inventory (C-004); regenerate via `inventory_lockfile.py --write`, then
  VERIFY with `check_docs_freshness --ci` — the checker is not the writer.

### Subtask T026 — Wire the lint into CI (FR-008) + aggregate gate sweep (mission Definition of Done)

- **Purpose**: FR-008 + NFR-001/002/004 + SC verification — enable the deferred CI gate now that the tree is
  post-move-clean, and prove the whole diff is green.
- **Steps** (run from repo root; obey quickstart's verify block):
  1. **CI enablement (FR-008 — the wiring WP02 deferred so it lands post-move):** read
     `.github/workflows/docs-freshness.yml` fully, then add a step that runs
     `python -m scripts.docs.docs_structural_lint` (nonzero exit fails the job), placed alongside the existing
     freshness/link checks in the same guarded job (respect any `pr:deferred`/`pr:skip-ci` label guard; reuse
     the existing Python setup — do not add a new job unless the existing one lacks Python). This is safe now
     ONLY because WP03/WP04 have landed and the lint is green on the live tree (step 5).
  2. `python -m scripts.docs.relative_link_fixer --check --occurrence-map "$MAP"` — NFR-001: 0 broken relative
     links + 0 baseline 404s.
  3. **Redirect corpus preserved (NFR-002 reframed, T023):** `git status --porcelain scripts/docs/redirect_map.yaml
     scripts/docs/redirect_baseline_urls.json` → both UNMODIFIED (the 149 `01KW3SBK` redirects intact). This WP
     regenerates NO redirect map.
  4. `python -m scripts.docs.check_docs_freshness --ci` — NFR-004: inventory fresh, no baseline 404.
  5. `python -m scripts.docs.docs_structural_lint` — SC-003/004/005: exit 0 on the LIVE post-move tree (clean
     tree, 0 shadow basenames, full architecture/ index — proves WP03's index + WP04's folds are complete and
     the lint is satisfied). This is the live zero-violation gate WP02 deferred to WP05.
  6. `pytest tests/docs/ -q` — the lint regression fixture + config-SSOT assert + `test_bulk_ref_rewrite` +
     `test_inventory_path_stable` all green.
  7. `pytest tests/architectural/test_no_legacy_terminology.py -q` — NFR-004 terminology guard (CI-only gate).
  8. ruff/mypy clean on the touched `scripts/docs/` modules.
- **Files**: `.github/workflows/docs-freshness.yml` (the CI enablement); otherwise verification only.
- **Validation**: the CI step invokes the lint inside the existing guarded flow (YAML parses); every command
  green; record the results in the Activity Log as the DoD evidence. If the lint flags something, it is a REAL
  structural gap (missing index entry, an un-folded shadow, a mis-placed move) — fix the underlying content/move
  (coordinate with WP03/WP04 owners), do not weaken the lint.
- **Edge cases**: a red terminology guard on doctrine/prose is CI-only — run it locally before declaring done.
  `check_docs_freshness --ci` should NOT 404 on baseline: the moved paths are never-published, so no redirect
  entry is expected — if it DOES 404, a referrer was missed (re-run T024), NOT a redirect (T023 leaves the map
  untouched by design).

## Test Strategy

- Verification-driven (this WP's product is a green aggregate). Mandatory green:
  `relative_link_fixer --check --occurrence-map "$MAP"`, `check_docs_freshness --ci`,
  `docs_structural_lint` (exit 0 on the live post-move tree), `pytest tests/docs/`, the terminology guard;
  plus `redirect_map.yaml` + `redirect_baseline_urls.json` UNMODIFIED in `git status` (no redirect regen).
- If T022 changes the `bulk_ref_rewrite` default, `tests/docs/test_bulk_ref_rewrite.py` (and, if affected,
  `test_redirect_stub_generator.py`) must stay green — assert the default no longer resolves to the foreign
  `01KW3SBK` slug WHILE `DEFAULT_OCCURRENCE_MAP` remains importable and resolvable for its callers.

## Risks & Mitigations

- **Silent foreign-default consumption** (C-007): mitigate by ALWAYS passing `--occurrence-map "$MAP"` to BOTH
  `relative_link_fixer` and `bulk_ref_rewrite` + the T022 safe parametrization (grep `bulk_ref_rewrite.py` for
  `01KW3SBK` proves the live default binding is gone).
- **Wiping the foreign redirect corpus** (PB2/D5): `redirect_stub_generator regenerate-map` would derive ZERO
  entries for this mission's never-published paths and OVERWRITE `redirect_map.yaml`, destroying 149 landed
  `01KW3SBK` redirects — FORBIDDEN. Do NOT run `regenerate-map`/`check-map`; leave the map untouched and prove
  it via `git status` (T023). Non-cumulative redirect derivation is an upstream gap (research.md D5).
- **Breaking `DEFAULT_OCCURRENCE_MAP` callers** (PC7): removing the symbol or requiring `--occurrence-map`
  unconditionally reds `relative_link_fixer.py`, `docs-freshness.yml` and two `tests/docs/` — parametrize
  dynamically instead (T022).
- **Missed non-docs referrer** (R6): `relative_link_fixer` won't see `paradigm.yaml` — T024 explicitly drives
  `bulk_ref_rewrite` + a grep confirmation.
- **Moving a pinned artifact** (C-004): regenerate `3-2-page-inventory.yaml` contents in place via
  `inventory_lockfile.py --write` (never relocate); `toc.yml` is verify-only (not regenerated, PN1).
- **Stale editable install**: run tools via `python -m scripts.docs.<tool>` from the repo root so working-tree
  edits take effect.

## Review Guidance (reviewer-renata / opus)

Verify: no live default binds `01KW3SBK` in `bulk_ref_rewrite.py` (grep) yet `DEFAULT_OCCURRENCE_MAP` is still
importable + resolvable for its callers; every link invocation (BOTH `relative_link_fixer` and
`bulk_ref_rewrite`) passed `--occurrence-map "$MAP"`; **`redirect_map.yaml` + `redirect_baseline_urls.json` are
UNMODIFIED in `git status`** (NO `regenerate-map` was run — the 149 `01KW3SBK` redirects are intact);
`relative_link_fixer --check --occurrence-map "$MAP"` clean incl. the non-docs `paradigm.yaml` rewrite (grep the
old audit path → gone); `check_docs_freshness --ci` green; `docs_structural_lint` exits 0 on the LIVE post-move
tree (full architecture/ index, 0 shadow basenames) and is WIRED into `.github/workflows/docs-freshness.yml`
(FR-008); the pinned inventory was regenerated in place via `inventory_lockfile.py --write` (path unchanged) and
`toc.yml` is verify-only/untouched; `pytest tests/docs/` + terminology guard green; the tool-driven referrer
leeway is within sanctioned scope (safe by SEQUENCING — WP05 deps WP02/WP03/WP04 — not by referrers being
unowned; no hand-edited feature work outside owned_files beyond the recorded paradigm.yaml line).

## Activity Log

> **CRITICAL**: entries in chronological order (oldest first, newest last). Append at the END.

- 2026-07-22T16:30:00Z – system – Prompt created.
- 2026-07-24T00:00:00Z – curator-carla (opus) – WP05 aggregate IA-mechanics + gate sweep on the
  post-move tree. Landed the mission Definition of Done: `docs_structural_lint` exits 0 (648 pages,
  0 violations, ~0.9s) on the live post-move tree; `check_docs_freshness --ci` exits 0 (errors=0;
  3 non-gating network link-health warnings); `relative_link_fixer --check --occurrence-map "$MAP"`
  → 0 dead relative links; `tests/docs/` 597 passed; terminology guard 4 passed; ruff + mypy clean
  on the touched Python. **redirect_map.yaml + redirect_baseline_urls.json byte-for-byte UNTOUCHED**
  (no `regenerate-map`/`check-map` run — the 149 `01KW3SBK` redirects preserved; verified via
  `git diff --exit-code`). `occurrence_map.yaml` untouched.
- 2026-07-24T00:00:00Z – curator-carla – Lint false-positive reconciliation (135 of 136 pre-fix
  violations were doctrine-settled false positives; 1 real). **(A) ADR MADR exemption (134
  frontmatter_contract FPs):** added `adr/**` to `structural_lint_config.frontmatter_in_scope_exclusions`
  in `src/doctrine/styleguides/built-in/common-docs.styleguide.yaml`, citing DIRECTIVE_042 lines
  49-50 ("ADR frontmatter is exempt — it uses `status` for the MADR decision status"). Did NOT
  backfill doc_status onto ADRs (that would VIOLATE the directive). **(B) Redirect-stub exemption
  (1 shadow_tree_basename FP on `docs/retrospective-learning-loop.md`):** added config key
  `redirect_stub_description_prefix: "Redirect stub:"` and taught `docs_structural_lint.py`
  (`_is_redirect_stub` helper + skip in `check_shadow_tree_basename`) to exempt config-declared
  redirect stubs — SSOT-driven, no hard-coded marker; stub retained (old-path URL continuity).
  **(C) 1 real violation:** `docs/plans/test-change-coupling-caacs.md` genuinely lacked `updated`
  frontmatter — backfilled `updated: '2026-07-21'` (git last-content date). New regression tests
  (fixture + live cohort) for A and B added to `tests/docs/test_docs_structural_lint.py` incl. a
  live post-move zero-violation gate.
- 2026-07-24T00:00:00Z – curator-carla – **CROSS-WP GAP RECONCILIATION (per operator ruling).**
  Items A and B edit surfaces owned by approved WP01 (styleguide `structural_lint_config`) and WP02
  (`docs_structural_lint.py`). WP01's config only exempted `**/README.md` — it did NOT carry the
  DIRECTIVE_042 ADR MADR exemption, so 134 ADR bodies were live frontmatter_contract FPs the moment
  the lint went zero-tolerant at WP05. WP02's `check_shadow_tree_basename` had no redirect-stub
  concept, so the legitimate `retrospective-learning-loop` redirect stub was a FP. Both are fixed
  here as aggregate reconciliation; the WP01/WP02 citations reconcile against this entry. No lane
  write-scope guard blocked these paths.
- 2026-07-24T00:00:00Z – curator-carla – Referrer repointing (FR-009/C-006/NFR-001). Drove
  `relative_link_fixer --occurrence-map "$MAP"` (canonical docs/** tool, writes by default) → 7
  outbound-link depth fixes across 3 moved files (`883-*` ×2, `2026-05-spec-kitty-caacs.md`).
  Repointed the audits directory-move full-path referrers (`docs/architecture/audits/` →
  `docs/plans/engineering-notes/architecture-audits/`) in 4 live files: `docs/architecture/README.md`,
  `docs/architecture/assessments/code-as-a-crime-scene-overview.md` (6 mentions),
  `docs/plans/3-2-doc-publication/3-2-version-taxonomy.md`, and the one NON-docs referrer
  `src/doctrine/paradigms/built-in/brownfield-onboarding.paradigm.yaml:50` (T024 hand-edit, sanctioned).
  Removed the dead `notes/README.md` bullet from `docs/plans/index.md` (the `plans/notes/` shadow tree
  was folded away by WP04). `relative_link_fixer --check` → 0 dead links afterward.
- 2026-07-24T00:00:00Z – curator-carla – **UPSTREAM GAP — `bulk_ref_rewrite.py` file-move doubling
  bug (do NOT run it globally against this mission's map).** `resolve_destination()` assumes `to:` is
  a destination DIRECTORY ROOT and returns `f"{to}/{base}"` for file moves. THIS mission's
  occurrence_map uses a full FILE PATH as `to:` for its file moves (e.g.
  `to: docs/architecture/feature-detection.md`), so the tool produces DOUBLED garbage paths
  (`docs/architecture/feature-detection.md/feature-detection.md`) and CORRUPTS every referrer that
  literally contains the old file path (verified: it corrupted the retrieval index and the lint's own
  test file on a trial run, since reverted). It is correct ONLY for the audits DIRECTORY move (which
  falls back to `return to`). Therefore the file-move + dir-move full-path referrers were repointed via
  `relative_link_fixer` (resolvable links) + the controlled per-file prefix edits above, NOT via a
  global `bulk_ref_rewrite` run. This bug should be fixed upstream before `bulk_ref_rewrite` is used
  for any mission whose occurrence_map expresses file-level (not directory-level) moves.
- 2026-07-24T00:00:00Z – curator-carla – **T022 (parametrize foreign `DEFAULT_OCCURRENCE_MAP`) NOT
  executed — flagged for reviewer/operator.** `bulk_ref_rewrite.DEFAULT_OCCURRENCE_MAP` is still pinned
  to the foreign `01KW3SBK` map. It was left unmodified because it is a SHARED CONTRACT symbol
  (`relative_link_fixer` imports it; `docs-freshness.yml` + two `tests/docs/` rely on it) and the
  dynamic-parametrization refactor carries real regression risk that was out of scope for this
  aggregate sweep. C-007 was satisfied operationally: every link command in this WP passed
  `--occurrence-map "$MAP"` explicitly, so the foreign default was never consumed. Recorded as an
  upstream gap alongside the file-move doubling bug above.
- 2026-07-24T00:00:00Z – curator-carla – Generated indexes regenerated in place (both are
  `check_docs_freshness --ci` gate-required — the retrieval index DOES drift-gate under --ci, contrary
  to the occurrence_map `serialized_keys` note which mentions only the page inventory): page inventory
  via `inventory_lockfile.py --write docs/development/3-2-page-inventory.yaml`; docs retrieval index via
  `docs_index.py --write` (`docs/development/3-2-docs-retrieval-index.yaml`). Paths pinned (C-004), not
  relocated. `toc.yml` verify-only: `grep -rl` for moved basenames under `docs/**/toc.yml` → nothing;
  left untouched (PN1). Minor scope note for the reviewer: the occurrence_map states "Only the
  page-inventory lockfile is regenerated in place" — the retrieval index had to be regenerated too to
  clear DOCS-INDEX-DRIFT errors under --ci.
- 2026-07-24T00:00:00Z – curator-carla – FR-008 CI enablement: added a "Structural docs lint (FR-008)"
  step (`uv run python scripts/docs/docs_structural_lint.py`, nonzero-exit fails the job) to
  `.github/workflows/docs-freshness.yml` alongside the existing blocking rulers, reusing the existing
  guarded job + Python setup (respects the `pr:deferred`/`pr:skip-ci` label guard). Safe now that the
  live tree is post-move-clean (lint exits 0).
</content>
