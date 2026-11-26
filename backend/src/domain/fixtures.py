from random import Random


DATASET_NAME = '2026-11-25_LS植毛刷束实测.csv'


def demo_rows() -> list[dict]:
    rng = Random(261125)
    rows = []

    def add(length, diameter, count, material, process_use):
        rows.append({
            'id': f'LS-1125-{len(rows) + 1:03d}',
            'bristle_length_mm': round(length, 2),
            'bundle_diameter_mm': round(diameter, 2),
            'bristle_count': count,
            'material': material,
            'process_use': process_use,
        })

    recipes = (
        (18, 2.4, 82, '棕榈纤维', '细槽清扫'),
        (26, 3.3, 136, '棕榈纤维', '板面扫灰'),
        (27, 3.4, 142, '尼龙610', '边缘去屑'),
        (43, 5.6, 278, '剑麻纤维', '粗面刷洗'),
    )
    for length, diameter, count, material, process_use in recipes:
        for _ in range(24):
            add(length + rng.uniform(-2.4, 2.4), diameter + rng.uniform(-0.27, 0.27),
                count + rng.randint(-15, 15), material, process_use)

    for bridge in (
        (22.1, 2.83, 110, '棕榈纤维', '边缘去屑'),
        (25.4, 3.24, 133, '尼龙610', '板面扫灰'),
        (26.3, 3.31, 140, '棕榈纤维', '边缘去屑'),
        (27.2, 3.41, 145, '棕榈尼龙混纤', '边缘去屑'),
        (33.0, 4.2, 190, '剑麻纤维', '板面扫灰'),
        (36.0, 4.6, 210, '尼龙610', '粗面刷洗'),
        (34.5, 4.3, 201, '棕榈纤维', '粗面刷洗'),
        (25.4, 3.14, 128, '棕榈纤维', '细槽清扫'),
    ):
        add(*bridge)
    return rows
