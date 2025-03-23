from itertools import combinations

VIDEO_LENGTH = 18
VIDEO_ROOT = f"video/{VIDEO_LENGTH}sec"

NUM_PROMPTS = 100
NUM_CRITERIA = 5
NUM_TURNS = 3
NUM_COMBINATIONS = 15
TOTAL_EVALUATIONS = NUM_PROMPTS * NUM_CRITERIA * NUM_COMBINATIONS * NUM_TURNS  # 22500
NUM_EVALUATORS = 150

MIN_REVIEW_DURATION_IN_SEC = 18

DEBUG_MODE = False


MODEL_LIST = [
    "attention",
    "deltanet",
    "mamba",
    "sliding-window",
    "ttt-linear",
    "ttt-mlp",
]
CRITERIA = {
    0: [
        "Text Following",
        "How close does the video follow the text prompt, including the key elements and actions?",
        "If the prompt says Tom should be in the kitchen but the video shows him somewhere else, like the living room, this means the video doesn't follow the text.",
    ],
    1: [
        "Motion Smoothness",
        "Does the motion of characters look smooth and consistent throughout the video? It checks that movements are clear, fluid, and don't have strange jumps or visual glitches.",
        "If Jerry suddenly appears somewhere else, moves in jerky steps, or his shape distorts randomly, this shows poor motion smoothness.",
    ],
    2: [
        "Aesthetics",
        "How pleasing does the video look? It checks the quality of colors, lighting, camera angles, and how everything fits together visually.",
        "If the colors clash, lighting changes abruptly, or scenes look messy and unattractive, the video has poor visual appeal.",
    ],
    3: [
        "Scene Consistency",
        "Do characters and settings stay the same across scenes? It checks if characters, objects, and locations remain consistent, even if there's a gap between scenes.",
        "If Jerry has a red scarf in one scene but suddenly doesn't have it in the next scene without explanation, the video has poor scene consistency.",
    ],
    4: [
        "Character Emotions",
        "Does the video clearly show the emotions of characters through their facial expressions and body language? It checks if characters display feelings that match the described actions or situations.",
        "If Jerry is supposed to look scared but instead seems calm or happy, that's a violation.",
    ],
}


def get_eval_batch_size():
    return TOTAL_EVALUATIONS // NUM_EVALUATORS


def get_eval_batch_count():
    return NUM_EVALUATORS


def get_criteria(criteria_id):
    return CRITERIA[criteria_id]


def get_model(model_id):
    return MODEL_LIST[model_id]


def get_turn_count():
    return NUM_TURNS


def get_criteria_count():
    return NUM_CRITERIA


def get_prompt_count():
    return NUM_PROMPTS


def get_total_evaluations_count():
    return TOTAL_EVALUATIONS


def get_combo(combo_id):
    combos = list(combinations(MODEL_LIST, 2))
    if combo_id < 0 or combo_id >= len(combos):
        raise ValueError(f"combo_id must be between 0 and {len(combos) - 1}")
    model_left, model_right = combos[combo_id]
    return model_left, model_right
