from math import fsum
from statistics import fmean

from .clustering import group_members
from .diagnostics import display_group_codes
from .schema import CATEGORIES, DIMENSIONS, FIELDS


GROUP_FIELDS = {
    'group': '候选组', 'count': '刷束数', 'representative_id': '首件试装编号',
    'length_profile': '露毛长度均值［实测范围］mm', 'diameter_profile': '束径均值［实测范围］mm',
    'count_profile': '根数均值［实测范围］', 'material_mode': '主要毛料 / 占比',
    'use_mode': '主要用途 / 占比', 'numeric_cost': '尺寸及根数成本',
    'categorical_cost': '类别加权成本', 'objective': '组内目标值',
    'review_count': '待核刷束数', 'action': '换模交接动作',
}
MEMBER_FIELDS = {
    'id': FIELDS['id'], 'group': '分配组', 'alternative_group': '最近备选组',
    **{key: label for key, label in FIELDS.items() if key != 'id'},
    'distance': '到分配组距离', 'alternative_distance': '到备选组距离',
    'margin_percent': '备选相对差距（%）', 'numeric_cost': '尺寸及根数成本',
    'categorical_cost': '类别加权成本', 'mismatch_fields': '与组众数不同的字段',
    'status': '核对状态', 'action': '交接动作',
}
START_FIELDS = {
    'start': '起点序号', 'seed': '随机种子', 'iterations': '分配轮次', 'status': '收敛状态',
    'numeric_cost': '尺寸及根数成本', 'categorical_cost': '类别加权成本',
    'objective': '总目标值', 'selected': '采纳',
}


def table(key, title, labels, rows):
    return {'key': key, 'title': title, 'columns': list(labels), 'labels': labels.copy(), 'rows': rows}


def profile(rows, key):
    values = [row[key] for row in rows]
    return f'{fmean(values):.3f}［{min(values):g}–{max(values):g}］'


def member_export(row, member, codes, weight):
    if member.boundary and member.mismatch_fields:
        status = '边界且类别不同'
        action = '核实毛料与用途，复测露毛长度和束径，再对照备选组试装。'
    elif member.boundary:
        status = '边界'
        action = '复测露毛长度和束径、复点根数，再对照备选组试装。'
    elif member.mismatch_fields:
        status = '类别不同'
        action = '核对来料标签和工单，按毛料或用途隔开放置，确认后试装。'
    else:
        status = '组内候选'
        action = '按本组首件试装结果排入换模顺序。'
    return {
        **row, 'group': codes[member.group], 'alternative_group': codes[member.alternative],
        'distance': round(member.distance, 8),
        'alternative_distance': round(member.alternative_distance, 8),
        'margin_percent': round(member.margin * 100, 6),
        'numeric_cost': round(member.numeric_cost, 8),
        'categorical_cost': round(weight * len(member.mismatch_fields), 8),
        'mismatch_fields': '、'.join(CATEGORIES[key] for key in member.mismatch_fields) or '无',
        'status': status, 'action': action,
    }


def group_export(rows, members, trial, codes, weight):
    indices_by_group = group_members(trial.labels, len(trial.centers))
    records = []
    for group, code in codes.items():
        indices = indices_by_group[group]
        originals = [rows[index] for index in indices]
        details = [members[index] for index in indices]
        representative = min(details, key=lambda item: (item.distance, rows[item.index]['id']))
        representative_id = rows[representative.index]['id']
        numeric = fsum(item.numeric_cost for item in details)
        categorical = weight * sum(len(item.mismatch_fields) for item in details)
        review_count = sum(item.needs_review for item in details)
        material, use = trial.centers[group].categorical
        material_share = sum(row['material'] == material for row in originals) / len(originals)
        use_share = sum(row['process_use'] == use for row in originals) / len(originals)
        if len(indices) <= 2:
            action = f'单独试装 {representative_id}，确认是否需要独立备模。'
            if review_count:
                action = f'先核对本组 {review_count} 束待核记录。' + action
        elif review_count:
            action = f'先核对本组 {review_count} 束待核记录，再用 {representative_id} 做首件试装。'
        else:
            action = f'用 {representative_id} 做首件试装，验过后集中换模。'
        records.append({
            'group': code, 'count': len(indices), 'representative_id': representative_id,
            'length_profile': profile(originals, 'bristle_length_mm'),
            'diameter_profile': profile(originals, 'bundle_diameter_mm'),
            'count_profile': profile(originals, 'bristle_count'),
            'material_mode': f'{material} / {material_share:.1%}',
            'use_mode': f'{use} / {use_share:.1%}',
            'numeric_cost': round(numeric, 8), 'categorical_cost': round(categorical, 8),
            'objective': round(numeric + categorical, 8), 'review_count': review_count,
            'action': action,
        })
    return records


def report_tables(rows, members, trial, trials, weight):
    codes = display_group_codes(rows, trial)
    review_order = sorted(members, key=lambda item: (not item.boundary, not item.needs_review,
                                                     item.margin, rows[item.index]['id']))
    review_rows = [member_export(rows[item.index], item, codes, weight)
                   for item in review_order if item.needs_review]
    all_rows = [member_export(rows[item.index], item, codes, weight)
                for item in sorted(members, key=lambda item: (codes[item.group], rows[item.index]['id']))]
    trial_rows = [{
        'start': item.number, 'seed': item.seed, 'iterations': item.iterations,
        'status': '已收敛' if item.converged else '未收敛',
        'numeric_cost': round(item.numeric, 8), 'categorical_cost': round(item.categorical, 8),
        'objective': round(item.objective, 8), 'selected': '是' if item.number == trial.number else '否',
    } for item in trials]
    return [
        table('groups', '换模候选与首件试装', GROUP_FIELDS, group_export(rows, members, trial, codes, weight)),
        table('boundary_review', '边界与类别核对清单', MEMBER_FIELDS, review_rows),
        table('members', '全量刷束分组', MEMBER_FIELDS, all_rows),
        table('starts', '多起点目标值核对', START_FIELDS, trial_rows),
    ]
