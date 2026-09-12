# Tracer: design-decisions

One entry per finding: `YYYY-MM-DD · actor · <text>`.

---

2026-08-02 · orchestrator · Confirmed HiC decision: WP01/FR-002 proceeds as scope+pin of the charter/context.py:249 C-003 prose-presence gate (NOT a retire) per the post-tasks squad correction — retiring would regress 26 charter.md-only fixtures. All Wave-0 implementers briefed on this framing.

2026-08-02 · orchestrator · WP10 reviewer nit (non-blocking, for WP13's ADR citation): the test docstring/commit message for the AST charter-import gate says pytestarch 'resolves module-level imports only' -- reviewer's mutation test disproved this (a PLAIN function-level import in an untouched module also went red under pytestarch). What pytestarch actually misses is imports nested inside try/except handlers specifically (the shape of the original edge), not function-scope generally. WP13's ADR should cite the precise claim (try/except-nested import blind spot), not the broader 'module-level only' framing.

2026-08-02 · orchestrator · WP11 follow-on note (non-blocking, from reviewer): tests/architectural/charter_path_literal_allowlist.yaml's composite key (file, qualname, token) is not fully unique - src/doctrine/synthesizer or generate.py has 2 sites (lines 325, 389) sharing an identical key, only distinguished today by the exact-accounting/census-ceiling tests rather than the key itself. Suggest adding an ordinal/occurrence field or a no-duplicate-keys assertion in a future hardening pass.
