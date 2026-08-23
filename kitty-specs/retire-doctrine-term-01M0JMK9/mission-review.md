# Mission Review: `retire-doctrine-term-01M0JMK9` — Retire the Doctrine Term (mission 196)

**Reviewer**: reviewer-renata (post-merge mission review, `spec-kitty-mission-review` skill) · **Run**: 2026-08-23 ·
**Reviewed tree**: `feat/retire-doctrine-term` @ `e8b41e383` (0 behind / 94 ahead of `origin/main` `2621a56d06b9ae4e7da07ee206879c30a4d8b363`) ·
**Mission type**: planning-only (C-001) — deliverables are planning artifacts plus one ADR; no product code changed.

## Governance applied

- **Profile** `reviewer-renata` (builtin): initialization "quality gate, not an implementer"; avoidance boundary — no
  rewriting of the work, no product decisions; canonical verbs review/approve/reject/flag/assess; directive refs
  001, 024, 030, 032, 041, 051; tactics `code-review-incremental`, `reverse-speccing`, `language-driven-design`,
  `delete-the-assertion-not-the-test`, `supply-chain-install-safety`. Applied: every finding is stated with artifact +
  line/section and a severity; nothing in the mission was edited; this report is the only file written.
- **Charter context `--action review`** (compact): project directives DIR-001..DIR-013 loaded; the ones binding on this
  planning mission are DIR-005/DIR-030-family (tests/gates green on touched docs surfaces — verified via Gate 1/2 and
  the docs gates), DIR-008 (no secrets/credential handling — checked in the embedded audit script), DIR-009 (no breaking
  change shipped — none), DIR-013 (pre-existing red must be issue-tracked — no pre-existing red encountered). Org pack
  `spec-kitty-internal` present; tools git/pytest/ruff/mypy/spec-kitty.
- **Reviewer stance**: `reverse-speccing` — requirements were re-derived from the artifacts and cross-checked against
  the three governing decision moments rather than trusting WP05's verdict; arithmetic, hashes, and the override text
  were recomputed independently (see FR matrix and "Re-derivations" below).

## Gate Results

| Gate | Command | Result | Exit |
|---|---|---|---|
| 1 — contract | `PWHEADLESS=1 .venv/bin/pytest tests/contract/ -q -p no:cacheprovider -n auto --dist loadfile` | 297 passed, 5 skipped (27.3 s) | **0** |
| 2 — architectural | `PWHEADLESS=1 .venv/bin/pytest tests/architectural/ -q -p no:cacheprovider -n auto --dist loadfile` | 1679 passed, 5 skipped, 2 xfailed, 1 warning (4 m 31 s). The single warning is `tests/architectural/test_project_store_boundary.py:860` "project-store census shrank; keep the ratchet baseline unchanged" — a pre-existing ratchet advisory unrelated to this mission's diff (no `src/` file changed). | **0** |
| 3 — cross-repo E2E | `spec-kitty-end-to-end-testing` sibling checkout | **NOT RUN** — the sibling checkout does not exist next to this repo, and the mission changes no runtime code (diff outside `kitty-specs/retire-doctrine-term-01M0JMK9/` is four docs files). Recorded plainly as not executed; no exception artifact claimed. | — |
| 4 — issue matrix | `kitty-specs/retire-doctrine-term-01M0JMK9/issue-matrix.json` | One row `#2727`, verdict `deferred-with-followup` (in the allow-list `fixed | verified-already-fixed | deferred-with-followup | in-mission`, `src/specify_cli/cli/commands/agent/issue_verdict.py:297`); `evidence_ref` names the follow-up handle `#2727` (satisfies the `#\d+` / `Follow-up:` rule in `src/specify_cli/tasks/issue_matrix_migration.py:124-127`) and binds the glossary-authority slice into M1 via `stacked-plan.md` §2.4/§3.1. | **PASS** |
| supplemental — docs gates | `PWHEADLESS=1 .venv/bin/pytest tests/docs/test_description_length_gate.py tests/docs/test_docs_seo.py tests/architectural/test_no_legacy_terminology.py -q -p no:cacheprovider -n auto --dist loadfile` | 829 passed (17.9 s) | 0 |
| supplemental — ADR registration | `.venv/bin/python -m scripts.docs.freshen_adr_inventory --check` | `clean (missing_rows=0 inventory_stale=False)` | 0 |
| supplemental — inventory regenerate-and-match | `inventory.md` §8 script extracted to scratch (byte-identical to the gitignored working copy `inventory-audit.py`), run `--base 2621a56d… --mode inventory` into scratch | TSV SHA-256 `3631531b404cd379ce7b8d7a2dccb65cd7878f6cd65b95b922ae64d175013d2a` = pinned (`inventory.md` §1); 9,124,049 bytes; 49,050 rows = 48,328 content + 722 pathname; `--selftest` 8/8 PASS; `--mode terminal` on the frozen base reports `hits` (zero unreachable until M6, as designed). Scratch TSV/summary deleted after the check. | 0 / selftest 0 |

