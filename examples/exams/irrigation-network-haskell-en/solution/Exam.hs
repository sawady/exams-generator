-- Irrigation network — reference solution (invented example exam)
module Exam where

import Data.Maybe (catMaybes, mapMaybe)

----------------------------------------------------------------------
-- Data types
----------------------------------------------------------------------

type Plot = String
type Liters = Int

data Network = Sprinkler Plot Liters
             | Valve Bool Network
             | Split [Network]
  deriving (Show, Eq)

----------------------------------------------------------------------
-- Exercise 1: explicit recursion
----------------------------------------------------------------------

-- a.
flow :: Network -> Liters
flow (Sprinkler _ l)  = l
flow (Valve True n)   = flow n
flow (Valve False _)  = 0
flow (Split ns)       = sum (map flow ns)

-- b.
wateredPlots :: Network -> [Plot]
wateredPlots (Sprinkler p _)  = [p]
wateredPlots (Valve True n)   = wateredPlots n
wateredPlots (Valve False _)  = []
wateredPlots (Split ns)       = concatMap wateredPlots ns

-- c.
openAll :: Network -> Network
openAll (Sprinkler p l) = Sprinkler p l
openAll (Valve _ n)     = Valve True (openAll n)
openAll (Split ns)      = Split (map openAll ns)

-- d. A closed valve on the way costs one; an open one costs nothing.
valvesToOpen :: Plot -> Network -> Maybe Int
valvesToOpen p (Sprinkler q _)  = if p == q then Just 0 else Nothing
valvesToOpen p (Valve True n)   = valvesToOpen p n
valvesToOpen p (Valve False n)  = fmap (+ 1) (valvesToOpen p n)
valvesToOpen p (Split ns)       = bestOf (map (valvesToOpen p) ns)

-- The smallest of the present values, or Nothing if there are none.
-- `minimum` would pick Nothing, because Nothing < Just x.
bestOf :: [Maybe Int] -> Maybe Int
bestOf ms = case catMaybes ms of
  [] -> Nothing
  xs -> Just (minimum xs)

-- e.
prune :: Network -> Maybe Network
prune (Sprinkler p l)  = Just (Sprinkler p l)
prune (Valve True n)   = fmap (Valve True) (prune n)
prune (Valve False _)  = Nothing
prune (Split ns)       = splitOf (mapMaybe prune ns)

-- A split with the given branches, or Nothing if there are none left.
splitOf :: [Network] -> Maybe Network
splitOf [] = Nothing
splitOf ns = Just (Split ns)

----------------------------------------------------------------------
-- Exercise 2a: structural fold
----------------------------------------------------------------------

foldNetwork :: (Plot -> Liters -> b) -> (Bool -> b -> b) -> ([b] -> b) -> Network -> b
foldNetwork fs _  _  (Sprinkler p l) = fs p l
foldNetwork fs fv fl (Valve o n)     = fv o (foldNetwork fs fv fl n)
foldNetwork fs fv fl (Split ns)      = fl (map (foldNetwork fs fv fl) ns)

----------------------------------------------------------------------
-- Exercise 2b: redefinitions with the fold
----------------------------------------------------------------------

flow' :: Network -> Liters
flow' = foldNetwork (\_ l -> l) (\open r -> if open then r else 0) sum

openAll' :: Network -> Network
openAll' = foldNetwork Sprinkler (\_ n -> Valve True n) Split

valvesToOpen' :: Plot -> Network -> Maybe Int
valvesToOpen' p = foldNetwork
  (\q _ -> if p == q then Just 0 else Nothing)
  (\open r -> if open then r else fmap (+ 1) r)
  bestOf

-- The closed valve discards what the fold already computed behind it.
prune' :: Network -> Maybe Network
prune' = foldNetwork
  (\p l -> Just (Sprinkler p l))
  (\open r -> if open then fmap (Valve True) r else Nothing)
  (splitOf . catMaybes)

----------------------------------------------------------------------
-- Exercise 3
----------------------------------------------------------------------

-- The sprinklers that get water, from left to right.
wateredSprinklers :: Network -> [(Plot, Liters)]
wateredSprinklers = foldNetwork
  (\p l -> [(p, l)])
  (\open r -> if open then r else [])
  concat

-- foldl visits the sprinklers from left to right, so a new plot goes last.
flowByPlot :: Network -> [(Plot, Liters)]
flowByPlot = foldl addFlow [] . wateredSprinklers

-- Adds the liters to the plot's entry, or appends one if the plot is new.
addFlow :: [(Plot, Liters)] -> (Plot, Liters) -> [(Plot, Liters)]
addFlow [] entry = [entry]
addFlow ((q, m) : rest) (p, l)
  | p == q    = (q, m + l) : rest
  | otherwise = (q, m) : addFlow rest (p, l)

----------------------------------------------------------------------
-- Demo
----------------------------------------------------------------------

garden :: Network
garden = Split [ Sprinkler "tomatoes" 4
               , Valve False (Sprinkler "roses" 9)
               , Valve True (Split [Sprinkler "herbs" 2, Sprinkler "tomatoes" 3])
               ]

{-
>>> flow garden
9
>>> flow' (openAll' garden)
18
>>> wateredPlots garden
["tomatoes","herbs","tomatoes"]
>>> valvesToOpen "roses" garden
Just 1
>>> valvesToOpen' "tomatoes" garden
Just 0
>>> valvesToOpen "cabbage" garden
Nothing
>>> prune (Valve False (Sprinkler "roses" 9))      -- edge case: nothing remains
Nothing
>>> prune' (Split [Split [], Valve True (Sprinkler "herbs" 2)])
Just (Split [Valve True (Sprinkler "herbs" 2)])
>>> flowByPlot garden
[("tomatoes",7),("herbs",2)]
-}
