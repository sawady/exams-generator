/* Print queue — reference solution, exercise 1 (client code, invented example exam). */
#include "print_queue.h"

/* Removes every job with more than `maxPages` pages, keeping the others in
 * their original order, and returns how many jobs were removed.
 *
 * Efficiency: O(N), N = size(q). Each of the N jobs is dequeued once and
 * enqueued at most once, and both operations are O(1). Re-enqueueing never
 * overflows because the queue never holds more jobs than it had at the start.
 */
int cancelLargeJobs(PrintQueue q, int maxPages) {
    int n = size(q);
    int removed = 0;
    for (int i = 0; i < n; i++) {
        Job job = dequeue(q);
        if (job.pages > maxPages) {
            removed++;
        } else {
            enqueue(q, job);
        }
    }
    return removed;
}

/* Demo:
 *   q = [ {1, 3}, {2, 50}, {3, 7} ]
 *   cancelLargeJobs(q, 10) == 1, and q becomes [ {1, 3}, {3, 7} ]
 *   cancelLargeJobs(q, 0)  == 2 (edge case: everything is cancelled)
 */
