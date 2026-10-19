from core.cinematic_topic_common import board


def build_storyboard():
    return board(64, (
        ("missing_globals", "problem_ui", 0, 6, 0, 1, ("process",), "snap_focus", {"role": "problem", "title": "После обновления", "detail": "process · describe · module?"}),
        ("not_random", "config_diff", 6, 10, 1, 2, ("не случайная",), "push_in", {"role": "cause", "before": "types: auto", "after": "types: []"}),
        ("types_default", "config_diff", 10, 17, 2, 3, ("types",), "pan", {"role": "cause", "before": "all @types", "after": "types: []"}),
        ("modern_defaults", "process_chain", 17, 24, 3, 4, ("strict",), "pan", {"role": "mechanism", "title": "Новые defaults", "nodes": ("strict", "esnext", "es2025", "rootDir")}),
        ("explicit_config", "config_diff", 24, 31, 4, 5, ("явно",), "push_in", {"role": "result", "before": "types: []", "after": 'types: ["node", "vitest/globals"]'}),
        ("keep_strict", "warning", 31, 35, 5, 6, ("strict",), "snap_focus", {"role": "limitation", "title": "Не скрывай проблему", "detail": "strict остаётся включён"}),
        ("migration_order", "resolution", 35, 40, 6, 7, ("TypeScript 7",), "pull_back", {"role": "resolution", "title": "Порядок миграции", "detail": "TS 6 diagnostics → TS 7"}),
    ))
