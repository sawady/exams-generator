## Curso de ejemplo

## Parcial — Guardia veterinaria

Primavera de 2026

> Examen de ejemplo inventado para el repositorio `exams-generator`.

## Contexto

La **guardia de una veterinaria** atiende a sus pacientes según la **urgencia** del caso.
Cada **paciente** tiene una `ficha` que lo identifica y una `urgencia`, donde un número
más chico significa más urgente. Entre pacientes con la misma urgencia se atiende primero
al que llegó antes. Por ejemplo, si ingresan las fichas 1 (urgencia 3), 2 (urgencia 1) y
3 (urgencia 3), se atiende primero a la 2, después a la 1 y por último a la 3.

## Interfaz

Sea *N* la cantidad de pacientes en espera.

```c
typedef struct {
    int ficha;
    int urgencia;
} Paciente;

struct GuardiaSt;
typedef struct GuardiaSt* Guardia;
```

- ``Guardia nuevaGuardia(int capacidad)``: una guardia vacía con lugar para `capacidad`
  pacientes. Precondición: `capacidad > 0`. *O(1)*.
- ``int cantidad(Guardia g)``: la cantidad de pacientes en espera. *O(1)*.
- ``bool estaLlena(Guardia g)``: si no queda lugar. *O(1)*.
- ``void ingresar(Guardia g, Paciente p)``: agrega a `p` a la espera. Precondición: la
  guardia no está llena y la ficha de `p` no está en espera. *O(log N)*.
- ``Paciente proximo(Guardia g)``: el próximo paciente a atender, sin sacarlo.
  Precondición: la guardia no está vacía. *O(1)*.
- ``Paciente atender(Guardia g)``: saca y devuelve al próximo paciente. Precondición: la
  guardia no está vacía. *O(log N)*.
- ``void subirUrgencia(Guardia g, int ficha, int nuevaUrgencia)``: cambia la urgencia de
  un paciente en espera por otra igual o más urgente. Precondición: la ficha está en
  espera y `nuevaUrgencia` no es mayor que su urgencia actual. *O(N)*.
- ``void destruirGuardia(Guardia g)``: libera toda la memoria de la guardia. *O(1)*.

## Representación

Los pacientes se guardan en una **heap binaria** sobre un arreglo: los hijos de la
posición `i` están en `2 * i + 1` y `2 * i + 2`. El campo `orden` numera los ingresos para
desempatar.

```c
typedef struct {
    Paciente paciente;
    int orden;
} Entrada;

struct GuardiaSt {
    Entrada* heap;
    int cantidad;
    int capacidad;
    int proximoOrden;
};

/* Indica si `a` debe atenderse antes que `b`. Ya está implementada. */
static bool antes(Entrada a, Entrada b);
```

## Ejercicios

**Ejercicio 1)** Escribir los **invariantes de representación** de `GuardiaSt`.

**Ejercicio 2)** Implementar `ingresar` y `atender` en *O(log N)*. Indicar el propósito de
cada función auxiliar.

**Ejercicio 3)** Implementar `subirUrgencia` en *O(N)*. Explicar por qué, para restablecer
el invariante, alcanza con comparar la entrada modificada contra sus ancestros.

**Ejercicio 4)** Como **usuario** de la interfaz, implementar

```c
int atenderHasta(Guardia g, int umbral, Paciente* salida);
```

que atiende, en orden, a todos los pacientes con urgencia menor o igual que `umbral`, los
copia en `salida` y devuelve cuántos fueron. Se supone que `salida` tiene lugar suficiente.
Indicar su costo en función de *N* y de la cantidad *K* de pacientes atendidos.

**IMPORTANTE:** las soluciones deben mantener los costos pedidos.
