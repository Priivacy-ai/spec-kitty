---
work_package_id: WP02
title: Golden-CLI characterization harness (the safety net)
dependencies: []
requirement_refs:
- C-003
- FR-001
- NFR-001
planning_base_branch: refactor/wave4-sync-degod
merge_target_branch: refactor/wave4-sync-degod
branch_strategy: Planning artifacts for this mission were generated on refactor/wave4-sync-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into refactor/wave4-sync-degod unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
history:
- Created by /spec-kitty.tasks (Wave-4 sync degod)
agent_profile: python-pedro
authoritative_surface: tests/characterization/
create_intent:
- tests/characterization/test_sync_cli_safe.py
execution_mode: code_change
owned_files:
- tests/characterization/test_sync_cli_safe.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your profile before anything else: `/ad-hoc-profile-load python-pedro`. Then run
`spec-kitty charter context --action implement --json` and apply the resolved
directives/tactics. State which you applied — the ATDD-first tactic
(`acceptance-test-first`) is load-bearing here: this WP *is* the acceptance harness that must
land green **before** any extraction.

## Objective

Freeze the observable CLI contract of the SAFE `spec-kitty sync` subcommands — their exact
**flags**, **exit codes**, and **`--json` envelope shape** — via in-process
`CliRunner().invoke(app, …)` characterization tests. This is the safety net the whole Wave-4
degod rests on: every later extraction commit must keep these snapshots green (INV-1), so the
harness must land **before** the first `sync.py` body is relocated (it is the prerequisite for
the WP03→WP12 chain).

