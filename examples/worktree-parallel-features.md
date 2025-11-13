# Parallel Feature Development with Worktrees

Develop 3+ features simultaneously without branch switching chaos.

## The Problem Without Worktrees

### Traditional Branch Switching
```bash
# Working on Feature A
git checkout feature-a
# Implement, test, commit...

# Context switch to Feature B (loses IDE state)
git checkout feature-b
# Implement, test, commit...

# Back to Feature A (loses IDE state again)
git checkout feature-a
# What was I doing? 🤔
```

**Pain Points:**
- Lost IDE state on every switch
- Rebuilds/reinstalls on context switch
- Can't compare features side-by-side
- Accidental commits to wrong branch
- Mental overhead tracking current branch

### Worktree Solution
```bash
# All features available simultaneously
cd .worktrees/001-auth          # Feature A
cd .worktrees/002-dashboard     # Feature B
cd .worktrees/003-api-v2        # Feature C

# Each has own:
- Working directory
- IDE window
- Build artifacts
- Node_modules/venv
- Shell history
```

**Benefits:**
- No context switching
- Side-by-side development
- Parallel testing
- No branch confusion
- Dashboard shows all features

## Scenario: Three Parallel Features

**Project:** E-commerce platform
**Timeline:** 2-week sprint
**Features:**
- Feature A: User Authentication (Week 1-2)
- Feature B: Product Dashboard (Week 1-2)
- Feature C: Payment Integration (Week 2)

## Setup: Initial Project

### 1. Initialize Project (One-time)
```bash
spec-kitty init ecommerce-platform --ai claude
cd ecommerce-platform
claude
```

### 2. Create Constitution (One-time)
```text
/spec-kitty.constitution

Create principles for:
- Security: PCI compliance for payments, secure auth
- Testing: 80% coverage, integration tests required
- Performance: <200ms API responses
```

## Feature A: User Authentication

### Terminal 1 (Week 1, Monday)
```bash
cd ~/ecommerce-platform
claude
```

```text
/spec-kitty.specify

Build user authentication with:
- Email/password registration
- JWT-based sessions
- Password reset via email
- OAuth integration (Google, GitHub)
```

**Result:** Creates `.worktrees/001-auth/`

```bash
# Switch to feature worktree
cd .worktrees/001-auth
claude  # Restart in worktree
```

```text
/spec-kitty.plan
Use Python FastAPI, PostgreSQL, Redis for sessions,
SendGrid for email, JWT tokens with refresh rotation.

/spec-kitty.tasks
# Creates 6 work packages

/spec-kitty.implement
# Start implementing...
```

**Keep Terminal 1 open - you'll come back to it!**

## Feature B: Product Dashboard

### Terminal 2 (Week 1, Tuesday - While Feature A is in progress)
```bash
cd ~/ecommerce-platform  # Back to main repo
claude  # New agent instance
```

```text
/spec-kitty.specify

Build product dashboard showing:
- Product catalog with search/filter
- Inventory management
- Sales analytics graphs
- Low stock alerts
```

**Result:** Creates `.worktrees/002-dashboard/`

```bash
cd .worktrees/002-dashboard
claude  # Restart in worktree
```

```text
/spec-kitty.plan
Use Next.js frontend, Chart.js for graphs,
TanStack Query for data fetching, Tailwind CSS.

/spec-kitty.tasks
# Creates 8 work packages

/spec-kitty.implement
# Start implementing...
```

**Keep Terminal 2 open too!**

## Feature C: Payment Integration

### Terminal 3 (Week 2, Monday - Both A and B still in progress)
```bash
cd ~/ecommerce-platform  # Back to main repo
claude  # Another new agent instance
```

```text
/spec-kitty.specify

Integrate payment processing with:
- Stripe checkout
- Subscription management
- Invoice generation
- Refund handling
```

**Result:** Creates `.worktrees/003-payment/`

```bash
cd .worktrees/003-payment
claude  # Restart in worktree
```

