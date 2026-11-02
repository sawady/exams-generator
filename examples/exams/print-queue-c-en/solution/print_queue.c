/* Print queue — reference solution, exercises 2-4 (invented example exam). */
#include <stdlib.h>

#include "print_queue.h"

struct PrintQueueSt {
    Job* jobs;     /* circular buffer of `capacity` slots */
    int first;     /* index of the oldest job */
    int count;     /* jobs currently waiting */
    int capacity;
    int pages;     /* cached sum of the pages of the waiting jobs */
};

/* ------------------------------------------------------------------
 * Exercise 2: representation invariants
 *
 *   - jobs points to an array of exactly `capacity` Job, and capacity > 0.
 *   - 0 <= first < capacity.
 *   - 0 <= count <= capacity.
 *   - The waiting jobs are jobs[(first + i) % capacity] for 0 <= i < count,
 *     in arrival order.
 *   - pages == sum of .pages over the waiting jobs, and every waiting job
 *     has pages > 0 (so pages >= count).
 * ------------------------------------------------------------------ */

PrintQueue newQueue(int capacity) {
    PrintQueue q = malloc(sizeof(struct PrintQueueSt));
    q->jobs = malloc(sizeof(Job) * capacity);
    q->first = 0;
    q->count = 0;
    q->capacity = capacity;
    q->pages = 0;
    return q;
}

int size(PrintQueue q) { return q->count; }

bool isFull(PrintQueue q) { return q->count == q->capacity; }

int pendingPages(PrintQueue q) { return q->pages; }

/* ------------------------------------------------------------------
 * Exercise 3: enqueue and dequeue in O(1)
 * ------------------------------------------------------------------ */

void enqueue(PrintQueue q, Job job) {
    int last = (q->first + q->count) % q->capacity;
    q->jobs[last] = job;
    q->count++;
    q->pages += job.pages;
}

Job dequeue(PrintQueue q) {
    Job job = q->jobs[q->first];
    q->first = (q->first + 1) % q->capacity;
    q->count--;
    q->pages -= job.pages;
    return job;
}

/* ------------------------------------------------------------------
 * Exercise 4: grow in O(N). Copying in queue order "unrolls" the circle,
 * so the new buffer starts at index 0.
 * ------------------------------------------------------------------ */

void grow(PrintQueue q) {
    int newCapacity = q->capacity * 2;
    Job* bigger = malloc(sizeof(Job) * newCapacity);
    for (int i = 0; i < q->count; i++) {
        bigger[i] = q->jobs[(q->first + i) % q->capacity];
    }
    free(q->jobs);
    q->jobs = bigger;
    q->first = 0;
    q->capacity = newCapacity;
}

void destroyQueue(PrintQueue q) {
    free(q->jobs);
    free(q);
}
