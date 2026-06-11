# Quickstart / Validation — Tooling Stability & Guard Coherence (01KTRC04)

## SC-1 — One guard, no message privilege
```bash
# the #1334 repro (permanent negative test): prefix-crafted message on protected ref → REFUSED
python -m pytest tests/ -k "protection_preserved or 1334 or commit_guard" -q
# structural: only the facade imports protection internals
python -m pytest tests/ -k "safe_commit_import_boundary" -q
rg -n "_is_protected_branch_exception" src/   # expect: gone
```

## SC-2 — Verdict from structure
```bash
# report with clean frontmatter + scary prose ("CRITICAL", "BLOCK") → ready
# report with a critical finding + reassuring prose → blocked
python -m pytest tests/ -k "analysis_findings or record_analysis_verdict" -q
rg -n "infer_verdict|infer_issue_counts" src/specify_cli/analysis_report.py  # expect: replaced/deleted
```

## SC-3 — Fragment threading
```bash
python -m pytest tests/architectural/test_execution_context_parity.py -q   # extended assertion green
rg -n "coord" src/specify_cli/status/aggregate.py | grep -v StatusSurfaceFragment  # no local composition
```

## SC-4 — Debt cleared
```bash
python -m mypy src/doctrine/drg/merge.py --strict          # clean
rg -n 'getattr\(.*"provenance"' src/                        # expect: zero consumers
wc -l src/specify_cli/cli/commands/doctor.py                # reduced; render moved to _profile_health_render.py
```

## SC-5 — No regression
```bash
PWHEADLESS=1 python -m pytest tests/ -q && ruff check . && python -m pytest tests/architectural -q
```

## SC-6 — Protected-target e2e (the catch-22 killer, #1777/#1784)
```bash
# fresh repo, protected main as target:
spec-kitty agent mission create … && /specify → safe-commit spec.md   # commits to RESOLVED destination, no refusal-to-nowhere
/plan && /tasks && spec-kitty agent mission finalize-tasks …          # reads the SAME resolution — no "spec.md not found"
# guard refusal messages (when triggered) name the resolved destination
```

## Ergonomics spot-checks (FR-002)
```bash
spec-kitty safe-commit --to-branch <branch> -m "msg" some/dir/        # dir expands w/ report, commits
SPEC_KITTY_INFER_DESTINATION_REF=1 …                                  # no false "No requested changes"
```

## Cleanup discipline
- Negative-suite repos live under tmp_path; no `test-feature-*` mission/branch leakage.