Known environment caveats (recorded, not mission defects, per the task brief and `verification-report.md` §7): writer
commands stalled post-commit on this machine (#3680) and were recovered by "persist … annotation (writer stalled before
commit)" commits; the pre-review gate reported `no_coverage` because the global CLI interpreter lacks pytest; `spec-kitty`
prints `logged_out_on_connected_teamspace` on every command (read-only commands still return).

## Orientation and review history

- `spec-kitty agent tasks status --mission retire-doctrine-term-01M0JMK9`: 5/5 WPs `done`, weighted readiness 100 %.
- `meta.json`: `mission_id 01M0JMK90CFFDKA4RCCTQK9675`, `mission_number 196`, `acceptance_mode pr`, `accept_commit
  1f9ed1805` (ancestor of HEAD), `baseline_merge_commit bf7e2012e` (ancestor of HEAD), `target_branch feat/retire-doctrine-term`.
- Event log (`status.events.jsonl`, 103 events): one `force: true` transition — WP01 `in_review → planned` by `user`
  ("Force move to planned", 22:20:14Z) = the cycle-1 rejection path (`tasks/WP01-adr-authoring-registration/review-cycle-1.md`:
  ADR frontmatter `description` 232 chars > 180-char gate); cycle 2 approved (`review-cycle-2.md`, description 175 chars,
  body byte-identical). WP02–WP05 approved first pass; approvals for WP02–WP04 exist only as status-event annotations (no
  `review-cycle-*.md`), which the verification report already lists as O-4. No arbiter events. All five `approved → done`
  transitions were emitted by `merge` at 00:39–00:40Z.
- **Profile-level self-review on WP05**: WP05 was implemented under profile `reviewer-renata` (per `tasks/WP05-…md`
  `agent_profile: reviewer-renata`, role implementer) and reviewed under the same profile (different shell PIDs, actor
  `user` on approval). WP05 is a verify-only WP, so this is tolerable, but structural independence is weaker than for
  WP01–WP04 (see R-6).

## Git timeline and coverage map (baseline `2621a56d0`)

- `git diff 2621a56d0..HEAD --stat -- . ':!kitty-specs/retire-doctrine-term-01M0JMK9'` → exactly four files, all
  planned: `docs/adr/3.x/2026-08-22-2-retire-doctrine-term-charter-is-the-canonical-vocabulary.md` (+278),
  `docs/adr/3.x/2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md` (+2, pointer note only),
  `docs/adr/3.x/index.md` (+1, generator row), `docs/development/3-2-page-inventory.yaml` (+6, generator entry).
  Nothing under `src/`, `tests/`, `packs/`, `.kittify/`, `scripts/`.
- `git diff 2621a56d0..HEAD --stat -- kitty-specs/ ':!kitty-specs/retire-doctrine-term-01M0JMK9'` → **empty** (historical
  missions untouched; `DM-01M0NMS9WPH33EPFCJQRTQVNSA` honoured at the git level).
- Owned-file coverage: every `owned_files` entry of WP01–WP05 has a diff (`implementation-baseline.json` +18,
  `docs/adr/3.x/index.md` +1, `3-2-page-inventory.yaml` +6, prior ADR +2, new ADR +278, `inventory.md` +803,
  `methodology.md` +247, `stacked-plan.md` +359, `verification-report.md` +135). `inventory-hits.tsv` (WP02 owned) is
  intentionally untracked via the mission-local `.gitignore` (`DM-01M0NMSD60JYG7K7V5MJCKJ3P8`). No owned file without a
  diff; no diff outside the owned/allowed set except the mission-runtime files listed under Drift D-2/D-3.
