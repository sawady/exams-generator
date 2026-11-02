// Estacionamiento — solución de referencia, ejercicio 4 (examen de ejemplo inventado).
#include "estacionamiento.h"

#include <vector>

/* Ejercicio 4
 *
 * a. Con la versión del enunciado, para la lista {"AA", "BB", "AA"} el ciclo
 *    llega a i == 3 y lee ps[3], fuera del vector: comportamiento indefinido
 *    (puede devolver cualquier cosa o terminar el programa).
 *
 * b. Los dos errores:
 *    1. La condición del for es `i <= ps.size()`: recorre una posición de más.
 *       Va `i < ps.size()` (con un índice sin signo, para no comparar con signo
 *       distinto).
 *    2. Cuenta las patentes que SÍ entraron: `ingresar` devuelve true cuando el
 *       auto entra. Hay que contar cuando devuelve false.
 *
 *    Corregida, con un estacionamiento vacío de capacidad 2 y la lista
 *    {"AA", "BB", "AA"}, devuelve 1: el segundo "AA" ya está adentro.
 */
int ingresarTodas(Estacionamiento& e, const std::vector<Patente>& ps, Minuto ahora) {
    int rechazadas = 0;
    for (std::size_t i = 0; i < ps.size(); i++) {
        if (!e.ingresar(ps[i], ahora)) {
            rechazadas++;
        }
    }
    return rechazadas;
}

/* Demo:
 *   Estacionamiento e(2, 100);
 *   ingresarTodas(e, {"AA", "BB", "AA"}, 0) == 1
 *   ingresarTodas(e, {}, 0)                 == 0   (caso de borde: lista vacía)
 */
