# Course profile: Intro to Algorithms at Example University (fictional)

<!-- Copy this file to $EXAMS_DATA_DIR/course.md and adapt it to your course.
The model reads it with `get_course_profile` and it takes precedence over the
generic style guide. The course, the university and every rule below are
invented: they only show the kind of rules a profile can state. -->

## Course

- Header line 1: "Example University — Intro to Algorithms".
- Exams: one midterm and one final. Header line 3: "<Season> <Year>".
- Exam language: English. Time: 2 hours, on paper, one handwritten cheat sheet allowed.

## Languages and allowed subset

- **Python** for every exercise: type hints required, `dataclasses` allowed, no
  third-party libraries. From the standard library only `collections` and `heapq`.
- No list comprehensions in the first midterm (they are taught later).
- Recursion must be stated as such in the exercise when it is required.

(The compiler and mypy do not enforce rules like these: reviewers must.)

## Structure

3 or 4 exercises, numbered consecutively:

1. **Modelling**: define the data types for the domain.
2. **Client code**: use a given interface; state the cost of the solution.
3. **Implementation**: one or two operations of a data structure, keeping a stated
   invariant.
4. (Final only) **Reading code**: trace a short function, or find its bug.

Every implementation exercise ends with:
"**NOTE:** state the invariant you rely on before writing any code."

## Auxiliary data types students may assume

`list`, `dict`, `set`, `collections.deque` and `heapq`, with the costs listed in the
appendix. Include in the appendix only those the exam uses.

## Other rules a profile could state

Examples of rules other courses might add here (this fictional course does not):

- Haskell: no guards, no `where` helpers, or no higher-order functions except
  partial application; every function written by explicit pattern matching.
- C++: a restricted subset, for instance structs, pointers, arrays, `new`/`delete`
  and `std::string` only, with no classes, templates or standard containers.
- Several languages in one exam (for example a Haskell part and a C++ part over the
  same domain), with a fixed order of exercise types per part.
- A fixed closing call-out after some exercises (preconditions, helper functions,
  efficiency justification).
