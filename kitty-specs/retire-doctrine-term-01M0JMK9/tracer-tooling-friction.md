# Tracer: Tooling Friction — retire-doctrine-term

Seeded at planning (post-analyze, pre-implement). Append during implementation; assess at close per the
`mission-tracer-files` procedure (charter Standing Order #3).

## Friction log

- **Post-write teamspace sync hangs CLI writers when logged out.** `spec-kitty agent mission
  record-analysis` persisted and committed `analysis-report.md` correctly but then blocked past a
  2-minute tool timeout on `logged_out_on_connected_teamspace` sync. Read-only commands return in ~3 s.
  Workaround: wrap writer commands in `timeout` and verify the on-disk/commit result rather than the
  exit code.
- **Corpus round-trip test parametrisation.** `tests/contract/test_example_round_trip.py` ids are not
  selectable with `-k <mission-slug>`; run the whole file (≈30 cases) when checking mission contracts.
- **`finalize-tasks --validate-only` warns on planned-new owned globs** (WP01's ADR glob matches zero
  files before authoring). Expected; not actionable.
- **WP01:** `implement` claims and `mark-status` stall ~4 min after committing (dossier-sync hook waits on the
  stuck machine sync cutover); handled with `timeout` + on-disk verification. The canonical implement prompt
  never printed, so the WP prompt file + contracts were used directly as the brief.
- **WP01:** two ADRs already share sequence `2026-08-22-1`; took `2026-08-22-2` (UTC date of authoring).
- **WP01 cycle 2:** the docs description-length gate (50–180 chars, `scripts/docs/description_length_check.py`) was caught by review, not by the authoring checklist — add `tests/docs/test_docs_seo.py` to the ADR-authoring precheck.
- **WP02:** APFS normalises a `\xff` filename byte to UTF-8 `ÿ`, so the "non-UTF-8 path" fixture can only assert a
  non-ASCII byte on macOS; real non-UTF-8 names need a Linux runner. The contract's unreserved set excludes `/`,
  so TSV paths carry `%2F` — compliant and lossless, but worth knowing before eyeballing the file. Writer commands
  (`mark-status`) stall after writing on this machine (#3680); commits verified on disk.

## WP03 — methodology (planner-priti, 2026-08-23)

- No new tooling friction beyond #3680 (writer stall after commit); the WP is a single planning document. The
  mission-state table in `inventory.md` was sufficient to derive per-transition arithmetic without re-running the
  audit.

- WP04: no new friction beyond #3680 (writer stall after commit). The 17-field wave template is verbose for six
  waves; a schema-driven renderer (YAML wave spec → Markdown tables) would make WP05's field-completeness check
  mechanical instead of visual.

## WP05 — verification (reviewer-renata, 2026-08-23)

- Pre-review gate reports `no_coverage … No module named 'pytest'` because the global `spec-kitty` interpreter lacks
  pytest; the required suites were run with `.venv/bin/pytest` (855 passed). Every CLI call also prints
  `logged_out_on_connected_teamspace`; read-only commands still return.
- Writer commands that run the dossier hook stall ~4 min after committing (#3680); handled with `timeout` + on-disk
  verification, as in WP01–WP04.
- WP02–WP04 approvals exist only as status-event annotations — no `review-cycle-*.md` is written on approve-without-
  reject, so the reviewer had to read `status.events.jsonl` for their evidence; a `review-cycle` record on every
  verdict would make closeout verification file-based.
- `grep -rnE "\bX1\b"` style stale-conflict sweeps are noisy because every artifact restates the forbidden list as a
  negation; a canonical "rejections" phrasing (or a machine-readable forbidden-terms list) would make the sweep exact.

### Assess at close (mission-tracer-files procedure)

Unresolved items to carry into the tracker/backlog: (1) #3680 writer stall after commit (already filed);
(2) global CLI interpreter without pytest makes the pre-review coverage gate a false `no_coverage`; (3) approve-path
review records not materialised as `review-cycle-*.md`; (4) the ADR-authoring precheck should include
`tests/docs/test_docs_seo.py` (WP01 cycle-1 finding). None blocked the mission; all are tooling-gap inputs.

## Whole-mission squad fold (2026-08-23)

- **Approval events are note strings.** Every `in_review → approved` event is `actor: user` with a prose `reference` and
  no `review_ref`/`policy_metadata`; WP02–WP05 have no `review-cycle-*.md`. The reviewer identity exists only on the
  preceding `in_review` claim. Upstream gap: approvals should carry the claim's policy metadata and a `review_ref` to a
  record with a filled `reproduction_command`.
- **`acceptance-matrix.json` is a scaffold after `accept`.** `overall_verdict: pending` with TODO notes although
  acceptance was recorded; 95 of 237 missions look the same. Upstream gap: `spec-kitty accept` neither fills nor
  validates it.
- **Session-limit kills.** All four squad agents were terminated by the account session limit mid-run and resumed from
  saved progress after the reset; no artifact was lost (they are read-only), but a long squad should be dispatched with
  the limit window in mind.
- **`spec-kitty agent decision defer` requires `--rationale`** (not shown by the first `--help` pass); the open/defer
  pair is otherwise a clean way to hand an operator decision downstream.
