import datetime
import os
import os.path as osp
import sqlite3
import time
from itertools import combinations

import streamlit as st

from config import MODEL_LIST, NUM_COMBINATIONS, NUM_CRITERIA, NUM_PROMPTS, NUM_TURNS
from pool_manager import get_db_lock

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
                current_index INTEGER, 
                left_model TEXT,
                right_model TEXT,
                rating INTEGER,
                review_duration INTEGER, 
                clicked_video_count INTEGER, 
                clicked_video_unrepeated_count INTEGER, 
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                deleted_at DATETIME DEFAULT NULL,
                FOREIGN KEY (evaluation_pool_id) REFERENCES evaluation_pool(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )"""
    )

    c.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_type INTEGER NOT NULL, -- 1 for criteria_id 1 and 2, 2 for criteria_id 0 and 3
            deleted_at DATETIME DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )"""
    )

    # NEW: Create model combinations table to map combo_id to actual models
    c.execute(
        """CREATE TABLE IF NOT EXISTS model_combinations (
            combo_id INTEGER PRIMARY KEY,
            left_model TEXT NOT NULL,
            right_model TEXT NOT NULL,
            UNIQUE(left_model, right_model)
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

    # Check if model combinations table needs to be populated
    c.execute("SELECT COUNT(*) FROM model_combinations")
    count = c.fetchone()[0]

    if count == 0:  # Only prefill if table is empty
        model_combos = []
        combos = list(combinations(MODEL_LIST, 2))
        for combo_id, (left_model, right_model) in enumerate(combos):
            model_combos.append((combo_id, left_model, right_model))

        # Insert all model combinations
        c.executemany(
            """INSERT INTO model_combinations 
               (combo_id, left_model, right_model) 
               VALUES (?, ?, ?)""",
            model_combos,
        )

    conn.commit()
    conn.close()


def save_response(
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

    with get_db_lock():
        conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
        c = conn.cursor()

        try:
            # Begin transaction
            conn.execute("BEGIN TRANSACTION")

            print(
                "SAVING RESPONSE",
                f"user_id={user_id}",
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
                    current_index, 
                    evaluation_pool_id,
                    left_model, 
                    right_model, 
                    rating, 
                    review_duration, 
                    clicked_video_count, 
                    clicked_video_unrepeated_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
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
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    cutoff_time = datetime.datetime.now() - datetime.timedelta(minutes=30)
    cutoff_time_str = cutoff_time.strftime("%Y-%m-%d %H:%M:%S")

    # Check if all evaluations for criteria 3 and 4 are completed
    c.execute(
        """
        SELECT COUNT(*) as remaining_count
        FROM evaluation_pool
        WHERE criteria_id IN (0, 3)
        AND status != 'completed' OR
        (status = 'in_progress' AND assigned_at < ?)
    """,
        (cutoff_time_str,),
    )

    result = c.fetchone()
    remaining_evals = result["remaining_count"]

    # Determine which assignment type to assign
    assignment_type = 2 if remaining_evals > 0 else 1

    # Insert new user with the determined assignment type
    c.execute(
        """
        INSERT INTO users (assignment_type) 
        VALUES (?)
    """,
        (assignment_type,),
    )

    # Retrieve the auto-generated user id
    new_user_id = c.lastrowid
    conn.commit()
    conn.close()

    return new_user_id


def fetch_all_responses():
    conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
    c = conn.cursor()
    c.execute("""SELECT * FROM evaluations ORDER BY evaluation_pool_id ASC""")
    rows = c.fetchall()
    column_names = [desc[0] for desc in c.description]

    conn.close()

    return rows, column_names


def get_user_eval_count(user_id):
    conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
    c = conn.cursor()
    c.execute(
        "SELECT COUNT(*) FROM evaluations WHERE user_id = ?",
        (user_id,),
    )
    count = c.fetchone()[0]
    conn.close()
    return count


# if __name__ == "__main__":
#     create_db()
#     print(f"fetching evaluations...")
#     evaluations = fetch_evaluations()
#     for evaluation in evaluations:
#         print(evaluation)
