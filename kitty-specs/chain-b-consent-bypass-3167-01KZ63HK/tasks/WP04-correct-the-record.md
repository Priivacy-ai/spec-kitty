---
work_package_id: WP04
title: Correct the record and close the tracker
dependencies:
- WP02
- WP03
requirement_refs:
- FR-008
- FR-009
- FR-010
planning_base_branch: feat/chain-b-consent-bypass-3167
merge_target_branch: feat/chain-b-consent-bypass-3167
branch_strategy: Planning artifacts for this mission were generated on feat/chain-b-consent-bypass-3167.
  During /spec-kitty.implement this WP may branch from a dependency-specific base,
  but completed changes must merge back into feat/chain-b-consent-bypass-3167 unless
  the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
- T021
phase: Phase 4 - The record
history:
- at: '2026-08-04T10:30:00Z'
  actor: system
  action: Prompt generated from wps.yaml
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/runtime.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/sync/runtime.py
- docs/context/orchestration.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – Correct the record and close the tracker

## ⚡ Do This First: Load Agent Profile

Load `python-pedro`.

## Goal

Three false-or-soon-false pointers corrected, and the tracker closed honestly. No behaviour change.

## Why a docstring is worth a work package

This mission's own first draft asserted that a **true** docstring was false, because "the drain" has
three referents in this codebase and no glossary entry. That mistake nearly shipped a rewrite of correct
documentation, which would then have claimed coverage for a module with no live caller. A false pointer
is how an auditor concludes a gate exists.

## Subtasks

### T017 — Annotate the auto-start boundary at `sync/runtime.py:106`

`:106` stays on the checkout chain per operator decision **D-M5a-1 = a** (`C-001`): auto-start is not
an egress boundary, and `runtime.py:141-148` binds `sync.auto_start` and `sync.enabled` apart in
explicit terms. Add a comment so its Chain-B call is not read as an unfixed bypass.

**The comment must NOT claim the publish gate covers every path.** A started runtime emits a
`build_id` in a `pong` (`sync/client.py:409-414`) that `event_project_consents_to_publish` never
sees; it is classified not-project-data at `tests/architectural/test_egress_consent_boundary.py:567-575`.
**Point at that per-sender enumeration** instead of overclaiming. Shipping a fresh false coverage claim
two lines from the one being fixed would be an unusually direct way to fail this mission.

### T018 — One glossary entry for "the drain"

Add it to `docs/context/orchestration.md`, following the `primary` / `merge` / `routing`
precedent already there — those entries exist because the same overload class caused real defects.

The three referents:

| Term use | Means |
|---|---|
| the drain (dispatch selection) | `delivery/selection.py` — the live event drain |
| the body drain | `sync/background.py:280` — artifact body upload |
| the retired queue-backed drain | `sync/batch.py` — **gone as of this mission** |

**Operator decision:** in-place prose naming is scoped to the files this mission already opens. The other
13 files (`emitter.py` alone has 11 occurrences) are **out of scope** — file them in T019, do not sweep
them. They are hot cross-mission files and a sweep there collides with M2.

### T019 — File the 8 residuals

Each gets a real issue, and the numbers are recorded in `spec.md`'s out-of-scope register. A
`deferred-with-followup` verdict is only honest once the follow-up exists.

The **six File rows** from the register (row 7 is Fold — do not file it), plus:
8. `core/batch_partition.py::split_in_half` now has **zero production consumers** — kept as a canonical
   leaf by operator decision. Its T018 AST sweep still guards `src/` against hand-rolled midpoint math.
9. FR-009's 13 out-of-scope files still carrying ambiguous "the drain" prose.

Highest-value of the seven, for issue-body quality: `consented_project_uuids` **writes machine-global
config on read** (`sync/consent.py:483,:512` → `_reconcile_index` → `set_project_consent`) —
measured: the index goes `None` → `True` after one read and the grant **survives removal of the
project-local grant**.

Cite as `owner/repo#NNNN` in mission artifacts. Verify with `discover_issue_references(mission_dir)`
against a positive control afterwards — a bare foreign `#NNNN` mints a row this mission cannot resolve.

### T020 — Move `#3167` to a terminal verdict

Its row is currently `in-mission`, which is **rejected on the `done` transition**. Use the canonical
writer:

```bash
.venv/bin/spec-kitty agent issue-verdict --mission chain-b-consent-bypass-3167-01KZ63HK \
  --issue "#3167" --verdict <terminal> --actor <you> --wp WP04 --evidence-ref "..."
```

The evidence is WP01's manifest: one site **retired** rather than migrated because it had no production
caller, and `sync/runtime.py:106` **deliberately unchanged** per D-M5a-1 = a with the
defence-in-depth residual filed. Do not claim the issue's original ask was delivered as written — it was
not, deliberately, and the honest record is worth more than a tidy one.

### T021 — Populate the acceptance matrix, and use negative invariants

`acceptance-matrix.json` currently holds **10 scaffolded FR rows with `evidence: None`**. It is
structurally present and semantically empty — the same shape as the accept gate's `contracts/` check
being satisfied by `mkdir` alone. A matrix of placeholders passing a gate is precisely what this
programme exists to remove.

Record a verdict per criterion:

```bash
.venv/bin/spec-kitty agent mission acceptance-verdict --mission chain-b-consent-bypass-3167-01KZ63HK \
  --criterion FR-001 --result pass --verification-method <how> --actor <you> --evidence-ref "..."
```

**And register the deletion's absence claims as NEGATIVE INVARIANTS** (`--negative-invariant` with
`--verification-method grep_absence`) — for a retirement mission that is the form the evidence actually
takes, and it is executable rather than narrated:

