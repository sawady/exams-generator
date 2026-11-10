/* Guardia veterinaria — solución de referencia, ejercicios 1 a 3 (examen de ejemplo inventado). */
#include <stdlib.h>

#include "guardia.h"

typedef struct {
    Paciente paciente;
    int orden;         /* número de ingreso: desempata entre urgencias iguales */
} Entrada;

struct GuardiaSt {
    Entrada* heap;     /* heap binaria: los hijos de i están en 2 * i + 1 y 2 * i + 2 */
    int cantidad;      /* pacientes en espera */
    int capacidad;
    int proximoOrden;  /* número del próximo ingreso */
};

/* Indica si `a` debe atenderse antes que `b`: es un orden total, porque `orden` no se repite. */
static bool antes(Entrada a, Entrada b) {
    if (a.paciente.urgencia != b.paciente.urgencia) {
        return a.paciente.urgencia < b.paciente.urgencia;
    }
    return a.orden < b.orden;
}

/* ------------------------------------------------------------------
 * Ejercicio 1: invariantes de representación
 *
 *   - heap apunta a un arreglo de exactamente `capacidad` Entrada, y capacidad > 0.
 *   - 0 <= cantidad <= capacidad.
 *   - Propiedad de heap: para todo 0 < i < cantidad, la entrada heap[(i - 1) / 2]
 *     se atiende antes que heap[i], es decir antes(heap[(i - 1) / 2], heap[i]).
 *   - Entre las posiciones 0 y cantidad - 1 no se repiten ni `orden` ni `ficha`.
 *   - Para todo 0 <= i < cantidad, 0 <= heap[i].orden < proximoOrden.
 * ------------------------------------------------------------------ */

Guardia nuevaGuardia(int capacidad) {
    Guardia g = malloc(sizeof(struct GuardiaSt));
    g->heap = malloc(sizeof(Entrada) * capacidad);
    g->cantidad = 0;
    g->capacidad = capacidad;
    g->proximoOrden = 0;
    return g;
}

int cantidad(Guardia g) { return g->cantidad; }

bool estaLlena(Guardia g) { return g->cantidad == g->capacidad; }

Paciente proximo(Guardia g) { return g->heap[0].paciente; }

/* Propósito: intercambia las entradas de las posiciones i y j. */
static void intercambiar(Guardia g, int i, int j) {
    Entrada aux = g->heap[i];
    g->heap[i] = g->heap[j];
    g->heap[j] = aux;
}

/* Propósito: restablece la propiedad de heap cuando la entrada de la posición i
 * puede tener que atenderse antes que sus ancestros. O(log N). */
static void flotar(Guardia g, int i) {
    while (i > 0 && antes(g->heap[i], g->heap[(i - 1) / 2])) {
        intercambiar(g, i, (i - 1) / 2);
        i = (i - 1) / 2;
    }
}

/* Propósito: restablece la propiedad de heap cuando la entrada de la posición i
 * puede tener que atenderse después que sus descendientes. O(log N). */
static void hundir(Guardia g, int i) {
    while (true) {
        int primero = i;
        int izquierdo = 2 * i + 1;
        int derecho = 2 * i + 2;
        if (izquierdo < g->cantidad && antes(g->heap[izquierdo], g->heap[primero])) {
            primero = izquierdo;
        }
        if (derecho < g->cantidad && antes(g->heap[derecho], g->heap[primero])) {
            primero = derecho;
        }
        if (primero == i) {
            return;
        }
        intercambiar(g, i, primero);
        i = primero;
    }
}

/* ------------------------------------------------------------------
 * Ejercicio 2: ingresar y atender en O(log N). La altura de la heap es
 * O(log N), porque el arreglo la mantiene completa.
 * ------------------------------------------------------------------ */

void ingresar(Guardia g, Paciente p) {
    Entrada nueva = { p, g->proximoOrden };
    g->proximoOrden++;
    g->heap[g->cantidad] = nueva;
    g->cantidad++;
    flotar(g, g->cantidad - 1);
}

Paciente atender(Guardia g) {
    Paciente p = g->heap[0].paciente;
    g->cantidad--;
    g->heap[0] = g->heap[g->cantidad];
    hundir(g, 0);
    return p;
}

/* ------------------------------------------------------------------
 * Ejercicio 3: subirUrgencia en O(N): la búsqueda es O(N) y flotar es O(log N).
 *
 * La entrada modificada sólo puede adelantarse: sigue atendiéndose antes que
 * todos sus descendientes, así que la propiedad de heap sólo puede romperse
 * entre ella y su padre, y flotar la restablece subiéndola por sus ancestros.
 * ------------------------------------------------------------------ */

void subirUrgencia(Guardia g, int ficha, int nuevaUrgencia) {
    int i = 0;
    while (g->heap[i].paciente.ficha != ficha) {
        i++;
    }
    g->heap[i].paciente.urgencia = nuevaUrgencia;
    flotar(g, i);
}

void destruirGuardia(Guardia g) {
    free(g->heap);
    free(g);
}
