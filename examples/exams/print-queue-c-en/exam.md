## Example Course

## Midterm — Print queue

Fall 2026

> Invented example exam for the `exams-generator` repository.

## Context

The shared printer of a small **design studio** keeps the documents waiting to be
printed in a **print queue**. Each **job** has a unique `id` and a number of `pages`,
always positive. Jobs are printed in arrival order. For example, after sending jobs
`{1, 3}`, `{2, 50}` and `{3, 7}`, the next job to print is `{1, 3}` and there are 60
pending pages.

## Interface

Let *N* be the number of jobs in the queue.

```c
typedef struct {
    int id;
    int pages;
} Job;

struct PrintQueueSt;
typedef struct PrintQueueSt* PrintQueue;
```

- ``PrintQueue newQueue(int capacity)``: an empty queue with room for `capacity` jobs.
  Precondition: `capacity > 0`. *O(1)*.
- ``int size(PrintQueue q)``: number of waiting jobs. *O(1)*.
- ``bool isFull(PrintQueue q)``: whether the queue has no room left. *O(1)*.
- ``int pendingPages(PrintQueue q)``: total pages of the waiting jobs. *O(1)*.
- ``void enqueue(PrintQueue q, Job job)``: adds `job` at the end. Precondition: the
  queue is not full. *O(1)*.
- ``Job dequeue(PrintQueue q)``: removes and returns the first job. Precondition: the
  queue is not empty. *O(1)*.
- ``void grow(PrintQueue q)``: doubles the capacity, keeping the jobs in order. *O(N)*.
- ``void destroyQueue(PrintQueue q)``: frees all the memory of the queue. *O(1)*.

## Exercises

**Exercise 1)** As a **user** of the interface, implement

```c
int cancelLargeJobs(PrintQueue q, int maxPages);
```

which removes every job with more than `maxPages` pages, keeps the rest in their
original order, and returns how many jobs were removed. State its efficiency and
justify it.

For exercises 2 to 4, consider this representation, where the jobs are stored in a
**circular buffer**:

| `print_queue.h` | `print_queue.c` |
|---|---|
| `struct PrintQueueSt;`<br>`typedef struct PrintQueueSt* PrintQueue;` | `struct PrintQueueSt {`<br>`    Job* jobs;`<br>`    int first;`<br>`    int count;`<br>`    int capacity;`<br>`    int pages;`<br>`};` |

**Exercise 2)** Write the **representation invariants** of `PrintQueueSt`.

**Exercise 3)** Implement `enqueue` and `dequeue` in *O(1)*.

**Exercise 4)** Implement `grow` in *O(N)*. Explain what happens to `first`.

**REMINDER:** state the purpose and preconditions of any helper function you write.
