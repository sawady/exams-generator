# Haskell

## Code

- The solution is a module (`module Exam where`) that type-checks with
  `ghc -fno-code`. A file without a header is checked as if it had one.
- Identifiers in the exam's language (English names for an English exam).
- Give every top-level function a type signature.
- Derive `Show` and `Eq` on data types that the demo prints or compares.
- Use `Maybe` (or `Either`) for domain failures. If a constructor can cut a traversal
  short, every function that goes through it propagates the `Maybe`.
- Prefer explicit pattern matching on each constructor. Whether guards, `where`
  helpers or higher-order functions are allowed is a course decision: check the
  course profile.
- A demo block at the end, as a comment: one `>>>` line per main function with its
  expected result.

## Designing the algebraic data type

For recursion exercises, a type with 3-4 constructors often works well when it
mixes:

- a base case (`End`, `Leaf`, `Done`);
- a unary recursive case that changes some state (`Toll cost rest`);
- a unary recursive case with a cut-off condition;
- a binary case (a fork).

Mixing unary and binary recursive constructors makes folds and their types
interesting.

## Typical exercise types

Pick the ones the course profile asks for:

1. **Explicit recursion**: 3-5 functions over the type, at least one threading an
   extra parameter (budget, position, accumulated state) through the traversal.
2. **Recursion schemes**: define `foldT` (structural) and `recT` (primitive) and
   *deduce* their types.
3. **Rewrite with schemes**: redefine exercise 1 using only the schemes, with no
   explicit recursion. When a function threads state, the fold usually returns a
   function.
4. **Equational reasoning / structural induction**: state a property as an equality
   between functions using composition (`f . g = f`) and prove it by induction. It
   must need the induction hypothesis on sub-structures, not only case analysis.
5. **Abstract data types**: use a given interface as a client (with efficiency),
   write representation invariants, implement one or two operations.

Hints for threading functions may give the helper's type, never its code.
