from core.cinematic_topic_common import board


def build_storyboard():
    return board(63, (
        ("double_click", "problem_ui", 0, 4, 0, 1, ("настройки",), "snap_focus", {"role": "problem", "title": "Два быстрых перехода", "detail": "profile → settings"}),
        ("stale_response", "browser_navigation", 4, 9, 1, 2, ("старый",), "pan", {"role": "cause", "url": "/settings", "states": ("profile fetch", "settings fetch", "старый render")}),
        ("manual_router", "process_chain", 9, 14, 2, 3, ("pushState",), "handheld", {"role": "cause", "title": "Роутер вручную", "nodes": ("pushState", "popstate", "cancel")}),
        ("navigate_event", "browser_navigation", 14, 18, 3, 4, ("navigate",), "push_in", {"role": "mechanism", "url": "/settings", "states": ("navigate event", "destination", "type")}),
        ("intercept", "code_build", 18, 23, 4, 5, ("event.signal",), "push_in", {"role": "mechanism", "title": "Один lifecycle", "lines": ("event.intercept({", "  async handler() {", "    fetch(url, { signal: event.signal })")}),
        ("abort_old", "browser_navigation", 23, 28, 5, 6, ("отменяется",), "snap_focus", {"role": "result", "url": "/settings", "states": ("profile: aborted", "settings: loading", "settings: rendered")}),
        ("navigation_type", "timeline", 28, 32, 6, 7, ("navigationType",), "pan", {"role": "mechanism", "events": ("push", "reload", "traverse")}),
        ("native_guard", "warning", 32, 36, 7, 8, ("не всё",), "snap_focus", {"role": "limitation", "title": "Оставь браузеру", "detail": "external · download · unsupported"}),
        ("fallback", "resolution", 36, 40, 8, 9, ("fallback",), "pull_back", {"role": "resolution", "title": "Современный lifecycle", "detail": "Navigation API + fallback"}),
    ))
