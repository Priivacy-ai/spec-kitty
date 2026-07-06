# Tracer: approach

How the work was actually approached (append during implementation).

- Started from the ticket's own evidence trail, then **reproduced the tax live**
  (+3 lines → red, only `loc` differs) before writing any spec — red-first witness.
- Confirmed the fix is feasible and precise at the code level (drop `loc` at
  `live_derived_worklist`, dir-keyed index compare, live floor) before committing to the
  approach, so the spec/plan describe a validated design, not a guess.
- Fix applied at the **shared derivation** (not the test assertion) so the pytest gate
  and the `--verify-census` CLI are both fixed by one change — avoids a second authority.
- ATDD: red-first test uses a **rank-altering** churn between two adjacent members so a
  single failing test forces both loc-drop (FR-001) and order-insensitivity (FR-007).
- **[close]** Landed clean: 14/14 worklist tests, ruff + mypy --strict clean, zero `src/`
  changes, SC-001 reproduction GREEN. Independent `reviewer-renata` APPROVED after
  verifying red→green at the base commit and regenerating the census in-memory to prove a
  faithful `--emit-census`. All three planning point-cuts + analysis were clean/minor with
  every confirmed finding folded. One follow-up carried to the pre-merge gate: the full
  `tests/architectural/` suite (SC-006), which the reviewer couldn't finish inside a
  9-minute wall-clock.
