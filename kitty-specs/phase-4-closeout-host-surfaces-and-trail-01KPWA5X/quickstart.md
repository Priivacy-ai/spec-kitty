# Quickstart: Phase 4 Closeout — Operator Walkthrough

**Mission**: `phase-4-closeout-host-surfaces-and-trail-01KPWA5X`
**Audience**: operators and reviewers verifying Tranche A + Tranche B behaviour after merge.

This walkthrough exercises every user-visible behaviour this mission ships. Each section names the FR and SC that it validates.

## Prerequisites

- Clean checkout of the branch that merged this mission.
- Python environment active (`source .venv/bin/activate` or equivalent).
- No SaaS auth token set (we will toggle auth on in one optional step only).
- `spec-kitty` installed from this checkout.

## 1. Host-surface parity (Tranche A) — FR-001, FR-002, SC-001

### 1.1 Read the promoted matrix

```bash
less docs/host-surface-parity.md
```

Expected:

- One row per supported host surface (15 total: 13 slash-command + 2 Agent Skills).
- Every row has a `parity_status` of `at_parity`, `partial`, or `missing`.
- Every non-`at_parity` row has a `notes` column explaining the gap and remediation plan.

### 1.2 Spot-check one surface for inline parity content

Open one surface that the matrix marks `at_parity` with `guidance_style=inline` (e.g. `.agents/skills/spec-kitty.advise/SKILL.md`) and confirm it has all three sections:

- "Governance context injection" (how to inject `governance_context_text`).
- "Discover profiles / Get governance context" (advise/ask/do usage).
- "Close the record" (how to call `profile-invocation complete`).

### 1.3 Spot-check one surface for pointer parity

Open one surface marked `at_parity` with `guidance_style=pointer`. Confirm it contains an explicit pointer to the canonical skill pack (e.g. "For the canonical advise/ask/do contract, see `.agents/skills/spec-kitty.advise/SKILL.md`.").

## 2. Dashboard wording (Tranche A) — FR-003, FR-004, SC-002

### 2.1 Start the dashboard

```bash
spec-kitty dashboard
```

### 2.2 Verify user-visible wording

Open the dashboard in a browser. Confirm:

- Mission selector label reads **Mission Run:**, not `Feature:`.
- Mission header reads **Mission Run: <name>**, not `Feature: <name>`.
- "Mission Run Overview" heading appears where "Feature Overview" used to.
- "Mission Run Analysis" heading appears where "Feature Analysis" used to.
- Empty state reads "Create your first mission…" and "…run `/spec-kitty.specify` to create your first mission run".
- Unknown-mission fallback label reads "Unknown mission", not "Unknown feature".
- Diagnostics page: the active-mission diagnostic row reads "no mission context" when no mission is selected.

### 2.3 Verify backend identifiers are preserved (FR-004, C-007)

From DevTools → Elements panel:

- The selector `<select>` still has id `feature-select` (unchanged).
- The selector container still has id `feature-selector-container`.
- CSS class `.feature-selector` still applies.

From DevTools → Application → Cookies:

- `lastFeature` cookie is still set on selection (no cookie migration).

From DevTools → Network:

- API routes retain `/api/kanban/<feature>` and `/api/artifact/<feature>/<name>` shape.
- JSON responses retain `feature_id`, `feature_number`, `current_feature` field names.

## 3. Mode of work is derived at the CLI (Tranche B) — FR-008

### 3.1 Open an advisory invocation

```bash
spec-kitty advise "how should I split this refactor" --json
```

### 3.2 Inspect the trail

```bash
# Grab the invocation_id from the JSON output; call it $ID.
head -n 1 .kittify/events/profile-invocations/$ID.jsonl | python -m json.tool
```

Expected: `mode_of_work` field is `"advisory"`.

### 3.3 Repeat for task execution

```bash
spec-kitty do "add a README badge" --json
# ... inspect: mode_of_work should be "task_execution"
```

### 3.4 Repeat for query

```bash
spec-kitty profiles list --json
# No invocation is opened — profiles list is a query with no InvocationRecord.
spec-kitty invocations list --limit 3 --json
# Same — query, no InvocationRecord opened.
```

Confirmed: query commands do not open invocation records.

## 4. Correlation links (Tranche B) — FR-007, SC-003

### 4.1 Close a task-execution invocation with two artifacts and one commit

```bash
# Start a task-execution invocation:
spec-kitty ask implementer "implement the login handler" --json
# -> note $ID from the response

# ... do the work, commit it ...
COMMIT_SHA=$(git rev-parse HEAD)

spec-kitty profile-invocation complete \
    --invocation-id $ID \
    --outcome done \
    --artifact src/login/handler.py \
    --artifact tests/login/test_handler.py \
    --commit $COMMIT_SHA \
    --json
```

Expected JSON response includes:
- `"evidence_ref": null` (no `--evidence` passed)
- `"artifact_links": ["src/login/handler.py", "tests/login/test_handler.py"]` (both repo-relative, order preserved)
- `"commit_link": "<sha>"`

### 4.2 Inspect the trail file

```bash
cat .kittify/events/profile-invocations/$ID.jsonl
```

Expected four lines in order:
1. `started` event (with `mode_of_work: "task_execution"`)
2. `completed` event
3. `artifact_link` with `ref=src/login/handler.py`
4. `artifact_link` with `ref=tests/login/test_handler.py`
5. `commit_link` with the recorded SHA

### 4.3 Verify ref normalisation for an out-of-checkout path

