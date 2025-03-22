import json
import os
import os.path as osp
import sqlite3
import time
from config import get_combo, get_criteria_count, get_global_index, get_prompt_count, get_total_evaluations_count, get_turn_count
import streamlit as st
from batch_manager import get_eval_batch_size

SAVE_PATH = "eval"


def create_db():
    os.makedirs(SAVE_PATH, exist_ok=True)
    conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS evaluations
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                user_id INTEGER, 
                global_index INTEGER,
                current_index INTEGER, 
                prompt_id INTEGER, 
                criteria_id INTEGER,
                turn_id INTEGER,
                combo_id INTEGER,
                left_model TEXT,
                right_model TEXT,
                rating INTEGER,
                review_duration INTEGER, 
                clicked_video_count INTEGER, 
                clicked_video_unrepeated_count INTEGER, 
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, global_index)
            )"""
    )
    conn.commit()

    c.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    conn.commit()
    conn.close()


def save_response(
    global_index,
    current_index,
    prompt_id,
    criteria_id,
    turn_id,
    combo_id,
    left_model,
    right_model,
    rating,
    user_id,
    review_duration,
):
    clicked_video_count = st.session_state.clicked_video_count
    clicked_video_unrepeated_count = len(st.session_state.clicked_video_ids)
    
    conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
    c = conn.cursor()
    print(
        "SAVING RESPONSE",
        f"user_id={user_id}",
        f"global_index={global_index}",
        f"current_index={current_index}",
        f"prompt_id={prompt_id}",
        f"criteria_id={criteria_id}",
        f"turn_id={turn_id}",
        f"combo_id={combo_id}",
        f"left_model={left_model}",
        f"right_model={right_model}",
        f"rating={rating}",
        f"review_duration={review_duration}",
        f"clicked_video_count={clicked_video_count}",
        f"clicked_video_unrepeated_count={clicked_video_unrepeated_count}",
        f"time={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}",
        sep="\n"
    )
    c.execute(
        """
        INSERT INTO evaluations (
            user_id, 
            global_index, 
            current_index, 
            prompt_id, 
            criteria_id, 
            turn_id, 
            combo_id, 
            left_model, 
            right_model, 
            rating, 
            review_duration, 
            clicked_video_count, 
            clicked_video_unrepeated_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, global_index) DO UPDATE SET
            current_index = excluded.current_index,
            prompt_id = excluded.prompt_id,
            criteria_id = excluded.criteria_id,
            turn_id = excluded.turn_id,
            combo_id = excluded.combo_id,
            left_model = excluded.left_model,
            right_model = excluded.right_model,
            rating = excluded.rating,
            review_duration = excluded.review_duration,
            clicked_video_count = excluded.clicked_video_count,
            clicked_video_unrepeated_count = excluded.clicked_video_unrepeated_count
        """,
        (
            user_id,
            global_index,
            current_index,
            prompt_id,
            criteria_id,
            turn_id,
            combo_id,
            left_model,
            right_model,
            rating,
            review_duration,
            clicked_video_count,
            clicked_video_unrepeated_count,
        ),
    )
    conn.commit()
    conn.close()


def get_new_user_id():
    conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
    c = conn.cursor()
    c.execute("INSERT INTO users DEFAULT VALUES")

    # Retrieve the auto-generated user id
    new_user_id = c.lastrowid
    conn.commit()
    conn.close()

    return new_user_id - 1  # Minus 1 for indexing into batches


def fetch_all_responses():
    conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
    c = conn.cursor()
    c.execute("""SELECT * FROM evaluations ORDER BY prompt_id, criteria_id, combo_id, turn_id""")
    rows = c.fetchall()
    column_names = [desc[0] for desc in c.description]

    conn.close()

    return rows, column_names


def is_entry_valid(entry):
    user_id, global_index, current_index, prompt_id, criteria_id, turn_id, combo_id, left_model, right_model, rating = (
        entry
    )

    batch_size = get_eval_batch_size()

    # Check indexing
    if global_index != get_global_index(user_id, current_index):
        return False

    if global_index >= get_total_evaluations_count():
        return False

    if current_index >= batch_size:
        return False

    # Check Rating
    if rating < 0 or rating > 2:
        return False

    # Check combo
    curr_combo = get_combo(combo_id)
    if left_model not in curr_combo or right_model not in curr_combo:
        return False

    if turn_id < 0 or turn_id >= get_turn_count():  # Three turns
        return False

    if criteria_id < 0 or criteria_id >= get_criteria_count():
        return False

    if prompt_id < 0 or prompt_id >= get_prompt_count():
        return False

    return True


def get_valid_user_response_indices(user_id):
    conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
    c = conn.cursor()
    c.execute(
        "SELECT DISTINCT user_id, global_index, current_index, prompt_id, criteria_id, turn_id, combo_id, left_model, right_model, rating FROM evaluations WHERE user_id = ?",
        (user_id,),
    )
    rows = c.fetchall()
    visited_indices = set()
    entries = []

    rows = sorted(rows, key=lambda x: x[-1], reverse=True)
    for row in rows:
        curr_user_id, current_index = row[0], row[2]
        assert current_index <= get_eval_batch_size()
        assert curr_user_id == user_id, "DB returned user_id not associated with user."

        if is_entry_valid(row):
            visited_indices.add(current_index)
            entries.append(row)

    conn.close()
    return visited_indices, entries


# if __name__ == "__main__":
#     create_db()
#     print(f"fetching evaluations...")
#     evaluations = fetch_evaluations()
#     for evaluation in evaluations:
#         print(evaluation)
