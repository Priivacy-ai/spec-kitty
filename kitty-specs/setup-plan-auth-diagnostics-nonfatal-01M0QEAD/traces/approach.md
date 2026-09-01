# Approach Trace

## Selected approach

Compose two existing authorities without conflating them:

1. Local readiness auth classifies authenticated, logged out, or unknown.
2. Sync preflight classifies structural hosted-delivery safety.
3. Setup-plan always computes its local result.
4. Unsafe hosted enqueue/delivery is skipped and represented by additive warnings.
5. The local result alone determines exit status.

This supersedes the narrower initial idea of changing only auth refusal severity. The user explicitly broadened the separation to all structural sync-boundary failures while preserving fail-closed hosted delivery.
