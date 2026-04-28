# Quickstart: Charter Golden-Path Operator Walk

**Mission**: `charter-e2e-hardening-tranche-2-01KQ9NVQ`
**Audience**: Reviewers verifying the strict golden-path E2E behaves as specified, and operators running the Charter flow on a fresh project.

This walk mirrors the operator sequence the strict E2E (`tests/e2e/test_charter_epic_golden_path.py`) executes after this mission lands. Every step uses public CLI commands only — no internal helpers, no hand-seeded files. Each `--json` output must parse with strict full-stream `json.loads`.

---

## Prerequisites

- A clean working directory (the E2E uses a temp dir; humans can use any empty folder).
- `spec-kitty` CLI installed (or invoke via `uv run spec-kitty …` from the repo).
- No `SPEC_KITTY_ENABLE_SAAS_SYNC` env variable (this walk is the deterministic offline path).

---

## Step 1 — Initialize a fresh project

```bash
mkdir charter-walk && cd charter-walk
git init
spec-kitty init
```

**Expect**:

- `.kittify/` directory created.
- `.kittify/metadata.yaml` exists and contains `spec_kitty.schema_version` and `spec_kitty.schema_capabilities` (FR-001).
- No bootstrap helper or manual metadata edit needed.

**Verify**:

```bash
grep -E "schema_version|schema_capabilities" .kittify/metadata.yaml
```

---

## Step 2 — Run the charter interview / generate path

```bash
spec-kitty charter generate --json > generate.json
```

**Expect**:

- Exactly one JSON document on stdout (FR-005).
- `result: "success"`.
- If the generated charter requires git tracking before validation, the JSON includes a `next_step.action == "git_add"` field with the paths to stage (see `contracts/charter-bundle-validate.json`). The E2E follows this instruction verbatim.

**Verify**:

```bash
python -c "import json,sys; d=json.load(open('generate.json')); assert d['result']=='success'"
```

If the JSON contained a tracking instruction:

```bash
git add <paths from next_step.paths>
```

---

## Step 3 — Validate the bundle

```bash
spec-kitty charter bundle validate --json > validate.json
```

**Expect**:

- Exactly one JSON document on stdout.
- `result: "success"`, with no `issues` array entries.
- No SaaS sync warnings appended to stdout (FR-005).

**Verify**:

```bash
python -c "import json; d=json.load(open('validate.json')); assert d['result']=='success' and not d.get('issues')"
```

---

## Step 4 — Synthesize doctrine (dry-run)

```bash
spec-kitty charter synthesize --adapter fixture --dry-run --json > dryrun.json
```

**Expect**:

- Strict envelope per `contracts/charter-synthesize-dry-run.json`.
- `result: "success"`.
- `planned_artifacts` lists the doctrine paths the non-dry-run would create.

**Verify**:

```bash
python -c "import json; d=json.load(open('dryrun.json')); assert d['result']=='success' and d['planned_artifacts']"
```

No `--dry-run-evidence` fallback is used (FR-004).

---

## Step 5 — Synthesize doctrine (real)

```bash
spec-kitty charter synthesize --adapter fixture --json > synth.json
```

**Expect**:

- Strict envelope per `contracts/charter-synthesize.json`.
- `result: "success"`.
- `.kittify/doctrine/` exists on disk and contains the manifest/provenance artifacts the adapter is supposed to produce.
- The directory was created by this command, **not** seeded by the test (FR-004, C-001).

**Verify**:

```bash
ls .kittify/doctrine/
python -c "import json; d=json.load(open('synth.json')); assert d['result']=='success' and d['written_artifacts']"
```

---

## Step 6 — Run charter status / lint

```bash
spec-kitty charter status --json > status.json
spec-kitty charter lint --json > lint.json
```

**Expect**:

- Each call produces exactly one JSON document on stdout.
- `result: "success"` (or whatever public status field your charter status command uses — confirmed during WP01 research).

---

## Step 7 — Query the next runtime step

