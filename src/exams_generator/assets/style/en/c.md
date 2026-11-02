# C

## Code

- The solution compiles with `gcc -fsyntax-only -std=c11 -Wall -Wextra` (no `main`
  needed). Warnings are reported; likely bugs (missing return, implicit declarations,
  pointer/integer mix-ups) fail the check.
- Split an abstract data type into a header with an opaque type and the prototypes,
  and a source file with the struct definition and the implementation. One common
  layout: `name.h` declares `struct NameSt;` and `typedef struct NameSt* Name;`,
  `name.c` defines `struct NameSt`. Follow the naming the course profile asks for,
  if any. Save both files as solution files.
- Every `malloc` has an owner and a matching `free`; provide a `destroy` operation for
  every type that allocates.
- No global mutable state. No I/O inside operations unless the exercise is about I/O.
- Document purpose and preconditions above each prototype.

## In the statement

- Show the header and the private struct side by side in a two-column table when the
  exercise asks students to work on the representation:

  | `queue.h` | `queue.c` |
  |---|---|
  | `struct QueueSt;`<br>`typedef struct QueueSt* Queue;` | `struct QueueSt {`<br>`  int* buf; int first; int size; int cap;`<br>`};` |

- If fields are abbreviated so the exam fits on paper, say so in a **NOTE:**.

## Typical exercise types

1. **Client code**: given the interface, implement a function that uses it, and state
   its efficiency.
2. **Representation invariants**: given the struct, list the invariants that keep a
   value valid (2-4 non-trivial ones).
3. **Implementation**: implement one or two interface operations with the requested
   efficiency, managing memory by hand (arrays, linked nodes, resizing).
4. **Memory reasoning**: draw or describe the heap after a sequence of operations; spot
   a leak or a dangling pointer.
