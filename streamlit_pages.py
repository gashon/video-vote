import datetime
import io
import json
import os
import os.path as osp
import random
import sqlite3

import streamlit as st
from fpdf import FPDF

from batch_manager import get_eval_batch_size
from config import CRITERIA, DEBUG_MODE, MODEL_LIST, VIDEO_LENGTH, VIDEO_ROOT, get_combo
from response_handler import fetch_all_responses

SAVE_PATH = "eval"


def get_rankings(sorted_videos):
    scores = {model: 0 for model in MODEL_LIST}
    for i, video in enumerate(sorted_videos):
        scores[video] = i + 1
    return scores


def start_page():
    st.title("TTT Video-evaluation")
    st.warning(
        f"Please only use Google Chrome as your browser if you are not already doing so!"
    )
    st.markdown(f"#### Welcome!")
    st.markdown(
        """
        My name is Karan Dalal. I am a researcher at Stanford University. We are working on a machine learning project to study different methods of generating long videos with AI.

        In this survey, you will be evaluating videos generated by different machine learning models trained on the Tom and Jerry cartoon. We will provide you with two videos, side by side, and a specific criteria for rating. You will simply select the video that better matches the criteria.
    """
    )

    st.markdown("Please follow the instructions below to complete the evaluation.")

    st.markdown(
        f"""
                * You will make **{get_eval_batch_size()} comparisons** by watching two {VIDEO_LENGTH}-second videos generated from the same prompt.
                * You will select the video that better matches the criterion.

                The estimated time for this task is 1 hour. Criterion will be one of the following four options:"""
    )

    for i, criterion in CRITERIA.items():
        with st.expander(f"**{criterion[0]}**: {criterion[1]}", expanded=True):
            if criterion[2]:
                st.write(f"Violation example: {criterion[2]}")
            good_example_video = osp.join("example_videos", f"criterion{i}-good.mp4")
            bad_example_video = osp.join("example_videos", f"criterion{i}-bad.mp4")
            reason_text = osp.join("example_videos", f"criterion{i}-reason.txt")
            if osp.exists(good_example_video):
                with open(reason_text) as f:
                    reason_text = f.read()
                col1, col2 = st.columns(2)
                with col1:
                    st.caption("Good example👍")
                    st.video(good_example_video, start_time=0, format="video/mp4")
                with col2:
                    st.caption("Bad example👎")
                    st.video(bad_example_video, start_time=0, format="video/mp4")

                st.caption(f"{reason_text}")

    st.write(
        "*The description of the criterion will be displayed again, no need to worry about memorizing it.*"
    )
    st.markdown("### Instructions")
    st.markdown(
        """
                1. Watch both videos considering the given criteria.

                2. If necessary for evaluation based on the criteria (e.g. Text following), the prompts that generated the two videos will be displayed. Please read the prompts carefully

                3. Select the better video, or mark a tie **focus strictly on this criterion** WITHOUT taking into account any other criteria or personal preferences.

                4. Feel free to watch the videos as many times as you need to make the best choice. However, you will NOT be able to return to the previous question after pressing the **[ Next ]** button.

                """
    )
    st.markdown("Please confirm the following:")

    checked = [False] * 2
    checked[0] = st.checkbox(
        "I will watch both videos in their entirety and read the text prompt before making a decision."
    )
    checked[1] = st.checkbox(
        "I will be thoughtful and make my best judgment before finalizing any decisions."
    )

    st.markdown("If you are ready, click the **[ Start ]** button below to begin.")
    st.warning(
        "Please do not click start unless you fully commit to finishing this set of evaluation."
    )
    return all(checked)


def success_final_page(user_id):
    st.success(
        f"User-{user_id:03d} have completed all evaluations.\n Please enter code CJKM933K to get your reward. Thank you for your participation! Note: Once you leave this page, you cannot return."
    )

    # evals = sorted(evals, key=lambda x: x[2])

    # pdf = FPDF()
    # pdf.set_auto_page_break(auto=True, margin=15)
    # pdf.add_page()
    # pdf.set_font("Arial", size=12)

    # pdf.cell(0, 10, f"Receipt for user{user_id:03d}", ln=True)
    # for row in evals:
    #     pdf.cell(0, 10, " ".join([str(item) for item in row[2:]]), ln=True)

    # pdf_buffer = io.BytesIO()
    # pdf_buffer.write(pdf.output(dest="S").encode("latin1"))
    # pdf_buffer.seek(0)

    # st.download_button(
    #     label="📥 Download Receipt",
    #     data=pdf_buffer,
    #     file_name=f"user{user_id:03d}.pdf",
    #     mime="application/pdf",
    # )