```bash
spec-kitty next --json > next-issue.json
```

**Expect**:

- Strict envelope per `contracts/next-issue.json`.
- Either `status: "issued"` with `step.prompt_file` non-empty and resolvable on disk, OR `status: "blocked"` with a `reason`.
- **Never** `prompt_file: null`, missing, empty, or pointing at a non-existent path (FR-006).

**Verify**:

```bash
python -c "
import json, os
d = json.load(open('next-issue.json'))
if d['status'] == 'issued':
    pf = d['step']['prompt_file']
    assert pf and os.path.exists(pf), f'unresolvable prompt_file: {pf!r}'
"
```

---

## Step 8 — Advance the runtime

```bash
spec-kitty next --result success --json > next-advance.json
```

**Expect**:

- Strict envelope per `contracts/next-advance.json`.
- `.kittify/events/profile-invocations/` exists.
- The directory contains paired `started` and `completed` records for the action that was just issued and advanced (FR-007). The `completed` record's `outcome` is `done` (or whatever value matches the success result), drawn from the accepted vocabulary.

**Verify**:

```bash
ls .kittify/events/profile-invocations/
# Inspect a record file:
python -c "
import json, glob
files = sorted(glob.glob('.kittify/events/profile-invocations/*'))
events = [json.load(open(f)) for f in files]
kinds = {e['event'] for e in events}
assert {'started','completed'} <= kinds, f'missing lifecycle pair: {kinds}'
"
```

---

## Step 9 — Retrospect summary (if part of tranche-1 spine)

```bash
spec-kitty retrospect summary --json > retro.json
```

**Expect**:

- Exactly one JSON document on stdout.

(WP01 research confirms whether retrospect is part of the tranche-1 spine or has been moved out; if not present, this step is dropped from the E2E.)

---

## Step 10 — Source-checkout pollution guard

After the run completes, the source checkout must be unchanged (FR-012, NFR-004). The E2E asserts this internally; humans can verify with:

```bash
cd /path/to/spec-kitty-source-checkout
git status --porcelain   # expect empty
```

---

## What the strict E2E removes

This walk maps 1:1 to the strict E2E. Compared to the PR #838 version, the strict E2E removes:

| Removed bypass | What it tolerated | Now enforced by |
|---|---|---|
| `_parse_first_json_object` | Trailing junk after first JSON object | Strict full-stream `json.loads` (FR-009) |
| `_bootstrap_schema_version` | Hand-stamping schema fields in `.kittify/metadata.yaml` | FR-001 + Step 1 verify |
| Manual `git add` for generate↔validate | Undocumented operator action | FR-002 + Step 2 follow-the-instruction |
| `--dry-run-evidence` fallback | Seeding doctrine via debug path | FR-004 + Step 5 |
| Hand-seeding `.kittify/doctrine/` | Test pre-creating expected artifacts | FR-004 + Step 5 |
| Conditional prompt-file acceptance | Tolerating `prompt_file: null` | FR-006 / FR-011 + Step 7 |
| Profile-invocation early-return | Tolerating missing lifecycle dir | FR-007 / FR-010 + Step 8 |

Each row is a regression the strict gate now catches.

---

## Verification commands (mirrors NFR-001..006)

```bash
# Narrow gate
uv run pytest tests/e2e/test_charter_epic_golden_path.py -q -s

# Targeted gates
uv run pytest tests/e2e tests/next \
  tests/integration/test_documentation_runtime_walk.py \
  tests/integration/test_research_runtime_walk.py -q
uv run pytest tests/charter tests/specify_cli/mission_step_contracts \
  tests/doctrine_synthesizer -q
uv run ruff check src tests

# Strict typing
uv run mypy --strict src/specify_cli src/charter src/doctrine \
  tests/e2e/test_charter_epic_golden_path.py

# Determinism (run 5×)
for i in 1 2 3 4 5; do
  uv run pytest tests/e2e/test_charter_epic_golden_path.py -q || break
done
```

All commands must exit 0.
