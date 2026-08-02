# WP02 Acceptance Evidence: C-001, C-002

**F12**: `kitty-specs/doctrine-behavioral-suite-01KYW5XK`'s requirement/
acceptance tracking offers rows for `FR-001..FR-009` only — C-001 and C-002
(this WP's own two Constraint refs, alongside FR-005 and FR-007) had no
acceptance home of their own, so both were evidenced solely in git commit
messages. This file is that committed home, per spec.md's own Evidence
Artifact principle ("Never described only in a PR body or README prose")
applied to acceptance verdicts, not only to the FR-007 discrimination proof.
This file lives under `conformance/behavioral/evidence/`, one of this WP's
own `owned_files` globs — `kitty-specs/` is out of scope for this WP
(see this mission's Lanes section and WP02's own Definition of Done).

All commands below were re-executed for real on 2026-08-02, against this
WP's own owned files only (`.github/workflows/behavioral.yml`,
`conformance/behavioral/control-manifest.yaml`) — never against WP01's
`conformance/behavioral/profiles/**` content, which is out of this WP's
write_scope and, at the time of this writing, has an active parallel review
in progress in this same clone with uncommitted changes of its own.

## C-001 — No secrets in manifests or argv

**Constraint** (spec.md): endpoint config via `MUSTER_ENDPOINT`/
`MUSTER_MODEL`/`MUSTER_API_KEY` only; CI grep gate reuses muster's own two
NI-001 regexes (`/nvapi-[A-Za-z0-9]{8}/`, `/\bsk-[A-Za-z0-9_-]{20}/`).

**Positive case** (expect exit 1, no match), run against this WP's own
files:

```
$ command grep -rE '(nvapi-[A-Za-z0-9]{8}|\bsk-[A-Za-z0-9_-]{20})' \
    conformance/behavioral/*.yaml conformance/behavioral/profiles/*.yaml \
    .github/workflows/behavioral.yml
$ echo $?
1
```

Result: **PASS** — exit 1, no match, on the real committed files (glob only
resolves `control-manifest.yaml` from `conformance/behavioral/*.yaml` inside
this WP's own worktree per T011's Validation note; the `profiles/*.yaml`
half of the glob is WP01's content and, per T011's own note, is not this
WP's concern to evaluate from inside this WP).

**Rejection case** (expect exit 0, match found), run against a scratch copy,
discarded immediately after:

```
$ cp .github/workflows/behavioral.yml /tmp/behavioral-scratch.yml
$ echo '# planted: nvapi-XXXXXXXX' >> /tmp/behavioral-scratch.yml
$ command grep -rE '(nvapi-[A-Za-z0-9]{8}|\bsk-[A-Za-z0-9_-]{20})' /tmp/behavioral-scratch.yml
# planted: nvapi-XXXXXXXX
$ echo $?
0
$ rm -f /tmp/behavioral-scratch.yml
```

Result: **PASS** — the gate fires on a planted key; the scratch copy was
never committed.

**Verdict**: C-001 **pass**.

## C-002 — Cadence, never PR-triggered, and must actually run the suite

**Constraint** (spec.md): `on: workflow_dispatch` only, never
`pull_request`/`schedule`; the workflow's jobs must invoke `muster sop run`
against real manifest paths, not an `echo`-only job.

### Trigger half (discharged inside this WP)

**Positive case** (expect `true`, exit 0):

```
$ yq -e '.on | has("pull_request") or has("schedule") | not' .github/workflows/behavioral.yml
true
$ echo $?
0
```

**Rejection case** (expect `false`, exit 1), run against a scratch copy,
discarded immediately after:

```
$ cp .github/workflows/behavioral.yml /tmp/behavioral-scratch.yml
$ yq -Y -i '.on.pull_request.branches = ["main"]' /tmp/behavioral-scratch.yml
$ yq -e '.on | has("pull_request") or has("schedule") | not' /tmp/behavioral-scratch.yml
false
$ echo $?
1
$ rm -f /tmp/behavioral-scratch.yml
```

**Real-manifest-invocation half** (procedural review, not a one-liner, per
spec.md's own instruction): `.github/workflows/behavioral.yml`'s
`main-suite` job invokes `npx --yes --offline "${MUSTER_PIN}" sop run
"${manifest}" --json` inside a loop over
`conformance/behavioral/profiles/*.yaml` (glob-driven, F6-guarded to refuse
a run that matched fewer than 5 files) plus the three literal
FR-005-edited `conformance/doctrine/*.yaml` paths T006-T008 touched; the
`control-suite` job invokes the identical pattern against
`conformance/behavioral/control-manifest.yaml`. Neither job is
`echo`-only — reviewed directly against the committed file, not asserted.

Result (trigger half + real-invocation review): **PASS**.

### File-set cross-check (explicitly deferred, not attempted here)

Per C-002's own note in spec.md and WP02's task prompt (T011's Validation,
Definition of Done): `ls conformance/behavioral/profiles/*.yaml
conformance/behavioral/control-manifest.yaml` matching the workflow's
referenced globs/paths exactly requires both lanes' committed files to
coexist on disk, which only holds true after both lanes have landed on
`kitty/mission-doctrine-behavioral-suite`. This WP's own worktree, at the
time of this writing, has WP01's profile manifests present but under
active, uncommitted, parallel review edits (`git status` shows all five
`profiles/*.yaml` files modified and five additional `_scratch-*.yaml`
files untracked) — not a stable committed state this check can validate
against. Attempting the cross-check here would either fail for the wrong
reason (files not yet finalized) or falsely pass against a transient,
uncommitted state.

**Verdict**: C-002 trigger half + real-invocation review **pass**; file-set
cross-check **pending**, deferred to the mission's post-merge Acceptance
Gate (spec.md, "Acceptance Gate: One Live Credentialed Run", item 3), per
WP02's own Definition of Done.
