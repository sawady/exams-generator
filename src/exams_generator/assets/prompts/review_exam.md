Review the saved exam `{name}` with the exams-generator tools.

1. `load_exam` with name `{name}`, then `get_course_profile` and `get_style_guide`
   for its languages and locale.
2. `check_exam`: report every failing or skipped language.
3. Go through this checklist and report each item as OK or with the concrete problem
   and a suggested fix:
   - The header, structure and exercise numbering follow the course profile.
   - Every exercise is solvable with the types and interfaces given in the statement.
   - Requested efficiencies are achievable with the stated costs, and every variable
     used in a bound is defined.
   - The exam fits the allotted time (implementation exercises ask for one or two
     operations).
   - The statement contains no solutions, grading criteria, internal notes,
     placeholders, or names of real people.
   - The reference solution answers every exercise, in the same order and numbering,
     and stays inside the language subset the course allows (the compiler does not
     enforce course restrictions: check them by reading).
   - Pen-and-paper answers (invariants, proofs, efficiency) are present and correct.
4. Do not modify the exam unless the teacher asks; propose changes as a list.