def show_videos_page(eval_id):
    prompt_id, criteria_id, combo_id, turn_id = eval_id

    eval_batch_size = get_eval_batch_size()
    st.subheader(f"{st.session_state.current_index+1}/{eval_batch_size}")
    st.progress(st.session_state.current_index / eval_batch_size)
    st.caption(f"Prompt id: {prompt_id:03d} - Criteria id: {criteria_id}")

    # Initialize counters in session state
    if "clicked_video_count" not in st.session_state:
        st.session_state.clicked_video_count = 0
    if "clicked_video_ids" not in st.session_state:
        st.session_state.clicked_video_ids = set()

    st.markdown(f"#### Criteria - `{CRITERIA[criteria_id][0]}`:")
    st.markdown(f"{CRITERIA[criteria_id][1]}")
    st.caption(f"*Example violation: {CRITERIA[criteria_id][2]}")

    st.divider()

    if CRITERIA[criteria_id][0] in ["Text Following", "Character Emotions"]:
        with open(
            osp.join(VIDEO_ROOT, MODEL_LIST[0], f"prompt-{prompt_id}/summary.txt"),
            "r",
            encoding="utf-8",
        ) as f:
            prompt = f.read()
        st.markdown("#### Prompt:")
        st.markdown(f"{prompt}")
        st.divider()

    combo = list(get_combo(combo_id))

    rng = random.Random(hash(f"{prompt_id}_{criteria_id}_{combo_id}_{turn_id}"))
    rng.shuffle(combo)

    left_model = combo[0]
    right_model = combo[1]

    st.caption(
        f"Please refresh the page or contact kdalal@berkeley.edu if there is an issue with the video player."
    )

    def get_model_path(model_name):
        return osp.join(VIDEO_ROOT, model_name, f"prompt-{prompt_id}/000000.mp4")

    left_video_path = get_model_path(left_model)
    right_video_path = get_model_path(right_model)

    cols = st.columns(2)

    with cols[0]:
        st.markdown("Left")
        st.video(left_video_path, autoplay=False)

    with cols[1]:
        st.markdown("Right")
        st.video(right_video_path, autoplay=False)

    rating_mapping = {"left": 0, "tie": 1, "right": 2}

    rating = st.pills(
        f"Which video is better?",
        options=["left", "tie", "right"],
        key=f"vid-{prompt_id}-{criteria_id}-{turn_id}-{combo_id}",
    )
    st.warning(
        f"Please watch both videos before making your selection. Our software can detect if you have not watched both videos."
    )
    if rating is None:

        return left_model, right_model, None

    return left_model, right_model, rating_mapping[rating]