```text
/spec-kitty.plan
Use Stripe API v2024, webhook handlers,
idempotency keys, PCI-compliant data handling.

/spec-kitty.tasks
# Creates 7 work packages

/spec-kitty.implement
# Start implementing...
```

## Dashboard View: All Three Features

Open dashboard in browser:
```bash
open http://localhost:3000
```

**You see:**
```
Feature: 001-auth (Progress: 60%)
├─ Planned: WP04, WP05
├─ Doing: WP03 (Agent: claude, PID: 12345)
├─ Review: WP02
└─ Done: WP01

Feature: 002-dashboard (Progress: 40%)
├─ Planned: WP05, WP06, WP07, WP08
├─ Doing: WP04 (Agent: claude, PID: 12346)
├─ Review: WP03
└─ Done: WP01, WP02

Feature: 003-payment (Progress: 25%)
├─ Planned: WP03, WP04, WP05, WP06, WP07
├─ Doing: WP02 (Agent: claude, PID: 12347)
├─ Review: —
└─ Done: WP01
```

**All visible at once!**

## Working Across Features

### Switch Context Instantly
```bash
# Terminal 1: Working on auth
cd .worktrees/001-auth
vim src/auth/jwt.py
pytest tests/test_jwt.py

# Terminal 2: Working on dashboard (simultaneously!)
cd .worktrees/002-dashboard
vim components/ProductCard.tsx
npm test

# Terminal 3: Working on payments (simultaneously!)
cd .worktrees/003-payment
vim api/stripe_webhooks.py
pytest tests/test_webhooks.py
```

**All running at the same time - no git checkout!**

### Compare Implementations
```bash
# Want to see how auth handles errors vs payments?
diff .worktrees/001-auth/src/errors.py .worktrees/003-payment/api/errors.py

# Copy pattern from one feature to another
cp .worktrees/001-auth/tests/conftest.py .worktrees/002-dashboard/tests/
```

### IDE Setup
```bash
# VS Code: Open three windows
code .worktrees/001-auth
code .worktrees/002-dashboard
code .worktrees/003-payment

# Or use split panes in one window
```

**Each IDE window maintains state independently!**

## Merge Order: Feature Completion

### Feature A Completes First (Week 1, Friday)
```bash
# Terminal 1
cd .worktrees/001-auth
```

```text
/spec-kitty.accept
# ✓ All tasks in done/
# ✓ Coverage: 84%
# ✓ Security validation passed

/spec-kitty.merge --push
# Merged to main
# Cleaned up .worktrees/001-auth
# Deleted branch 001-auth
```

**Terminal 1 now free for new work!**

### Feature B Completes Second (Week 2, Wednesday)
```bash
# Terminal 2
cd .worktrees/002-dashboard
```

```text
/spec-kitty.accept
/spec-kitty.merge --push
# Merged to main (no conflicts with Feature A - already integrated!)
```

### Feature C Completes Last (Week 2, Friday)
```bash
# Terminal 3
cd .worktrees/003-payment
```

```text
/spec-kitty.accept
/spec-kitty.merge --push
# Merged to main
```

**Sprint complete - all three features shipped!**

## Benefits Realized

### 1. No Context Switching
**Without Worktrees:**
```bash
git checkout 001-auth      # 5 seconds + mental load
# Work for 30 minutes
git checkout 002-dashboard # 5 seconds + mental load
# Where was I? Check notes...
```

**With Worktrees:**
```bash
cd .worktrees/001-auth     # Instant
# Work for 30 minutes
cd .worktrees/002-dashboard # Instant
# IDE state preserved, exactly where you left off
```

### 2. Parallel Testing
**Without Worktrees:**
```bash
# Can't test both features simultaneously
git checkout feature-a
pytest  # Must wait...
git checkout feature-b
pytest  # More waiting...
```

**With Worktrees:**
```bash
# Terminal 1
cd .worktrees/001-auth && pytest &

# Terminal 2
cd .worktrees/002-dashboard && npm test &

# Terminal 3
cd .worktrees/003-payment && pytest &

# All running in parallel!
```

