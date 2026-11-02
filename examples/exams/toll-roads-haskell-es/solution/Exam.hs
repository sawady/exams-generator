-- Rutas con peajes — solución de referencia (examen de ejemplo inventado)
module Exam where

----------------------------------------------------------------------
-- Tipos de datos
----------------------------------------------------------------------

type Km = Int
type Costo = Int

data Ruta = Llegada
          | Tramo Km Ruta
          | Peaje Costo Ruta
          | Cruce Ruta Ruta
  deriving (Show, Eq)

----------------------------------------------------------------------
-- Ejercicio 1: recursión explícita
----------------------------------------------------------------------

-- a.
kmMinimos :: Ruta -> Km
kmMinimos Llegada       = 0
kmMinimos (Tramo k r)   = k + kmMinimos r
kmMinimos (Peaje _ r)   = kmMinimos r
kmMinimos (Cruce r1 r2) = min (kmMinimos r1) (kmMinimos r2)

-- b.
cantidadDeRecorridos :: Ruta -> Int
cantidadDeRecorridos Llegada       = 1
cantidadDeRecorridos (Tramo _ r)   = cantidadDeRecorridos r
cantidadDeRecorridos (Peaje _ r)   = cantidadDeRecorridos r
cantidadDeRecorridos (Cruce r1 r2) = cantidadDeRecorridos r1 + cantidadDeRecorridos r2

-- c.
sinPeajes :: Ruta -> Ruta
sinPeajes Llegada       = Llegada
sinPeajes (Tramo k r)   = Tramo k (sinPeajes r)
sinPeajes (Peaje _ r)   = sinPeajes r
sinPeajes (Cruce r1 r2) = Cruce (sinPeajes r1) (sinPeajes r2)

-- d. El presupuesto viaja hacia abajo: cada peaje lo achica antes de seguir.
puedeLlegar :: Costo -> Ruta -> Bool
puedeLlegar _ Llegada       = True
puedeLlegar p (Tramo _ r)   = puedeLlegar p r
puedeLlegar p (Peaje c r)   = if c > p then False else puedeLlegar (p - c) r
puedeLlegar p (Cruce r1 r2) = puedeLlegar p r1 || puedeLlegar p r2

-- e. Sólo el primer peaje de cada recorrido: después del peaje, la ruta queda intacta.
quitarPrimerPeaje :: Ruta -> Ruta
quitarPrimerPeaje Llegada       = Llegada
quitarPrimerPeaje (Tramo k r)   = Tramo k (quitarPrimerPeaje r)
quitarPrimerPeaje (Peaje _ r)   = r
quitarPrimerPeaje (Cruce r1 r2) = Cruce (quitarPrimerPeaje r1) (quitarPrimerPeaje r2)

----------------------------------------------------------------------
-- Ejercicio 2a: esquemas de recursión
----------------------------------------------------------------------

foldRuta :: b -> (Km -> b -> b) -> (Costo -> b -> b) -> (b -> b -> b) -> Ruta -> b
foldRuta fl _  _  _  Llegada       = fl
foldRuta fl ft fp fc (Tramo k r)   = ft k (foldRuta fl ft fp fc r)
foldRuta fl ft fp fc (Peaje c r)   = fp c (foldRuta fl ft fp fc r)
foldRuta fl ft fp fc (Cruce r1 r2) = fc (foldRuta fl ft fp fc r1) (foldRuta fl ft fp fc r2)

recRuta :: b
        -> (Km -> Ruta -> b -> b)
        -> (Costo -> Ruta -> b -> b)
        -> (Ruta -> Ruta -> b -> b -> b)
        -> Ruta -> b
recRuta fl _  _  _  Llegada       = fl
recRuta fl ft fp fc (Tramo k r)   = ft k r (recRuta fl ft fp fc r)
recRuta fl ft fp fc (Peaje c r)   = fp c r (recRuta fl ft fp fc r)
recRuta fl ft fp fc (Cruce r1 r2) = fc r1 r2 (recRuta fl ft fp fc r1) (recRuta fl ft fp fc r2)

