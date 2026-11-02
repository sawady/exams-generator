## Curso de ejemplo

## Parcial — Rutas con peajes

Primavera de 2026

> Examen de ejemplo inventado para el repositorio `exams-generator`.

## Contexto

La **Cooperativa de Transporte del Valle** planifica los viajes de sus camiones por una
red de caminos rurales. Desde el depósito, cada camión sigue una **ruta** que puede
dividirse en cruces hasta alcanzar alguna **llegada**. Por el camino se recorren
**tramos** de cierta cantidad de kilómetros y se pagan **peajes**. Por ejemplo, una ruta
puede empezar con un tramo de 10 km y, en un cruce, ofrecer un recorrido con un peaje
de 5 seguido de 20 km, o uno de 40 km seguido de un peaje de 2.

Una **llegada** es el final de un recorrido. Un **tramo** indica cuántos kilómetros se
recorren antes de seguir. Un **peaje** indica cuánto hay que pagar para seguir. Un
**cruce** ofrece dos rutas posibles; el camión elige una.

## Tipos de datos

```haskell
type Km    = Int
type Costo = Int

data Ruta = Llegada
          | Tramo Km Ruta
          | Peaje Costo Ruta
          | Cruce Ruta Ruta
```

Se supone que todos los kilómetros y costos son positivos.

## Ejercicios

**Ejercicio 1)** Definir las siguientes funciones **por recursión explícita**:

a. ``kmMinimos :: Ruta -> Km``, que describe la cantidad de kilómetros del recorrido
   más corto hasta alguna llegada.

b. ``cantidadDeRecorridos :: Ruta -> Int``, que describe cuántos recorridos distintos
   llevan a una llegada.

c. ``sinPeajes :: Ruta -> Ruta``, que describe la misma ruta sin ningún peaje.

d. ``puedeLlegar :: Costo -> Ruta -> Bool``, que dado un presupuesto indica si existe
   algún recorrido en el que se puedan pagar todos los peajes sin quedar en negativo.

e. ``quitarPrimerPeaje :: Ruta -> Ruta``, que describe la ruta en la que, en cada
   recorrido, se eliminó el primer peaje (si lo hay). Los peajes posteriores se
   mantienen.

**AYUDA:** para `puedeLlegar` conviene pensar en el presupuesto *restante* al pasar por
cada peaje.

**Ejercicio 2)** Esquemas de recursión sobre `Ruta`.

a. Definir los esquemas de recursión **estructural** (`foldRuta`) y **primitiva**
   (`recRuta`). Deducir y escribir sus tipos.

b. Redefinir las funciones del ejercicio 1 usando **exclusivamente** esos esquemas. No
   se permite recursión explícita ni funciones auxiliares recursivas.

**Ejercicio 3)** Demostrar por inducción estructural que:

```haskell
cantidadDeRecorridos . sinPeajes = cantidadDeRecorridos
```