- C-001 probe: `scripts/audit_retired_term_zero.py`, `scripts/migrate_charter_interview_answers.py`,
  `.kittify/charter-packs/`, `docs/context/charter.md` all absent at HEAD; `docs/context/doctrine.md` and the ADR
  filename unchanged — no premature M1/M5 rename.

## FR Coverage Matrix

Status legend: ADEQUATE / PARTIAL / MISSING. "Evidence" names what constrains the requirement in the absence of product code.

| Req | Owner WP | Realising artifact (section/line) | Evidence that constrains it | Status |
|---|---|---|---|---|
| FR-001 ADR records decision, override, I1 effectiveness, exact I6 audits | WP01 | ADR `2026-08-22-2-…md` L55-66 (Decision Outcome, I1 effective), L78-88 (override), L201-223 (guard and exact terminal audit) | Override blockquote byte-identical to `contracts/adr-content-contract.md` §3 L33-38 (6 quoted lines, programmatic compare = True); ADR contains `:(exclude)kitty-specs/`, `git ls-tree -r -z --name-only`, `bytes((100,111,99,116,114,105,110,101))`, exit 0/1/2 semantics, check marker `terminology-zero-current-tree` | ADEQUATE |
| FR-002 ADR defines Charter Pack/Bundle/Active/Inactive + surviving kinds | WP01 | ADR L68-76 | Matches contract §2 L19-27 item-for-item | ADEQUATE |
| FR-003 M1 atomic glossary + complete Charter authority graph through owning workflows | WP01 (ADR) + WP04 (binding) | ADR L131-167 (9-row per-artifact owner map + glossary transaction); `stacked-plan.md` §3.1 L286-309; `issue-matrix.json` #2727 | Owner map semantically identical to contract §6 L86-122 (9/9 rows incl. `graph.yml` zero-consumer deletion, `charter sync` non-writer, five named answers-migration tests); zero-consumer claim spot-checked: no `graph.yml` reference in `src/**/*.py` or `scripts/**/*.py` at HEAD | ADEQUATE |
| FR-004 every hit outside fixed `kitty-specs/` root in scope | WP01/WP02 | ADR L90-106 scope table + L105-106; `inventory.md` §5 L166-174 | Regenerated TSV: 0 rows under `kitty-specs/`, 0 rows lacking `OC-##`, 0 X/exempt values, mandatory surfaces present (`src/doctrine/**`, `tests/**`, `.github/workflows/**`, `.kittify/charter/**`, `docs/adr/**`, `docs/reports/**`, generated manifests) | ADEQUATE |
| FR-005 3.x aliases temporary; 4.0 zero | WP01 | ADR L55-60, L190-199, L203-223; `methodology.md` §2.2 L110-123 | CR-01..08 each `removal M6`; `stacked-plan.md` §2.2 L236-248 removal list M6 {CR-01…CR-08} | ADEQUATE |
| FR-006 manifest set-equal to both audits, proven by regeneration against recorded hash | WP02 | `inventory.md` §1 L5-29, §8 script L202-803 | **Re-derived**: regeneration at base `2621a56d…` → SHA-256 `3631531b…` match, 49,050 rows, content stdout SHA `9bc3f415…` / pathname stdout SHA `0b2f3b78…` recorded; selftest 8/8 incl. `independent_hash_recompute_all_rows` (49,050) and `fixture_two_process_byte_identical` | ADEQUATE |
| FR-007 every hit exactly one M1–M6 owner; no X/terminal exemption | WP02/WP04 | `inventory.md` §3 L67-130 (44 populated OCs, default owners); `stacked-plan.md` §2.1 L174-227, §2.3 L250-266 | **Re-derived from TSV**: 44 populated OCs, partition by default owner = M1 304 · M2 13,259 · M3 111 · M4 647 · M5 34,729 · M6 0 = 49,050; hand-summed from §3 rows: M1 221+80+2+1; M2 633+40+56+48+815+1,657+54+312+413+110+641+1,566+6,076+173+51+67+181+332+30+4; M3 55+42+14; M4 171+51+253+12+75+83+2; M5 611+815+27,990+2,960+1,660+284+320+14+72+3 — all agree; every §2.1 owner = inventory default (DD-010) | ADEQUATE |
| FR-008 methodology: M1→M6, I0→I6, guards, rollback, exact zero gate | WP03 | `methodology.md` §1.1-1.4 L17-95, §2 L97-130, §3.4 L173-190, §4.3 L223-232 | I0–I6 table byte-identical to `data-model.md` §6 L114-124; ten named guard mutations §2.1 L107; arithmetic §1.2 L38 recomputed = 49,050 | ADEQUATE |
| FR-009 stacked plan: deterministic inputs/outputs/deps/ownership/tests/gates/rollback | WP04 | `stacked-plan.md` §1 L38-170 (M1–M6), §2.4 L268-282 | Each wave entry carries the 17 schema fields of `contracts/stacked-plan-schema.md` L19-21 (counted: 17/17 for M1–M5; M6 verified by inspection L152-170); slugs equal the schema's fixed stack L8-15; every wave `change_mode: bulk_edit` | ADEQUATE |
| FR-010 M1 zero decisions; M2 single bounded topology gate | WP04 | `stacked-plan.md` §3.1 L286-309 (`local_design_questions = 0`), §3.2 L311-332 (1 bounded pre-edit) | M1 dry run maps every Charter artifact to one fixed action or verified no-op; M2 gate "cannot change scope, order, or the terminal zero rule" (L330-332); M3–M6 `local_design_questions = 0` (L104, L126, L148, L170) | ADEQUATE |
| FR-011 fixed vocabulary, seams, ID mappings, root destination, zero-audit method recorded | WP01 | ADR L68-76, L108-129, L201-223 | Seven-ID table + `doctrine-daphne`→`charter-daphne` + `018-…` mapping identical to contract §5 L61-80; `.kittify/charter-packs/` root; `charter:<kind>:<id>` URN | ADEQUATE |
| NFR-001 frozen-base inventory reproducible, byte-safe, per-hit, set-equal; terminal evidence binds one commit/tree | WP02 | `inventory.md` §1 (tree OID `26e6fdd2…`), §7 selftests; `contracts/inventory-schema.md` L77-103 (`match_sha256` preimage) | Regeneration byte-identical (above); hostile-path fixture (colon+tab, non-UTF-8, mixed case, archived file) PASS; terminal attestation design binds commit+tree (ADR L215-221) | ADEQUATE |
| NFR-002 ADR self-sufficient without chat context | WP01 | ADR whole; `quickstart.md` §3 eight questions L26-43 | All eight answerable from ADR text alone (vocabulary L68-76; scope L90-106; override L78-88; M1 graph L131-167; M2 L171-177; M3/M4 L178-185; M5 + two exclusions L62-66, L186-189; M6 L190-223); the ADR cites the three DMs and the contracts directory as its technical story (L17-20) | ADEQUATE |
| NFR-003 100 % hits one owner; 100 % missions complete contracts; zero unresolved cross-wave inputs | WP04 | `stacked-plan.md` §2.1, §2.3, §1, §2.4 | Partition re-derived (49,050/49,050); 17/17 fields per wave; §2.4 eight joins each with a handoff gate; `issue-matrix.json` #2727 bound not deferred | ADEQUATE |
| C-001 planning/docs only | all | git diff (above) | Four docs files + mission dir only; downstream artefacts absent at HEAD | ADEQUATE |
| C-002 ADR registration via canonical freshen workflow | WP01 | `docs/adr/3.x/index.md` +1, `3-2-page-inventory.yaml` +6 | `freshen_adr_inventory --check` clean rc 0; both diffs are generator-shaped rows | ADEQUATE |
| C-003 override scope: current-tree history outside `kitty-specs/` mutable; two fixed exclusions | WP01/WP02 | ADR L62-66, L78-88, L101-102; `research.md` R2/R10; `contracts/README.md` item 1, 6 | Drift grep (below) finds no surviving "only Git object history"/"all of HEAD" claim outside the DM ledger and the dated `reasons-canvas.md` log (O-1, already amended in `250c76732`) | ADEQUATE |
| C-004 no baseline/allowlist survives I6 | WP03 | `methodology.md` §2.1 "Deletion" L108, §3.4 L175-179; `stacked-plan.md` M6 L158-166 | M6 `removes_compatibility` = all eight CRs; guard baseline store deleted; "no exception question" | ADEQUATE |
| C-005 non-public executable topology in scope (M2) | WP01/WP02/WP04 | ADR L97-98, L171-177; `inventory.md` OC-14..OC-24, OC-42..44; `contracts/operator-surface-map-schema.md` L7-8 | 12,189 S7 rows + 295 S9 + 633 S1 + 40 S10 all owned by M2; `src/doctrine/**` (OC-16 815 + OC-42 181) and `src/charter/**` consumers (OC-17 1,657) mapped | ADEQUATE |
| SC-001 independent reviewer confirms ADR self-sufficiency + explicit override | WP05 (+ this review) | `verification-report.md` §1.15; this review NFR-002 row | Confirmed independently here (override quote byte-identical; eight questions answered) | ADEQUATE |
| SC-002 regenerated inventory set-equal, hash match, no unclassified/excluded rows outside fixed root | WP02/WP05 | `inventory.md` §1; `verification-report.md` §2 | Re-derived here (hash, counts, 0 X rows, 0 `kitty-specs/` rows) | ADEQUATE |
| SC-003 every hit once; every CR one introduction + M6 removal | WP04 | `stacked-plan.md` §2.1-2.3 | Re-derived partition; CR-01..08 source counts from TSV (2/104/56/50/105/31/18/365 = 731 annotated rows) match `inventory.md` §4 and `stacked-plan.md` §2.2; introduction wave = source-OC owner for all eight | ADEQUATE |
| SC-004 M1 zero decisions; M2 bounded pre-edit gate; I6 = both exact audits + no exception machinery | WP04/WP05 | `stacked-plan.md` §3; M6 entry L150-170 | As FR-010 + C-004 | ADEQUATE |

