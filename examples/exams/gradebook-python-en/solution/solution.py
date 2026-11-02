"""Gradebook — reference solution (invented example exam).

Demo:

>>> book = Gradebook()
>>> book.record(Submission("ada", "t1", 7))
>>> book.record(Submission("ada", "t1", 5))   # a lower retry does not count
>>> book.record(Submission("bob", "t1", 9))
>>> book.best("ada", "t1")
7
>>> ranking(book)
[('bob', 9), ('ada', 7)]
>>> ranking(Gradebook())                      # edge case: nobody submitted
[]
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Submission:
    student: str
    task: str
    score: int


# ---------------------------------------------------------------------------
# Exercise 1: invariant
#
#   For every student s and task t in best_scores, best_scores[s][t] is the
#   maximum score among all recorded submissions of s for t, and it is in
#   range(0, 11). Students with no submissions do not appear.
# ---------------------------------------------------------------------------


@dataclass
class Gradebook:
    best_scores: dict[str, dict[str, int]] = field(default_factory=dict)

    # -----------------------------------------------------------------------
    # Exercise 2: record, O(1) on average
    # -----------------------------------------------------------------------
    def record(self, sub: Submission) -> None:
        if not 0 <= sub.score <= 10:
            raise ValueError(f"score out of range: {sub.score}")
        tasks = self.best_scores.setdefault(sub.student, {})
        tasks[sub.task] = max(tasks.get(sub.task, sub.score), sub.score)

    def best(self, student: str, task: str) -> int:
        """Raises KeyError if the student never submitted the task."""
        return self.best_scores[student][task]

    def students(self) -> list[str]:
        return list(self.best_scores)

    def tasks_of(self, student: str) -> list[str]:
        return list(self.best_scores.get(student, {}))


# ---------------------------------------------------------------------------
# Exercise 3: client code. O(S*T + S log S), S students, T tasks per student.
# ---------------------------------------------------------------------------
def ranking(book: Gradebook) -> list[tuple[str, int]]:
    totals = [
        (student, sum(book.best(student, task) for task in book.tasks_of(student)))
        for student in book.students()
    ]
    return sorted(totals, key=lambda pair: (-pair[1], pair[0]))
