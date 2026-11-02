## Curso de ejemplo

## Final — Estacionamiento

Primavera de 2026

> Examen de ejemplo inventado para el repositorio `exams-generator`.

## Contexto

Un **estacionamiento** de barrio tiene una cantidad fija de lugares y cobra una
**tarifa por hora**. Cada auto se identifica por su **patente** y, al entrar, se anota el
**minuto de entrada** (los minutos se cuentan desde la apertura). Al retirarse se cobra
cada **hora iniciada**, y toda estadía paga al menos una hora. Por ejemplo, con una
tarifa de 100, un auto que entra en el minuto 0 y sale en el minuto 61 paga 200; uno que
entra y sale en el mismo minuto paga 100.

## Interfaz

Sea *N* la cantidad de autos adentro.

```cpp
using Patente = std::string;
using Minuto = int;

class Estacionamiento {
public:
    Estacionamiento(int capacidad, int tarifaPorHora);
    int capacidad() const;
    int ocupados() const;
    bool estaAdentro(const Patente& p) const;
    int recaudado() const;

    bool ingresar(const Patente& p, Minuto ahora);
    int retirar(const Patente& p, Minuto ahora);
    std::vector<Patente> masAntiguos(int k) const;

private:
    int capacidad_;
    int tarifa_;
    std::unordered_map<Patente, Minuto> entradas_;  // patente -> minuto de entrada
    int recaudado_;
};
```

- ``Estacionamiento(int capacidad, int tarifaPorHora)``: un estacionamiento vacío.
  Precondición: `capacidad > 0` y `tarifaPorHora > 0`. *O(1)*.
- ``capacidad()``, ``ocupados()``, ``estaAdentro(p)``, ``recaudado()``: la cantidad de
  lugares, la de autos adentro, si la patente `p` está adentro y el total cobrado hasta
  ahora. *O(1)*.
- ``ingresar(p, ahora)``: si hay lugar y `p` no está adentro, la anota con minuto de
  entrada `ahora` y devuelve `true`; si no, no cambia nada y devuelve `false`. *O(1)*.
- ``retirar(p, ahora)``: saca a `p`, suma el importe a lo recaudado y lo devuelve. Si `p`
  no está adentro lanza `std::out_of_range`. Se supone que `ahora` no es anterior al
  minuto de entrada de `p`. *O(1)*.
- ``masAntiguos(k)``: las `k` patentes que llevan más tiempo adentro, de la más antigua a
  la más nueva (si hay menos de `k`, todas). Si dos entraron en el mismo minuto, va
  primero la menor en orden alfabético. Si `k <= 0`, ninguna.

El constructor y las cuatro operaciones de consulta ya están implementados. Las
operaciones de `std::unordered_map` tienen costo promedio *O(1)*.

## Ejercicios

**Ejercicio 1)** Implementar `ingresar` y `retirar`.

**Ejercicio 2)** Escribir los **invariantes de representación** de `Estacionamiento`.
Para cada uno, indicar qué operación podría romperlo y por qué no lo hace.

**Ejercicio 3)** Implementar `masAntiguos` con costo *O(N log N)* en el peor caso.
Justificar el costo.

**Ejercicio 4)** Un cliente de la clase escribió la siguiente función:

```cpp
// Propósito: intenta ingresar cada patente de ps, en orden, en el minuto ahora,
// y devuelve cuántas no pudieron entrar.
int ingresarTodas(Estacionamiento& e, const std::vector<Patente>& ps, Minuto ahora) {
    int rechazadas = 0;
    for (int i = 0; i <= ps.size(); i++) {
        if (e.ingresar(ps[i], ahora)) {
            rechazadas++;
        }
    }
    return rechazadas;
}
```

a. ¿Qué pasa al llamarla con un estacionamiento vacío de capacidad 2 y la lista
   `{"AA", "BB", "AA"}`?

b. La función tiene dos errores. Encontrarlos y corregirlos. ¿Qué devuelve la versión
   corregida para el caso del punto a?

**IMPORTANTE:** se puede usar cualquier parte de la biblioteca estándar de C++17.
