# Quickstart: Verifying the Tranche 2 Fixes

**Mission**: `release-3-2-0a6-tranche-2-01KQ9MKP`

This walkthrough verifies the seven defects are resolved by reproducing the documented golden path on a fresh project and inspecting the relevant artifacts.

---

## Prerequisites

- A POSIX shell.
- `spec-kitty` CLI installed from the tranche-2 build (this branch).
- For SaaS-touching invocations: `export SPEC_KITTY_ENABLE_SAAS_SYNC=1` (per machine-level AGENTS.md).

---

## 1. Fresh-project golden path (validates #840, #841, #839)

```bash
mkdir /tmp/sk-tranche2-demo && cd /tmp/sk-tranche2-demo
git init -q

# Init a fresh project — should stamp metadata schema fields automatically (#840).
spec-kitty init

# Inspect: schema fields are present, no manual editing required.
grep -E '^(schema_version|schema_capabilities)' .kittify/metadata.yaml

# Charter setup → generate → synthesize, no manual git operations.
spec-kitty charter setup       # interactive on a real run; scriptable via flags in tests
spec-kitty charter generate    # auto-tracks charter.md (#841)
spec-kitty charter bundle validate    # MUST succeed without an intervening `git add`

spec-kitty charter synthesize  # works on fresh project, no .kittify/doctrine/ hand seeding (#839)

# Drive `next` once.
spec-kitty next --agent claude
```

**Expected**: every command above exits 0. No manual `git add`, no hand edits to `.kittify/metadata.yaml`, no hand seeding of `.kittify/doctrine/`.

---

## 2. Strict `--json` parsing under SaaS failure (validates #842)

```bash
# Force SaaS off-and-unauthenticated:
unset SPEC_KITTY_ENABLE_SAAS_SYNC

# Pipe a --json command into strict json.loads:
spec-kitty agent mission branch-context --json | python -c 'import sys, json; json.loads(sys.stdin.read()); print("OK")'
```

**Expected**: prints `OK`. Any sync diagnostic appears on stderr only.

Repeat with the four SaaS states:
- `disabled`: as above.
- `unauthorized`: SaaS reachable, missing/invalid auth — same expectation.
- `network-failed`: simulate by blocking the SaaS host — same expectation.
- `authorized-success`: SaaS reachable + authorized — same expectation.

---

## 3. Agent identity preservation (validates #833)

In a real mission, run an implement step with a 4-arity agent string:

```bash
spec-kitty agent action implement WP01 --agent claude:opus-4-7:reviewer-default:reviewer
```

**Expected**: the rendered implement / review prompt includes `opus-4-7`, `reviewer-default`, and `reviewer`. Inspect via the prompt-rendering test fixtures or by viewing the generated `.kittify/.../implement-prompt.md` file. No silent fallback to default `model` / `profile_id` / `role` unless those segments were not supplied.

Verify partial-string fallbacks too:

```bash
spec-kitty agent action implement WP01 --agent claude:opus-4-7
```

**Expected**: `model = opus-4-7`; `profile_id` and `role` fall back to documented defaults.

---

## 4. Review-cycle counter precision (validates #676)

In a mission with a WP currently in `for_review`:

```bash
# Re-run implement multiple times without any reviewer rejection.
for i in 1 2 3 4; do
  spec-kitty agent action implement WPNN --agent claude
done

# Inspect counter and artifacts.
spec-kitty agent tasks status --feature <mission-slug>
ls .kittify/<mission>/...review-cycle-*.md
```

**Expected**: the review-cycle counter for `WPNN` is unchanged across all 4 runs; no new `review-cycle-N.md` files were created.

Now simulate a real rejection and re-check:

```
... reviewer rejects WPNN ...

ls .kittify/<mission>/...review-cycle-*.md
```

**Expected**: exactly one new `review-cycle-N.md` exists where `N` matches the post-increment counter value.

---

## 5. Profile-invocation lifecycle records (validates #843)

Drive a `next` cycle:

```bash
spec-kitty next --agent claude --mission <mission-handle>
# ... agent acts on the issued action ...
spec-kitty next --agent claude --mission <mission-handle>   # advance
```

Inspect the local invocation store:

```bash
# Implementation detail of the local store path; a `doctor` surface should list orphans.
spec-kitty doctor identity --json     # or the equivalent invocation-doctor surface
```

**Expected**: paired `started` and `completed` records exist for the action `next` issued, with the same `canonical_action_id`. If you Ctrl-C between issuance and advance, the orphan `started` is observable on the doctor output rather than silently overwritten on the next run.

---

## 6. Run the consolidated E2E

```bash
PWHEADLESS=1 pytest tests/e2e/test_charter_epic_golden_path.py -v
```

**Expected**: passes within the < 120s budget (NFR-007). The test no longer hand-seeds `.kittify/doctrine/` and no longer hand-edits `.kittify/metadata.yaml`.

---

## Negative paths (sanity checks)

- Run `charter generate` outside a git repo: should exit non-zero with an actionable error naming the remediation (FR-014).
- Run `init` on a directory with a hand-edited `metadata.yaml`: existing keys must be byte-identical post-`init` (NFR-008).
- Run `implement` with an unknown agent string `claude:opus-4-7:::`: empty trailing segments fall back to defaults; no silent discard.

---

## Acceptance summary

If every step above behaves as expected, the seven defects are closed and the tranche-2 acceptance criteria from `spec.md` are satisfied:

- ✅ Fresh `init → charter setup/generate/synthesize → next` paths require no manual metadata or doctrine seeding.
- ✅ `json.loads(stdout)` succeeds on covered `--json` commands across the four SaaS states.
- ✅ Agent identity preserves `tool`, `model`, `profile_id`, `role`.
- ✅ Review-cycle counter advances only on real rejections.
- ✅ `next` writes paired profile-invocation lifecycle records.
