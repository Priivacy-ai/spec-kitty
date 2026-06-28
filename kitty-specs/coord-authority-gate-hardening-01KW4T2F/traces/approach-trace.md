# Approach Trace — coord-authority-gate-hardening-01KW4T2F

**Purpose:** the "how we chose to work" record. Seeded at spec→plan; append during implement; assess at close.
> Format: `[date] [phase] DECISION — rationale — alternative rejected`

---

## Seeded during spec (2026-06-27)

1. **[pre-spec] 4-lens adjacent-discovery squad BEFORE speccing** (alphonso code-state / debbie testing-tech-debt / paula scope-foldables / priti tracker). Rationale: the operator flagged the testing-tech-debt intersection; the squad grounded scope in the merged tree. Payoff: found #2198 is ~already-done (verify-annotate, not greenfield), the lighter scope-unify+param-discipline beats inter-proc, and #2199 is trivial. Alternative rejected: spec straight from the issue text.
2. **[scope] Fold #2197 in (operator's call) to maximize #2160 closures** — closes 4 residuals (#2197/#2198/#2199/#2214), leaving only #2167/#2017. Trade-off accepted: the mission is NOT purely behavior-neutral (one production routing change), paired with the scan-scope un-mask. Alternative rejected: keep #2197 separate (cleaner boundary, fewer closures).
3. **[discipline] Build to CT7/#2077 (debbie's verdict — operator's flagged focus)** so the hardening REDUCES not ADDS test-suite friction: content-anchored composite_key, no file:line ratchets, non-vacuous, self-mutation-tested. #2198 becomes CT7's exemplar. Alternative rejected: line-pinned gates (the #2071 anti-pattern).
4. **[approach] Prefer lighter scope-unify + parameter-discipline over full inter-procedural** (the sole net-ADD friction risk). Inter-proc only as a fallback spike. Rationale: full data-flow tracking is the classic false-positive engine (flag a caller that folds one hop up → correct change reverted).

<!-- append during implement: WP sequencing, the inter-proc spike decision (if any), the pre-merge full-gate dry-run. -->
