from collections import Counter
from dataclasses import dataclass
from math import fsum, sqrt
from random import Random
from statistics import fmean

from .schema import CATEGORIES, DIMENSIONS


START_SEED = 261125
MAX_ITERATIONS = 60


@dataclass(frozen=True)
class Prototype:
    numeric: tuple[float, ...]
    categorical: tuple[str, ...]


@dataclass(frozen=True)
class MixedData:
    points: list[Prototype]
    scale: tuple[float, ...]

    @classmethod
    def from_rows(cls, rows):
        columns = [[row[key] for row in rows] for key in DIMENSIONS]
        means = [fmean(column) for column in columns]
        scales = tuple(sqrt(fmean((value - mean) ** 2 for value in column))
                       if min(column) != max(column) else 0.0
                       for column, mean in zip(columns, means))
        points = [Prototype(
            tuple((row[key] - mean) / scale if scale else 0.0
                  for key, mean, scale in zip(DIMENSIONS, means, scales)),
            tuple(row[key] for key in CATEGORIES),
        ) for row in rows]
        return cls(points, scales)


def numeric_cost(point, prototype):
    length, diameter, count = point.numeric
    other_length, other_diameter, other_count = prototype.numeric
    return (length - other_length) ** 2 + (diameter - other_diameter) ** 2 + (count - other_count) ** 2


def mismatches(point, prototype):
    material, use = point.categorical
    other_material, other_use = prototype.categorical
    return int(material != other_material) + int(use != other_use)


def distance(point, prototype, weight):
    return numeric_cost(point, prototype) + weight * mismatches(point, prototype)


def starting_centers(points, k, weight, seed):
    rng = Random(seed)
    centers = [points[rng.randrange(len(points))]]
    candidates = [distance(point, centers[0], weight) for point in points]
    while len(centers) < k:
        picked = points[rng.choices(range(len(points)), weights=candidates)[0]]
        centers.append(picked)
        if len(centers) < k:
            candidates = [min(best, distance(point, picked, weight))
                          for best, point in zip(candidates, points)]
    return centers


def assign(points, centers, weight, previous):
    labels, costs = [], []
    groups = range(len(centers))
    for point, prior in zip(points, previous):
        distances = [distance(point, center, weight) for center in centers]
        label = min(groups, key=distances.__getitem__)
        if prior >= 0 and distances[prior] == distances[label]:
            label = prior
        labels.append(label)
        costs.append(distances[label])
    return labels, costs


def fill_empty_groups(labels, costs, k):
    counts = Counter(labels)
    empty = [group for group in range(k) if not counts[group]]
    if not empty:
        return
    # A moved member initially represents the new group by itself at zero cost.
    ordered = sorted(range(len(labels)), key=lambda index: (-costs[index], index))
    donors = iter(ordered)
    for group in empty:
        index = next(index for index in donors if counts[labels[index]] > 1)
        counts[labels[index]] -= 1
        labels[index] = group
        counts[group] = 1


def mode(values):
    counts = Counter(values)
    return min(counts, key=lambda value: (-counts[value], value))


def group_members(labels, k):
    groups = [[] for _ in range(k)]
    for index, label in enumerate(labels):
        groups[label].append(index)
    return groups


def update_centers(points, labels, k):
    centers = []
    for indices in group_members(labels, k):
        members = [points[index] for index in indices]
        centers.append(Prototype(
            tuple(map(fmean, zip(*(point.numeric for point in members)))),
            tuple(map(mode, zip(*(point.categorical for point in members)))),
        ))
    return centers


@dataclass(frozen=True)
class Trial:
    number: int
    seed: int
    centers: list[Prototype]
    labels: list[int]
    iterations: int
    converged: bool
    numeric: float
    categorical: float

    @property
    def objective(self):
        return self.numeric + self.categorical


def fit_start(points, k, weight, number):
    seed = START_SEED + number - 1
    centers = starting_centers(points, k, weight, seed)
    previous = [-1] * len(points)
    converged = False
    for iteration in range(1, MAX_ITERATIONS + 1):
        labels, costs = assign(points, centers, weight, previous)
        if labels == previous:
            converged = True
            break
        fill_empty_groups(labels, costs, k)
        if labels == previous:
            # A repair can restore the old partition even when a point prefers another group.
            break
        centers = update_centers(points, labels, k)
        previous = labels
    numeric = fsum(numeric_cost(point, centers[label]) for point, label in zip(points, labels))
    categorical = weight * sum(mismatches(point, centers[label]) for point, label in zip(points, labels))
    return Trial(number, seed, centers, labels, iteration, converged, numeric, categorical)


def fit(data, k, weight, n_starts):
    if k > len(set(data.points)):
        raise ValueError('候选组数超过不同刷束规格组合数，请调低组数或补充台账')
    trials = [fit_start(data.points, k, weight, number) for number in range(1, n_starts + 1)]
    best = min(trials, key=lambda trial: (trial.objective, not trial.converged, trial.number))
    return best, trials
