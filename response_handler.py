import json
import os.path as osp
import sqlite3

import streamlit as st

from video_display import MODEL_LIST

SAVE_PATH = "eval"


def create_db():
    conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS evaluations")
    c.execute(
        """CREATE TABLE evaluations
                 (id INTEGER PRIMARY KEY, prompt_id INTEGER, criteria_id INTEGER, rating TEXT)"""
    )
    conn.commit()
    conn.close()


def save_response(prompt_id, criteria_id, rating, batch_id):

    for i, model in enumerate(MODEL_LIST):
        st.session_state.scores[criteria_id][model] += rating[i]
    st.session_state.scores["evaluated_prompts"].append(prompt_id)
    with open(osp.join(SAVE_PATH, f"{batch_id}.json"), "w") as f:
        json.dump(st.session_state.scores, f)

    conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
    c = conn.cursor()
    rating_json = json.dumps(rating)  # Convert the rating list to a JSON string
    c.execute(
        "INSERT INTO evaluations (prompt_id, criteria_id, rating) VALUES (?, ?, ?)",
        (prompt_id, criteria_id, rating_json),
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

