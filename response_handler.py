import json
import os
import os.path as osp
import sqlite3
import time

import streamlit as st

from batch_manager import get_eval_batch_size
from config import (
    NUM_COMBINATIONS,
    NUM_CRITERIA,
    NUM_EVALUATORS,
    NUM_PROMPTS,
    NUM_TURNS,
    TOTAL_EVALUATIONS,
    get_combo,
    get_criteria_count,
    get_global_index,
    get_prompt_count,
    get_total_evaluations_count,
    get_turn_count,
)

SAVE_PATH = "eval"


def create_db():
    os.makedirs(SAVE_PATH, exist_ok=True)
    conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
    c = conn.cursor()

    # Pre-filled evaluation pool table with status tracking
    c.execute(
        """CREATE TABLE IF NOT EXISTS evaluation_pool
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_id INTEGER, 
                criteria_id INTEGER,
                turn_id INTEGER,
                combo_id INTEGER,
                user_id INTEGER,
                status TEXT DEFAULT 'available',
                assigned_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(prompt_id, criteria_id, turn_id, combo_id)
            )"""
    )

    # Completed evaluations table (with user feedback)
    c.execute(
        """CREATE TABLE IF NOT EXISTS evaluations
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                evaluation_pool_id INTEGER,
                user_id INTEGER, 
                global_index INTEGER,
                current_index INTEGER, 
                left_model TEXT,
                right_model TEXT,
                rating INTEGER,
                review_duration INTEGER, 
                clicked_video_count INTEGER, 
                clicked_video_unrepeated_count INTEGER, 
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (evaluation_pool_id) REFERENCES evaluation_pool(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, global_index)
            )"""
    )

    c.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )"""
    )

    # Prefill the evaluation_pool table
    c.execute("SELECT COUNT(*) FROM evaluation_pool")
    count = c.fetchone()[0]

    if count == 0:  # Only prefill if table is empty
        evals = []
        for prompt in range(NUM_PROMPTS):
            for criteria in range(NUM_CRITERIA):
                for turn in range(NUM_TURNS):  # use turn id for uniqueness in db
                    for combo in range(NUM_COMBINATIONS):
                        evals.append((prompt, criteria, turn, combo))

        # Insert all evaluation combinations
        c.executemany(
            """INSERT INTO evaluation_pool 
               (prompt_id, criteria_id, turn_id, combo_id) 
               VALUES (?, ?, ?, ?)""",
            evals,
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

    try:
        # Begin transaction
        conn.execute("BEGIN TRANSACTION")

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
            sep="\n",
        )

        # First, find the evaluation_pool ID that matches our criteria
        c.execute(
            """
            SELECT id FROM evaluation_pool
            WHERE prompt_id = ? AND criteria_id = ? AND turn_id = ? AND combo_id = ?
            """,
            (prompt_id, criteria_id, turn_id, combo_id),
        )

        pool_id_row = c.fetchone()
        if not pool_id_row:
            print(
                f"Warning: Could not find matching evaluation_pool entry for prompt_id={prompt_id}, criteria_id={criteria_id}, turn_id={turn_id}, combo_id={combo_id}"
            )
            pool_id = None
        else:
            pool_id = pool_id_row[0]

            # Update the status in evaluation_pool to completed
            c.execute(
                """
                UPDATE evaluation_pool
                SET status = 'completed'
                WHERE id = ?
                """,
                (pool_id,),
            )

        # Insert or update the evaluation record
        c.execute(
            """
            INSERT INTO evaluations (
                user_id, 
                global_index, 
                current_index, 
                evaluation_pool_id,
                left_model, 
                right_model, 
                rating, 
                review_duration, 
                clicked_video_count, 
                clicked_video_unrepeated_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, global_index) DO UPDATE SET
                current_index = excluded.current_index,
                evaluation_pool_id = excluded.evaluation_pool_id,
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
                pool_id,
                left_model,
                right_model,
                rating,
                review_duration,
                clicked_video_count,
                clicked_video_unrepeated_count,
            ),
        )

        # Commit transaction
        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"Error in save_response: {e}")

    finally:
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
    c.execute(
        """SELECT * FROM evaluations ORDER BY prompt_id, criteria_id, combo_id, turn_id"""
    )
    rows = c.fetchall()
    column_names = [desc[0] for desc in c.description]

    conn.close()

    return rows, column_names


def is_entry_valid(entry):
    (
        user_id,
        global_index,
        current_index,
        eval_pool_id,
        left_model,
        right_model,
        rating,
    ) = entry

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

    return True


def get_valid_user_response_indices(user_id):
    conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
    c = conn.cursor()
    c.execute(
        "SELECT DISTINCT user_id, global_index, current_index, evaluation_pool_id, left_model, right_model, rating FROM evaluations WHERE user_id = ?",
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