```bash
spec-kitty ask implementer "write a scratch log" --json
# -> note $ID2

echo "scratch" > /tmp/scratch.log

spec-kitty profile-invocation complete \
    --invocation-id $ID2 \
    --outcome done \
    --artifact /tmp/scratch.log \
    --json

grep '"ref"' .kittify/events/profile-invocations/$ID2.jsonl
```

Expected: the persisted `ref` is `"/tmp/scratch.log"` (absolute, because the path is outside the checkout).

## 5. Mode enforcement at Tier 2 promotion (Tranche B) — FR-009, SC-004

### 5.1 Attempt evidence promotion on an advisory invocation

```bash
spec-kitty advise "should I refactor this module" --json
# -> note $ADVISE_ID

echo "some notes" > /tmp/notes.md

spec-kitty profile-invocation complete \
    --invocation-id $ADVISE_ID \
    --outcome done \
    --evidence /tmp/notes.md
```

Expected:
- Exit code 2.
- Error message contains: "Cannot promote evidence on invocation … mode is advisory; Tier 2 evidence is only allowed on task_execution or mission_step invocations."
- The invocation file has **no** `completed` event (the invocation is still open).
- No `.kittify/evidence/$ADVISE_ID/` directory was created.

### 5.2 Close the advisory invocation cleanly

```bash
spec-kitty profile-invocation complete \
    --invocation-id $ADVISE_ID \
    --outcome done
```

Expected: succeeds, `completed` event appended, no evidence artifact.

## 6. SaaS read-model policy (Tranche B) — FR-010, SC-005

### 6.1 Read the operator policy table

Open `docs/trail-model.md` and navigate to the "SaaS Read-Model Policy" subsection. Confirm the table lists exactly 16 rows (4 modes × 4 event kinds) and that each row specifies `project`, `include_request_text`, `include_evidence_ref`.

### 6.2 Predict projection from the table

Given the table alone, confirm you can predict — without reading code — the projection behaviour for:

- `(advisory, started)` → projected, body omitted, no evidence.
- `(query, started)` → no projection.
- `(mission_step, completed)` → projected with body and evidence_ref.
- `(task_execution, artifact_link)` → projected, body omitted, no evidence.

## 7. Tier 2 evidence stays local-only (Tranche B) — FR-011, SC-006

### 7.1 Read the deferral note

Open `docs/trail-model.md` and navigate to the "Tier 2 SaaS Projection — Deferred" subsection. Confirm:

- Status is stated decisively: Tier 2 evidence remains **local-only** in 3.2.x.
- The reasoning (D5) is present.
- The revisit trigger is named.

### 7.2 Verify behaviour

Even with SaaS sync enabled and authenticated (if you want to optionally toggle this on), evidence artifacts in `.kittify/evidence/<invocation_id>/` are **not** uploaded. This is the status quo from 3.2.0a5 and is confirmed by the deferral note.

## 8. Local-first invariant holds (Tranche B) — FR-012, NFR-007, SC-008

### 8.1 Ensure sync is disabled / unauthenticated

```bash
unset SPEC_KITTY_SAAS_TOKEN  # if set
# confirm routing returns effective_sync_enabled=False for this checkout
```

### 8.2 Run the full exercise above

Redo sections 3–5 above. Confirm every invocation file is written correctly.

### 8.3 Verify no propagation errors were logged

```bash
test -f .kittify/events/propagation-errors.jsonl && wc -l .kittify/events/propagation-errors.jsonl || echo "file absent"
```

Expected:
- Either the file is absent, or it has zero lines.

### 8.4 Timing spot-check (NFR-001)

```bash
time spec-kitty advise "a trivial ask" --json
```

Expected wall time dominated by CLI startup, not by trail I/O. `started` event write budget is ≤ 5 ms (enforced by NFR-001 test).

## 9. Tracker hygiene at merge (FR-014, SC-007)

This is a manual checklist for the release owner when the mission merges to `main`. It does **not** run automatically.

- [ ] Close `#496` (Phase 4 host-surface breadth follow-on).
- [ ] Close `#701` (Phase 4 trail follow-on).
- [ ] Update `#466` (Phase 4 tracker) to reflect that Phase 4 follow-on has shipped.
- [ ] Update `#534` (spec-kitty explain) with a cross-link to `#499` (DRG glossary addressability) and `#759` (Phase 5 glossary foundation) as the unblocker.
- [ ] Leave `#461` (umbrella roadmap) open.
- [ ] Verify the CHANGELOG unreleased section has the Tranche A + Tranche B entries.
- [ ] Verify `docs/trail-model.md` links to `docs/host-surface-parity.md` and to the SaaS Read-Model Policy subsection.

## 10. Rollback guidance

If any Tranche B behaviour is found to be regressive after merge:

1. **Correlation links**: no rollback needed — links are additive events on existing files; remove the flags from the CLI to stop producing them.
2. **Mode enforcement**: can be temporarily bypassed by passing an invocation that has no `mode_of_work` (pre-mission records, or a programmatically-opened invocation that omits the field). Proper rollback is a hotfix reverting the `InvalidModeForEvidenceError` raise in `complete_invocation`.
3. **SaaS policy**: reverting the policy lookup in `_propagate_one` restores 3.2.0a5 behaviour exactly.
4. **Dashboard wording**: a wording revert is a three-file edit; backend identifiers are untouched so no data migration is needed.

Each rollback is a surgical revert; no schema change needs to be undone.
