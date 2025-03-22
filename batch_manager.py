import numpy as np
import random

from config import (
    NUM_PROMPTS,
    NUM_CRITERIA,
    NUM_TURNS,
    NUM_COMBINATIONS,
    TOTAL_EVALUATIONS,
    NUM_EVALUATORS
)


def get_eval_batch_size():
    return TOTAL_EVALUATIONS // NUM_EVALUATORS


def create_batches():
    evals = []

    for prompt in range(NUM_PROMPTS):
        for criteria in range(NUM_CRITERIA):
            for turn in range(NUM_TURNS):  # use turn id for uniqueness in db
                for combo in range(NUM_COMBINATIONS):
                    curr_eval = (prompt, criteria, combo, turn)
                    evals.append(curr_eval)

    rng = random.Random(42)  # Guarantee same ordering every time
    rng.shuffle(evals)  # Need shuffle to prevent feeding evaluators same info every time

    if len(evals) % NUM_EVALUATORS != 0:
        raise ValueError("Num evals must be divisible by the num evaluators")

    batch_size = get_eval_batch_size()

    return [evals[i * batch_size : (i + 1) * batch_size] for i in range(NUM_EVALUATORS)]
