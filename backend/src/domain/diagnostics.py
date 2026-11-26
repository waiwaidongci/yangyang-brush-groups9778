from dataclasses import dataclass

from .clustering import group_members, mismatches, numeric_cost
from .schema import CATEGORIES, DIMENSIONS


@dataclass(frozen=True)
class Member:
    index: int
    group: int
    alternative: int
    numeric_cost: float
    mismatch_fields: tuple[str, ...]
    distance: float
    alternative_distance: float
    margin: float
    boundary: bool

    @property
    def needs_review(self):
        return self.boundary or bool(self.mismatch_fields)


def assess_members(data, trial, weight, margin_threshold):
    members = []
    for index, (point, group) in enumerate(zip(data.points, trial.labels)):
        numeric = [numeric_cost(point, center) for center in trial.centers]
        distances = [cost + weight * mismatches(point, center)
                     for cost, center in zip(numeric, trial.centers)]
        alternative = min((candidate for candidate in range(len(distances)) if candidate != group),
                          key=distances.__getitem__)
        assigned_dist, alternate_dist = distances[group], distances[alternative]
        denominator = max(assigned_dist, alternate_dist)
        margin = (alternate_dist - assigned_dist) / denominator if denominator else 0.0
        mismatch_fields = tuple(key for key, actual, expected in
                                zip(CATEGORIES, point.categorical, trial.centers[group].categorical)
                                if actual != expected)
        members.append(Member(index, group, alternative, numeric[group], mismatch_fields,
                              assigned_dist, alternate_dist, margin, margin <= margin_threshold))
    return members


def display_group_codes(rows, trial):
    groups = group_members(trial.labels, len(trial.centers))
    ordered = sorted(range(len(groups)), key=lambda group: rows[groups[group][0]]['id'])
    return {group: f'G{order:02d}' for order, group in enumerate(ordered, 1)}


def warnings_for(data, trial, trials, members):
    warnings = []
    constants = [DIMENSIONS[key][0] for key, scale in zip(DIMENSIONS, data.scale) if not scale]
    if constants:
        warnings.append('下列尺寸或根数列为常量，未贡献距离：' + '、'.join(constants) + '。')
    if not trial.converged:
        warnings.append('选中的起点未达到稳定分配，请核对备选组；可增加起点数或调整候选组数后重算。')
    if max(item.objective for item in trials) - trial.objective > 1e-8:
        warnings.append('不同起点产生了不同目标值，已采用最低目标值对应的分组。')
    sizes = group_members(trial.labels, len(trial.centers))
    if any(len(group) <= 2 for group in sizes):
        warnings.append('存在仅含 1–2 束的小组，请单独试装并核实是否需要独立备模。')
    if any(member.needs_review for member in members):
        warnings.append('先核对边界或类别失配刷束，再安排同组换模首件试装。')
    return warnings
