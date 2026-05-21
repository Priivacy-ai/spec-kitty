---
name: debugger-debbie
description: >-
  Dispatch a five-paradigm parallel debugging swarm against a stubborn,
  recurring, or shape-shifting bug. Each paradigm is a separate sub-agent
  with a different epistemology; they investigate independently and
  converge. Triggers: "investigate this deeply", "five paradigms on it",
  "dispatch Debugger Debbie", "we keep peeling the same kind of mask",
  "this is the Nth time this drift class has hit us", "the previous
  point-fixes did not stop the chain", "give me a structural answer
  not another reactive patch". Does NOT handle: one-line typo fixes,
  bugs with an already-localised stack trace, or first-occurrence
  bugs cheaper to fix than investigate (5×subagent budget).
---

# debugger-debbie

Dispatch a five-paradigm parallel debugging swarm — five sub-agents,
each constrained to a different structured debugging epistemology —
against a single bug. Independent investigations converge on the same
fix while each surfaces findings the others structurally cannot.

This is a **heavy** skill. Five sub-agents × investigation time ×
tokens. Do not use it for cheap bugs. Use it when reactive patches
keep arriving in the same shape and the team is asking for a
structural answer.

---

## When to Use This Skill

Use this skill when ANY of the following are true:

- A bug class has recurred three or more times under different
  surface symptoms.
- Multiple reactive PRs have shipped point-fixes and the next mask is
  expected.
- The bug crosses a system boundary (CLI ↔ SaaS, producer ↔ schema,
  snapshot ↔ fixture) and ownership is contested.
- An operator says "we keep finding new versions of the same thing".
- A canary, gate, or release blocker has fired and the team needs
  high confidence before re-running it.
- The mean-time-to-recur is shorter than the mean-time-to-fix.

Do NOT use this skill when:

- The bug has a clear stack trace and a single suspect file.
- The fix is mechanical (typo, missing import, wrong constant).
- Total token cost of five paradigms exceeds the cost of just
  shipping the fix.
- A previous run of this skill is still in flight on the same bug.

---

## The Five Paradigms

Each paradigm has a memorable label, a one-line essence, and a
unique strength. The full team is dispatched in parallel; they do
not communicate until synthesis.

### 1. The Falsifier — hypothesis-driven scientific method

Observe, form falsifiable hypotheses, design experiments that can
refute them, run, refine. Produces a hypothesis tree with explicit
verdicts ("hypothesis H3: FALSIFIED at commit X by experiment E").

**Strength:** prevents re-litigation. A falsified hypothesis cannot
be re-investigated without new evidence. Surfaces the
highest-leverage hypothesis early so the swarm narrows.

**Failure mode alone:** speculation theatre — beautiful hypotheses
disconnected from observable reality.

### 2. The Five-Whys Cartographer — 5 Whys + Ishikawa fishbone

Descend from the immediate symptom to a cause whose removal prevents
recurrence. Categorise contributing causes across Methods, Machines,
Materials, Measurements, Manpower, and Mother Nature. Build a
Pareto table mapping historical incidents to root causes.

**Strength:** finds the terminal root cause where other paradigms
stop at the proximate cause. Names structural forks: "two parallel
emit pipelines for the same conceptual event, only one of which
constructs payloads via the canonical model."

**Failure mode alone:** collapses to a linear narrative without
the fishbone categorisation; mistakes the loudest cause for the
deepest.

### 3. The Bisector — delta debugging and git bisect discipline

Pick a decidable property. Identify the introducing commit. Compute
the drift lifetime. Build the precise timeline of when each
contributing change landed and how long it lay dormant.

