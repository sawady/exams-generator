# C

## Código

- La solución compila con `gcc -fsyntax-only -std=c11 -Wall -Wextra` (no hace falta
  `main`). Los warnings se informan; los errores probables (falta de `return`,
  declaraciones implícitas, mezclar punteros y enteros) hacen fallar la verificación.
- Un tipo abstracto se divide en un header con el tipo opaco y los prototipos, y un
  archivo fuente con la definición del struct y la implementación. Una organización
  habitual: `nombre.h` declara `struct NombreSt;` y `typedef struct NombreSt* Nombre;`,
  `nombre.c` define `struct NombreSt`. Si el perfil del curso pide otra convención de
  nombres, seguirla. Guardar ambos como archivos de la solución.
- Todo `malloc` tiene un dueño y su `free`; cada tipo que reserva memoria ofrece una
  operación para destruirlo.
- Sin estado global mutable. Sin entrada/salida dentro de las operaciones salvo que el
  ejercicio trate sobre eso.
- Propósito y precondiciones documentados sobre cada prototipo.

## En el enunciado

- Mostrar el header y el struct privado lado a lado, en una tabla de dos columnas,
  cuando el ejercicio pide trabajar sobre la representación:

  | `cola.h` | `cola.c` |
  |---|---|
  | `struct ColaSt;`<br>`typedef struct ColaSt* Cola;` | `struct ColaSt {`<br>`  int* buf; int primero; int tam; int cap;`<br>`};` |

- Si se abrevian campos para que el examen entre en papel, aclararlo con una
  **OBSERVACIÓN:**.

## Tipos de ejercicio habituales

1. **Usuario**: dada la interfaz, implementar una función que la use y dar su
   eficiencia.
2. **Invariantes de representación**: dado el struct, listar los invariantes que
   mantienen válido un valor (2-4 no triviales).
3. **Implementación**: implementar una o dos operaciones de la interfaz con la
   eficiencia pedida, manejando la memoria a mano (arrays, nodos enlazados,
   redimensionado).
4. **Razonamiento sobre memoria**: dibujar o describir la memoria dinámica después de
   una secuencia de operaciones; encontrar una pérdida o un puntero colgante.
