# Gate 3 Operator Exception

**Operator**: Robert Douglass (GitHub: [@robertDouglass](https://github.com/robertDouglass))
**Approver**: Robert Douglass (GitHub: [@robertDouglass](https://github.com/robertDouglass))
**Date**: 2026-08-24
**Failing scenario**: `tests/teamspace_readiness/test_upsun_target_readiness.py::test_discovered_upsun_target_readiness`
**Failing assertion**: `assert status == "pass", failure_reason`

## Environmental rationale

The discovered Upsun develop target is reachable and reports healthy service and dependency readiness. `GET /health/ready/` returns `status: "ready"` with PostgreSQL, Redis, the channel layer, the Celery broker, and the drain queue all healthy. The sole failing assertion is the deployment-provenance check because `GET /health/` reports `git_sha: "unknown"` with `git_sha_source: "build"`.

The required credential-optional deploy-provenance support already landed in `Priivacy-ai/spec-kitty-saas` PR [#991](https://github.com/Priivacy-ai/spec-kitty-saas/pull/991). The remaining action is environmental: configure `UPSUN_PROVENANCE_API_TOKEN` on the Upsun develop environment and redeploy. The product implementation for issue [#3432](https://github.com/Priivacy-ai/spec-kitty/issues/3432) does not modify SaaS deployment provenance, network transport, or the readiness canary. This exception therefore covers one environmental assertion only and does not waive a product-code defect.

## Reproduction command

```bash
./scripts/run-teamspace-readiness-canary.sh --single --yes
```

The failing GitHub Actions evidence is the `canary` job in `Priivacy-ai/spec-kitty-end-to-end-testing` PR [#589](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/pull/589), run `32689531614`.

## Follow-up

The operator will configure `UPSUN_PROVENANCE_API_TOKEN`, redeploy the Upsun develop environment, and rerun the single readiness scenario no later than 2026-08-31. The outcome will be recorded on [spec-kitty-end-to-end-testing PR #589](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/pull/589). The exception expires after that retry window and must not be reused for another scenario or assertion.
