# Core #3328 WP03 implementer evidence

- Mission: `worktree-owned-root-3328-01KZRG01` (`01KZRG011AR66KDMYJHGGDEJ1V`)
- Work package: `WP03`
- Profile / Op: `python-pedro` / `01KZRY9F8DY9JS4T7H02K9X1PF`
- Commit: `032bc5d62`
- RED: parser rejected `--owned-checkout`; explicit `.worktrees` invocation was blocked by the legacy decorator. `/tmp/core-3328-wp03-red.xml`, SHA256 `328fff1cd1e77966c2d3cc858cf68892376f9e5bb75c60bb6bd9d7fee0e34235`.
- Focused GREEN: `30 passed in 52.13s` for `tests/agent/test_context_validation_unit.py`.
- Full GREEN: `722 passed, 1 skipped in 455.29s` for `tests/agent/test_context_validation_unit.py tests/runtime/` with xdist. JUnit SHA256 `c86ff8a6a4e14b22039b84e78944bd598222784aa3462f7ff65bb451b084c649`.
- Compatibility GREEN: `35 passed in 75.61s` for next preflight/selector suites. JUnit SHA256 `920eb353b7c8dc0af17abb70c3a276c947c9db551482ec66b0d5db2fcdf45be2`.
- Static gates: Ruff clean; mypy reports no issues; `git diff --check` clean.
- Transition: canonical `for_review` event `01KZS0MVYNGSD7D0ZB2CW7B8RK`; pre-review gate `no_new_failures` with one pre-existing baseline failure.
- Correlation limitation: transition rejected the Op linkage because the older dispatch record has `mission_id=None` (`recorded=None, target='01KZRG011AR66KDMYJHGGDEJ1V'`). The supported transition was repeated without the invalid authoritative linkage; this file preserves the separate Op correlation.
- Design: command-local dispatcher preserves the original `require_main_repo` path when no flag is present. Explicit opt-in bypasses only the syntactic guard, then validates via `resolve_ownership_claim` before runtime notice/preflight/mission operations. Only `OWNED` selects the claimed checkout as the effective root.
