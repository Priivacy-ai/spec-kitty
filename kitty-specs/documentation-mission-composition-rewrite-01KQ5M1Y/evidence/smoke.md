# T030 — Dogfood Smoke Evidence

Mission: `documentation-mission-composition-rewrite-01KQ5M1Y` (#502)
Subtask: T030 (NFR-005 / SC-001 / SC-006 / C-008 / C-010 — dogfood smoke from a separate temp repo using `uv --project`)
Run by: claude:opus-4.7:reviewer-renata:implementer (WP07)

## HEAD SHA at run time

```
0fc53df3d77cb257325a862111a061e3331c8d34
```

(lane: `kitty/mission-documentation-mission-composition-rewrite-01KQ5M1Y-lane-a`)

## Why this matters

- **NFR-005 / #735**: The smoke MUST use `uv run --project <SPEC_KITTY_REPO>`
  and MUST NOT use `uv run --directory <SPEC_KITTY_REPO>`. `--directory` changes
  the CWD inside the spec-kitty source tree and breaks JSON output via SaaS sync
  trailing noise — the mission-review verdict downgrades to UNVERIFIED on any
  hit.
- **C-010**: The smoke repo MUST live OUTSIDE the spec-kitty source tree to
  prove that the documentation mission is invocable as a normal operator
  scenario. Running it inside the spec-kitty checkout would conflate the
  "operator drives a fresh project" path with the "developer dogfoods within
  source tree" path.
- **C-008**: The smoke MUST be present in the commit so the mission-review
  skill can read it without re-executing.

## Command sequence (verbatim)

```bash
TMP_REPO_PARENT="$(mktemp -d -t docs-smoke-XXXXXX)"
TMP_REPO="${TMP_REPO_PARENT}/repo"
SPEC_KITTY_REPO="/private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260426-184741-CfhGXa/spec-kitty/.worktrees/documentation-mission-composition-rewrite-01KQ5M1Y-lane-a"

# Init temp repo OUTSIDE spec-kitty tree (C-010).
mkdir -p "$TMP_REPO" && cd "$TMP_REPO"
git init --initial-branch=main
git config user.email "smoke@test.local"
git config user.name "Smoke"
echo "# smoke repo" > README.md && git add README.md && git commit -m init

# Scaffold spec-kitty assets in the temp repo via --project (NEVER --directory, per #735).
uv run --project "$SPEC_KITTY_REPO" --python 3.13 spec-kitty init --ai claude --non-interactive
git add -A && git commit -m "scaffold spec-kitty"

# Create a documentation mission via --project.
uv run --project "$SPEC_KITTY_REPO" --python 3.13 \
    spec-kitty agent mission create demo-docs --mission-type documentation --json \
    > create.json

MISSION_HANDLE=$(python3 -c 'import json; print(json.load(open("create.json"))["mission_slug"])')

# Drive the runtime via --project.
uv run --project "$SPEC_KITTY_REPO" --python 3.13 \
    spec-kitty next --agent claude --mission "${MISSION_HANDLE}" --json \
    > next.json
```

The temp repo lived at `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/docs-smoke-XXXXXX.6SG2Z3M7xJ/repo` for this run (cleaned up after capture per the
quickstart cleanup step).

## Verbatim stdout — `spec-kitty init`

```
╭──────────────────────────────────────────────────────────────────────────────╮
│  Specify Project Setup                                                       │
│  Project         repo                                                        │
│  Working Path                                                                │
│  /private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/docs-smoke-XXXXXX  │
│  .6SG2Z3M7xJ/repo                                                            │
╰──────────────────────────────────────────────────────────────────────────────╯
✓ git detected - will be used for version control
Selected AI assistant(s): Claude Code
Initialize Specify Project
├── ● Check required tools (ok)
├── ● Select AI assistant(s) (Claude Code)
├── ● Bootstrap global runtime (ok)
├── ● Install skills globally (13 skills installed globally)
├── ● Claude Code: fetch latest release (packaged data)
├── ● Claude Code: download template (local files)
├── ● Claude Code: extract template (agent configured (commands managed globally))
├── ● Claude Code: archive contents (templates ready)
├── ● Claude Code: extraction summary (commands ready)
├── ● Claude Code: cleanup (done)
├── ● Claude Code: install skill pack (13 skills installed)
├── ○ Ensure scripts executable
└── ● Finalize (project ready)

Project ready.
```

(Exit `0`. The CLI also wrote `.gitignore`, `.gitattributes`, `.claudeignore`,
`.kittify/config.yaml`, `.kittify/metadata.yaml`, and the skills manifest.)

## Verbatim stdout — `spec-kitty agent mission create demo-docs --mission-type documentation --json` (`create.json`)

```json
{"result": "success", "mission_slug": "demo-docs-01KQ5R5A", "mission_number": null, "mission_id": "01KQ5R5AKKNNG8W4YC70YY6RHE", "mission_type": "documentation", "slug": "demo-docs-01KQ5R5A", "friendly_name": "demo docs", "purpose_tldr": "demo docs", "purpose_context": "This mission advances demo docs on main so stakeholders can track the work from mission creation onward.", "feature_dir": "/private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/docs-smoke-XXXXXX.6SG2Z3M7xJ/repo/kitty-specs/demo-docs-01KQ5R5A", "spec_file": "/private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/docs-smoke-XXXXXX.6SG2Z3M7xJ/repo/kitty-specs/demo-docs-01KQ5R5A/spec.md", "meta_file": "/private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/docs-smoke-XXXXXX.6SG2Z3M7xJ/repo/kitty-specs/demo-docs-01KQ5R5A/meta.json", "created_at": "2026-04-26T20:37:11.494570+00:00", "created_files": ["/private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/docs-smoke-XXXXXX.6SG2Z3M7xJ/repo/kitty-specs/demo-docs-01KQ5R5A/spec.md", "/private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/docs-smoke-XXXXXX.6SG2Z3M7xJ/repo/kitty-specs/demo-docs-01KQ5R5A/meta.json", "/private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/docs-smoke-XXXXXX.6SG2Z3M7xJ/repo/kitty-specs/demo-docs-01KQ5R5A/tasks/README.md"], "write_mode": "update_existing_files", "next_step": "Read then update spec_file/meta_file; do not recreate with blind write.", "origin_binding": {"attempted": false, "succeeded": false, "error": null}, "current_branch": "main", "CURRENT_BRANCH": "main", "target_branch": "main", "base_branch": "main", "TARGET_BRANCH": "main", "BASE_BRANCH": "main", "planning_base_branch": "main", "PLANNING_BASE_BRANCH": "main", "merge_target_branch": "main", "MERGE_TARGET_BRANCH": "main", "EXPECTED_TARGET_BRANCH": "main", "EXPECTED_BASE_BRANCH": "main", "branch_matches_target": true, "BRANCH_MATCHES_TARGET": true, "branch_strategy_summary": "Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main.", "runtime_vars": {"now_utc_iso": "2026-04-26T20:37:12Z", "current_branch": "main", "target_branch": "main", "base_branch": "main", "planning_base_branch": "main", "merge_target_branch": "main", "branch_matches_target": true, "branch_strategy_summary": "Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main."}, "NOW_UTC_ISO": "2026-04-26T20:37:12Z", "branch_context": {"current_branch": "main", "target_branch": "main", "base_branch": "main", "planning_base_branch": "main", "merge_target_branch": "main", "expected_checkout_branch": "main", "matches_target": true, "branch_strategy_summary": "Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main."}, "spec_kitty_version": "3.2.0a4"}
```

(`mission_type` = `documentation`, `mission_slug` = `demo-docs-01KQ5R5A`,
`result` = `success`. The trailing stderr lines `Not authenticated, skipping
sync` are #735 SaaS-sync noise on stderr only — they did not corrupt the JSON
on stdout.)

## Verbatim stdout — `spec-kitty next --agent claude --mission demo-docs-01KQ5R5A --json` (`next.json`)

```json
{
  "kind": "query",
  "agent": "claude",
  "mission_slug": "demo-docs-01KQ5R5A",
  "mission_number": "",
  "mission_type": "documentation",
  "mission": "documentation",
  "mission_state": "not_started",
  "timestamp": "2026-04-26T20:37:12.769427+00:00",
  "action": null,
  "wp_id": null,
  "workspace_path": null,
  "prompt_file": null,
  "reason": null,
  "guard_failures": [],
  "progress": null,
  "origin": {},
  "run_id": null,
  "step_id": null,
  "decision_id": null,
  "input_key": null,
  "question": null,
  "options": null,
  "is_query": true,
  "preview_step": "discover"
}
```

## Decision interpretation

| Field | Value | Meaning |
|---|---|---|
| `kind` | `query` | The runtime is asking the agent to author `spec.md` (the standard pre-spec init query). |
| **`mission`** | **`documentation`** | ✅ SC-001 satisfied — mission key resolved to documentation. |
| `mission_type` | `documentation` | Confirms the documentation mission was selected end-to-end. |
| `mission_state` | `not_started` | Fresh mission with no `spec.md` yet — expected behavior. |
| **`preview_step`** | **`discover`** | ✅ SC-001 next-step preview — `discover` is the documentation mission's first composed action; the documentation contracts wired by WP04/WP05 are reachable from the runtime. |
| `guard_failures` | `[]` | No fail-closed guard fires at this stage; the runtime is in the pre-spec query path. |

This is the SC-001 "blocked/query before spec.md" outcome explicitly allowed by
the WP07 task spec §T030 Validation: *"a `kind == "blocked"` decision with a
`guard_failures` list naming `spec.md`, OR a `query` whose `mission ==
documentation` and whose preview/issued step is one of
`{discover, audit, design, generate, validate, publish}`"*. The `query` form
satisfies the requirement: `mission == documentation` and
`preview_step == discover`.

## Verifications

### V1 — `mission == "documentation"`

```bash
$ python3 -c 'import json; d=json.load(open("next.json")); print(d["mission"])'
documentation
```

✅ Pass.

### V2 — Documentation-native step verb

```bash
$ python3 -c 'import json; d=json.load(open("next.json")); print(d["preview_step"])'
discover
```

`discover` ∈ `{discover, audit, design, generate, validate, publish}` ✅.

### V3 — No `--directory` invocation anywhere

The transcript file `/tmp/wp07-smoke-transcript.txt` was inspected:

```bash
$ grep -E "uv (run|--).*--directory" /tmp/wp07-smoke-transcript.txt
$ echo $?
1
```

Zero matches (`grep` exit `1` = no lines matched). The two literal occurrences
of the string `--directory` in the transcript are header comments documenting
the prohibition (e.g. *"use --project, NEVER --directory per #735"*) — they are
not invocations. All three `uv run` calls used `--project`:

```bash
$ grep -c -- "--project" /tmp/wp07-smoke-transcript.txt
3
```

✅ Pass — NFR-005 / #735 satisfied.

### V4 — Smoke repo OUTSIDE the spec-kitty source tree

```bash
$ pwd
/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/docs-smoke-XXXXXX.6SG2Z3M7xJ/repo
```

The temp repo path begins with `/var/folders/.../docs-smoke-XXXXXX.../repo`,
which is outside the spec-kitty checkout at
`/private/var/folders/.../spec-kitty-20260426-184741-CfhGXa/spec-kitty`.
✅ C-010 satisfied.

### V5 — Trail records

```bash
$ ls -la "${HOME}/.kittify/events/profile-invocations/" 2>&1 | head
ls: /Users/robert/.kittify/events/profile-invocations/: No such file or directory

$ find "${TMP_REPO}/.kittify" -type d
${TMP_REPO}/.kittify
${TMP_REPO}/.kittify/memory
${TMP_REPO}/.kittify/memory/templates

$ find "${TMP_REPO}" -name "*.jsonl" -type f
${TMP_REPO}/kitty-specs/demo-docs-01KQ5R5A/status.events.jsonl
```

The `query` decision did not yet emit a `<action>-started.jsonl` invocation
record because no action has been issued — `kind: query` is a pre-action
runtime probe asking the agent to author `spec.md`. The mission is recorded in
`status.events.jsonl` (the canonical mission-state event log per the 034 model).
This is consistent with the SC-001 "before spec.md exists" path documented in
`quickstart.md`. The test
`tests/integration/test_documentation_runtime_walk.py` (WP06) is the
authoritative end-to-end proof of action-record emission once `spec.md` is
authored; that suite passed in this WP's regression sweep (see
`evidence/regression.md`).

## Cleanup

The temp repo parent directory was removed after evidence capture:

```bash
$ rm -rf /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/docs-smoke-XXXXXX.6SG2Z3M7xJ
$ echo "cleanup done"
cleanup done
```

## Outcome

✅ **PASS.** Documentation mission is reachable end-to-end from a fresh temp
repo via `uv --project`; `next.json` resolves to `mission: documentation`
with `preview_step: discover` (a documentation-native action verb). NFR-005,
SC-001 (preview path), C-008, and C-010 are satisfied. No `--directory`
invocations occurred at any point.
