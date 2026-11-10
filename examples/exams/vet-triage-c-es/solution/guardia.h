/* Guardia veterinaria: interfaz dada en el enunciado (examen de ejemplo inventado). */
#ifndef GUARDIA_H
#define GUARDIA_H

#include <stdbool.h>

typedef struct {
    int ficha;
    int urgencia;
} Paciente;

struct GuardiaSt;
typedef struct GuardiaSt* Guardia;

/* Una guardia vacía con lugar para `capacidad` pacientes. Precondición: capacidad > 0. O(1). */
Guardia nuevaGuardia(int capacidad);

/* Cantidad de pacientes en espera. O(1). */
int cantidad(Guardia g);

/* Si no queda lugar. O(1). */
bool estaLlena(Guardia g);

/* Agrega a `p` a la espera. Precondición: !estaLlena(g) y la ficha de `p` no está en espera. O(log N). */
void ingresar(Guardia g, Paciente p);

/* El próximo paciente a atender, sin sacarlo. Precondición: cantidad(g) > 0. O(1). */
Paciente proximo(Guardia g);

/* Saca y devuelve al próximo paciente. Precondición: cantidad(g) > 0. O(log N). */
Paciente atender(Guardia g);

/* Cambia la urgencia de un paciente por otra igual o más urgente.
 * Precondición: la ficha está en espera y nuevaUrgencia no es mayor que la actual. O(N). */
void subirUrgencia(Guardia g, int ficha, int nuevaUrgencia);

/* Libera toda la memoria de la guardia. O(1). */
void destruirGuardia(Guardia g);

#endif
