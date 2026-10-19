from core.cinematic_topic_common import board


def build_storyboard():
    return board(62, (
        ("index_shelves", "problem_ui", 0, 4, 0, 1, ("B-tree",), "push_in", {"role": "problem", "title": "B-tree как полки", "detail": "куда попадёт новый ключ?"}),
        ("v4_scatter", "index_tree", 4, 10, 1, 2, ("случайный",), "pan", {"role": "cause", "mode": "v4", "keys": ("a83f…", "19cd…", "f401…")}),
        ("v7_bits", "timeline", 10, 16, 2, 3, ("время",), "push_in", {"role": "mechanism", "events": ("timestamp 48 bit", "version 7", "random")}),
        ("v7_locality", "index_tree", 16, 21, 3, 4, ("рядом",), "pan", {"role": "result", "mode": "v7", "keys": ("019a…", "019b…", "019c…")}),
        ("node_api", "code_build", 21, 26, 4, 5, ("randomUUIDv7",), "push_in", {"role": "mechanism", "title": "Node.js 24.16", "lines": ("import { randomUUIDv7 }", "  from 'node:crypto';", "const id = randomUUIDv7();")}),
        ("use_cases", "before_after", 26, 31, 5, 6, ("порядком",), "pull_back", {"role": "result", "before": "UUIDv4: random", "after": "UUIDv7: time"}),
        ("not_sequence", "warning", 31, 36, 6, 7, ("не строгий",), "snap_focus", {"role": "limitation", "title": "Не sequence", "detail": "строгий порядок не гарантирован"}),
        ("timestamp_visible", "resolution", 36, 40, 7, 8, ("время",), "pull_back", {"role": "resolution", "title": "Выбирай осознанно", "detail": "UUID раскрывает время создания"}),
    ))