**Totals**: 23 requirements traced — **23 ADEQUATE, 0 PARTIAL, 0 MISSING**. No punted FR.

### Re-derivations performed by this review (not trusted from WP05)

1. Wave partition 304 / 13,259 / 111 / 647 / 34,729 / 0 = 49,050 — hand-summed from `inventory.md` §3 rows and
   recomputed from the regenerated TSV by `occurrence_class_id` → default owner; identical to `stacked-plan.md` §2.3 and
   `methodology.md` §1.2.
2. ADR contains the contract §3 override quote verbatim (6/6 blockquote lines equal) and the fixed `kitty-specs/`
   pathspec/drop.
3. `freshen_adr_inventory --check` clean (rc 0).
4. End-to-end regeneration of `inventory-hits.tsv` from the `inventory.md` §8 script at base `2621a56d…` into the
   scratchpad → SHA-256 `3631531b…` match; scratch TSV deleted afterwards.

## Drift Findings

| ID | Severity | Finding | Where |
|---|---|---|---|
| D-1 | LOW (hygiene) | `acceptance-matrix.json` was committed as an unfilled scaffold (`overall_verdict: "pending"`, 12 `pending` criteria, 11 `TODO: replace with a real acceptance criterion` notes) although acceptance was recorded (`meta.json` `accept_commit 1f9ed1805`). The real acceptance evidence lives in `verification-report.md` (SC-001..SC-004 PASS). Not a spec drift, but the accept step left a placeholder artifact in the mission dir. | `kitty-specs/retire-doctrine-term-01M0JMK9/acceptance-matrix.json` (commit `cd9894165`) |
| D-2 | INFO (pre-existing tooling pattern) | A nested dossier snapshot `kitty-specs/retire-doctrine-term-01M0JMK9/.kittify/dossiers/retire-doctrine-term-01M0JMK9/snapshot-latest.json` (+542) is committed inside the mission directory by the "Add tasks …" commits. The same nested `.kittify/dossiers/` pattern exists in ≥10 earlier missions (e.g. `kitty-specs/062-…`, `063-…`, `077-…`), so it is an upstream dossier-root behaviour, not this mission's defect. Flagged for an upstream gap (dossier root resolving relative to the mission dir). | mission dir; `git ls-files | grep dossiers/` |
| D-3 | INFO | Untracked working copies `inventory-audit.py`, `inventory-summary.json`, `inventory-hits.tsv` and `__pycache__/` sit in the mission dir; the first three are ignored by the mission-local `.gitignore` (per `DM-01M0NMSD60JYG7K7V5MJCKJ3P8`), `__pycache__/` by the root `.gitignore`. The embedded §8 script is byte-identical to the working copy, so the committed `inventory.md` remains the single source. | `kitty-specs/retire-doctrine-term-01M0JMK9/.gitignore` |
| D-4 | INFO | Locked-decision consistency: grep for `sole/only exclusion`, `all of HEAD`, `only Git object history`, `X1/X2/X3`, `user-visible only`, `rewrites this planning mission`, `managed-path ledger` across spec/plan/research/data-model/contracts/WPs/inventory/methodology/stacked-plan/verification/ADR — every hit is a negation, rejection, or forbidden-list restatement. The only positive-form occurrence is the dated 2026-08-22 log bullet in `reasons-canvas.md` L80-81, immediately amended by the `DM-01M0NMS9…` parenthetical (folded in `250c76732`; WP05 O-1). Acceptable as a chronological deviation log. | `reasons-canvas.md` L79-82 |
| D-5 | INFO | WP02's `for_review` note says "45 OCs"; populated classes are 44 (OC-05 and OC-50 are declared zero-row placeholders per `stacked-plan.md` §2.1 L177 and `methodology.md` §1.2 L39). Already recorded as WP05 O-2; no deliverable is inconsistent. | `status.events.jsonl` 22:57:35Z |
| D-6 | INFO | M5 archive-referrer re-cite rule is present and consistent in `research.md` R10 L131-135, `stacked-plan.md` §0 L28-29 and M5 L148, `methodology.md` §1.3(5) L73-74 and §3.3 M5 row, ADR scope table L101 and contract §4 L54. `stacked-plan.md` §0 archive gate (L25-29) and `methodology.md` §3.5 (L192-199) agree after the O-3 fold (executable form; methodology adds the planning-mission-only exception for this mission's own WP outputs). | as cited |
| D-7 | INFO | Non-goal/constraint invasion: none. No renames executed; no runtime managed-path ledger introduced (explicitly rejected `methodology.md` §4.4, ADR L182, L275); historical `kitty-specs/` diff empty; ADR filename and `docs/context/doctrine.md` untouched (M5/M1 work). | git diff |
| D-8 | INFO (pre-existing) | Two ADRs already share the `2026-08-22-1-` prefix on the baseline (`…-performance-test-pipeline.md`, `…-canonical-mission-type-reader-legacy-retirement.md`); the new ADR correctly took `-2`. The baseline collision is not this mission's. | `docs/adr/3.x/` at `2621a56d0` |

## Risk Findings (holes a downstream M1–M6 implementer would hit)

| ID | Severity | Risk | Where / suggested handling |
|---|---|---|---|
| R-1 | MEDIUM | **Archive gate wording vs concurrent missions.** `stacked-plan.md` §0 L26-27 and the M5 `merge_gate` L144 say `git diff --stat <base> <result> -- kitty-specs/` may show "only the wave's own newly created mission directory". Any unrelated mission landing on `main` between a wave's base and its result adds other `kitty-specs/<slug>/` paths, which would trip the gate as phrased. The invariant that matters is the first clause ("no pre-existing path edited/renamed/deleted"); the "only additions from this wave" clause should be restated as "no pre-existing path changed; additions are whole new mission directories" or the gate must diff against the wave's merge-base on the result branch. | `stacked-plan.md` §0 L25-29, M5 L144; `methodology.md` §3.5 L192-199 |
| R-2 | MEDIUM | **M2 is very large and single-gated.** M2 owns 13,259 rows (6,076 in `tests/**`, 1,657 in `src/charter/**` consumers, 815 in `src/doctrine/**` code) plus 181+332+30+4 pathnames, with one pre-edit topology-map approval and "no two waves run in parallel" (`methodology.md` §1.1). `src/charter/` already exists with 95 files carrying hits, so every collision disposition must be frozen before the first edit. The plan allows dependency-slice editing but no intra-wave sub-missions; a downstream planner should expect to split M2's WPs by dependency slice with closure checks per slice, exactly as §3.2 step 6 implies. | `stacked-plan.md` M2 L62-82, §3.2 L311-332 |
| R-3 | LOW–MEDIUM | **Regenerate-and-match depends on git output stability, and the git version is not pinned.** SC-002/FR-006 rest on byte-identical `git grep -a -i -n -o --column --full-name -z` and `git ls-tree -r -z --name-only` stdout. `inventory.md` §1 records argv, rc and stdout hashes but not `git --version` (this review ran git 2.52.0). A future git release changing `--column`/`-o` record formatting would break the hash match without any tree change. Suggest recording `git --version` alongside the hashes in each wave's `occurrence_map`, and treating a mismatch with unchanged raw-output hashes as a tooling, not evidence, failure. | `inventory.md` §1 L5-29; `methodology.md` §4.1 L203-210 |
| R-4 | LOW | **Embedded WP02 script carries the literal token** in rule descriptions/predicates (e.g. L213, L224, L306-340 of the extracted script). It lives under the excluded `kitty-specs/` root so it never trips I6, but M6's `scripts/audit_retired_term_zero.py` cannot lift those rule tables verbatim; it must be token-literal-free (ADR L215-223). The wave-local audits in M1–M5 that reuse the §8 script (`stacked-plan.md` §0 L21) are fine because the script is read from `kitty-specs/`. | `inventory.md` §8; ADR L215 |
| R-5 | LOW | **OC-30 evidence JSON is test-consumed.** `docs/reports/test-sanitation/**` (27,990 rows, M5-owned) is referenced by `tests/architectural/test_marker_job_completeness.py`; M5's rewrite/regeneration of those census files must keep that architectural test's expectations (the referrer's own token rows, if any, are OC-24/M2). Cross-wave coupling worth naming in M5's `inputs`. | `inventory.md` OC-30 L100; `stacked-plan.md` M5 L136 |
| R-6 | LOW | **WP05 self-review at profile level** (implemented and reviewed as `reviewer-renata`). Verify-only WP, approvals by `user`; acceptable, but downstream waves should keep the implementer and reviewer profiles distinct (the charter's adversarial-squad / review cadence). | `status.events.jsonl` 23:55–00:33Z |
| R-7 | LOW | **`CLAUDE.md` is a symlink to `AGENTS.md`** (`120000` mode); the inventory therefore counts AGENTS.md only (OC-35, 14 rows). `AGENTS.md:509` cites archive mission slug `doctrine-silence-guards-01KYFV7Q` — an M5 re-cite case (`mission_id`/mid8 or token-free path). Inventory and plan already cover it (OC-35 → M5), recorded here so M5 does not treat CLAUDE.md as a second file. | `AGENTS.md` L509 |
| R-8 | LOW | **CI check-marker wiring is forward-named only.** `terminology-zero-current-tree` has no workflow today; M6 owns "CI/release gate wiring for the check marker" (`stacked-plan.md` M6 L164) — adequate ownership, but the release publish gate is not named to a file (`.github/workflows/release.yml` is the obvious host). | `stacked-plan.md` M6 L164-166 |
| R-9 | LOW | **Answers-migration script design is fixed by behaviour, not by code.** M1 "zero decisions" assumes `scripts/migrate_charter_interview_answers.py` and the five named tests can be written purely from the contract (§6 L95, L113-122). Execution detail (coordinate freezing over the live `answers.yaml`) is left to M1, which is execution not decision; flagged so M1 does not reopen it as a design question. | ADR L141, L151-159 |

## Silent Failure Candidates

N/A for product code — the mission ships no runtime code. For the evidence tooling: the embedded audit script fails closed
(`AuditError` → exit 2) on grep rc >1, rc/stdout inconsistency, non-NUL framing, missing revision prefix, a path under
the excluded root, and non-token matches (script L70-135); the `mutation_git_audit_failure_cannot_pass_zero` and
`test_content_audit_rejects_git_rc_gt1` selftests PASS (8/8). One soft spot: `--mode terminal` prints `"result": "hits"`
/ exit 1 on the frozen base but the script does **not** accept the M6 command identity `--json -`
(`usage: … error: unrecognized arguments: --json -`); that interface belongs to the future
`scripts/audit_retired_term_zero.py` (ADR L215-217), so no silent failure today, but M6 must not assume the WP02 script
is the terminal entrypoint.

## Security Notes

- Embedded audit script (`inventory.md` §8): git invoked via `subprocess.run(argv_list, stdout=PIPE, stderr=PIPE,
  check=False)` — list argv, no `shell=True`, no `os.system`/`popen` (script L53-58, L424); token built as
  `bytes((100,111,99,116,114,105,110,101))` (L28); stderr passed through unchanged; fail-closed on every rc/format
  inconsistency. Writes only to operator-supplied `--out`/`--summary` paths (default mission dir = excluded root), `--out`
  written as `.tmp` + `os.replace` (no fsync — acceptable for ephemeral evidence); never writes into the audited tree by
  default; selftest uses `tempfile` repos. `--git` accepts an arbitrary executable path (used by the mutation selftest) —
  local dev tool, not a CI entrypoint; the planned M6 entrypoint should not expose that option.
- `implementation-baseline.json`: well-formed, target tip + implementation base + ancestry flag + capture commands; no
  secrets. Atomic-write mechanics cannot be re-verified post hoc; the file content is consistent with `git merge-base`
  ancestry (re-checked: `2621a56d0`, `00b7eb06e`, `1f9ed1805`, `bf7e2012e` are all ancestors of HEAD).
- No credentials, tokens, or external endpoints in any changed file; no loopback/HTTP changes.

## Final Verdict

**PASS WITH NOTES.**

Rationale: every FR/NFR/C/SC traces to an artifact with independent evidence (23/23 ADEQUATE); the three governing
decision moments are honoured consistently across spec, plan, research, data model, contracts, WPs, methodology,
stacked plan and ADR; the diff is exactly the planning set (four docs files + the mission directory; historical
`kitty-specs/` untouched; no premature rename); Gates 1, 2 and 4 pass (exit 0 / 0 / PASS), Gate 3 is plainly NOT RUN
for the stated reason; the inventory regenerates byte-identically from the committed script; `freshen_adr_inventory
--check` is clean. The notes are (i) the unfilled `acceptance-matrix.json` scaffold (D-1, hygiene), (ii) the archive-gate
wording that would trip on concurrent unrelated missions (R-1, fix in the M1 wave's planning before adoption), and
(iii) the unpinned git version behind regenerate-and-match (R-3). None blocks the planning mission's release.

## Open items

1. D-1 — fill or explicitly retire `acceptance-matrix.json` (operator decision: keep as scaffold, or populate from
   `verification-report.md` SC rows). Also worth an upstream note: the `accept` step does not populate the matrix.
2. R-1 — before M1 is specified, restate the archive gate in `stacked-plan.md` §0 / M5 `merge_gate` and
   `methodology.md` §3.5 as "no pre-existing `kitty-specs/` path changed; additions are whole new mission directories",
   or diff against the wave's own merge-base.
3. R-3 — record `git --version` in every wave's `occurrence_map` (and retroactively in `inventory.md` §1).
4. D-2 — file the upstream gap for nested `.kittify/dossiers/` snapshots inside mission directories (pre-existing).
5. R-5 — add `tests/architectural/test_marker_job_completeness.py` to M5's named inputs/consumers of OC-30.
6. Process: keep implementer and reviewer profiles distinct in downstream waves (R-6); WP02–WP04 approvals are
   event-log annotations only (O-4) — acceptable here, but `review-cycle-*.md` records are the stronger audit trail.

## Retrospective Reminder

`kitty-specs/retire-doctrine-term-01M0JMK9/retrospective.yaml` **exists** (4,764 bytes; `schema_version: 1`,
`created_at 2026-08-23T00:40:15Z`, `created_by spec-kitty-generator`, `provenance.kind runtime_post_completion`, commit
`e8b41e383`). The retrospective was captured post-merge; no further action required for this review.

## Post-squad amendment (2026-08-23)

After this review's PASS WITH NOTES verdict, the whole-mission adversarial squad folded convergent findings
(`squad-findings-whole-mission.md`): R-1 (archive gate) is now a merge-base-scoped `--name-status` test; R-3 (`git
--version`) is recorded in every attestation; R-4 (entrypoint interface / commit-OID binding) is fixed in the contract;
R-5 (`test_marker_job_completeness.py`) is an M5 input; the terminal contract additionally requires toplevel-only
execution with a `:(top)`-anchored pathspec (a cwd-relative run produced a false zero on the real repository), symlink
target and NFKC/format-character passes; the guard is tree-independent; ownership was re-derived by live seam (OC-03 and
OC-41 → M2, CR-07 introduced by M2, CR-01/CR-04/CR-05 re-sourced), so the wave sums are 302 / 13,344 / 111 / 564 /
34,729 / 0 (this review's 304 / 13,259 / 111 / 647 figures are the pre-fold partition of the unchanged TSV). R-6
(independence): the squad's anti-laziness lens confirms implementer and reviewer were distinct agents per WP but notes
that approvals are recorded as `actor: user` notes without `review_ref` — filed as an upstream gap. One operator
decision was deferred in the ledger (`DM-01M0P6C8C7Q6SPBT412V39RPN0`, serialized historical records → M5). Verdict
unchanged: PASS WITH NOTES, with the notes above now folded or tracked.