### 3. No Branch Confusion
**Without Worktrees:**
```bash
git branch  # Which am I on again?
git commit  # Oh no, wrong branch!
git reset HEAD~1
git checkout correct-branch
git cherry-pick abc123
```

**With Worktrees:**
```bash
# Impossible to commit to wrong branch
# Each terminal IS the branch
# Directory name reminds you which feature
```

### 4. Side-by-Side Comparison
```bash
# Compare auth and payment error handling
diff .worktrees/001-auth/src/errors.py \
     .worktrees/003-payment/api/errors.py

# View both in VS Code side-by-side
code --diff .worktrees/001-auth/README.md \
             .worktrees/002-dashboard/README.md
```

### 5. Dashboard Coordination
**One screen shows all features:**
- PM sees progress on all three
- Bottlenecks visible (Feature B stuck in review)
- Rebalance work based on dashboard
- Export single report for all features

## Advanced: Shared Code Between Features

### Problem: Both features need same util
```bash
# Feature A creates utility
cd .worktrees/001-auth
vim src/utils/validation.py  # Email validator

# Feature B needs it too
cd .worktrees/002-dashboard
# How to share?
```

### Solution 1: Merge Feature A First
```bash
cd .worktrees/001-auth
/spec-kitty.accept
/spec-kitty.merge

# Now Feature B can use it
cd .worktrees/002-dashboard
git pull origin main  # Get the utility
from utils.validation import validate_email  # Use it!
```

### Solution 2: Create Shared Utilities Feature
```bash
cd ~/ecommerce-platform
/spec-kitty.specify
Create shared utilities for email validation, date formatting, etc.

cd .worktrees/000-shared-utils
# Implement quickly
/spec-kitty.accept && /spec-kitty.merge

# Now both A and B can use
```

## Common Patterns

### Pattern 1: Dependent Features
```
Week 1: Feature A (Auth) → Merge
Week 2: Feature B (Dashboard - needs auth) → Use merged A
```

### Pattern 2: Independent Features
```
Week 1-2: Feature A (Auth) || Feature B (Dashboard) → Merge both
         (Developed in parallel, no dependencies)
```

### Pattern 3: Sequential Features
```
Feature A → Complete & Merge
Feature B → Complete & Merge
Feature C → Complete & Merge
(But all worktrees exist simultaneously for easy comparison)
```

## Tips for Parallel Development

1. **Name terminals clearly**
   ```bash
   # Set terminal title
   echo -e "\033]0;Feature A: Auth\007"
   ```

2. **Use tmux/screen for persistence**
   ```bash
   tmux new -s auth
   tmux new -s dashboard
   tmux new -s payment
   ```

3. **Dashboard as coordination hub**
   - Daily standup: Show dashboard
   - Identify blocked features
   - Rebalance work across features

4. **Merge frequently**
   - Don't let features diverge for weeks
   - Merge completed features immediately
   - Reduces integration conflicts

5. **Shared dependencies**
   - Create "000-shared-X" features for common code
   - Merge these first
   - Other features pull and use

## Cleanup

### Manual Cleanup (if needed)
```bash
# List all worktrees
git worktree list

# Remove completed worktree
git worktree remove .worktrees/001-auth

# Remove branch
git branch -d 001-auth
```

**But `/spec-kitty.merge` does this automatically!**

## Summary

| Aspect | Branch Switching | Worktrees |
|--------|-----------------|-----------|
| Context Switch Time | 5-10 seconds | Instant (cd) |
| IDE State | Lost on switch | Preserved |
| Parallel Work | No | Yes |
| Branch Confusion | Common | Impossible |
| Side-by-Side Compare | Difficult | Easy |
| Dashboard View | N/A | All features visible |
| Mental Overhead | High | Low |

**Worktrees + Spec Kitty = Parallel feature development without the pain!**
