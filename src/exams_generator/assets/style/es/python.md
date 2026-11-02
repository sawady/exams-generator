# Python

## Código

- La solución compila a bytecode y, si mypy está instalado, tipa con
  `mypy --check-untyped-defs`. Anotar todas las funciones para que mypy tenga qué
  verificar.
- `dataclasses` (o `typing.NamedTuple`) para los registros del dominio y `enum.Enum`
  para conjuntos cerrados de valores.
- Las operaciones son funciones puras o métodos; sin `input()`/`print()` adentro salvo
  que el ejercicio trate sobre entrada/salida.
- Lanzar una excepción específica (`ValueError`, `KeyError`) cuando no se cumple una
  precondición, y decir cuál en el enunciado.
- La demo puede ser un docstring de módulo o un comentario con líneas `>>>` (estilo
  doctest).

## Tipos de ejercicio habituales

1. **Modelado**: definir los tipos de datos de un dominio descripto.
2. **Usuario**: dada la interfaz de una clase o módulo, escribir una función que la use,
   con su complejidad.
3. **Implementación**: implementar uno o dos métodos de una estructura manteniendo un
   invariante (y enunciar el invariante).
4. **Lectura de código**: dada una función corta, decir qué devuelve para una entrada,
   encontrar el error o dar su complejidad.
