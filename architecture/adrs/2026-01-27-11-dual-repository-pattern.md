# Dual-Repository Pattern for Private spec-kitty-events Dependency

**Filename:** `2026-01-27-11-dual-repository-pattern.md`

**Status:** Accepted

**Date:** 2026-01-27

**Deciders:** Robert Douglass

**Technical Story:** Feature 004 (CLI Event Log Integration) requires integrating the completed spec-kitty-events library (Feature 003) into the CLI. The library is private during MVP phase but will eventually be open sourced.

---

## Context and Problem Statement

Spec Kitty is transitioning from a local-only CLI tool to a distributed SaaS platform. The event sourcing library (`spec-kitty-events`) built in Feature 003 must be shared between:
- **spec-kitty CLI** (public repository, PyPI distribution)
- **spec-kitty Django** (future SaaS backend, private)

The library provides Lamport clocks, CRDT merge rules, and conflict detection - solving the Last-Write-Wins data loss problem discovered in Feature 002.

**Constraints:**
- spec-kitty is PUBLIC (GitHub + PyPI)
- spec-kitty-events is PRIVATE (MVP phase, will open source later)
- Solo maintainer (no team coordination overhead)
- CI/CD must work autonomously (no laptop dependency)

**Question:** How do we structure repositories and manage the private dependency?

## Decision Drivers

* **CI/CD autonomy** - Builds must work without developer's laptop
* **Deterministic builds** - Same code every time (no "works on my machine")
* **Private during MVP** - Events library hidden until stable
* **PyPI compatibility** - Public users can install spec-kitty-cli
* **Future open source path** - Clean transition when events goes public
* **Solo developer simplicity** - No complex infrastructure overhead

## Considered Options

* **Option 1:** Dual-repository with Git dependency + commit pinning
* **Option 2:** Monorepo (single repository for both)
* **Option 3:** Git submodule
* **Option 4:** Private PyPI index (Gemfury, AWS CodeArtifact)
* **Option 5:** Vendoring from day 1

## Decision Outcome

**Chosen option:** "Dual-repository with Git dependency + commit pinning", because it:
- Enables CI/CD autonomy (no laptop needed)
- Provides deterministic builds (commit hash = exact behavior)
- Keeps events private while CLI is public
- Requires no infrastructure (no private PyPI)
- Has clean path to open source (just remove vendoring step)

### Consequences

#### Positive

* **CI/CD autonomy** - Deploy key + Git dependency = fully automated builds
* **Deterministic** - Commit hash pinning guarantees same behavior
* **Explicit integration points** - You control when events updates land
* **Private during MVP** - Events stays hidden, CLI is public
* **Clean transition** - Remove vendoring when events goes public
* **Shared library** - CLI and Django use same logic (no code duplication)

#### Negative

* **Manual commit updates** - Each events change requires updating pyproject.toml
* **SSH key management** - Deploy key needs rotation every 12 months
* **Vendoring complexity** - PyPI release requires vendor script
* **Two-repo coordination** - Feature branches must be manually synchronized

#### Neutral

* **No local pip -e** - Forces rigorous workflow but slows rapid iteration
* **Git dependency size** - Clones full repo history (but small <5MB)

### Confirmation

**Validation signals:**
- CI builds pass without manual intervention (autonomy achieved)
- No "works on my machine" bugs (determinism achieved)
- PyPI users can install without GitHub access (vendoring works)
- Clean transition when events goes public (no major refactor)

**Confidence level:** High - Similar to how many open source projects handle private/vendored dependencies during development.

## Pros and Cons of the Options

### Option 1: Dual-Repository + Git Dependency

Git dependency in pyproject.toml with commit hash pinning:
```toml
spec-kitty-events = { git = "https://...", rev = "abc1234" }
```

**Pros:**

* CI/CD works autonomously (no local paths)
* Deterministic builds (exact commit hash)
* No infrastructure costs ($0/month)
* Forces explicit integration points (good discipline)
* Clean path to open source

**Cons:**

* Manual commit hash updates
* SSH deploy key setup required
* Vendoring step for PyPI releases
* Two-repo branch coordination

### Option 2: Monorepo

Single repository with both CLI and events as packages.

**Pros:**

* Single clone, easier local dev
* Atomic commits across components
* No Git dependency complications

**Cons:**

* ❌ **Cannot make events private while keeping CLI public** (deal-breaker)
* All contributors see events code (violates privacy requirement)
* Release complexity (two packages from one repo)

### Option 3: Git Submodule

Events as submodule in `external/spec-kitty-events/`.

**Pros:**

* Explicit version pinning (commit in .gitmodules)
* No SSH setup for CI (submodule handles it)

**Cons:**

* ❌ Complex developer onboarding (`git submodule update --init`)
* Easy to forget `git submodule update` (silent breakage)
* Path dependency breaks CI without submodule
* Still requires vendoring for PyPI

### Option 4: Private PyPI Index

Host spec-kitty-events on private PyPI (Gemfury, AWS CodeArtifact).

**Pros:**

* Standard pip/poetry workflow (no Git deps)
* Version ranges and semantic versioning
* Good for larger teams

**Cons:**

* ❌ Infrastructure overhead (setup + maintenance)
* ❌ Cost ($50-200/month hosted, $0-500/month AWS)
* ❌ Auth setup for CI and developers
* ❌ Overkill for solo developer

### Option 5: Vendoring from Day 1

Copy events code into `src/specify_cli/_vendored/events/`.

**Pros:**

* Zero external dependencies
* Works on PyPI without complications

**Cons:**

* ❌ Loses version control for events
* ❌ Hard to sync changes between CLI and Django
* ❌ No shared test suite (divergence risk)
* ❌ Violates DRY (code duplication)

## More Information

**Implementation details:**
- Deploy key setup: GitHub Settings > Deploy Keys (read-only)
- Secret name: `SPEC_KITTY_EVENTS_DEPLOY_KEY`
- Vendoring script: `scripts/vendor_and_release.py` (to be created in Feature 004)
- Constitution: `.kittify/memory/constitution.md` (Architecture: Private Dependency Pattern)

**Related decisions:**
- Feature 001: SaaS Transformation Research (validated 4-phase roadmap)
- Feature 002: Event Log Storage Research (identified LWW flaw)
- Feature 003: Event Log Library (built spec-kitty-events v0.1.0-alpha)

**Future considerations:**
- Open source events library when stable (6+ months, no major bugs)
- Consider private PyPI if team grows beyond solo developer
- Alternatively, merge to monorepo if privacy requirement relaxes

**Code references:**
- spec-kitty-events: https://github.com/Priivacy-ai/spec-kitty-events (private)
- pyproject.toml: Git dependency declaration
- .github/workflows/: CI configuration with deploy key setup
