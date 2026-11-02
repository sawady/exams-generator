/* Print queue: interface given in the statement (invented example exam). */
#ifndef PRINT_QUEUE_H
#define PRINT_QUEUE_H

#include <stdbool.h>

typedef struct {
    int id;
    int pages;
} Job;

struct PrintQueueSt;
typedef struct PrintQueueSt* PrintQueue;

/* An empty queue with room for `capacity` jobs. Precondition: capacity > 0. O(1). */
PrintQueue newQueue(int capacity);

/* Number of jobs waiting. O(1). */
int size(PrintQueue q);

/* Whether the queue has no room left. O(1). */
bool isFull(PrintQueue q);

/* Total pages of all waiting jobs. O(1). */
int pendingPages(PrintQueue q);

/* Adds `job` at the end. Precondition: !isFull(q) and job.pages > 0. O(1). */
void enqueue(PrintQueue q, Job job);

/* Removes and returns the first job. Precondition: size(q) > 0. O(1). */
Job dequeue(PrintQueue q);

/* Doubles the capacity, keeping the jobs in order. O(N). */
void grow(PrintQueue q);

/* Frees all memory used by the queue. O(1). */
void destroyQueue(PrintQueue q);

#endif
