# Solo Developer Workflow

Quick iteration for individual developers using Spec Kitty with a single AI agent.

## Context
- **Developer:** Solo full-stack engineer
- **Agent:** Claude Code (or Cursor, Gemini, etc.)
- **Pattern:** Fast iteration with systematic tracking
- **Benefit:** Dashboard provides visual progress even working solo

## Complete Workflow

### 0. Install & Initialize (One-time)
```bash
# Install CLI
pip install spec-kitty-cli

# Initialize project
spec-kitty init my-saas-app --ai claude

# Navigate to project
cd my-saas-app
```

### 1. Project Setup (One-time)
Start your AI agent:
```bash
claude
```

Create project principles:
```text
/spec-kitty.constitution

Create principles focused on:
- Code quality: Clean, well-documented code
- Testing: Unit tests for all business logic
- Security: Input validation and sanitization
- Performance: Sub-200ms API responses
```

### 2. Start First Feature
Define what to build:
```text
/spec-kitty.specify

Build a user authentication system with email/password login,
password reset via email, and session management. Users should
be able to register, login, logout, and recover forgotten passwords.
Include rate limiting on auth endpoints.
```

**Important:** After specify completes, switch to the feature worktree:
```bash
cd .worktrees/001-auth-system
claude  # Restart agent in feature worktree
```

### 3. Technical Planning
Define how to build it:
```text
/spec-kitty.plan

Use Python FastAPI for backend, PostgreSQL for database,
JWT tokens for sessions, bcrypt for password hashing,
SendGrid for email delivery, Redis for rate limiting.
```

### 4. Optional: Research
If you need to investigate technical decisions:
```text
/spec-kitty.research

Investigate JWT refresh token rotation best practices
and rate limiting strategies for authentication endpoints.
```

### 5. Break Down Into Tasks
Generate work packages:
```text
/spec-kitty.tasks
```

**Check your dashboard:**
```bash
# Open in browser (already running from init)
open http://localhost:3000
```

You'll see your tasks organized in the "Planned" lane!

### 6. Implement Feature
Execute implementation:
```text
/spec-kitty.implement
```

The command will:
- Move a work package to "doing"
- Implement according to plan
- Move to "for_review" when complete

**Repeat** `/spec-kitty.implement` until all work packages are done.

**Monitor progress:** Keep dashboard open in browser to see tasks moving through lanes.

### 7. Self-Review
Review your completed work:
```text
/spec-kitty.review
```

This helps catch issues before considering the feature complete.

### 8. Validate & Ship
Final validation:
```text
/spec-kitty.accept
```

Merge to main:
```text
/spec-kitty.merge --push
```

**Result:** Feature complete, worktree cleaned up, back in main repo!

### 9. Start Next Feature
```bash
cd ~/my-saas-app  # Back to main repo
claude
```

Then repeat from step 2 with a new feature!

## Dashboard Benefits for Solo Developers

Even working alone, the dashboard provides:

1. **Visual Progress** - See exactly where you are in the feature
2. **Context Recovery** - Return after interruption and know what's next
3. **Motivation** - Watch tasks move from planned → done
4. **Documentation** - Activity logs show your development history
5. **Quality** - Systematic workflow prevents skipping steps

## Time Estimates

| Phase | Time (Simple Feature) | Time (Complex Feature) |
|-------|----------------------|------------------------|
| Constitution | 10 min (one-time) | 10 min (one-time) |
| Specify | 5-10 min | 15-30 min |
| Plan | 5-10 min | 15-30 min |
| Tasks | 2 min | 2 min |
| Implement | 30-60 min | 2-8 hours |
| Review | 5-10 min | 15-30 min |
| Accept & Merge | 2 min | 5 min |
| **Total** | **~1 hour** | **~3-10 hours** |

## Tips for Solo Developers

- **Keep dashboard open** - It's your visual TODO list
- **One feature at a time** - Resist urge to skip worktree workflow
- **Use `/spec-kitty.clarify`** - Ask yourself questions before planning
- **Self-review seriously** - `/spec-kitty.review` catches bugs early
- **Constitution matters** - Even solo, it keeps you consistent
- **Don't skip acceptance** - `/spec-kitty.accept` ensures quality gates

## Common Solo Developer Questions

**Q: Is this overkill for small features?**
A: For tiny changes, yes. For anything >30 min of coding, the structure helps.

**Q: Can I skip the worktree?**
A: Technically yes (Spec Kitty falls back), but worktrees prevent branch switching confusion.

**Q: Do I need the dashboard if I'm solo?**
A: It's optional but highly recommended - provides visual progress and easy resumption.

**Q: What if I need to pause mid-feature?**
A: Just stop. Dashboard shows where you left off. Pick up with `/spec-kitty.implement` later.
