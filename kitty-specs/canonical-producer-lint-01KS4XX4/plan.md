# Plan — Canonical Producer Lint (AST CI rule)

**Spec**: [`spec.md`](spec.md)
**Mission slug**: `canonical-producer-lint-01KS4XX4`
**Issue**: [Priivacy-ai/spec-kitty#1248](https://github.com/Priivacy-ai/spec-kitty/issues/1248)

## 1. Architecture

### 1.1 Single-source-of-truth model

```
spec-kitty/scripts/lint_canonical_producers.py     ← THE rule (Python stdlib `ast` only)
                  │
                  ├── invoked by spec-kitty/.github/workflows/canonical-producer-lint.yml (local path)
                  ├── invoked by spec-kitty-saas/.github/workflows/canonical-producer-lint.yml (clone @ pinned SHA)
                  └── invoked by spec-kitty-e2e-testing/.github/workflows/canonical-producer-lint.yml (clone @ pinned SHA)
```

The script is the only place the rule lives. The two cross-repo workflows clone `spec-kitty` at a pinned SHA (captured at the time of writing — recorded in workflow env as `SPEC_KITTY_LINT_SHA`) and invoke `python <clone>/scripts/lint_canonical_producers.py --paths <repo-paths>`. When the rule needs to evolve, all three workflows re-point the SHA in a single follow-up sweep.

### 1.2 Visitor architecture

```python
class _CanonicalProducerVisitor(ast.NodeVisitor):
    # Per-file state
    findings: list[Finding]
    exemptions_by_line: dict[int, ExemptionToken]   # line → parsed exemption
    canonical_names: set[str]                       # local names bound to canonical models
                                                     # (e.g. `payload = WPApprovedPayload(...)`)

    def visit_ImportFrom(self, node): ...           # tracks `from spec_kitty_events.lifecycle import *Payload`
    def visit_Assign(self, node): ...               # tracks `x = SomeCanonicalPayload(...)`
    def visit_AnnAssign(self, node): ...            # tracks `x: SomePayload = ...`
    def visit_FunctionDef(self, node): ...          # checks (b): dict[str, Any] return + event-shaped body
    def visit_AsyncFunctionDef(self, node): ...     # same as FunctionDef
    def visit_Call(self, node): ...                 # checks (c): emit_*/enqueue_*/send_event with inline dict payload=
    def visit_Dict(self, node): ...                 # checks (a): {event_type, payload} dict literals
```

Findings are filtered against `exemptions_by_line` after visit. An exemption with an invalid tracker still produces a finding (the message says "exemption is missing tracker ref").

Exemptions are parsed from tokenized comments (using `tokenize`), keyed by the comment's line number, then attached to AST nodes by matching the node's line range. A comment on the line before a dict literal exempts the literal; a comment on the dict literal's first key line also exempts.

### 1.3 Canonical-name detection

The lint considers a dict NOT a violation if it is:

- The argument to a call whose `func.attr` or `func.id` ends in `Payload`, `Envelope`, or matches `StatusEvent` / `EventEnvelope` / `LifecycleEvent`.
- A `.model_dump()` call result (i.e. the dict literal is conceptually replaced by pydantic-derived data — but `.model_dump()` returns a dict, not a literal, so this is structurally not a `Dict` node and is therefore not visited).
- Bound to a name that the visitor recognizes as a canonical instance (e.g. `event = {"event_type": ..., "payload": payload_obj.model_dump()}` is still a violation; the lint is intentionally strict — refactor to `LifecycleEvent(event_type=..., payload=payload_obj).model_dump()`).

The set of canonical model name suffixes is a constant at the top of the script:

```python
_CANONICAL_SUFFIXES = ("Payload", "Envelope", "Event")
_CANONICAL_NAMES = {"StatusEvent", "EventEnvelope", "LifecycleEvent"}
_EMIT_NAME_PATTERNS = (re.compile(r"^emit_"), re.compile(r"^enqueue_"), re.compile(r"^send_event$"))
```

## 2. Files and file surfaces

### 2.1 spec-kitty (this repo)

- **NEW** `scripts/lint_canonical_producers.py` — ~250 lines including docstring, visitor, CLI, exit codes.
- **NEW** `tests/lint/__init__.py` — empty package init.
- **NEW** `tests/lint/test_canonical_producers.py` — ~200 lines, ~15 test cases covering each AC.
- **NEW** `tests/lint/fixtures/` — synthetic Python files for positive / negative / exempt cases.
- **NEW** `.github/workflows/canonical-producer-lint.yml` — runs on PR + push to main; invokes `python scripts/lint_canonical_producers.py --paths src scripts tests`.

### 2.2 spec-kitty-saas

- **NEW** `.github/workflows/canonical-producer-lint.yml` — clones spec-kitty at pinned SHA, runs against repo Python tree excluding `apps/`.
- **NO CHANGES** to `apps/` (owned by sibling subagent #258).
- **NO CHANGES** to any existing `.github/workflows/` files.

### 2.3 spec-kitty-end-to-end-testing

- **NEW** `.github/workflows/canonical-producer-lint.yml` — clones spec-kitty at pinned SHA, runs against repo's Python tree.
- **NO CHANGES** to any existing `.github/workflows/` files.

### 2.4 Workspace doc (orchestrator-owned, NOT this mission)

Mission return contract proposes the diff for `spec-kitty-mission-workflow.md`:

- 5-line section under "Non-negotiables (summary)" or as a new "Harness drift class — operating doctrine" section.
- One-line cross-reference embedded in the existing C-007 line.

## 3. Data / control flow

### 3.1 Invocation

```bash
# Local (developer)
python scripts/lint_canonical_producers.py --paths src/ scripts/

# CI (spec-kitty)
python scripts/lint_canonical_producers.py --paths src scripts tests

# CI (saas, e2e — after cloning spec-kitty)
python "$SPEC_KITTY_CLONE/scripts/lint_canonical_producers.py" --paths src
```

Exit codes:

- `0` — no violations
- `1` — at least one violation
- `2` — usage error (bad `--paths`, etc.)

Output: one finding per line, format `<path>:<line>:<col>: <code> <message>`. Codes:

- `CP001` — dict literal with `event_type`+`payload` outside canonical model call
- `CP002` — `dict[str, Any]`-returning function builds event-shaped dict
- `CP003` — inline dict as `payload=` kwarg to emit/enqueue/send_event
- `CP900` — exemption present but tracker ref missing or malformed

### 3.2 Workflow trigger

```yaml
on:
  pull_request:
    paths: ["**/*.py"]
  push:
    branches: [main]
```

Job runs on `ubuntu-latest`, uses Python 3.11 (matches the repo's other workflows). For saas + e2e, the workflow clones spec-kitty at `${{ env.SPEC_KITTY_LINT_SHA }}` (captured at writing time via `gh api repos/Priivacy-ai/spec-kitty/commits/main --jq .sha`).

## 4. Test strategy

### 4.1 Unit tests (`tests/lint/test_canonical_producers.py`)

Each test parses a small Python snippet, runs the visitor, asserts on findings. Behavior-only assertions (which code, which line, how many findings) — no assertions on visitor internals.

| Test | Asserts |
|---|---|
| `test_lint_clean_canonical_construction_zero_findings` | `WPApprovedPayload(...)` → 0 findings |
| `test_lint_hand_rolled_event_dict_class_a` | `{"event_type": "X", "payload": {...}}` → CP001 |
| `test_lint_canonical_dict_inside_payload_call_zero_findings` | `EventEnvelope(payload={"event_type": ..., "payload": ...})` → 0 (it's inside a canonical call) |
| `test_lint_dict_str_any_return_class_b` | `def f() -> dict[str, Any]: return {"event_type": "X", "payload": ...}` → CP002 |
| `test_lint_dict_str_any_return_no_event_shape_zero_findings` | `def f() -> dict[str, Any]: return {"foo": 1}` → 0 |
| `test_lint_emit_with_inline_dict_payload_class_c` | `emit_status(payload={...})` → CP003 |
| `test_lint_emit_with_model_dump_zero_findings` | `emit_status(payload=p.model_dump())` → 0 |
| `test_lint_emit_with_name_bound_zero_findings` | `payload = WPApprovedPayload(...); emit_status(payload=payload)` → 0 |
| `test_lint_exempt_valid_tracker_zero_findings` | `# canonical-producer-exempt: #1248 — ...` → 0 |
| `test_lint_exempt_invalid_tracker_cp900` | `# canonical-producer-exempt: TODO` → CP900 |
| `test_lint_exempt_above_literal` | comment on prior line still exempts |
| `test_lint_exit_code_zero_on_clean` | CLI returns 0 |
| `test_lint_exit_code_one_on_violation` | CLI returns 1 |
| `test_lint_exit_code_two_on_usage_error` | CLI returns 2 |
| `test_lint_self_scan_of_repo` | `python scripts/lint_canonical_producers.py --paths src scripts tests` returns 0 (or has documented exemptions only) |

### 4.2 Integration

CI workflow invocation is the integration test. When the PR opens, the workflow runs against the diff; we observe a green check (or a red check for a deliberately-introduced violation in the existing-exemption audit step).

## 5. Implementation strategy

### 5.1 Build order

1. **WP01 — Lint script + unit tests.** Land the script and its tests in `spec-kitty/`. This is the canonical artifact; everything downstream depends on it.
2. **WP02 — Existing-exemption audit.** Run the script against `spec-kitty`, `spec-kitty-saas` (non-`apps/`), `spec-kitty-end-to-end-testing`. Document findings in `kitty-specs/.../existing-exemptions-audit.md`. Add inline exemption comments where genuinely needed; tighten the rule if the false-positive rate exceeds 5%.
3. **WP03 — spec-kitty CI hook.** Add `.github/workflows/canonical-producer-lint.yml` in this repo.
4. **WP04 — spec-kitty-saas CI hook.** Add the workflow file in saas (via `git worktree add` on the saas repo). Pinned SHA = the merge commit from WP03 (or the head-of-main at workflow-write time if WP03 hasn't merged yet — re-point in a follow-up if needed).
5. **WP05 — spec-kitty-e2e-testing CI hook.** Same shape as WP04.

### 5.2 Dependencies

- WP01 → WP02 → WP03, WP04, WP05 (WP02 depends on the script; WP03-05 depend on having something stable to invoke).
- WP04 and WP05 are parallel after WP02. WP03 is parallel with WP04/WP05 once WP02 is clean.

### 5.3 Cross-repo coordination

For WP04 and WP05, use `git worktree add` from the canonical sibling repo paths so we don't clobber sibling subagents (#258 in saas, #61 in e2e) who have their own checkouts.

```bash
# saas
git -C /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-saas \
  worktree add ../spec-kitty-saas-canonical-lint kitty/canonical-producer-lint

# e2e
git -C /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-end-to-end-testing \
  worktree add ../spec-kitty-end-to-end-testing-canonical-lint kitty/canonical-producer-lint
```

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| False positives on existing canonical code | Self-scan in WP02; tighten rule before opening any PR. Stop condition at 5%. |
| File-level collision with #1247 in spec-kitty | #1247 uses `canary-gate.yml`; we use `canonical-producer-lint.yml`. Different files. Document if collision surfaces. |
| Pinned SHA goes stale | Document re-point procedure in workflow file comment. Future mission can wire an automated refresh. |
| Tracker-ref regex too narrow | Permit `<repo>?#\d+` (so both `#1248` and `Priivacy-ai/spec-kitty#1248` pass). |
| AST visitor misses async function defs | Test case `test_lint_async_dict_str_any_return_class_b` (covered in WP01). |
| Comment-attribution off-by-one (comment above literal vs on literal) | Both positions exempt; covered by `test_lint_exempt_above_literal`. |

## 7. Operating-rule compliance

- **No SaaS DB mutation** — N/A; this mission adds CI only.
- **No ingress-limit changes** — N/A.
- **No final 3.2.0 cut** — N/A; no version bump.
- **`unset GITHUB_TOKEN`** — required before every `gh` write (PR creation, audit comments).
- **No direct pushes to main** — confirmed; all changes via PR.
- **Producers construct via canonical pydantic** — applies to this mission itself; lint script writes no events; workflows produce no events. Self-clean by construction.
- **`spec-kitty next` is the only entry point** — confirmed.
- **`status.events.jsonl` sole authority** — confirmed; no direct edits.
- **Reviewer-renata** — required, after `analyze` clean.
- **Frontend-freddy** — not triggered (no frontend surfaces).
