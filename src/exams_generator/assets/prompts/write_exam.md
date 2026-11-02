Write a new programming exam with the exams-generator tools.

- Topic / domain: {topic}
- Programming language(s): {languages}
- Exam language: {locale_name} (locale `{locale}`). Write the statement, identifiers
  and comments in this language.
- Kind: {kind}
- Number of exercises: {exercises}
- Extra notes from the teacher: {notes}

If the topic is unclear or missing, ask before writing anything.

## Steps

1. Call `list_languages`. If a language you need has `available: false`, tell the
   teacher (with the `hint`) before going on: its solution cannot be verified.
2. Read the rules, in order of precedence:
   - `get_course_profile`: course-specific rules (header, allowed language subset,
     exercise structure, length). They win over everything else.
   - `get_style_guide` for each language, with `locale="{locale}"`.
   - `get_template` for each language, `kind="statement"` and `kind="solution"`.
   - Optionally `list_exams` and `load_exam` on one or two previous exams, to imitate
     their style and register. Imitate the form, never reuse their content.
3. Design before writing: the domain, the types and interfaces, and what each exercise
   assesses. Keep it solvable in the allotted time: an implementation exercise asks for
   one or two operations, not the whole interface. Prefer a single domain with real
   links between exercises (and between languages, if there are several). Vary the
   representations with respect to previous exams.
4. Write the reference solution first, as solution files (`Exam.hs`, `queue.h` +
   `queue.c`, `solution.py`...). Call `check_snippet` (or check all files through
   `save_exam`) and fix every error until the check passes. Do not hide failures.
5. Write the statement in Markdown, following the template and the style guide. It must
   not contain solutions, grading criteria or internal notes. Every requested
   efficiency must be achievable with the given costs; every variable in a bound must
   be defined.
6. Pick a short `name` (`[A-Za-z0-9_-]`, e.g. `2026-midterm-library`) and call
   `save_exam` with the statement, the solution files, a title, tags and
   `locale="{locale}"`. Check that the returned `check.ok` is true.
7. Call `render_exam` with `variant="statement"` (and `variant="solution"` if the
   teacher wants an answer key). If rendering fails, fix the Markdown (usually a LaTeX
   special character or an unclosed code fence) and save again.
8. Report: the exam name, a two-line summary of each exercise, the check result and
   the PDF path(s). Mention anything you were unsure about so the teacher can review it.
