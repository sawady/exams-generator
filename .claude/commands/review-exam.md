---
description: Review a saved exam against the course profile and style guide (exams-generator MCP server)
argument-hint: <exam name>
---

Review the exam `$ARGUMENTS` with the `exams` MCP server tools:

1. `load_exam`, `get_course_profile`, and `get_style_guide` for its languages and locale.
2. `check_exam`; report failing or skipped languages.
3. Report OK or a concrete problem plus a suggested fix for each item:
   - header, structure and numbering follow the course profile;
   - every exercise is solvable with what the statement gives;
   - requested efficiencies are achievable and every variable in a bound is defined;
   - it fits the allotted time;
   - the statement has no solutions, grading criteria, internal notes, placeholders or
     real people's names;
   - the solution answers every exercise in order and stays inside the language subset
     the course allows (the compiler does not enforce course rules);
   - pen-and-paper answers (invariants, proofs, efficiency) are present and correct.
4. Do not change the exam unless asked; propose changes as a list.
