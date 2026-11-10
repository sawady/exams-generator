## Example Course

## Midterm — Irrigation network

Fall 2026

> Invented example exam for the `exams-generator` repository.

## Context

A **community garden** waters its plots through a network of pipes. A **sprinkler**
delivers some liters per minute to a plot. A **valve**, open or closed, controls the
pipe that continues behind it: water only gets past it when it is open. A **split**
divides a pipe into any number of branches. A plot may have several sprinklers.

For example, in this garden the roses stay dry until their valve is opened, and the
sprinklers that get water deliver 4 + 2 + 3 = 9 liters per minute:

```haskell
garden :: Network
garden = Split [ Sprinkler "tomatoes" 4
               , Valve False (Sprinkler "roses" 9)
               , Valve True (Split [Sprinkler "herbs" 2, Sprinkler "tomatoes" 3])
               ]
```

## Data types

```haskell
type Plot   = String
type Liters = Int

data Network = Sprinkler Plot Liters
             | Valve Bool Network      -- True means open
             | Split [Network]
```

All the liters are positive. A `Split []` is a dead end.

## Exercises

**Exercise 1)** Define these functions by **explicit recursion** on `Network`. Functions
from the `Prelude` and `Data.Maybe` may be used on lists.

a. ``flow :: Network -> Liters``, the liters per minute delivered by the sprinklers
   that get water.

b. ``wateredPlots :: Network -> [Plot]``, the plots of the sprinklers that get water,
   from left to right, repeated if a plot has several of them.

c. ``openAll :: Network -> Network``, the same network with every valve open.

d. ``valvesToOpen :: Plot -> Network -> Maybe Int``, the smallest number of closed
   valves that must be opened to water the plot, or `Nothing` if the plot has no
   sprinkler in the network.

e. ``prune :: Network -> Maybe Network``, the network without the parts water cannot
   reach: closed valves disappear along with everything behind them, and so do splits
   with no branch left. It is `Nothing` if nothing remains.

**HELP:** `Nothing < Just x` in the `Ord` instance of `Maybe`, so `minimum` does not
solve the `Split` case of `valvesToOpen`.

**Exercise 2)** Folding over `Network`.

a. Define the structural fold `foldNetwork` and write its type.

b. Redefine `flow`, `openAll`, `valvesToOpen` and `prune` using `foldNetwork`, with no
   explicit recursion on `Network`.

**Exercise 3)** Define ``flowByPlot :: Network -> [(Plot, Liters)]``, the liters per
minute each plot receives. Each plot that gets water appears once, in the order in
which it is first reached from left to right. For the garden above, the result is
`[("tomatoes", 7), ("herbs", 2)]`. The list of sprinklers that get water must be
obtained with `foldNetwork`, and it must be combined with `foldl` or `foldr`.