| Invariant | Shape |
|---|---|
| `batch_sync` and `sync_all_queued_events` are absent from `sync/batch.py` | `grep_absence` |
| zero transmit primitives remain in `sync/batch.py` | `grep_absence` |
| the `E15` entry is gone from the egress allowlist | `grep_absence` |

**Cite what WP01–WP03 already measured** — the frozen manifest, K=91, the 3→0 primitive count, the
69→69 API delta, the cone attribution — rather than re-deriving any of it. An invariant whose evidence
is "verified by inspection" is the thing NFR-001 explicitly forbids for the refusal side.

## Done when

- [ ] `runtime.py:106`'s comment names the real gate **and** does not claim it covers every path.
- [ ] The glossary entry exists with all three referents; the 13 out-of-scope files are untouched.
- [ ] 8 residual issues filed, numbers recorded in `spec.md`'s register. Row 7 (Fold) is NOT filed.
- [ ] `#3167`'s matrix row carries a terminal verdict with the manifest as evidence.
- [ ] `discover_issue_references(mission_dir)` re-run with a positive control; every minted row has a row in the matrix.
- [ ] `ruff check` clean on `sync/runtime.py`.
- [ ] `acceptance-matrix.json` has **zero** rows left with `evidence: None`, and the three deletion
      absence claims are registered as **negative invariants** with `grep_absence`, each executable.

---

## Standing rules — these were each paid for. Do not paraphrase them.

**Measurement**
- *Never pipe a suite whose exit status you intend to trust.* Redirect, and quote the `N passed` line. An empty output file is no measurement.
- *A killed run is neither a pass nor a fail.* Re-run narrowed. Say you did. Do not explain it away.
- *Pin the interpreter:* `.venv/bin/python -m pytest`. Quote `sys.executable` **and** the `plugins:` header for anything load-bearing. `pytest-timeout` and `xdist` exist **only** in that venv.
- *Read the failure text, not the tally.*
- *Print the input count alongside any "all checks passed."* A gate that ran on zero files passes vacuously.
- *Red first* — and make the red **the consequence**, not a boolean.
- *Include a positive control that must pass.*
- *Any assertion of absence must establish why the thing would otherwise have happened.*
- *Control your diagnostic:* run any probe first against a case whose answer you already know.
- Use `-ra`, **not** `-rf`. `-rf` suppresses the error short-summary, which makes the standing `grep -c '^ERROR '` return 0 on a run that had errors. This actually happened on this mission.

**Concurrency**
- **Do not run `tests/sync` and `tests/cli` sessions concurrently.** They spawn real daemons and `pgrep`/port-scan; sibling sessions reap each other. 16 recorded false reds. This mission sweeps `tests/sync` and `tests/architectural` only — do not add `tests/cli`.
- `pgrep -af 'run_sync[_]daemon'` before every measurement. Leaked daemons on ports 9400-9402 contaminate the next one.
- **Put reaps in a script file**, where the command line is just `bash script.sh`. `pkill -f <pattern>` matches your own shell's command line and kills it — and so does `pgrep -f` in a script that greps for itself. The `[b]racket` trick is required in **both** forms. This bit a prior agent on this very mission.
- One live agent per file. The files this WP owns are listed in its frontmatter; do not touch another WP's.

**Git**
- **Explicit-path staging. `git add <paths>`, never `git add -A`.** Thirteen files were lost to one stray `add -A`.
- Commit via `spec-kitty safe-commit <paths> --to-branch feat/chain-b-consent-bypass-3167 -m "..."`.
- **`ruff format` is NOT clean on this repo** (`line-length = 164`). Only `ruff check` is meaningful.
- `git add` on an ignored file **silently does nothing** without `-f`. Confirm with `git status` that what you meant to stage is staged.

**Scope**
- **File follow-up issues for anything found out of scope rather than absorbing it.** That rule is what produced this mission; honour it again.
- Cite issues as `owner/repo#NNNN` for foreign issues and bare `#3167` for this mission's own. A bare `#NNNN` for a *foreign* issue in `spec.md`, `plan.md`, `research.md`, `analysis-report.md`, `tasks/*.md` or `contracts/*.md` mints a mandatory issue-matrix row this mission cannot resolve. Verify with `discover_issue_references(mission_dir)` — the multi-file API the merge gate actually calls — against a positive control.
- **A `len(x) == N` assertion in `tests/architectural/` trips the golden-count ratchet** (`test_golden_count_ban.py`). If the count genuinely *is* the contract, annotate `# golden-count: cardinality-is-contract` on the assertion's own physical line. **Do not re-freeze the baseline.**

**The disposition that matters more than any rule**

This mission exists because a gate carried a consent decision on a code path nobody calls, and because a
test fixture granted that gate `True` for every file whose name lacked one word. **A disclosed red beats
a manufactured green.** If the honest answer is "this is a real defect and the suite stays red until
someone fixes it", that is an acceptable deliverable. What is not acceptable is narrowing a watch set,
loosening a check, re-freezing a baseline, or pinning something unverified to get a green badge.

If you catch yourself about to report a number without having checked what it counts — stop. That is the
failure this whole programme is about.

---

## Where `contracts/` artifacts go

`contracts/*.md` and the other dossier files live under `kitty-specs/` and therefore **cannot appear in a
work package's `owned_files`** — the framework rejects it, and the commit router sends planning artifacts
to the mission's target branch on its own. Write them normally and commit them with `safe-commit`; they
are deliverables even though they are not owned files.

One consequence worth naming: the accept gate's `contracts/` check is satisfied by
`p.exists()`, so **`mkdir contracts` alone would pass it**. Put a real contract there. An empty directory
that satisfies a gate is the exact failure this mission exists to remove.
