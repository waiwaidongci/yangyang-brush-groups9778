import math
import unicodedata


DIMENSIONS = {
    'bristle_length_mm': ('露毛长度（mm）', 2.0, 120.0),
    'bundle_diameter_mm': ('束径（mm）', 0.5, 20.0),
    'bristle_count': ('单束根数', 5, 2000),
}
CATEGORIES = {'material': '毛料', 'process_use': '工艺用途'}
FIELDS = {'id': '刷束编号', **{key: spec[0] for key, spec in DIMENSIONS.items()}, **CATEGORIES}
MIN_ROWS = 6
MAX_ROWS = 5000


def text_cell(value, limit):
    if not isinstance(value, str) or any(unicodedata.category(char)[0] == 'C' for char in value):
        raise ValueError('请输入文本且不得含控制字符')
    value = unicodedata.normalize('NFC', value).strip()
    if not value or len(value) > limit:
        raise ValueError(f'需填写 1–{limit} 个字符')
    return value


def number_cell(value, minimum, maximum):
    if type(value) not in (int, float, str):
        raise ValueError('请输入数值')
    try:
        number = float(value)
    except (ValueError, OverflowError):
        raise ValueError('请输入数值') from None
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError(f'请输入 {minimum:g}–{maximum:g} 之间的有限数值')
    if isinstance(minimum, int):
        if not number.is_integer():
            raise ValueError('根数必须是整数')
        return int(number)
    return number


def normalize_rows(rows: list[dict]) -> list[dict]:
    if not MIN_ROWS <= len(rows) <= MAX_ROWS:
        raise ValueError(f'刷束台账须有 {MIN_ROWS}–{MAX_ROWS} 条记录')
    normalized = []
    seen = set()
    for line, raw in enumerate(rows, start=2):
        if not isinstance(raw, dict) or raw.keys() != FIELDS.keys():
            raise ValueError(f'第 {line} 行须包含这些字段：' + '、'.join(FIELDS))
        row = {}
        for key, label in FIELDS.items():
            try:
                if key in DIMENSIONS:
                    _, minimum, maximum = DIMENSIONS[key]
                    row[key] = number_cell(raw[key], minimum, maximum)
                else:
                    row[key] = text_cell(raw[key], 64 if key == 'id' else 40)
            except ValueError as error:
                raise ValueError(f'第 {line} 行{label}：{error}') from None
        if row['id'] in seen:
            raise ValueError(f"第 {line} 行刷束编号重复：{row['id']}")
        seen.add(row['id'])
        normalized.append(row)
    return normalized
