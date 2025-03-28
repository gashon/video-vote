import datetime
import os.path as osp
import sqlite3
from threading import Lock

_db_lock = Lock()

SAVE_PATH = "eval"


def get_db_lock():
    return _db_lock


def get_sample_from_pool(user_id):
    """
    For a given user:
    1. First check if they already have an in_progress evaluation assigned to them
    2. If not, fetch a sample from the evaluation pool that:
       a. Has status='available' OR
       b. Has status='in_progress' but was assigned over 30 minutes ago
    3. Mark it as in_progress for the current user
    4. Only fetch samples that match the user's assignment_type criteria
    5. Preference samples with models the user hasn't seen before

    Args:
        user_id: The ID of the user requesting the evaluation

    Returns:
        tuple: (prompt_id, criteria_id, combo_id, turn_id) or None if no samples are available
    """
    # Acquire lock to prevent race conditions
    with _db_lock:
        conn = sqlite3.connect(
            osp.join(SAVE_PATH, "evaluations.db"), check_same_thread=True
        )
        conn.row_factory = sqlite3.Row

        c = conn.cursor()

        try:
            # Get user's assignment type
            c.execute(
                """
                SELECT assignment_type FROM users
                WHERE id = ?
                """,
                (user_id,),
            )
            user_assignment = c.fetchone()

            if not user_assignment:
                return None  # User not found

            assignment_type = user_assignment["assignment_type"]

            # Define criteria IDs based on assignment type
            criteria_ids = []
            if assignment_type == 1:
                criteria_ids = [1, 2]  # First assignment: criteria_id 1 and 2
            elif assignment_type == 2:
                criteria_ids = [0, 3]  # Second assignment: criteria_id 0 and 3

            criteria_ids_placeholders = ",".join(["?" for _ in criteria_ids])

            # First check if user already has an in_progress evaluation
            c.execute(
                f"""
                SELECT * FROM evaluation_pool
                WHERE 
                    user_id = ? AND 
                    status = 'in_progress' AND
                    criteria_id IN ({criteria_ids_placeholders})
                LIMIT 1
                """,
                (user_id, *criteria_ids),
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

            # Find available evaluations and prioritize ones with models the user hasn't seen
            c.execute(
                f"""
                WITH user_seen_models AS (
                    -- Aggregate model views across left and right positions
                    SELECT model_name, SUM(seen_count) AS seen_count
                    FROM (
                        SELECT 
                            mc.left_model AS model_name,
                            COUNT(*) AS seen_count
                        FROM evaluations e
                        JOIN evaluation_pool ep ON e.evaluation_pool_id = ep.id
                        JOIN model_combinations mc ON ep.combo_id = mc.combo_id
                        WHERE e.user_id = ?
                        GROUP BY mc.left_model

                        UNION ALL

                        SELECT 
                            mc.right_model AS model_name,
                            COUNT(*) AS seen_count
                        FROM evaluations e
                        JOIN evaluation_pool ep ON e.evaluation_pool_id = ep.id
                        JOIN model_combinations mc ON ep.combo_id = mc.combo_id
                        WHERE e.user_id = ?
                        GROUP BY mc.right_model
                    ) combined
                    GROUP BY model_name
                ),

                combo_exposure_score AS (
                    -- Calculate an exposure score for each combo (lower is better - unseen models)
                    SELECT 
                        mc.combo_id,
                        COALESCE(usm_left.seen_count, 0) + COALESCE(usm_right.seen_count, 0) AS total_exposure
                    FROM model_combinations mc
                    LEFT JOIN user_seen_models usm_left ON mc.left_model = usm_left.model_name
                    LEFT JOIN user_seen_models usm_right ON mc.right_model = usm_right.model_name
                    GROUP BY mc.combo_id
                )

                SELECT ep.* 
                FROM evaluation_pool ep
                JOIN combo_exposure_score ces ON ep.combo_id = ces.combo_id
                WHERE 
                    (ep.status = 'available' OR 
                     (ep.status = 'in_progress' AND ep.assigned_at < ?))
                    AND ep.criteria_id IN ({criteria_ids_placeholders})
                    AND NOT EXISTS (
                        SELECT 1 FROM evaluations e
                        JOIN evaluation_pool seen_ep ON e.evaluation_pool_id = seen_ep.id
                        WHERE 
                            e.user_id = ? 
                            AND seen_ep.prompt_id = ep.prompt_id
                            AND seen_ep.criteria_id = ep.criteria_id
                            AND seen_ep.combo_id = ep.combo_id
                    )
                ORDER BY ces.total_exposure ASC, RANDOM()
                LIMIT 1
                """,
                (user_id, user_id, cutoff_time_str, *criteria_ids, user_id),
            )

            row = c.fetchone()

            assign_a_completed_eval = bool(
                row is None
            )  # if no available evaluations, assign a completed one

            if assign_a_completed_eval:
                # If the user completed all of the allocated evaluations, still select some at random
                # but still respect the assigned criteria IDs and preference unseen models
                c.execute(
                    f"""
                    WITH user_seen_models AS (
                        -- Count how many times user has seen each model (on either left or right)
                        SELECT model_name, SUM(seen_count) AS seen_count
                        FROM (
                            SELECT 
                                mc.left_model AS model_name,
                                COUNT(*) AS seen_count
                            FROM evaluations e
                            JOIN evaluation_pool ep ON e.evaluation_pool_id = ep.id
                            JOIN model_combinations mc ON ep.combo_id = mc.combo_id
                            WHERE e.user_id = ?
                            GROUP BY mc.left_model

                            UNION ALL

                            SELECT 
                                mc.right_model AS model_name,
                                COUNT(*) AS seen_count
                            FROM evaluations e
                            JOIN evaluation_pool ep ON e.evaluation_pool_id = ep.id
                            JOIN model_combinations mc ON ep.combo_id = mc.combo_id
                            WHERE e.user_id = ?
                            GROUP BY mc.right_model
                        ) combined
                        GROUP BY model_name
                    ),

                    combo_exposure_score AS (
                        -- Calculate an exposure score for each combo (lower is better - unseen models)
                        SELECT 
                            mc.combo_id,
                            COALESCE(usm_left.seen_count, 0) + COALESCE(usm_right.seen_count, 0) AS total_exposure
                        FROM model_combinations mc
                        LEFT JOIN user_seen_models usm_left ON mc.left_model = usm_left.model_name
                        LEFT JOIN user_seen_models usm_right ON mc.right_model = usm_right.model_name
                        GROUP BY mc.combo_id
                    )

                    SELECT ep.* 
                    FROM evaluation_pool ep
                    JOIN combo_exposure_score ces ON ep.combo_id = ces.combo_id
                    WHERE 
                        (ep.user_id IS NULL OR ep.user_id != ?)
                        AND ep.criteria_id IN ({criteria_ids_placeholders})
                        AND NOT EXISTS (
                            SELECT 1 FROM evaluations e
                            JOIN evaluation_pool seen_ep ON e.evaluation_pool_id = seen_ep.id
                            WHERE 
                                e.user_id = ? 
                                AND seen_ep.prompt_id = ep.prompt_id
                                AND seen_ep.criteria_id = ep.criteria_id
                                AND seen_ep.combo_id = ep.combo_id
                        )
                    ORDER BY ces.total_exposure ASC, RANDOM()
                    LIMIT 1
                    """,
                    (user_id, user_id, user_id, *criteria_ids, user_id),
                )

                row = c.fetchone()

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

        finally:
            conn.close()
