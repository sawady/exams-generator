/* Guardia veterinaria — solución de referencia, ejercicio 4 (código cliente, examen de ejemplo inventado). */
#include "guardia.h"

/* Propósito: atiende, en orden, a todos los pacientes con urgencia menor o igual que
 * `umbral`, los copia en `salida` y devuelve cuántos fueron.
 * Precondición: `salida` tiene lugar para todos esos pacientes.
 *
 * Costo: O(K log N), con K la cantidad de pacientes atendidos. Hay K + 1 consultas a
 * proximo, en O(1), y K llamadas a atender, en O(log N). Los pacientes salen de menor a
 * mayor urgencia, así que el primero que supera el umbral corta el recorrido.
 */
int atenderHasta(Guardia g, int umbral, Paciente* salida) {
    int atendidos = 0;
    while (cantidad(g) > 0 && proximo(g).urgencia <= umbral) {
        salida[atendidos] = atender(g);
        atendidos++;
    }
    return atendidos;
}

/* Demo:
 *   g = [ ficha 1, urgencia 3 ], [ ficha 2, urgencia 1 ], [ ficha 3, urgencia 3 ]
 *   atenderHasta(g, 1, s) == 1, y s[0] tiene ficha 2
 *   atenderHasta(g, 3, s) == 2, y s tiene fichas 1 y 3, en ese orden
 *   atenderHasta(g, 3, s) == 0 (caso de borde: la guardia está vacía)
 */
