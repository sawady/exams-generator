# Guía de estilo de exámenes (general)

Convenciones por defecto para redactar exámenes de programación. El perfil del curso
(`get_course_profile`) tiene prioridad sobre esta guía: si dice otra cosa, se sigue el
perfil.

## El enunciado (Markdown que reciben los estudiantes)

- **Encabezado**: nombre del curso, tipo de examen (parcial, recuperatorio, final)
  y período, como indique el perfil del curso. Después, el título del examen: un nombre
  corto para el dominio.
- **Contexto**: uno a tres párrafos en prosa que motiven un dominio inventado y aclaren
  sus convenciones ("no hay dos socios con el mismo número"). Dar al menos un ejemplo
  concreto. Términos del dominio en **negrita** e identificadores entre `backticks`.
- **Tipos e interfaces** en bloques de código con el lenguaje indicado (`haskell`, `c`,
  `cpp`, `python`). Cada operación se describe en prosa junto a su firma: propósito,
  precondiciones ("Se supone que...", "Precondición:"), comportamiento en casos de borde
  y la eficiencia esperada cuando el curso la evalúa.
- **Ejercicios** numerados en forma consecutiva en todo el examen, aunque mezcle
  lenguajes: `**Ejercicio 1)**`, `**Ejercicio 2)**`, ... Los incisos como `a.`, `b.`.
- **Eficiencia** en cursiva con O mayúscula: *O(log N)*. Definir cada variable que
  aparezca en una cota (*N* = cantidad de socios, ...) al presentar la interfaz.
- **Llamados de atención** en negrita y mayúsculas: **OBSERVACIÓN:**, **AYUDA:**,
  **RECORDATORIO:**, **IMPORTANTE:**.
- **Anexo**: si los ejercicios usan interfaces auxiliares (maps, conjuntos, listas...),
  listar sólo las que se usan, en una tabla de firma y costo.

## Lo que el enunciado no debe incluir

- Soluciones, criterios de corrección ni notas internas del equipo docente.
- Nombres de personas reales, empresas reales ni datos de estudiantes.
- `TODO`, marcadores pendientes ni texto dirigido a quien redacta.

## Dificultad y alcance

- El examen tiene que poder resolverse en el tiempo disponible (típicamente 2-3 horas).
  Un ejercicio de implementación pide una o dos operaciones, no toda la interfaz.
- Cada ejercicio tiene que poder resolverse con los tipos e interfaces del enunciado.
  Las eficiencias pedidas tienen que ser alcanzables con los costos declarados.
- Preferir un único dominio que conecte todos los ejercicios, con vínculos reales (no
  cosméticos) entre las partes.
- Variar las representaciones entre exámenes; no recurrir siempre a la misma estructura.
- Las ayudas pueden nombrar el tipo de una función auxiliar, pero no dar su código.

## La solución de referencia

- Uno o más archivos fuente que **compilan / tipan** con el checker correspondiente
  (`check_snippet`, y `save_exam` vuelve a verificar). Un examen no está listo hasta que
  la verificación pasa.
- Reflejar el enunciado: un separador comentado por ejercicio, en el mismo orden y
  numeración.
- Los comentarios explican el *por qué* (invariantes, decisiones de diseño), no el
  *qué* hace el código.
- Las respuestas "de papel" (invariantes, demostraciones, justificación de eficiencia)
  van como comentarios de bloque en la solución, junto al ejercicio que responden.
- Cerrar con un bloque de demo (comentado) con algunas invocaciones de ejemplo y su
  resultado esperado, incluido al menos un caso de borde.
