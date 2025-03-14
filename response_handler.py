import json
import os.path as osp
import sqlite3
import time
import streamlit as st
from batch_manager import NUM_BATCHES

SAVE_PATH = "eval"


def create_db():
    conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS evaluations
                (id INTEGER PRIMARY KEY, user_id INTEGER, batch_id INTEGER, current_index INTEGER, prompt_id INTEGER, criteria_id INTEGER, rating TEXT, review_duration INTEGER, clicked_video_count INTEGER, clicked_video_unrepeated_count INTEGER, timestamp TEXT)"""
    )
    conn.commit()
    conn.close()


def save_response(prompt_id, criteria_id, rating, batch_id, user_id, current_index, review_duration):
    conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
    c = conn.cursor()
    rating_json = json.dumps(rating)  # Convert the rating list to a JSON string
    print(
        "SAVING RESPONSE",
        user_id,
        batch_id,
        current_index,
        prompt_id,
        criteria_id,
        rating_json,
        review_duration,
        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
    )
    c.execute(
        "INSERT INTO evaluations (user_id, batch_id, current_index, prompt_id, criteria_id, rating, review_duration, clicked_video_count, clicked_video_unrepeated_count, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            user_id,
            batch_id,
            current_index,
            prompt_id,
            criteria_id,
            rating_json,
            review_duration,
            st.session_state.clicked_video_count,
            len(st.session_state.clicked_video_ids),
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        ),
    )
    c.execute
    conn.commit()
    conn.close()

def fetch_evaluations():
    conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
    c = conn.cursor()
    c.execute("SELECT * FROM evaluations")
    rows = c.fetchall()
    conn.close()
    return rows

def fetch_valid_user_responses(user_id):

    conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
    c = conn.cursor()
    c.execute("SELECT DISTINCT user_id, batch_id, current_index, prompt_id, criteria_id, rating, timestamp FROM evaluations WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    unique_pairs = set()
    evaluations = []

    rows = sorted(rows, key=lambda x: x[-1], reverse=True)
    for row in rows:
        user_id, batch_id, current_index, prompt_id, criteria_id, rating, timestamp = row
        if (current_index, prompt_id, criteria_id) not in unique_pairs:
            try:
                rating_list = json.loads(rating)
            except json.JSONDecodeError:
                continue
            if (
                isinstance(user_id, int) and
                isinstance(batch_id, int) and
                isinstance(current_index, int) and
                isinstance(prompt_id, int) and
                isinstance(criteria_id, int) and
                isinstance(rating_list, list) and
                len(rating_list) == 4 and
                set(rating_list) == {1, 2, 3, 4} and
                batch_id == user_id%NUM_BATCHES
            ):
                unique_pairs.add((current_index, prompt_id, criteria_id))
                evaluations.append([user_id, batch_id, current_index, prompt_id, criteria_id, rating_list, timestamp])
    conn.close()
    return set([pair[0] for pair in unique_pairs]), evaluations

def count_valid_user_responses(user_id):
    evaluated_indices, evaluations = fetch_valid_user_responses(user_id)
    if len(evaluated_indices) > 0:
        batch_id = evaluations[0][1]
        print(f"User {user_id} has evaluated {evaluated_indices} indices in batch {batch_id}")
    else:
        print(f"User {user_id} has not evaluated any indices yet")
    return evaluated_indices

if __name__ == "__main__":
    create_db()
    print(f"fetching evaluations...")
    evaluations = fetch_evaluations()
    for evaluation in evaluations:
        print(evaluation)
