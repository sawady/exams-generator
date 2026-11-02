# Python

## Code

- The solution byte-compiles and, when mypy is installed, type-checks with
  `mypy --check-untyped-defs`. Annotate every function so mypy has something to check.
- Use `dataclasses` (or `typing.NamedTuple`) for domain records and `enum.Enum` for
  closed sets of values.
- Operations are pure functions or methods; no `input()`/`print()` inside them unless
  the exercise is about I/O.
- Raise a specific exception (`ValueError`, `KeyError`) for violated preconditions and
  say which in the statement.
- The demo block can be a module docstring or comment with `>>>` lines (doctest style).

## Typical exercise types

1. **Modelling**: define the data types for a described domain.
2. **Client code**: given a class or module interface, write a function that uses it,
   with its complexity.
3. **Implementation**: implement one or two methods of a data structure keeping an
   invariant (and state the invariant).
4. **Reading code**: given a short function, say what it returns for an input, find the
   bug, or give its complexity.
