from core.cinematic_topic_common import board


def build_storyboard():
    return board(61, (
        ("late_profile", "problem_ui", 0, 4, 0, 1, ("загружаться",), "snap_focus", {"role": "problem", "title": "Страница уже готова", "detail": "профиль только стартовал"}),
        ("effect_cause", "process_chain", 4, 9, 1, 2, ("useEffect",), "push_in", {"role": "cause", "title": "Запрос начинается поздно", "nodes": ("render", "useEffect", "fetch")}),
        ("waterfall", "process_chain", 9, 14, 2, 3, ("цепочкой",), "pan", {"role": "cause", "title": "Получается waterfall", "nodes": ("parent", "child", "fetch", "render")}),
        ("promise_first", "code_build", 14, 20, 3, 4, ("Promise",), "push_in", {"role": "mechanism", "title": "Promise создаётся заранее", "lines": ("const userPromise = getUser();", "<Profile data={userPromise} />", "const user = use(data);")}),
        ("suspense_flow", "data_flow", 20, 26, 4, 5, ("Suspense",), "pan", {"role": "mechanism", "title": "Ожидание контролирует Suspense", "nodes": ("Promise", "fallback", "Profile")}),
        ("single_flow", "before_after", 26, 31, 5, 6, ("поток",), "pull_back", {"role": "result", "before": "late fetch", "after": "Promise заранее"}),
        ("stable_promise", "warning", 31, 36, 6, 7, ("стабильным",), "snap_focus", {"role": "limitation", "title": "Не создавай заново", "detail": "Promise должен быть стабильным"}),
        ("error_boundary", "resolution", 36, 40, 7, 8, ("Error Boundary",), "pull_back", {"role": "resolution", "title": "Полная схема", "detail": "Suspense + Error Boundary"}),
    ))
