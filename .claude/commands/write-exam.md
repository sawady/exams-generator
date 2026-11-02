---
description: Write a programming exam with a compiler-checked solution and a PDF (exams-generator MCP server)
argument-hint: <topic> [lang=haskell|c|cpp|python] [locale=en|es] [kind=midterm|make-up|final] [n=4]
---

Write a new programming exam using the tools of the `exams` MCP server
(exams-generator). Do not write exam files by hand: save them with `save_exam`.

Read `$ARGUMENTS` as:

- **topic** (required): the domain of the exam. It is the main text.
- **lang**: programming language(s), comma separated (default `haskell`).
- **locale**: language of the exam, `en` or `es` (default: the server's).
- **kind**: `midterm`, `make-up` or `final` (default `midterm`).
- **n**: number of exercises (default: what the course profile says, else 4).

If the topic is unclear or missing, ask before writing anything.

## Steps

1. `list_languages`. If a language you need is not available, tell the user with its
   `hint`: the solution could not be verified.
2. Read the rules, in order of precedence: `get_course_profile` (wins over everything),
   `get_style_guide` for each language and the locale, `get_template` for each language
   (`statement` and `solution`). Optionally `list_exams` + `load_exam` on one or two
   previous exams to imitate their form, never their content.
3. Design first: domain, types and interfaces, what each exercise assesses. Solvable in
   the allotted time (implementation exercises ask for one or two operations), one
   domain with real links between exercises, representations that vary from previous
   exams.
4. Write the reference solution first and iterate with `check_snippet` until it passes.
5. Write the statement (Markdown) following template and style guide: no solutions,
   achievable efficiencies, every variable in a bound defined.
6. `save_exam` with a short `name`, the statement, the solution files, title, tags and
   locale. Confirm `check.ok` is true.
7. `render_exam` (`statement`, plus `solution` if an answer key is wanted). Fix the
   Markdown and save again if rendering fails.
8. Report the exam name, a two-line summary per exercise, the check result, the PDF
   path(s), and anything the teacher should double-check.

Arguments: $ARGUMENTS
