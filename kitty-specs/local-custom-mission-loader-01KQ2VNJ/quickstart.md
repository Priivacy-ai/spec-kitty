# Quickstart: Author and run a local custom Spec Kitty mission

This how-to walks an operator through authoring, validating, and running a project-authored custom mission with the Local Custom Mission Loader (Phase 6 / WP6.5).

## 1. Author the mission YAML

Create `.kittify/missions/<your-key>/mission.yaml` in your project. Example for the reference ERP mission used in tests (`tests/fixtures/missions/erp-integration/mission.yaml`):

```yaml
mission:
  key: erp-integration
  name: ERP Integration
  version: 0.1.0
  description: Lookup an ERP record, ask the operator a question, and emit a JS adapter.

steps:
  - id: query-erp
    title: Query the ERP system
    description: Pull the active record set from the ERP integration endpoint.
    agent_profile: researcher-robbie

  - id: lookup-provider
    title: Look up the matching provider
    description: For each ERP record, resolve the provider record from the directory.
    agent_profile: researcher-robbie
    depends_on: [query-erp]

  - id: ask-user
    title: Confirm the export shape
    description: Ask the operator which export shape to emit (per-record vs. batch).
    requires_inputs: [export_shape]
    depends_on: [lookup-provider]

  - id: create-js
    title: Generate the JS adapter
    agent_profile: implementer-ivan
    depends_on: [ask-user]

  - id: refactor-function
    title: Refactor the legacy function for the new adapter
    agent_profile: implementer-ivan
    depends_on: [create-js]

  - id: write-report
    title: Summarize the run
    agent_profile: researcher-robbie
    depends_on: [refactor-function]

  - id: retrospective
    title: Mission retrospective marker
    description: Reserved structural marker. Execution lands in a later tranche (#506-#511).
    depends_on: [write-report]
```

Notes:
- `agent_profile` accepts either `agent_profile` (snake) or `agent-profile` (kebab) in YAML.
- A step with `requires_inputs` is a decision-required gate; the runtime pauses and the operator answers via `spec-kitty agent decision resolve …`.
- The final step's `id` MUST be `retrospective`. The validator rejects missions without this marker.

## 2. Run the mission

```bash
spec-kitty mission run erp-integration --mission erp-q3-rollout --json
```

Expected JSON (success):

```json
{
  "result": "success",
  "mission_key": "erp-integration",
  "mission_slug": "erp-q3-rollout-01KQ…",
  "mission_id": "01KQ…",
  "feature_dir": "/abs/path/kitty-specs/erp-q3-rollout-01KQ…",
  "run_dir": "/abs/path/.kittify/runtime/runs/<run-id>",
  "warnings": []
}
```

## 3. Advance the runtime

```bash
spec-kitty next --agent claude --mission erp-q3-rollout-01KQ…
```

The runtime walks composed steps through the same composition path that `software-dev` uses, with `profile_hint` sourced from each step's `agent_profile`.

## 4. Answering decision-required steps

When a `requires_inputs` step is the active step, `spec-kitty next` exits with `decision_required`. Resolve it as you would for any other mission:

```bash
spec-kitty agent decision resolve <decision_id> --mission erp-q3-rollout-01KQ… \
  --final-answer "per-record"
```

Then re-run `spec-kitty next` to advance.

## 5. Validation errors

If the mission YAML is missing the retrospective marker:

```bash
$ spec-kitty mission run erp-integration --mission erp-q3-rollout --json
{
  "result": "error",
  "error_code": "MISSION_RETROSPECTIVE_MISSING",
  "message": "Custom mission 'erp-integration' has no retrospective marker step.",
  "details": {
    "file": "/abs/path/.kittify/missions/erp-integration/mission.yaml",
    "mission_key": "erp-integration",
    "actual_last_step_id": "write-report",
    "expected": "retrospective"
  },
  "warnings": []
}
$ echo $?
2
```

If the mission YAML uses a reserved key like `software-dev`:

```bash
$ spec-kitty mission run software-dev --mission whatever --json
{
  "result": "error",
  "error_code": "MISSION_KEY_RESERVED",
  "message": "Mission key 'software-dev' is reserved for the built-in mission. Rename your custom mission.",
  "details": {
    "mission_key": "software-dev",
    "file": "/abs/path/.kittify/missions/software-dev/mission.yaml",
    "tier": "project_legacy",
    "reserved_keys": ["software-dev", "research", "documentation", "plan"]
  },
  "warnings": []
}
```

The full closed enumeration of error codes is in [contracts/validation-errors.md](./contracts/validation-errors.md).

## 6. Where definitions are discovered

Discovery uses the existing internal-runtime precedence chain (highest precedence first):

1. **Explicit path** — `--mission-path <path>` (forthcoming or env-forwarded; not exposed by `mission run` directly in v1).
2. **Environment variable** — `SPEC_KITTY_MISSION_PATHS=/path/one:/path/two`.
3. **Project override** — `.kittify/overrides/missions/<key>/mission.yaml`.
4. **Project legacy** — `.kittify/missions/<key>/mission.yaml`.
5. **User global** — `~/.kittify/missions/<key>/mission.yaml`.
6. **Project config (mission packs)** — `.kittify/config.yaml mission_packs: [...]` referencing `mission-pack.yaml` manifests.
7. **Built-in** — `software-dev`, `research`, `documentation`, `plan`.

Custom missions cannot use a built-in key; the loader rejects with `MISSION_KEY_RESERVED`. Non-built-in shadowing emits a `MISSION_KEY_SHADOWED` warning and uses the higher-precedence layer.

## 7. What is NOT in v1

- No SaaS mission registry, no `mission install`, no cross-team distribution (deferred under [#516](https://github.com/Priivacy-ai/spec-kitty/issues/516)).
- No retrospective execution, no `retrospective.yaml`, no synthesizer handoff (deferred under #506-#511).
- No new built-in missions ship in this tranche.