**Strength:** turns "something changed" into "this commit, this
date, this author, this scope." Distinguishes upstream drift from
local drift ("the events package never drifted — only the CLI was
wrong.").

**Failure mode alone:** requires a decidable property; without one
it is unrunnable. Can find the introducing commit and miss the
structural cause behind why that commit was wrong.

### 4. The Matrix-Maker — differential and dual-system comparison

Compare two systems that should agree. Build a matrix of every
divergence. Explain every cell. The matrix IS the bug. Find
dormant masks not yet surfaced.

**Strength:** complete enumeration. Surfaces bugs that have not
yet fired. Proves identity claims ("these two encodings are the
same contract") with structural evidence rather than spot checks.

**Failure mode alone:** without observation data, the matrix can
be a beautifully consistent representation of a wrong assumption.

### 5. The Stenographer — trace-based observability

Drive every conclusion from observed data: logs, traces, queue
contents, HTTP response bodies, time-travel debuggers, eBPF.
The system tells you what it did; you read it; you do not guess.

**Strength:** finds the bug nobody is looking for. Discovers
parallel issues invisible to any deductive paradigm: "the error
renderer is reading the wrong key from the response, silently
discarding the violation diversity the entire investigation
needs."

**Failure mode alone:** trace data without organisation is
unreadable; a haystack the size of the bug.

---

## Step 1: Verify the Skill Applies

Before dispatching five sub-agents, confirm the bug warrants the
budget. Check the trigger criteria above. If the bug is a
first-occurrence or has a clean stack trace, recommend
`/investigate` instead and stop.

If the user names the skill explicitly ("run Debugger Debbie",
"five paradigms on it"), proceed even if criteria are marginal —
the user is taking the budget call.

---

## Step 2: Frame the Bug Statement

Write a one-paragraph bug statement that all five sub-agents will
investigate independently. The statement must include:

- The observable failure (what fires, where, when)
- The system boundary the bug crosses
- The recurrence history (how many prior masks of this class)
- Any prior reactive PRs and what they changed
- The decidable property each paradigm needs (used by the
  Bisector and the Falsifier)

Do NOT include hypotheses in the bug statement. Each paradigm must
form its own.

---

## Step 3: Dispatch the Five Sub-Agents in Parallel

Each sub-agent receives the bug statement plus a paradigm-specific
prompt. Dispatch all five in parallel — sequential dispatch
defeats the point.

### Prompt template — The Falsifier

> You are constrained to the hypothesis-driven scientific method
> (Zeller, "Why Programs Fail"). Read the bug statement. Produce a
> hypothesis tree: at least five falsifiable hypotheses, ranked by
> leverage. For each, design an experiment that could refute it.
> Run the experiments you can run. Mark each hypothesis CONFIRMED,
> FALSIFIED (with the experiment that falsified it), or UNRESOLVED
> (with the experiment required). Output: hypothesis tree with
> verdicts. Do NOT propose a fix until every high-leverage
> hypothesis is decided.

### Prompt template — The Five-Whys Cartographer

> You are constrained to 5 Whys plus Ishikawa fishbone (Toyota
> TPS / SRE postmortem discipline). Read the bug statement. Apply
> 5 Whys to descend from the immediate symptom to a cause whose
> removal prevents recurrence. For each Why, categorise
> contributing causes across Methods / Machines / Materials /
> Measurements / Manpower / Mother Nature. Build a Pareto table
> showing which historical incidents trace to which root cause.
> Output: 5-Whys descent, fishbone diagram (as a markdown list),
> and Pareto table. Name the structural fork explicitly.

### Prompt template — The Bisector

> You are constrained to delta debugging and git bisect discipline
> (Zeller and Hildebrandt). Read the bug statement. Identify a
> decidable property for the bug. Use `git bisect`, `git log`, and
> `git blame` to find the introducing commit. Compute the drift
> lifetime (introducing commit → first user-observed failure).
> Build a precise timeline including all related commits.
> Distinguish upstream drift from local drift. Output: introducing
> commit SHA, drift lifetime in days, timeline, and a one-line
> verdict on whether the drift is upstream or local.

### Prompt template — The Matrix-Maker

> You are constrained to differential / dual-system comparison.
> Read the bug statement. Identify the two systems that should
> agree. For each shared concept, build a row in the divergence
> matrix; for each system, build a column. Fill every cell.
> Explain every divergence. Surface dormant masks — divergences
> not yet observed as failures. Output: full divergence matrix
> (markdown table), explanation per cell, list of dormant masks
> with predicted failure conditions.

### Prompt template — The Stenographer

> You are constrained to trace-based observability. Read the bug
> statement. Do not reason about what the code should do — read
> what it did. Collect: logs, traces, HTTP request and response
> bodies, queue contents, error messages, retry counts. For each
> trace artifact, write one sentence describing what it says.
> Look for inconsistencies between what the code claims and what
> the trace shows. Output: trace catalog with annotations,
> inconsistencies found, and any bug you discovered that no
> deductive paradigm could have found.

---

## Step 4: Collect and Compare Verdicts

When all five sub-agents return, compile a convergence report:

- **Convergence:** do all five point at the same fix? If yes, the
  fix has unusually high confidence — five independent
  epistemologies converged.
- **Divergence:** any paradigm pointing elsewhere is a signal, not
  noise. Investigate before discounting.
- **Unique findings:** each paradigm should surface at least one
  finding the others did not. If a paradigm contributed nothing
  unique, refine its prompt.

The convergence is the deliverable. Five paradigms pointing at
one fix is structurally stronger evidence than one investigator's
confidence, however senior.

---

## Step 5: Author the Structural Fix Plan

The fix plan must include:

- The structural root cause (from The Five-Whys Cartographer)
- The introducing commit and drift lifetime (from The Bisector)
- The full divergence matrix including dormant masks (from The
  Matrix-Maker)
- The hypothesis tree with verdicts (from The Falsifier) — kept
  in the issue record to prevent re-litigation
- Any orthogonal bug discovered (from The Stenographer)
- The minimum diff that closes all currently-known masks plus
  the dormant ones

Do NOT ship five point-fixes. The purpose of the skill is to
deliver one structural intervention that closes the whole class.

---

## Step 6: Record the Investigation

Persist the artefacts so the next recurrence (if any) starts
ahead:

- File the structural fix as a parent issue.
- Attach the falsified hypothesis catalog so they cannot be
  re-investigated without new evidence.
- Attach the divergence matrix with the dormant-mask predictions.
- Cross-link every prior point-fix issue with a comment naming
  the structural cause.

---

## References

- `references/paradigm-prompts.md` — full prompt templates for each
  paradigm with worked examples
- `references/orthogonality-matrix.md` — what each paradigm catches
  that the others structurally miss
