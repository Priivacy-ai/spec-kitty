# 1.x Workflow

## Canonical Sequence

1. `spec-kitty specify <feature-intent>`
2. `spec-kitty plan`
3. `spec-kitty tasks`
4. `spec-kitty implement`
5. `spec-kitty review`
6. `spec-kitty merge`

## Why This Order Matters

1. `spec.md` defines requirements and acceptance intent.
2. `plan.md` captures architecture and implementation strategy.
3. `tasks.md` materializes executable work packages.
4. `implement` and `review` execute against plan and constitution constraints.

## Governance in 1.x

The legacy governance source is `.kittify/memory/constitution.md`.  
Workflow prompts and reviews are expected to align to those principles.