def admin_page():
    st.title("Admin Page")
    password = st.text_input("Enter admin password:", type="password")

    if password == "lakeside6":
        st.success("Access granted!")

        # Section for deleting users and their evaluations
        st.header("Delete User")
        user_ids_input = st.text_input(
            "Enter comma-separated user IDs to delete (e.g., 1,2,3):"
        )
        delete_button = st.button("Delete Selected Users")

        if delete_button and user_ids_input:
            try:
                # Parse the comma-separated user IDs
                user_ids = [
                    int(id.strip()) for id in user_ids_input.split(",") if id.strip()
                ]

                if user_ids:
                    # Call the function to mark users and their evaluations as deleted
                    deleted_count = delete_users_and_evaluations(user_ids)
                    st.success(
                        f"Successfully marked {len(user_ids)} user and {deleted_count} evaluations as deleted."
                    )
                else:
                    st.warning("No valid user IDs provided.")
            except ValueError:
                st.error("Invalid input. Please enter comma-separated numbers only.")
            except Exception as e:
                st.error(f"Error processing deletion: {str(e)}")

        # Admin report download section
        st.header("Download Reports")
        report_data = io.StringIO()
        entries, col_names = fetch_all_responses()
        json.dump(tuple(col_names), report_data)
        report_data.write("\n")

        for entry in entries:
            json.dump(entry, report_data)
            report_data.write("\n")

        report_data.seek(0)

        st.download_button(
            label="📥 Download Admin Report",
            data=report_data.getvalue(),
            file_name="admin_report.jsonl",
            mime="application/jsonl",
        )

        # Database download section
        st.header("Database Management")

        col1, col2 = st.columns(2)

        with col1:
            # Add download button for SQLite database file
            try:
                with open("eval/evaluations.db", "rb") as db_file:
                    db_bytes = db_file.read()

                st.download_button(
                    label="📥 Download SQLite Database",
                    data=db_bytes,
                    file_name="evaluations.db",
                    mime="application/octet-stream",
                )
            except FileNotFoundError:
                st.error("Database file not found at eval/evaluations.db")
            except Exception as e:
                st.error(f"Error accessing database file: {str(e)}")

        with col2:
            # Add upload functionality for replacing the database
            st.subheader("Replace Database")
            uploaded_file = st.file_uploader(
                "Upload SQLite Database", type=["db", "sqlite", "sqlite3"]
            )

            if uploaded_file is not None:
                if st.button("Replace Current Database"):
                    try:
                        # Create a backup of the current database first
                        import shutil
                        from datetime import datetime

                        # Generate timestamp for backup filename
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        backup_path = f"eval/evaluations_backup_{timestamp}.db"

                        # Create backup if original exists
                        if os.path.exists("eval/evaluations.db"):
                            shutil.copy2("eval/evaluations.db", backup_path)
                            st.info(f"Created backup at {backup_path}")

                        # Save the uploaded file to replace the current database
                        with open("eval/evaluations.db", "wb") as f:
                            f.write(uploaded_file.getbuffer())

                        st.success("Database successfully replaced!")
                        st.warning("Please refresh the page to use the new database.")
                    except Exception as e:
                        st.error(f"Error replacing database: {str(e)}")

        st.write("Refresh the page before downloading the most recent data.")
    else:
        if password:
            st.error("Access denied! Incorrect password.")


def delete_users_and_evaluations(user_ids):
    """
    Marks users and their evaluations as deleted by setting the deleted_at timestamp
    and returns evaluation_pool entries to available status.

    Args:
        user_ids: List of user IDs to mark as deleted

    Returns:
        int: Number of users successfully marked as deleted
    """
    conn = sqlite3.connect(osp.join(SAVE_PATH, "evaluations.db"))
    c = conn.cursor()

    try:
        # Start a transaction
        conn.execute("BEGIN TRANSACTION")

        # Get the current timestamp
        current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Update users table - mark users as deleted
        placeholders = ",".join(["?"] * len(user_ids))
        c.execute(
            f"""
            UPDATE users
            SET deleted_at = ?
            WHERE id IN ({placeholders})
            AND deleted_at IS NULL
            """,
            (current_timestamp, *user_ids),
        )

        # Get evaluation_pool_ids for the users' evaluations
        c.execute(
            f"""
            SELECT evaluation_pool_id
            FROM evaluations
            WHERE user_id IN ({placeholders})
            AND deleted_at IS NULL
            """,
            user_ids,
        )
        eval_pool_ids = [row[0] for row in c.fetchall()]

        # Mark evaluations as deleted
        c.execute(
            f"""
            UPDATE evaluations
            SET deleted_at = ?
            WHERE user_id IN ({placeholders})
            AND deleted_at IS NULL
            """,
            (current_timestamp, *user_ids),
        )

        # Reset the status of evaluation_pool entries if there are any
        if eval_pool_ids:
            pool_placeholders = ",".join(["?"] * len(eval_pool_ids))
            c.execute(
                f"""
                UPDATE evaluation_pool
                SET status = 'available', user_id = NULL
                WHERE id IN ({pool_placeholders})
                AND (status = 'completed' OR status='in_progress')
                """,
                eval_pool_ids,
            )

        # Commit the transaction
        conn.commit()

        # Return the number of users affected
        return c.rowcount

    except Exception as e:
        # Roll back in case of error
        conn.rollback()
        raise e
    finally:
        conn.close()
