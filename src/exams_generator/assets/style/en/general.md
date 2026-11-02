# Exam style guide (general)

Default conventions for writing programming exams. A course profile
(`get_course_profile`) overrides anything here: follow it when it says otherwise.

## The statement (Markdown handed to students)

- **Header**: course name, exam kind (midterm, make-up, final) and term, as the
  course profile specifies. Then the exam title, a short name for the domain.
- **Context**: one to three paragraphs of prose that motivate an invented domain and
  state its conventions ("no two members share an id"). Give at least one concrete
  example. Put domain terms in **bold** and identifiers in `backticks`.
- **Types and interfaces** go in fenced code blocks tagged with the language
  (`haskell`, `c`, `cpp`, `python`). Describe every operation in prose next to its
  signature: purpose, preconditions ("Assume that...", "Precondition:"), behaviour in
  edge cases, and the expected efficiency when the course grades it.
- **Exercises** are numbered consecutively across the whole exam, even when it mixes
  languages: `**Exercise 1)**`, `**Exercise 2)**`, ... Sub-items as `a.`, `b.`.
- **Efficiency** in italics with a capital O: *O(log N)*. Define every variable that
  appears in a bound (*N* = number of members, ...) where the interface is introduced.
- **Call-outs** in bold capitals: **NOTE:**, **HINT:**, **REMINDER:**, **IMPORTANT:**.
- **Appendix**: if exercises rely on auxiliary interfaces (maps, sets, lists...), list
  only the ones used, as a table of signature and cost.

## What the statement must not contain

- Solutions, grading criteria or internal notes for the teaching team.
- Names of real people, real companies or real student data.
- `TODO`, placeholders or text addressed to the author.

## Difficulty and scope

- The exam must be solvable in the allotted time (typically 2-3 hours). An
  implementation exercise asks for one or two operations, not the whole interface.
- Every exercise must be solvable with the types and interfaces given in the
  statement. Requested efficiencies must be achievable with the stated costs.
- Prefer a single domain that ties all exercises together, with real (not cosmetic)
  links between parts.
- Vary representations across exams; do not always reach for the same structure.
- Hints may name the type of a helper function, but must not give its code.

## The reference solution

- One or more source files that **compile / type-check** with the matching checker
  (`check_snippet`, then `save_exam` verifies again). An exam is not ready until its
  check passes.
- Mirror the statement: a comment banner per exercise, in the same order and numbering.
- Comments explain *why* (invariants, design decisions), not *what* the code does.
- For pen-and-paper answers (invariants, proofs, efficiency justifications), write them
  as block comments in the solution, next to the exercise they answer.
- End with a short demo block (as a comment) with a few example calls and their
  expected results, including at least one edge case.
