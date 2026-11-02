# C++

## Code

- The solution compiles with `g++ -fsyntax-only -std=c++17 -Wall -Wextra` (no `main`
  needed).
- Some courses restrict the language (for example: no classes, no templates, no
  standard containers). If yours does, state the subset in the course profile; the
  solution must stay inside it, because the compiler will not enforce it.
- With the full language, an abstract data type is usually a class: declaration in
  `name.h`, member definitions in `name.cpp`, the invariant kept by the constructor
  and every public method. Without classes, use the same opaque-pointer layout as in C.
- Prefer standard containers and RAII. When the exercise manages memory by hand, every
  `new` has a matching `delete` (`delete[]` for arrays).
- Document purpose and preconditions above each prototype.

## Typical exercise types

The same as for C (client code, invariants, implementation, memory reasoning). When
the course allows the full language, add: designing a class with an invariant kept by
its constructor and methods, and choosing a standard container with a justified cost.
