# C++

## Código

- La solución compila con `g++ -fsyntax-only -std=c++17 -Wall -Wextra` (no hace falta
  `main`).
- Algunos cursos restringen el lenguaje (por ejemplo: sin clases, sin templates, sin
  contenedores estándar). Si el tuyo lo hace, declarar el subconjunto en el perfil del
  curso; la solución tiene que respetarlo, porque el compilador no lo controla.
- Con el lenguaje completo, un tipo abstracto suele ser una clase: la declaración en
  `nombre.h`, las definiciones en `nombre.cpp`, y el invariante lo mantienen el
  constructor y cada método público. Sin clases, usar la misma organización con
  puntero opaco que en C.
- Preferir contenedores estándar y RAII. Cuando el ejercicio maneja la memoria a mano,
  todo `new` tiene su `delete` (`delete[]` para arrays).
- Propósito y precondiciones documentados sobre cada prototipo.

## Tipos de ejercicio habituales

Los mismos que en C (usuario, invariantes, implementación, razonamiento sobre memoria).
Si el curso permite el lenguaje completo, se suman: diseñar una clase cuyo invariante
mantienen el constructor y los métodos, y elegir un contenedor estándar justificando su
costo.
