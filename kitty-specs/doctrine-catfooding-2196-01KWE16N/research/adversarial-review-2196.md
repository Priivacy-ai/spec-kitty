## Structured review — Doctrine Catfooding

Reviewed via the practice this epic codifies (§1): a bounded, profile-loaded adversarial squad — three lenses (doctrine-fit/reconciliation · decomposition/dependencies · capstone/charter-compile feasibility), each reading the real doctrine + charter code.

**Verdict: strong, valuable initiative — right thesis, right decomposition shape — but not ready to execute as-is.** The epic correctly names "reconcile, don't duplicate" as its central risk, yet the current per-ticket framing under-manages exactly that, and the capstone mis-describes the charter-compile mechanism. ~10 fixable items (most low-effort) before dispatch.

### What's good
- **Catfooding thesis is sound** — compiling Spec Kitty's own charter from the doctrine it ships forces these standing orders out of ephemeral memory into activatable, enforceable artifacts.
- **Source fidelity high**; **decomposition shape right** — one child per section, the §5 split (#2200 construction / #2201 adjudication) is the cleanest cut, and the tickets already do *some* reconciliation (#2202 relocates §2's tracker bullet to #2207; #2206 `enhances` the existing commit-history tactic).
- **All named reconciliation targets exist on disk** — no dangling-DRG-edge risk from missing targets.

### 🔴 Blocking (fix in the epic before dispatch)
1. **Source doc doesn't exist.** `docs/development/quality-and-tech-debt-standing-orders.md` (the declared "Source") is not in the repo — only in this issue. Add a **step-0 child to create + commit it**; every conversion and the capstone's "human-readable mirror" AC assume it.
2. **Meta-vs-functional-parent contradiction.** The epic is labeled `scope-tracker` and says "not a functional parent," yet all 11 children are its native sub-issues — violating the very §8 tracker rule #2207 is chartered to encode. **Recommend: make #2196 the genuine functional epic; drop the scope-tracker framing** (no other functional home exists).
3. **Directive-number collision.** 7 children each mint "the next NNN directive" → all grab `043` in parallel. **Pre-allocate 043–049.**
4. **`graph.yaml` is one generated shared surface.** 7 parallel DRG regenerations collide. **Decide now:** serialize, or author edges per-ticket + regenerate once at the capstone.

### 🟠 Reconciliation — the epic over-provisions *new directives* for the most-doctrined sections
5. **§4 ≈ `DIRECTIVE_041` (tests-as-scaffold-not-friction) — near-total duplicate** (verbatim three-verdict / red-first / no-retry-to-green / realistic data). Only *"live evidence over static-fixed"* is new → **extend 041; do not author a new §4 directive.**
6. **§1's proposed *required* directive contradicts the shipped `adversarial-squad-deployment.procedure.yaml`**, which is explicitly optional and lists *"hard-wiring the squad as a gate"* as an anti-pattern → **recategorize §1 as a cadence styleguide/paradigm** (or narrow the directive to "*when* you run a squad, run it bounded + profile-loaded"), not "always run one."
7. **Already substantially covered:** §2 ≈ `DIRECTIVE_025` (boy-scout) + 024 + 040; **§8 tiered-rigour is complete in `tiered-standards.styleguide`**; **§7 "compress history" is `clean-linear-commit-history.tactic`**. Extend/reference these; the genuinely-new atoms are narrow (frozen-baseline ratchet, domain-matched fold, ownership-map leeway, role separation, PRs-only/read-intent/worktree-isolation/no-version-in-scope).
8. **Cross-ticket collisions** (author-once, reference-elsewhere): #2208 & #2202 both edit the brownfield paradigm; the frozen-baseline ratchet lands in both #2202 & #2200. Add a **shared-target lock**.
9. **Kind recategorizations:** §6 under-split (the terminology-guard sub-rule is a *tool* → **toolguide**, not a directive line); §7 too coarse (5 heterogeneous rules; "isolate PR agents" is worktree mechanics). §3's 3-artifact split is a judgment call — leave to the authoring ticket (drop the standalone tactic if procedure+template suffice).

### 🟠 Capstone (#2209) mis-describes the mechanism
10. **Compile sequence is inverted.** #2209 says "interview/select → generate → activate"; the code requires **activate first, then generate** (`charter generate` filters the DRG closure by activation state, so activate-after yields an incomplete reference index). Also **`charter generate` does not activate** (it renders `charter.md`; activation writes `config.yaml`) — the AC conflates them; and there is **no bridge from activation → interview `answers.yaml`** (a manual mirror step is required).
11. **#2209 is not greenfield** — a `charter.md` (v1.1.5) + fresh-seed manifest already exist; the capstone must **reconcile/supersede**, not compile from scratch.
12. **Push two checks left into every conversion ticket's DoD** (not deferred to the capstone): (a) **DRG node + edges added to `graph.yaml`** as a hard item — soft "where the artifact has them" → silent shallow cascade + incomplete reference closure; (b) **`doctor doctrine --json` green** — else a malformed early artifact only surfaces at the capstone, needing a bisect. Also: activating a directive **does not wire it into agent-profile `directives:` lists** — without that step the doctrine is inert for agent sessions.

**Watch:** #2207 and #2204 are the heaviest tickets (4–5 doctrine-surface touches) and most likely undersized — flag each for its own post-tasks squad.

### Bottom line
Worth doing and mostly well-shaped, but as written it would (a) create duplicate/conflicting authorities for §4/§2/§1, (b) hit parallel-execution collisions (directive numbers, `graph.yaml`), and (c) run the capstone in the wrong order against a non-empty charter. All fixable in the epic body + a few ticket edits before work starts. A corrected-scope mission is being specced to carry this out.
