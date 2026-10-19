from __future__ import annotations

from core.cinematic_storyboard import CinematicStoryboard, topic_60_storyboard
from core.cinematic_topic_61 import build_storyboard as topic_61_storyboard
from core.cinematic_topic_62 import build_storyboard as topic_62_storyboard
from core.cinematic_topic_63 import build_storyboard as topic_63_storyboard
from core.cinematic_topic_64 import build_storyboard as topic_64_storyboard
from core.cinematic_topic_65 import build_storyboard as topic_65_storyboard


SUPPORTED_TOPIC_IDS = (60, 61, 62, 63, 64, 65)
BUILDERS = {
    60: topic_60_storyboard,
    61: topic_61_storyboard,
    62: topic_62_storyboard,
    63: topic_63_storyboard,
    64: topic_64_storyboard,
    65: topic_65_storyboard,
}
REGISTERED_SCENE_KINDS = frozenset(
    {
        "conflict",
        "chaos",
        "terminal_command",
        "split_worktrees",
        "shared_history",
        "branch_warning",
        "cleanup_cta",
        "problem_ui",
        "process_chain",
        "code_build",
        "before_after",
        "data_flow",
        "timeline",
        "index_tree",
        "browser_navigation",
        "config_diff",
        "css_state_transition",
        "warning",
        "resolution",
    }
)


def supported_topic_ids() -> tuple[int, ...]:
    return SUPPORTED_TOPIC_IDS


def get_storyboard(topic_id: int) -> CinematicStoryboard:
    if topic_id not in SUPPORTED_TOPIC_IDS:
        raise ValueError(f"unsupported cinematic topic: {topic_id}")
    board = BUILDERS[topic_id]()
    validate_storyboard(board)
    return board


def validate_storyboard(board: CinematicStoryboard) -> None:
    if not board.shots:
        raise ValueError("storyboard must contain at least one shot")
    if board.shots[0].start != 0.0:
        raise ValueError("storyboard must start at 0.0")
    for index, shot in enumerate(board.shots):
        if shot.end <= shot.start:
            raise ValueError(f"shot {shot.id} has non-positive duration")
        if shot.narration_end <= shot.narration_start:
            raise ValueError(f"shot {shot.id} has empty narration range")
        if shot.kind not in REGISTERED_SCENE_KINDS:
            raise ValueError(f"unknown scene kind: {shot.kind}")
        if index and board.shots[index - 1].end != shot.start:
            raise ValueError(f"gap or overlap before shot {shot.id}")
