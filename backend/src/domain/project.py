from math import isfinite

from .clustering import MixedData, fit
from .diagnostics import assess_members, warnings_for
from .fixtures import DATASET_NAME, demo_rows as demo_rows
from .reporting import report_tables
from .schema import FIELDS, normalize_rows as normalize_rows


SETTINGS = (
    ('groups', '候选组数', 4, 2, 8, 1),
    ('category_weight', '类别失配权重', 1.5, 0.1, 10.0, 0.1),
    ('starts', '确定性起点数', 8, 1, 12, 1),
    ('boundary_percent', '边界相对差距阈值（%）', 15, 0, 50, 1),
)
SPEC = {
    'columns': list(FIELDS),
    'fields': FIELDS.copy(),
    'settings': [dict(zip(('key', 'label', 'default', 'min', 'max', 'step'), setting))
                 for setting in SETTINGS],
    'modules': {'datasets': '植毛台账', 'runs': '换模分组运行', 'results': '换模交接单', 'reviews': '换模复核'},
    'limitation': '分组以当前台账的尺寸与类目为依据。共模要通过首件试装，组号仅在本次运行内使用。',
    'dataset_name': DATASET_NAME,
    'recommendation': '先按边界与类别核对清单复测或核对工单，再用每组代表刷束做首件试装。',
}


def parameters(settings):
    if settings.keys() - {key for key, *_ in SETTINGS}:
        raise ValueError('存在本项目未定义的运行参数')
    checked = {}
    for key, label, default, minimum, maximum, step in SETTINGS:
        value = settings.get(key, default)
        if type(value) not in (int, float) or not minimum <= value <= maximum or not isfinite(value):
            raise ValueError(f'{label}须在 {minimum:g}–{maximum:g} 之间')
        if step == 1 and value != int(value):
            raise ValueError(f'{label}须为整数')
        checked[key] = int(value) if step == 1 else float(value)
    return checked


def analyze(rows: list[dict], settings: dict) -> dict:
    rows = sorted(normalize_rows(rows), key=lambda row: row['id'])
    config = parameters(settings)
    k, weight = config['groups'], config['category_weight']
    data = MixedData.from_rows(rows)
    trial, trials = fit(data, k, weight, config['starts'])
    members = assess_members(data, trial, weight, config['boundary_percent'] / 100)
    review_count = sum(member.needs_review for member in members)
    return {
        'summary': (f'将 {len(rows)} 束刷束分成 {k} 个换模候选组，采用第 {trial.number} 个起点，'
                    f'总目标值 {trial.objective:.4f}（尺寸及根数 {trial.numeric:.4f}、'
                    f'类别失配 {trial.categorical:.4f}）。先处理 {review_count} 束待核记录，再做首件试装。'),
        'metrics': {'台账刷束数': len(rows), '换模候选组数': k, '总目标值': round(trial.objective, 8),
                    '待核刷束数': review_count, '已收敛起点数': sum(item.converged for item in trials)},
        'tables': report_tables(rows, members, trial, trials, weight),
        'warnings': warnings_for(data, trial, trials, members),
    }
