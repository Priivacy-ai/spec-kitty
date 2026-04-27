# T13 — Dogfood Smoke Evidence v2 (Action-Issuing Re-run)

Mission: `documentation-mission-composition-fixup-01KQ6N5X` (#502 fix-up)
Subtask: T13 (FR-008 / FR-009 / NFR-005 / SC-006 — real action-issuing dogfood smoke from a fresh temp repo using `uv --project`)
Run by: claude:opus-4.7:reviewer-renata:implementer (WP03)

## Why this re-run exists

The predecessor smoke at `evidence/smoke.md` (preserved in-tree as the
historical F-2 finding evidence) recorded `kind: query` only. The query path
is read-only — it never dispatches a composed action and never writes
invocation-trail records. SC-006 / NFR-005 / Scenario 6 require
`StepContractExecutor` dispatch and paired `started`+`completed` trail entries.

This re-run authors `spec.md` and reports `--result success` so the runtime
issues the first composed action (`discover`) and a follow-up `--result
success` drives the composition dispatch through `_dispatch_via_composition`,
which writes the paired records.

The historical predecessor file `smoke.md` is intentionally retained alongside
this `smoke-v2.md` so reviewers can audit the original P1 finding without
spelunking through git history.

## HEAD SHA at run time

```
02dbb3f20f8b7a753fd68cdeb40e3a1b17c16940
```

(lane: `kitty/mission-documentation-mission-composition-fixup-01KQ6N5X-lane-a`)

## Command sequence (verbatim)

```bash
SPEC_KITTY_REPO="/private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260426-184741-CfhGXa/spec-kitty"
TMP_DIR="$(mktemp -d -t docs-smoke-v2-XXXXXX)"
TMP_REPO="$TMP_DIR/repo"

# Init temp repo OUTSIDE the spec-kitty source tree (C-010).
mkdir -p "$TMP_REPO" && cd "$TMP_REPO"
git init --initial-branch=main
git config user.email "smoke@test.local"
git config user.name "Smoke v2"
echo "# smoke v2 repo" > README.md && git add README.md && git commit -m init

# Scaffold spec-kitty assets via --project (NEVER --directory, per #735).
uv run --project "$SPEC_KITTY_REPO" --python 3.13 spec-kitty init --ai claude --non-interactive
git add -A && git commit -m "scaffold spec-kitty"

# Create a documentation mission.
uv run --project "$SPEC_KITTY_REPO" --python 3.13 \
    spec-kitty agent mission create demo-docs --mission-type documentation --json \
    > create.json
MISSION_HANDLE=$(python3 -c 'import json; print(json.load(open("create.json"))["mission_slug"])')

# Step 1 — Query mode (read-only probe).
uv run --project "$SPEC_KITTY_REPO" --python 3.13 \
    spec-kitty next --agent claude --mission "$MISSION_HANDLE" --json \
    > next-query.json

# Author spec.md (and the rest of the documentation gate artifacts) so the
# discover step's post-execution guard chain has no missing-artifact failure.
echo "# spec for $MISSION_HANDLE" > "kitty-specs/$MISSION_HANDLE/spec.md"
echo "# gap analysis" > "kitty-specs/$MISSION_HANDLE/gap-analysis.md"
echo "# plan" > "kitty-specs/$MISSION_HANDLE/plan.md"
mkdir -p "kitty-specs/$MISSION_HANDLE/docs"
echo "# docs" > "kitty-specs/$MISSION_HANDLE/docs/index.md"
echo "# audit" > "kitty-specs/$MISSION_HANDLE/audit-report.md"
echo "# release" > "kitty-specs/$MISSION_HANDLE/release.md"

# Step 2 — Issue the first composed step (`discover`) by reporting --result success.
uv run --project "$SPEC_KITTY_REPO" --python 3.13 \
    spec-kitty next --agent claude --mission "$MISSION_HANDLE" --result success --json \
    > next-issue.json

# Step 3 — Drive the composition dispatch (writes paired trail records).
uv run --project "$SPEC_KITTY_REPO" --python 3.13 \
    spec-kitty next --agent claude --mission "$MISSION_HANDLE" --result success --json \
    > next-advance.json

# Inspect the trail.
ls -la "$TMP_REPO/.kittify/events/profile-invocations/"
cat "$TMP_REPO/.kittify/events/profile-invocations/"*.jsonl
```

The temp repo lived at
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/docs-smoke-v2-XXXXXX.DwFwNHFEZh/repo`
for this run and was cleaned up after evidence capture.

## CLI flag note

The runtime issuance verb is `--result success` (canonical values:
`success | failed | blocked`). There is no `--outcome` flag on
`spec-kitty next`. The first call with `--result success` issues the first
composed step; a subsequent `--result success` advances through composition
dispatch and emits the paired invocation-trail records. This mirrors the
in-process `decide_next_via_runtime(...)` walk pattern used in
`tests/integration/test_documentation_runtime_walk.py` (WP02).

## Verbatim stdout — `create.json`

```json
{
    "result": "success",
    "mission_slug": "demo-docs-01KQ6PTT",
    "mission_number": null,
    "mission_id": "01KQ6PTTASX7NAHTRTF6W54Y0T",
    "mission_type": "documentation",
    "slug": "demo-docs-01KQ6PTT",
    "friendly_name": "demo docs",
    "purpose_tldr": "demo docs",
    "feature_dir": "/private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/docs-smoke-v2-XXXXXX.DwFwNHFEZh/repo/kitty-specs/demo-docs-01KQ6PTT",
    "spec_file": "/private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/docs-smoke-v2-XXXXXX.DwFwNHFEZh/repo/kitty-specs/demo-docs-01KQ6PTT/spec.md",
    "meta_file": "/private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/docs-smoke-v2-XXXXXX.DwFwNHFEZh/repo/kitty-specs/demo-docs-01KQ6PTT/meta.json",
    "created_at": "2026-04-27T05:33:13.021462+00:00",
    "spec_kitty_version": "3.2.0a4"
}
```

(Truncated to the identity/result fields. `result == "success"`,
`mission_type == "documentation"`, `mission_slug == "demo-docs-01KQ6PTT"`. The
trailing stderr lines `Not authenticated, skipping sync` are #735 SaaS-sync
noise on stderr only — they did not corrupt the JSON on stdout.)

## Verbatim stdout — `next-query.json` (read-only probe)

```json
{
  "kind": "query",
  "agent": "claude",
  "mission_slug": "demo-docs-01KQ6PTT",
  "mission_type": "documentation",
  "mission": "documentation",
  "mission_state": "not_started",
  "timestamp": "2026-04-27T05:33:22.121567+00:00",
  "action": null,
  "wp_id": null,
  "guard_failures": [],
  "run_id": null,
  "step_id": null,
  "is_query": true,
  "preview_step": "discover"
}
```

`kind == "query"`, `mission == "documentation"`, `preview_step == "discover"`.
The query response carries `preview_step` (NOT `step_id`) — confirming the
`Decision` schema the corrected `quickstart.md` now references.

## Verbatim stdout — `next-issue.json` (first --result success → step issued)

```json
{
  "kind": "step",
  "agent": "claude",
  "mission_slug": "demo-docs-01KQ6PTT",
  "mission_type": "documentation",
  "mission": "documentation",
  "mission_state": "discover",
  "timestamp": "2026-04-27T05:33:31.116407+00:00",
  "action": "discover",
  "guard_failures": [],
  "origin": {
    "mission_tier": "global_mission",
    "mission_path": "/Users/robert/.kittify/missions/documentation"
  },
  "run_id": "f6993bfc12d142a7ab2732920e90834f",
  "step_id": "discover",
  "is_query": false,
  "preview_step": null
}
```

`kind == "step"`, `step_id == "discover"`, `action == "discover"`,
`mission == "documentation"`. The `Decision` now carries `step_id` (NOT
`preview_step`) — this is exactly the dual schema the corrected `quickstart.md`
asserts via `d.get("step_id") or d.get("preview_step")`.

## Verbatim stdout — `next-advance.json` (second --result success → composition dispatch)

```json
{
  "kind": "step",
  "agent": "claude",
  "mission_slug": "demo-docs-01KQ6PTT",
  "mission_type": "documentation",
  "mission": "documentation",
  "mission_state": "audit",
  "timestamp": "2026-04-27T05:33:46.795671+00:00",
  "action": "audit",
  "guard_failures": [],
  "origin": {
    "mission_tier": "global_mission",
    "mission_path": "/Users/robert/.kittify/missions/documentation"
  },
  "run_id": "f6993bfc12d142a7ab2732920e90834f",
  "step_id": "audit",
  "is_query": false,
  "preview_step": null
}
```

Run-state advanced from `discover` → `audit` (same `run_id`), proving the
composition dispatch walked through `_dispatch_via_composition` and persisted
forward progress.

## Trail listing — `<TMP_REPO>/.kittify/events/profile-invocations/`

```
total 40
drwxr-xr-x  7 robert  staff  224 Apr 27 07:33 .
drwxr-xr-x  5 robert  staff  160 Apr 27 07:33 ..
-rw-r--r--  1 robert  staff  972 Apr 27 07:33 01KQ6PVVWFHQH7PXSRRDN6QQH5.jsonl
-rw-r--r--  1 robert  staff  937 Apr 27 07:33 01KQ6PVW6KAAHEW5P1KQPXTNH2.jsonl
-rw-r--r--  1 robert  staff  906 Apr 27 07:33 01KQ6PVWF9XPWBTG0CK66WM0DF.jsonl
-rw-r--r--  1 robert  staff  958 Apr 27 07:33 01KQ6PVWQXA6R38DZA8H901WWR.jsonl
-rw-r--r--  1 robert  staff  925 Apr 27 07:33 01KQ6PVX0EHG47S82K98PJEZ98.jsonl
```

Five trail files were written by the composition dispatch — one per step
contract sub-step (`bootstrap`, `capture_documentation_needs`,
`validate_scope`, `write_spec`, `commit_spec`) for the `discover` action.
Note: trail files live under `<TMP_REPO>/.kittify/events/profile-invocations/`
(NOT under `~/.kittify/`) — the predecessor `quickstart.md` looked under
`$HOME` which is wrong; the corrected `quickstart.md` now references the
project-local path.

## Trail content — paired records (representative sample)

`01KQ6PVVWFHQH7PXSRRDN6QQH5.jsonl` (action=`discover`, sub-step `bootstrap`):

```json
{"event": "started", "invocation_id": "01KQ6PVVWFHQH7PXSRRDN6QQH5", "profile_id": "researcher-robbie", "action": "discover", "request_text": "Execute mission step contract documentation-discover (documentation/discover).\nStep bootstrap: Load charter context for this action\nDeclared command: spec-kitty charter context --action discover --role discover --json\nCommand status: declared only; the host/operator owns execution.", "governance_context_hash": "098f5c79559d1435", "governance_context_available": true, "actor": "claude", "started_at": "2026-04-27T05:33:47.602678+00:00"}
{"event": "completed", "invocation_id": "01KQ6PVVWFHQH7PXSRRDN6QQH5", "profile_id": "researcher-robbie", "actor": "unknown", "started_at": "", "completed_at": "2026-04-27T05:33:47.603127+00:00", "outcome": "done", "evidence_ref": null, "mode_of_work": null}
```

`01KQ6PVW6KAAHEW5P1KQPXTNH2.jsonl` (action=`discover`, sub-step `capture_documentation_needs`):

```json
{"event": "started", "invocation_id": "01KQ6PVW6KAAHEW5P1KQPXTNH2", "profile_id": "researcher-robbie", "action": "discover", "request_text": "Execute mission step contract documentation-discover (documentation/discover).\nStep capture_documentation_needs: Capture target audience, iteration mode, and goals; emit spec.md\nResolved delegations: directive:DIRECTIVE_010, directive:DIRECTIVE_003", "governance_context_hash": "098f5c79559d1435", "governance_context_available": true, "actor": "claude", "started_at": "2026-04-27T05:33:47.880950+00:00"}
{"event": "completed", "invocation_id": "01KQ6PVW6KAAHEW5P1KQPXTNH2", "profile_id": "researcher-robbie", "actor": "unknown", "completed_at": "2026-04-27T05:33:47.881305+00:00", "outcome": "done", "evidence_ref": null}
```

`01KQ6PVWF9XPWBTG0CK66WM0DF.jsonl` (action=`discover`, sub-step `validate_scope`):

```json
{"event": "started", "invocation_id": "01KQ6PVWF9XPWBTG0CK66WM0DF", "profile_id": "researcher-robbie", "action": "discover", "request_text": "Execute mission step contract documentation-discover (documentation/discover).\nStep validate_scope: Validate documentation scope boundaries and feasibility\nResolved delegations: tactic:requirements-validation-workflow", "governance_context_hash": "098f5c79559d1435", "governance_context_available": true, "actor": "claude", "started_at": "2026-04-27T05:33:48.157170+00:00"}
{"event": "completed", "invocation_id": "01KQ6PVWF9XPWBTG0CK66WM0DF", "profile_id": "researcher-robbie", "actor": "unknown", "completed_at": "2026-04-27T05:33:48.157491+00:00", "outcome": "done", "evidence_ref": null}
```

`01KQ6PVWQXA6R38DZA8H901WWR.jsonl` (action=`discover`, sub-step `write_spec`):

```json
{"event": "started", "invocation_id": "01KQ6PVWQXA6R38DZA8H901WWR", "profile_id": "researcher-robbie", "action": "discover", "request_text": "Execute mission step contract documentation-discover (documentation/discover).\nStep write_spec: Write spec.md to kitty-specs/{mission_slug}/\nDeclared command: Write spec.md in kitty-specs/{mission_slug}/\nCommand status: declared only; the host/operator owns execution.", "governance_context_hash": "098f5c79559d1435", "governance_context_available": true, "actor": "claude", "started_at": "2026-04-27T05:33:48.430392+00:00"}
{"event": "completed", "invocation_id": "01KQ6PVWQXA6R38DZA8H901WWR", "profile_id": "researcher-robbie", "actor": "unknown", "completed_at": "2026-04-27T05:33:48.430704+00:00", "outcome": "done", "evidence_ref": null}
```

`01KQ6PVX0EHG47S82K98PJEZ98.jsonl` (action=`discover`, sub-step `commit_spec`):

```json
{"event": "started", "invocation_id": "01KQ6PVX0EHG47S82K98PJEZ98", "profile_id": "researcher-robbie", "action": "discover", "request_text": "Execute mission step contract documentation-discover (documentation/discover).\nStep commit_spec: Commit the documentation spec to main branch\nUnresolved delegation candidates: 029-agent-commit-signing-policy, 033-targeted-staging-policy", "governance_context_hash": "098f5c79559d1435", "governance_context_available": true, "actor": "claude", "started_at": "2026-04-27T05:33:48.697492+00:00"}
{"event": "completed", "invocation_id": "01KQ6PVX0EHG47S82K98PJEZ98", "profile_id": "researcher-robbie", "actor": "unknown", "completed_at": "2026-04-27T05:33:48.697788+00:00", "outcome": "done", "evidence_ref": null}
```

Every trail file contains a `started` event paired with a `completed` event
whose `outcome == "done"`. Every recorded `action` is `discover` — a
documentation-native step ID (∈ `{discover, audit, design, generate, validate,
publish}`). No software-dev verbs leaked through.

## Verifications

### V1 — `mission == "documentation"` on the issued step

```bash
$ python3 -c 'import json; d=json.load(open("next-issue.json")); print(d["mission"])'
documentation
```

PASS.

### V2 — `kind == "step"` with documentation-native `step_id` (issuance, not query)

```bash
$ python3 -c 'import json; d=json.load(open("next-issue.json")); print(d["kind"], d["step_id"])'
step discover
```

`kind == "step"` (NOT `query`) and `step_id == "discover"` — a real action was
issued. PASS.

### V3 — Run advanced through composition dispatch (discover → audit)

```bash
$ python3 -c 'import json; print(json.load(open("next-advance.json"))["mission_state"])'
audit
```

The second `--result success` drove the run forward via
`_dispatch_via_composition`. PASS.

### V4 — Paired trail records (FR-012 / SC-006)

```bash
$ ls "$TMP_REPO/.kittify/events/profile-invocations/" | wc -l
       5
$ for f in "$TMP_REPO/.kittify/events/profile-invocations/"*.jsonl; do
>   python3 -c "
> import json, sys
> evs = [json.loads(l) for l in open(sys.argv[1]).read().splitlines() if l.strip()]
> started = [e for e in evs if e.get('event') == 'started']
> completed = [e for e in evs if e.get('event') == 'completed']
> ok = bool(started and completed and completed[-1].get('outcome') in {'done', 'failed'})
> action = started[0].get('action') if started else None
> print(sys.argv[1].split('/')[-1], 'paired=', ok, 'action=', action)
> " "$f"
> done
01KQ6PVVWFHQH7PXSRRDN6QQH5.jsonl paired= True action= discover
01KQ6PVW6KAAHEW5P1KQPXTNH2.jsonl paired= True action= discover
01KQ6PVWF9XPWBTG0CK66WM0DF.jsonl paired= True action= discover
01KQ6PVWQXA6R38DZA8H901WWR.jsonl paired= True action= discover
01KQ6PVX0EHG47S82K98PJEZ98.jsonl paired= True action= discover
```

5 / 5 trail files contain paired `started`+`completed` records with `outcome ==
done` and `action == discover` (a documentation-native step ID). PASS.

### V5 — No `--directory` invocation anywhere

```bash
$ grep -E "uv (run )?--directory" smoke-v2.md
$ echo $?
1
```

Zero `uv run --directory` (or `uv --directory`) invocations occur in this file.
The literal string `--directory` appears only inside prose warnings and the
`grep -E` self-reference above documenting the prohibition — not as actual
command invocations. All `uv run` calls in the command sequence above use
`--project`. PASS — NFR-005 / FR-009 / #735 satisfied.

### V6 — Smoke repo OUTSIDE the spec-kitty source tree (C-010 / FR-009)

```bash
$ echo "$TMP_REPO"
/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/docs-smoke-v2-XXXXXX.DwFwNHFEZh/repo
$ case "$TMP_REPO" in
>   "/private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260426-184741-CfhGXa/spec-kitty"*) echo INSIDE;;
>   *) echo OUTSIDE;;
> esac
OUTSIDE
```

Temp repo path is OUTSIDE the spec-kitty checkout. PASS.

## Cleanup

```bash
$ rm -rf /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/docs-smoke-v2-XXXXXX.DwFwNHFEZh
$ echo "cleanup done"
cleanup done
```

## Outcome

PASS. Documentation mission is reachable end-to-end from a fresh temp repo via
`uv --project`; the runtime issued the `discover` action via two `--result
success` calls, advanced from `discover` → `audit`, and wrote 5 paired
`started`+`completed` invocation-trail records under
`<TMP_REPO>/.kittify/events/profile-invocations/` with `action == discover`
and `outcome == done`. No `MissionRuntimeError`. No `--directory` invocations.
Temp repo OUTSIDE the spec-kitty tree.

Closes #502 F-2 / NFR-005 / SC-006.
