# Haskell

## Código

- La solución es un módulo (`module Exam where`) que tipa con `ghc -fno-code`. Un
  archivo sin encabezado se verifica como si lo tuviera.
- Identificadores en el idioma del examen (nombres en español para un examen en
  español).
- Toda función de nivel superior lleva firma de tipo.
- Derivar `Show` y `Eq` en los tipos que la demo imprime o compara.
- `Maybe` (o `Either`) para errores de dominio. Si un constructor puede cortar un
  recorrido, toda función que pasa por él propaga el `Maybe`.
- Preferir pattern matching explícito sobre cada constructor. Si se permiten guardas,
  auxiliares en `where` u orden superior lo decide el curso: ver el perfil del curso.
- Un bloque de demo al final, como comentario: una línea `>>>` por función principal con
  su resultado esperado.

## Diseño del tipo algebraico

Para ejercicios de recursión suele funcionar bien un tipo con 3-4 constructores que
combine:

- un caso base (`Fin`, `Hoja`, `Llegada`);
- un caso recursivo unario que modifica algún estado (`Peaje costo resto`);
- un caso recursivo unario con una condición de corte;
- un caso binario (una bifurcación).

La mezcla de constructores recursivos unarios y binarios hace interesantes a los folds
y a sus tipos.

## Tipos de ejercicio habituales

Elegir los que pida el perfil del curso:

1. **Recursión explícita**: 3-5 funciones sobre el tipo, al menos una que arrastre un
   parámetro extra (presupuesto, posición, estado acumulado) durante el recorrido.
2. **Esquemas de recursión**: definir `foldT` (estructural) y `recT` (primitiva) y
   *deducir* sus tipos.
3. **Redefinir con esquemas**: reescribir el ejercicio 1 usando sólo los esquemas, sin
   recursión explícita. Cuando una función arrastra estado, el fold suele devolver una
   función.
4. **Razonamiento ecuacional / inducción estructural**: enunciar una propiedad como
   igualdad entre funciones usando composición (`f . g = f`) y demostrarla por
   inducción. Tiene que necesitar la hipótesis inductiva sobre las subestructuras, no
   sólo análisis de casos.
5. **Tipos abstractos de datos**: usar una interfaz dada como cliente (con eficiencia),
   escribir invariantes de representación, implementar una o dos operaciones.

Las ayudas para funciones que arrastran estado pueden dar el tipo de la auxiliar, nunca
su código.
