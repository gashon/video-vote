import datetime
import os.path as osp
import sqlite3

SAVE_PATH = "eval"

from config import (
    NUM_COMBINATIONS,
    NUM_CRITERIA,
    NUM_EVALUATORS,
    NUM_PROMPTS,
    NUM_TURNS,
    TOTAL_EVALUATIONS,
)


def all_evaluations_assigned():
    """
    Check if all evaluations have been assigned to evaluators
    Returns:
        bool: True if all evaluations have been assigned, False otherwise
    """
    conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
    c = conn.cursor()
    try:
        # No existing in_progress evaluation for this user, so find a new one
        # Calculate timestamp for 30 minutes ago
        cutoff_time = datetime.datetime.now() - datetime.timedelta(minutes=30)
        cutoff_time_str = cutoff_time.strftime("%Y-%m-%d %H:%M:%S")

        # Find an available evaluation
        c.execute(
            """
            SELECT COUNT(*) FROM evaluation_pool
            WHERE 
                status = 'available' OR 
                (status = 'in_progress' AND assigned_at < ?)
            """,
            (cutoff_time_str,),
        )
        count = c.fetchone()[0]
        return count == 0
    finally:
        conn.close()


def get_sample_from_pool(user_id):
    """
    For a given user:
    1. First check if they already have an in_progress evaluation assigned to them
    2. If not, fetch a sample from the evaluation pool that:
       a. Has status='available' OR
       b. Has status='in_progress' but was assigned over 30 minutes ago
    3. Mark it as in_progress for the current user

    Args:
        user_id: The ID of the user requesting the evaluation

    Returns:
        tuple: (prompt_id, criteria_id, combo_id, turn_id) or None if no samples are available
    """
    conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    try:
        # First check if user already has an in_progress evaluation
        c.execute(
            """
            SELECT * FROM evaluation_pool
            WHERE 
                user_id = ? AND 
                status = 'in_progress'
            LIMIT 1
            """,
            (user_id,),
        )

        row = c.fetchone()

        if row:
            # User already has an in_progress evaluation
            evaluation = dict(row)

            return (
                evaluation["prompt_id"],
                evaluation["criteria_id"],
                evaluation["combo_id"],
                evaluation["turn_id"],
            )

        # No existing in_progress evaluation for this user, so find a new one
        # Calculate timestamp for 30 minutes ago
        cutoff_time = datetime.datetime.now() - datetime.timedelta(minutes=30)
        cutoff_time_str = cutoff_time.strftime("%Y-%m-%d %H:%M:%S")

        # Find an available evaluation
        c.execute(
            """
            SELECT * FROM evaluation_pool
            WHERE 
                status = 'available' OR 
                (status = 'in_progress' AND assigned_at < ?)
            ORDER BY RANDOM()
            LIMIT 1
            """,
            (cutoff_time_str,),
        )

        row = c.fetchone()

        if not row:
            conn.close()
            return None

        # Convert to dict
        evaluation = dict(row)

        # Mark as in_progress
        c.execute(
            """
            UPDATE evaluation_pool 
            SET 
                user_id = ?,
                status = 'in_progress', 
                assigned_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (user_id, evaluation["id"]),
        )

        conn.commit()
        return (
            evaluation["prompt_id"],
            evaluation["criteria_id"],
            evaluation["combo_id"],
            evaluation["turn_id"],
        )

    except Exception as e:
        conn.rollback()
        print(f"Error in get_sample_from_pool: {e}")
        return None

    finally:
        conn.close()
