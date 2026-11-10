---
description: Write, review or fix programming exams with a reference solution checked by a real compiler, and render them to PDF, using the exams MCP server. Use when the user asks for an exam, a midterm, a make-up, a final or a programming exercise with a checked solution, in Haskell, C, C++ or Python, or wants to check or render one that is already saved.
---

# Writing exams with the `exams` server

Use the tools of the `exams` MCP server. Do not write exam files by hand: every exam goes
through `save_exam`, which checks the solution and commits it. `/exams-generator:write-exam`
and `/exams-generator:review-exam` run the full procedures.

## Order of precedence for writing rules

1. `get_course_profile`: the course's own rules. They win over everything else, including
   the language subset students may use, which no compiler can enforce.
2. `get_style_guide` for each language and the exam's locale.
3. `get_template` for each language, `statement` and `solution`.

## How the work goes

1. `list_languages` first. If a toolchain is missing, tell the user with its `hint`: that
   solution cannot be verified.
2. Design before writing: one invented domain, with real links between exercises, and what
   each exercise assesses. Use earlier exams (`list_exams`, `load_exam`) to imitate their
   form, never their content.
3. Write the solution first and iterate with `check_snippet` until it passes. Then write the
   statement: no solutions, no internal notes, every bound achievable and every variable in
   it defined.
4. `save_exam` with the locale, and confirm `check.ok` is true. Then `render_exam`.

## Reading results honestly

- A language reported as *skipped* has not been verified. Say so; never call it a pass.
- A check that passed proves that the solution compiles, not that it is right. If the
  `run_demos` tool is available (it is off by default), use it, and treat only `passed` as
  verified. Do not ask for it to be enabled unless the user brings it up.
- A saved exam can have a failing check (drafts are allowed). Always report it.

## Privacy

Exams contain their solutions. Keep them in the exams directory, and do not paste them in
public places such as issues or shared repositories.
