# Tracer: Design Decisions — sync-strict-json-auth-01KWA6KN

Rationale that would otherwise evaporate.

- 2026-06-29: Scope decision — root-cause fix in scope; CI-trigger blind-spot broadening (#2034 overlap) deferred to post-research decision `01KWA6Q7SPH9ZN20CH6EW68QDM` (user chose "decide after research"). Domain-matched fold candidate per §2; only fold if research shows it belongs here.
- 2026-06-29: Branch — dedicated `fix/sync-strict-json-auth` off `origin/main`, PR into `main`. Kept separate from the in-flight `pr/integration-boundary` branch so this red-test fix is independently reviewable.
