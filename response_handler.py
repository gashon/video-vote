import json
import os.path as osp
import sqlite3
import time

import streamlit as st

from video_display import MODEL_LIST

SAVE_PATH = "eval"


def create_db():
    conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS evaluations
                (id INTEGER PRIMARY KEY, prompt_id INTEGER, criteria_id INTEGER, rating TEXT, user_id INTEGER, batch_id INTEGER, review_duration INTEGER, clicked_video_count INTEGER, clicked_video_unrepeated_count INTEGER, timestamp TEXT)"""
    )
    conn.commit()
    conn.close()


def save_response(prompt_id, criteria_id, rating, batch_id, user_id, review_duration):

    conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
    c = conn.cursor()
    rating_json = json.dumps(rating)  # Convert the rating list to a JSON string
    print(
        "SAVING RESPONSE",
        prompt_id,
        criteria_id,
        rating_json,
        user_id,
        review_duration,
        SAVE_PATH,
    )
    c.execute(
        "INSERT INTO evaluations (prompt_id, criteria_id, rating, user_id, review_duration, clicked_video_count, clicked_video_unrepeated_count, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            prompt_id,
            criteria_id,
            rating_json,
            user_id,
            review_duration,
            st.session_state.clicked_video_count,
            len(st.session_state.clicked_video_ids),
            time.time(),
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


if __name__ == "__main__":
    create_db()
    print(f"fetching evaluations...")
    evaluations = fetch_evaluations()
    for evaluation in evaluations:
        print(evaluation)
