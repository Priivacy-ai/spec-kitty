# Phase 1 Data Model: 3.2.0a6 Tranche 2

This document captures the touched data shapes. Anything not listed here is unchanged.

---

## 1. `.kittify/metadata.yaml` — Project Metadata File

**Purpose**: per-project metadata file consumed by the runtime and migration code.

**Shape after `init` (post-#840)**:

```yaml
schema_version: <int>            # canonical migration target version known to the runtime
schema_capabilities:
  <capability_key>: <bool>       # additive map of capability flags supported by this schema
# Operator-authored keys (if any) preserved verbatim alongside the schema fields.
```

**Invariants**:

- `schema_version` is a non-empty integer matching the migration runner's known target at `init` time.
- `schema_capabilities` is a non-empty mapping of `str → bool`.
- `init` MUST be additive — operator-authored keys present before `init` are preserved byte-identical.
- Re-running `init` is idempotent: the resulting file content equals the prior content (modulo independent timestamps if any).

**Validation rules**:

- If the file exists and contains `schema_version` and `schema_capabilities`, do not overwrite.
- If the file exists but lacks one or both schema fields, merge in the missing fields without touching other keys.
- If the file does not exist, create it with both schema fields populated.

---

## 2. ResolvedAgent — Agent Identity 4-Tuple

**Purpose**: machine-resolved identity attached to a work package; consumed by implement / review prompt rendering.

**Shape**:

```
ResolvedAgent = (tool: str, model: str, profile_id: str, role: str)
```

**Construction rules** (from input string `s` to `WPMetadata.resolved_agent()`):

| Input segments | Result |
|---|---|
| `tool` | `(tool, default_model[tool], default_profile_id[tool], "implementer")` |
| `tool:model` | `(tool, model, default_profile_id[tool], "implementer")` |
| `tool:model:profile_id` | `(tool, model, profile_id, "implementer")` |
| `tool:model:profile_id:role` | `(tool, model, profile_id, role)` |

**Empty-segment handling**: An empty positional segment falls back to its default (e.g., `tool::profile_id:role` → uses default `model`).

**Invariants**:

- `tool` is always present and non-empty.
- `model`, `profile_id`, `role` are always non-empty in the resulting tuple (defaults fill any blanks).
- Parsing is total — no input shape silently discards fields.

**Defaults table** (illustrative; existing values from the agent registry):

- `default_model[claude]` = the agent registry's current Claude default
  (when not in `_AGENT_DEFAULTS`, falls back to frontmatter `model`, then to
  the constant `"unknown-model"`)
- `default_profile_id[<tool>]` = the agent registry's current default profile
  for that tool (when not in `_AGENT_DEFAULTS`, falls back to frontmatter
  `agent_profile`, then to the deterministic synthetic default
  `f"{tool}-default"`)
- `role` default = `implementer`

---

## 3. ReviewCycleCounter — Per-WP Review Counter

**Purpose**: tracks how many real review rejections a work package has received.

**Shape**:

```
ReviewCycleCounter:
  wp_id: str
  count: int >= 0
  artifacts: list[Path]   # one review-cycle-N.md per integer N in [1, count]
```

**Invariants**:

- Monotonic: `count` only ever increases.
- Advances exactly once per real `rejection` event for `wp_id`.
- For each integer `N` in `[1, count]`, exactly one `review-cycle-N.md` artifact exists.
- Reclaim / regenerate of an implement prompt MUST NOT change `count` and MUST NOT write a new artifact.

**State transitions**:

```
(count = N, no artifact for N+1)
  ── rejection event ──>
(count = N+1, new artifact review-cycle-(N+1).md)
```

There is no transition that advances `count` in response to a non-rejection event.

---

## 4. ProfileInvocationRecord — Lifecycle Pair

**Purpose**: paired records observable to local tooling that capture each public action issued by `next`.

**Shape**:

```
ProfileInvocationRecord:
  canonical_action_id: str        # = mission_step::action issued by next
  phase: "started" | "completed" | "failed"
  at: ISO-8601 datetime (UTC)
  agent: str                      # tool key (e.g., "claude")
  mission_id: ULID
  wp_id: str | null               # if action targets a specific WP
  reason: str | null              # for "failed" phase
```

**Invariants**:

- For every `started` record there should eventually exist exactly one paired `completed` or `failed` record sharing the same `canonical_action_id`.
- The `canonical_action_id` of a `started` record MUST equal the canonical mission step/action identifier `next` actually issued (no rewriting at completion time).
- Orphan `started` records (no pair) are observable rather than silently overwritten.

**Pair-matching rule** (validation):

```
match(records) = group records by (mission_id, canonical_action_id)
  for each group:
    expect 1 "started" + (0 or 1) "completed_or_failed"
    flag groups missing a partner record
```

The group key includes `mission_id` so two missions issuing the same
`mission_state::action` cannot cross-pair (a started in mission `m1` and a
completion in mission `m2` would otherwise balance globally and silently
hide the `m1` orphan).

---

## 5. Charter Bundle Validity Surface

**Purpose**: the contract between `charter generate` and `charter bundle validate`.

**Shape (post-#841)**:

```
ChartersBundleState:
  generate.produced_files: list[Path]   # at minimum, charter.md
  git.tracked_files: set[Path]          # files git knows about (staged or committed)
  validity: bool
```

**Invariants**:

- After `charter generate` completes successfully on a git repo, every entry in `generate.produced_files` is in `git.tracked_files` (auto-tracked / staged).
- `charter bundle validate` succeeds iff every required produced file is tracked.
- In a non-git environment, `charter generate` exits non-zero with an actionable error string.

---

## 6. Doctrine Synthesis Surface (#839)

**Purpose**: capture what `charter synthesize` reads/writes on a fresh project.

**Inputs (fresh project)**:
- `.kittify/charter/charter.md` — produced by `charter generate` (post-#841)
- In-package canonical doctrine seed bundled with `spec-kitty` (already present in the repo)

**Outputs**:
- `.kittify/doctrine/` — populated with the artifacts the runtime reads via `DoctrineService` (procedures, tactics, directives, guidelines, action index)

**Invariants**:
- `synthesize` is idempotent: running it twice produces an output set with the same files and bytewise-equal content (modulo any timestamps).
- `synthesize` does not require any pre-existing files under `.kittify/doctrine/` (i.e., no hand seeding).
- Running `synthesize` against a project missing the inputs above fails with an actionable error rather than silently producing an empty doctrine set.

---

## Out-of-scope shapes (not modified by this mission)

- `meta.json` mission identity fields (`mission_id`, `mission_slug`, `mission_number`, `created_at`) — frozen by C-004.
- `status.events.jsonl` schema — unchanged; status model remains canonical.
- Lane / worktree naming — unchanged; ULID + `mid8` model preserved.
- External shared package internals — out of bounds (C-007).
