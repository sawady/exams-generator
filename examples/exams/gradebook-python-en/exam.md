## Example Course

## Make-up exam — Gradebook

Fall 2026

> Invented example exam for the `exams-generator` repository.

## Context

An online course lets students **submit** each **task** as many times as they want;
only their **best score** for each task counts. Scores are integers from 0 to 10. For
example, if `ada` submits task `t1` with 7 and then with 5, her score for `t1` is 7.

## Data types

```python
@dataclass(frozen=True)
class Submission:
    student: str
    task: str
    score: int

@dataclass
class Gradebook:
    best_scores: dict[str, dict[str, int]]   # student -> task -> best score

    def record(self, sub: Submission) -> None: ...
    def best(self, student: str, task: str) -> int: ...
    def students(self) -> list[str]: ...
    def tasks_of(self, student: str) -> list[str]: ...
```

- `record` registers a submission. It raises `ValueError` if the score is out of range.
- `best` returns the best score of a student for a task, and raises `KeyError` if the
  student never submitted it.
- `students` and `tasks_of` list the students with submissions and the tasks a student
  submitted, in *O(S)* and *O(T)*, where *S* is the number of students and *T* the
  number of tasks of that student.

## Exercises

**Exercise 1)** Write the **invariant** that `best_scores` keeps.

**Exercise 2)** Implement `record` in *O(1)* on average.

**Exercise 3)** As a **user** of `Gradebook`, implement

```python
def ranking(book: Gradebook) -> list[tuple[str, int]]: ...
```

which returns each student with the sum of their best scores, from highest to lowest
total; ties are broken alphabetically. State its complexity.
