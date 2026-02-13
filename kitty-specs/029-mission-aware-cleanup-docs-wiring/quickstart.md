# Quickstart: Mission-Aware Cleanup & Docs Wiring

## Goal
Validate the cleanup and mission-aware wiring without relying on duplicated root scripts.

## Prerequisites
- Python 3.11+
- Git available
- Virtual environment configured

## Steps
1. Run the test suite to ensure no tests reference root `scripts/` paths.
2. Run task/acceptance flows in both main repo and a worktree to confirm consistent behavior.
3. Create a documentation mission feature and run plan/research; confirm a gap analysis report is generated and documentation state updates in `meta.json`.
4. Run validation/acceptance for the documentation mission; confirm missing gap analysis or state fails as expected.

## Expected Results
- Tests pass without root script duplication.
- Task/acceptance behavior matches across worktree and main repo.
- Documentation mission runs gap analysis and updates state during plan/research.
- Validation/acceptance enforces documentation mission artifacts.
