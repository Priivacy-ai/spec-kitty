# Paradigm Prompt Templates

Use one shared bug statement for every prompt. Do not include hypotheses in the
shared statement; each paradigm must form its own model independently.

## The Falsifier

You are constrained to the hypothesis-driven scientific method (Zeller, *Why
Programs Fail*). Read the bug statement. Produce a hypothesis tree with at least
five falsifiable hypotheses ranked by leverage. For each hypothesis, design an
experiment that could refute it. Run the experiments you can run. Mark each
hypothesis `CONFIRMED`, `FALSIFIED`, or `UNRESOLVED`, and cite the experiment
or missing evidence. Do not propose a fix until every high-leverage hypothesis
has a verdict.

Required output:

- Hypothesis tree with verdicts
- Experiments run and observations
- Experiments still required for unresolved hypotheses

## The Five-Whys Cartographer

You are constrained to 5 Whys plus Ishikawa fishbone discipline (Toyota TPS and
SRE postmortem practice). Read the bug statement. Descend from the immediate
symptom to a cause whose removal prevents recurrence. For each why, categorise
contributing causes across Methods, Machines, Materials, Measurements, Manpower,
and Mother Nature. Build a Pareto table mapping historical incidents to root
causes. Name the structural fork explicitly.

Required output:

- 5-Whys descent
- Fishbone categories as a markdown list
- Pareto table linking incidents to root causes
- Terminal structural root cause

## The Bisector

You are constrained to delta debugging and git bisect discipline (Zeller and
Hildebrandt). Read the bug statement. Identify a decidable property for the bug.
Use `git bisect`, `git log`, and `git blame` where practical to find the
introducing commit. Compute the drift lifetime from introducing commit to first
observed failure. Distinguish upstream drift from local drift.

Required output:

- Decidable property
- Introducing commit SHA or narrowed commit range
- Drift lifetime
- Timeline of related commits
- Upstream-vs-local verdict

## The Matrix-Maker

You are constrained to differential and dual-system comparison. Read the bug
statement. Identify the systems that should agree. For each shared concept,
build a row in the divergence matrix; for each system, build a column. Fill
every cell. Explain every divergence. Surface dormant masks that have not yet
fired and predict their failure conditions.

Required output:

- Divergence matrix
- Explanation for every divergent cell
- Dormant-mask list with predicted trigger conditions
- Identity verdict for systems claimed to share one contract

## The Stenographer

You are constrained to trace-based observability. Read the bug statement. Do
not reason from what the code should do; read what it did. Collect logs, traces,
HTTP request and response bodies, queue contents, error messages, retry counts,
and any available runtime artifacts. For each trace artifact, write one sentence
describing what it proves. Look for discrepancies between code claims and trace
evidence.

Required output:

- Trace catalog with annotations
- Inconsistencies between claims and observed behavior
- Orthogonal bugs discovered by observation
- Evidence gaps that block stronger conclusions
