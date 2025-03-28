from itertools import combinations

VIDEO_LENGTH = 63
VIDEO_ROOT = f"video/{VIDEO_LENGTH}sec"

NUM_PROMPTS = 100
NUM_CRITERIA = 1
NUM_TURNS = 1
NUM_COMBINATIONS = 3
TOTAL_EVALUATIONS = NUM_PROMPTS * NUM_CRITERIA * NUM_COMBINATIONS * NUM_TURNS  # 22500
NUM_EVALUATORS = 12

MIN_REVIEW_DURATION_IN_SEC = VIDEO_LENGTH

DEBUG_MODE = False

MODEL_LIST = [
    "deltanet",
    "mamba",
    "sliding-window",
    "ttt-mlp",
]

CRITERIA = {
    0: [
        "Overall Quality",
        "Which video is better",
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
    """
    Returns a tuple of (ttt-mlp, other_model) for the given combo_id.
    combo_id 0: ttt-mlp vs deltanet
    combo_id 1: ttt-mlp vs mamba
    combo_id 2: ttt-mlp vs sliding-window
    """
    if combo_id < 0 or combo_id >= NUM_COMBINATIONS:
        raise ValueError(f"combo_id must be between 0 and {NUM_COMBINATIONS - 1}")

    # Always have ttt-mlp as the left model
    model_left = "ttt-mlp"

    # The right model is one of the other three
    other_models = [model for model in MODEL_LIST if model != "ttt-mlp"]
    model_right = other_models[combo_id]

    return model_left, model_right
