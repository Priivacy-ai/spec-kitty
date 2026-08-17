# Quickstart: Verifying the Org-Tier Doctrine Fixes

This is a reviewer/implementer runbook for reproducing each defect pre-fix and confirming the
fix post-fix, using the same synthetic-org-pack methodology the spec's D-000(4) live-verified in
this checkout (347 → 348 DRG nodes). It complements, not replaces, the committed regression tests
(NFR-001) — use this to sanity-check the mechanism by hand before trusting a green test run.

## Prerequisites

```bash
cd <repo-root>   # your spec-kitty checkout
git branch --show-current   # must be pr/up-org-doctrine-consumers-01M05YAB
```

All commands below assume this working directory and branch.

## 1. Reproduce FR-002's baseline (pre-fix): DRG node count with no org root

```bash
.venv/bin/python -c "
from pathlib import Path
from charter._drg_helpers import load_validated_graph
graph = load_validated_graph(Path('.'))
print('node count (no org_root):', len(graph.nodes))
"
```

Expected: **347** (matches D-000(4)'s live-verified figure for this checkout at the time the spec
was authored; a small drift is possible if the built-in graph has grown since — treat 347 as the
*current* baseline to diff against, not a hardcoded eternal constant).

## 2. Build a minimal synthetic org pack

Mirror `tests/charter/test_org_scan_dirs_activation_regression.py::_write_org_directive_fixture`'s
shape — a flat-layout pack with one directive artifact file and one root-level DRG fragment:

```bash
mkdir -p /tmp/org-pack-quickstart/directives
cat > /tmp/org-pack-quickstart/directives/quickstart-probe.directive.yaml <<'EOF'
id: quickstart-probe
EOF
cat > /tmp/org-pack-quickstart/quickstart-probe.graph.yaml <<'EOF'
schema_version: "1.0"
generated_at: "2026-08-16T00:00:00Z"
generated_by: "quickstart"
nodes:
  - urn: "directive:quickstart-probe"
    kind: directive
edges: []
EOF
```

## 3. Confirm FR-002's fix: DRG node count with the synthetic org root supplied

```bash
.venv/bin/python -c "
from pathlib import Path
from charter._drg_helpers import load_validated_graph
graph = load_validated_graph(Path('.'), org_root=Path('/tmp/org-pack-quickstart'))
print('node count (with org_root):', len(graph.nodes))
print('probe node present:', any(n.urn == 'directive:quickstart-probe' for n in graph.nodes))
"
```

Expected: **348** (baseline + 1) and `probe node present: True`. This is SC-001's measurement —
the same delta the committed regression test in
`tests/specify_cli/mission_step_contracts/test_executor.py` asserts, but resolved through
`StepContractExecutor.execute()`'s own org-root-resolution path (post-IC-02) rather than by hand.

## 4. FR-001 pre/post check: org-only step contract visibility

Pre-fix (on `main` / before IC-02 lands), `MissionStepContractRepository` constructed the way
`executor.py`'s `__init__` did (project-dir only) cannot see an org-only contract:

```bash
.venv/bin/python -c "
from pathlib import Path
from doctrine.missions.step_contracts import MissionStepContractRepository
repo = MissionStepContractRepository(project_dir=Path('.kittify/doctrine/mission_step_contracts'))
print(repo.get_by_action('quickstart-mission', 'quickstart-action'))
"
```

Expected pre-fix: `None` even if an org pack ships a matching contract, because no `org_dirs` was
passed. Post-fix (IC-02 landed), the same call inside `StepContractExecutor.__init__` passes
`org_dirs=resolve_org_dirs(repo_root, "mission_step_contracts")`, so an org-only contract becomes
visible. This is SC-002's True/False mechanism.

## 5. FR-007: unresolved delegation candidate WARNING

Run any step contract with a `delegates_to.candidates` entry pointing at a nonexistent directive id
(the shipped `software-dev/specify` contract already has 7 real candidates — for a quick negative
control, pick a contract/action whose candidates are known to resolve; for the positive case, edit
a copy of a fixture contract to add one bogus candidate id) through
`_dispatch_via_composition`, with logging captured:

```bash
.venv/bin/python -c "
import logging
logging.basicConfig(level=logging.WARNING)
# ... invoke _dispatch_via_composition against a fixture with one bad candidate ...
"
```

Expected post-fix: one `WARNING` line naming the step id, contract id, and the bogus candidate
string. This is SC-004's mechanism — the committed test in `tests/runtime/test_bridge_composition.py`
uses `caplog` instead of manual logging config.

## 6. FR-008: expected-artifacts org override

```bash
mkdir -p /tmp/org-pack-quickstart/software-dev
cat > /tmp/org-pack-quickstart/software-dev/expected-artifacts.yaml <<'EOF'
schema_version: "1.0"
mission_type: software-dev
required_always:
  - quickstart-compliance-doc.md
required_by_step: {}
EOF
```

Post-fix, loading the manifest for `software-dev` with `repo_root` pointed at a project configured
to use `/tmp/org-pack-quickstart` as an org pack should return a manifest whose
`required_always` includes `quickstart-compliance-doc.md` — a content delta versus the built-in-only
baseline. This is SC-005's mechanism.

## Cleanup

```bash
rm -rf /tmp/org-pack-quickstart
```

## What this quickstart does NOT cover

- FR-004 (governance-profile) and FR-005/FR-006/FR-006a (gate bindings, runtime dispatch,
  mission-load validation) follow the identical org-pack-fixture pattern above, adapted to their
  own entry points (`resolve_mission_type_context`, `load_gate_bindings`,
  `_resolve_runtime_contract_for_step`, `_resolve_contract_refs` respectively) — omitted here for
  brevity; the committed regression tests are the authoritative reproduction for those four.
- This is a manual sanity-check aid, not a substitute for the red-first committed regression tests
  NFR-001 requires, nor for the reviewer verification checklist in `plan.md`'s Verification &
  Measurement Plan section.