Scope here is the *safe* subcommands — the ones whose golden can be frozen black-box without
stubbing non-deterministic internals. The four GAP commands whose substantive arms are
under-characterized or non-deterministic (`status` full human-render, `doctor`, `sync_workspace`,
and the full-report `diagnose` arm) are **frozen inside their own extraction WPs**
(WP09/WP10/WP11 respectively; WP-translation guard #6) — a "golden done" tick on THIS WP must
NOT be read as satisfying FR-001 for those monsters. You DO freeze the cheap/deterministic
`--json` arms that live on otherwise-safe surfaces (`status --check --json`, `diagnose --json`
skip/empty arms) here.

## Read first (source of truth)

The mission plan.md (IC-02 "Characterization safety net"; the "WP-translation guards" §, esp.
#6 gap-freeze gating, #8 test-env), `contracts/sync-cli-characterization-contract.md` (the
frozen list — items 1, 5, 6, 7 are in-scope here; items 2/3/4 defer to the monster WPs),
`data-model.md` (INV-1 behavior, INV-4 seam), `research/squad-findings-post-plan.md` (Pd-1 the
env-var name, Pr-4 gap-freeze gating). This is a Wave-4 degod: **zero behavior change**; this
WP produces the net that proves it.

## Environment (CRITICAL — worktree vs editable install)

Work in the lane worktree. The repo-root `.venv` editable-install points at the MAIN checkout,
so test YOUR changes with `PYTHONPATH=<worktree>/src`. Define `VENV=<repo>/.venv/bin;
WT=<worktree>`.

Run the harness (the SAAS-enable var is `SPEC_KITTY_ENABLE_SAAS_SYNC`, **NOT**
`SPEC_KITTY_SAAS_SYNC` — the misnamed form reads nothing and silently freezes the *skip* arm,
finding Pd-1):

```
SPEC_KITTY_ENABLE_SAAS_SYNC=1 PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 PYTHONPATH=$WT/src \
  $VENV/python -m pytest tests/characterization/test_sync_cli_safe.py -q -p no:cacheprovider
```

`SPEC_KITTY_ENABLE_SAAS_SYNC=1` reaches the non-skip render arms; `SPEC_KITTY_SYNC_DISABLE=1`
is orthogonal (disables the network/gate work, not render) — pairing both is the hermetic-golden
combo (Pd-5). Lint/type: `$VENV/ruff check <files>`, `$VENV/mypy --strict <files>`.
Real-port/daemon suites run `-n0`. NEVER run the full suite or `uv run`.

## Subtasks

### T004 — Golden harness scaffolding

**Purpose**: stand up the reusable CliRunner fixture set with the correct env + HOME
isolation so every snapshot is hermetic and reproducible.

**Steps**:

- Create `tests/characterization/test_sync_cli_safe.py`. Import the Typer `app` from
  `specify_cli.cli.commands.sync` and drive it with `typer.testing.CliRunner`.
- Add an **autouse** fixture that sets `SPEC_KITTY_ENABLE_SAAS_SYNC=1` (via
  `monkeypatch.setenv`) so invocations reach the non-skip arms; pair with
  `SPEC_KITTY_SYNC_DISABLE=1` where a command would otherwise attempt real network/gate work,
  keeping the golden hermetic.
- Isolate HOME/XDG per-test (tmp_path-based `HOME`, `XDG_*`) so no snapshot depends on the
  developer's real `~/.spec-kitty`. Pin the capture encoding (UTF-8) so emoji glyphs in the
  rendered output are stable.
- Provide a small helper (`invoke(*args)` → `Result`) and an assertion helper that captures
  `(exit_code, stdout)` and, for `--json` arms, `json.loads(stdout)` shape (keys + types, not
  volatile values like timestamps — assert shape/keys, redact/normalize volatile fields).

**Files**: `tests/characterization/test_sync_cli_safe.py`.

**Validation**: the fixture-only file collects and runs (even with a single smoke assertion)
green on the pre-decomposition `sync.py`.

### T005 — Freeze the SAFE subcommands' flags / exit-codes / `--json`

**Purpose**: capture the observable contract for the deterministic surfaces. A
`--json`-happy-path-only freeze does NOT satisfy FR-001 (contract rule 1) — capture the flag
matrix and exit-code arms, not just the success envelope.

**Steps** — one test (or parametrized case) per command, freezing exit code + output shape:

- `routes`, `share` / `unshare`, `opt-in` / `opt-out`, `now`, `gc`, `archive`, `mode`,
  `migrate`, the `project-store-*` family, `import-history`, `server` — freeze `--help`
  (flag set) + the primary invocation exit code + output shape.
- `now` (contract item 5): freeze `--strict` exit, preflight **exit 2**, unauthenticated
  **exit 1**, and the `EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE` recovery arm.
- `status --check --json` (contract item 1): single JSON envelope, **exit 0** (coherent) /
  **exit 2** (incoherent), human block suppressed. This is the `_emit_status_check_json`
  path (sync.py L5209 / L5435) — freeze both exit arms.
- `diagnose --json` (contract item 6): the `{available:false,…}` exit-2 arm and the
  `{total:0,…}` empty arm (both deterministic without a fixture). The full
  `{total,valid,invalid,results:[…]}` report arm needs a fixed event fixture and is deferred
  to its own freeze — capture only the two cheap arms here.
- **The coord exit-0 silent-skip arm** (contract item 7): with SaaS disabled, the guard
  prints the disabled notice and `return`s / `Exit(0)`. Freeze this exact print + exit-0
  behavior so a later extraction cannot accidentally turn a silent-skip into an error.

- **`diagnose` full-report is intentionally NOT frozen** here or anywhere (post-tasks squad
  Rn-4): `diagnose` renders its full `{total,valid,invalid,results:[…]}` report **inline**
  (`console.print` in the command body, ~L5972) and **no WP extracts that render**, so the
  populated-queue full report is outside the decomposition's blast radius. The two cheap
  `--json` arms above are sufficient; do not add a stub-heavy full-report fixture.

- **Freeze the `status` full-human-render AND `doctor` render NOW (post-tasks squad Rn-1 — the
  load-bearing fix).** These renders depend on the shared helpers `_render_per_project_store` /
  `_render_consent_readability` / `_render_tracker_egress`, which **WP04 (render) and WP07
  (store-report split) churn *before* the status/doctor extraction WPs**. If their goldens were
  frozen only in WP09/WP10 they would lock in a WP04/WP07 regression. Freeze them here, in this
  file, stubbing the pre-existing seams (all exist on the un-decomposed `sync.py`):
  - `status` (no `--check`, the full cc-90 render): stub `sync.get_vcs`, `sync._check_server_connection`,
    `sync.scan_sync_daemons` to fixed values; snapshot the full rendered table (all rows +
    the per-project/consent/tracker blocks) + exit code.
  - `doctor` (no args, no `--json` — Pd-3): stub the same seams; snapshot the Rich table +
    issues list + the "No issues detected. Sync is healthy." vs unhealthy summary + the
    `EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE` (exit-4) arm.
  These snapshots are the safety net WP04/WP07 must keep byte-green; WP09/WP10 then *verify*
  them (they do not re-freeze).

**Files**: `tests/characterization/test_sync_cli_safe.py`.

**Validation**: all safe-surface cases + the `status`/`doctor` full-render snapshots green on
pre-decomposition `sync.py`; each captures an exit code AND an output-shape assertion.

### T006 — Enumerate + document the ~60 monkeypatched-callee seam set

**Purpose**: the ~60 existing tests that `monkeypatch.setattr("…commands.sync.<name>", …)`
are an explicit **co-gate** (INV-4). Document the exact seam-name set so later WPs know which
symbols MUST remain reachable as `sync.<name>` attributes after relocation (via the late-bound
`sync_module.<name>` convention established in WP03).

**Steps**:

- Grep the test tree for the seam set and produce the authoritative list:
  ```
  grep -rEno 'setattr\(\s*["'"'"']?[^,]*commands\.sync[.:][A-Za-z_]+' tests/ | sort -u
  ```
  plus string-form patches (`monkeypatch.setattr("specify_cli.cli.commands.sync.<name>", …)`)
  and `patch("…commands.sync.<name>")` decorators.
- Record the deduplicated `<name>` set (expect ~60) as a module-level docstring/constant list
  in `test_sync_cli_safe.py` (or a sibling `SEAM_CALLEES` tuple) — this is the co-gate
  baseline the chain WPs check their relocations against. Do not rely on prose in a research
  file alone; make the list a live artifact in the test module.
- Optionally add a light assertion that each documented seam name currently resolves as an
  attribute of the `sync` module (`getattr(sync_module, name)`), so the baseline is
  executable — this is the pre-decomposition truth WP03+ must preserve.

**Files**: `tests/characterization/test_sync_cli_safe.py`.

**Validation**: the seam list is materialized and (if the assertion is added) green against
today's `sync.py`.

## Constraints (do NOT violate)

- **MUST set `SPEC_KITTY_ENABLE_SAAS_SYNC=1`** (autouse) to reach the non-skip arms — the
  misnamed `SPEC_KITTY_SAAS_SYNC` reads nothing (Pd-1).
- **MUST NOT mutate the DIR-041 positional-anchor ratchet allowlists** (contract rule 5 /
  C-003). The harness only *adds* test files; it never grows a ratchet.
- The four GAP commands (`status` full human-render, `doctor` table, `sync_workspace`,
  `diagnose` full-report) are frozen in WP09/WP10/WP11 — **not here**.

## Branch Strategy

Planning/base + merge target: `refactor/wave4-sync-degod`. The execution worktree is allocated
per the computed lane from `lanes.json` (`spec-kitty implement WP02` prepares it) — do not
reconstruct the path. This is **lane-b** (independent, prerequisite); it may run concurrently
with WP01 but MUST merge before WP03 begins (the chain head depends on it).

## Definition of Done

- [ ] `tests/characterization/test_sync_cli_safe.py` exists and is green on the
      **pre-decomposition** `sync.py` (env recipe above).
- [ ] Every safe subcommand from T005 has a frozen exit-code + output-shape snapshot;
      `now`'s four exit arms and the `status --check --json` exit-0/2 arms are captured.
- [ ] The coord exit-0 silent-skip arm is frozen exactly.
- [ ] The ~60 monkeypatched-callee seam set is enumerated and materialized in the module.
- [ ] `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is set (autouse); no snapshot froze a skip arm by
      accident.
- [ ] DIR-041 ratchets untouched; `ruff` + `mypy --strict` clean on the new file.

## Reviewer Guidance

Verify the WP-translation guards / contract rules that bind this WP:

- **FR-001 depth**: confirm the freeze is not `--json`-happy-path-only — flag matrix + exit
  codes (esp. exit 1/2/4 arms) are captured (contract rule 1).
- **Pd-1 env name**: grep the test for `SPEC_KITTY_ENABLE_SAAS_SYNC` and confirm the misnamed
  `SPEC_KITTY_SAAS_SYNC` appears nowhere. A snapshot that shows only the "sync disabled" skip
  text is a frozen-wrong-arm defect — reject it.
- **Guard #6**: confirm the four GAP commands are NOT frozen here (they belong to their own
  WPs); a `status`/`doctor`/`sync_workspace` full-render snapshot in this file is out of scope.
- **C-003**: confirm no `tests/architectural/_baselines.yaml` / DIR-041 allowlist grew.
- Confirm the seam-callee list is a live artifact (not just referenced prose) and matches a
  fresh grep of the test tree.
