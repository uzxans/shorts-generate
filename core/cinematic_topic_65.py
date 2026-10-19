from core.cinematic_topic_common import board


def build_storyboard():
    return board(65, (
        ("dialog_snap", "problem_ui", 0, 5, 0, 1, ("мгновенно",), "snap_focus", {"role": "problem", "title": "dialog[open]", "detail": "появился без transition"}),
        ("missing_start", "css_state_transition", 5, 10, 1, 2, ("начального",), "push_in", {"role": "cause", "from": "нет computed style", "to": "opacity: 1"}),
        ("starting_style", "code_build", 10, 16, 2, 3, ("@starting-style",), "push_in", {"role": "mechanism", "title": "Точка старта", "lines": ("@starting-style {", "  dialog[open] { opacity: 0;", "    transform: scale(.96); }")}),
        ("transition", "css_state_transition", 16, 21, 3, 4, ("соединяет",), "pan", {"role": "mechanism", "from": "opacity: 0 · scale .96", "to": "opacity: 1 · scale 1"}),
        ("allow_discrete", "code_build", 21, 26, 4, 5, ("allow-discrete",), "push_in", {"role": "mechanism", "title": "Для display", "lines": ("transition:", "  opacity .25s,", "  display .25s allow-discrete;")}),
        ("smooth_result", "before_after", 26, 31, 5, 6, ("без таймера",), "pull_back", {"role": "result", "before": "резко", "after": "плавный вход"}),
        ("reduced_motion", "warning", 31, 36, 6, 7, ("reduced-motion",), "snap_focus", {"role": "limitation", "title": "Уважай настройку", "detail": "prefers-reduced-motion: reduce"}),
        ("useful_motion", "resolution", 36, 40, 7, 8, ("объяснять",), "pull_back", {"role": "resolution", "title": "Движение со смыслом", "detail": "показывает изменение состояния"}),
    ))