----------------------------------------------------------------------
-- Ejercicio 2b: redefiniciones con esquemas
----------------------------------------------------------------------

kmMinimos' :: Ruta -> Km
kmMinimos' = foldRuta 0 (+) (\_ n -> n) min

cantidadDeRecorridos' :: Ruta -> Int
cantidadDeRecorridos' = foldRuta 1 (\_ n -> n) (\_ n -> n) (+)

sinPeajes' :: Ruta -> Ruta
sinPeajes' = foldRuta Llegada Tramo (\_ r -> r) Cruce

-- El fold devuelve una función que espera el presupuesto restante.
puedeLlegar' :: Costo -> Ruta -> Bool
puedeLlegar' p r = foldRuta
  (\_ -> True)
  (\_ f -> f)
  (\c f q -> c <= q && f (q - c))
  (\f g q -> f q || g q)
  r
  p

-- Necesita la sub-ruta original: es recursión primitiva.
quitarPrimerPeaje' :: Ruta -> Ruta
quitarPrimerPeaje' = recRuta Llegada (\k _ r' -> Tramo k r') (\_ r _ -> r) (\_ _ r1' r2' -> Cruce r1' r2')

----------------------------------------------------------------------
-- Ejercicio 3: demostración
----------------------------------------------------------------------
{-
  Propiedad: cantidadDeRecorridos . sinPeajes = cantidadDeRecorridos

  Por extensionalidad, para toda r :: Ruta,
    cantidadDeRecorridos (sinPeajes r) = cantidadDeRecorridos r
  Por inducción estructural sobre r.

  Caso Llegada:
    cantidadDeRecorridos (sinPeajes Llegada)
  = cantidadDeRecorridos Llegada                       (sinPeajes.1)

  Caso Tramo k r, HI: cantidadDeRecorridos (sinPeajes r) = cantidadDeRecorridos r
    cantidadDeRecorridos (sinPeajes (Tramo k r))
  = cantidadDeRecorridos (Tramo k (sinPeajes r))       (sinPeajes.2)
  = cantidadDeRecorridos (sinPeajes r)                 (cantidadDeRecorridos.2)
  = cantidadDeRecorridos r                             (HI)
  = cantidadDeRecorridos (Tramo k r)                   (cantidadDeRecorridos.2, al revés)

  Caso Peaje c r, misma HI:
    cantidadDeRecorridos (sinPeajes (Peaje c r))
  = cantidadDeRecorridos (sinPeajes r)                 (sinPeajes.3)
  = cantidadDeRecorridos r                             (HI)
  = cantidadDeRecorridos (Peaje c r)                   (cantidadDeRecorridos.3, al revés)

  Caso Cruce r1 r2, HI1 y HI2 para r1 y r2:
    cantidadDeRecorridos (sinPeajes (Cruce r1 r2))
  = cantidadDeRecorridos (Cruce (sinPeajes r1) (sinPeajes r2))                 (sinPeajes.4)
  = cantidadDeRecorridos (sinPeajes r1) + cantidadDeRecorridos (sinPeajes r2)  (cantidadDeRecorridos.4)
  = cantidadDeRecorridos r1 + cantidadDeRecorridos r2                          (HI1, HI2)
  = cantidadDeRecorridos (Cruce r1 r2)                                         (cantidadDeRecorridos.4, al revés)
-}

----------------------------------------------------------------------
-- Demo
----------------------------------------------------------------------

rutaEjemplo :: Ruta
rutaEjemplo = Tramo 10 (Cruce (Peaje 5 (Tramo 20 Llegada)) (Tramo 40 (Peaje 2 Llegada)))

{-
>>> kmMinimos rutaEjemplo
30
>>> cantidadDeRecorridos rutaEjemplo
2
>>> puedeLlegar 3 rutaEjemplo      -- sólo alcanza para el peaje de 2
True
>>> puedeLlegar 1 rutaEjemplo      -- caso de borde: ningún peaje es pagable
False
>>> quitarPrimerPeaje (Peaje 1 (Peaje 2 Llegada))
Peaje 2 Llegada
-}
