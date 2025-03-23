import time

import streamlit as st
from streamlit_cookies_manager import CookieManager

from batch_manager import create_batches
from config import DEBUG_MODE, MIN_REVIEW_DURATION_IN_SEC, get_eval_batch_size
from pool_manager import all_evaluations_assigned, get_sample_from_pool
from response_handler import (
    create_db,
    get_new_user_id,
    get_user_eval_count,
    save_response,
)
from streamlit_pages import admin_page, show_videos_page, start_page, success_final_page


def get_cookie_manager():
    # TODO: use an encrypted cookie manager to prevent tampering
    manager = CookieManager()

    if not manager.ready():
        st.stop()

    return manager


if __name__ == "__main__":
    #  streamlit run streamlit_app.py
    create_db()

    cookies = get_cookie_manager()
    batches = create_batches()
    if DEBUG_MODE:
        if st.button("Reset"):
            del cookies["user_id"]
            cookies["final_page"] = False
            cookies.save()
            st.rerun()

    if (
        int(st.query_params.get("user_id", "-1")) >= 0
        and cookies.get("user_id", None) is None
    ):
        cookies["user_id"] = st.query_params["user_id"]
        cookies["current_index"] = "0"
        cookies.save()
        st.rerun()

    # Admin page
    if st.query_params.get("admin", "") == "true":
        admin_page()

        st.stop()

    if all_evaluations_assigned():
        st.warning(
            "All evaluations have been assigned. Thank you for your participation!"
        )
        st.stop()

    # Start Page
    elif "user_id" not in cookies:
        ready = start_page()

        if st.button("Start", disabled=not ready):
            # cookies must be strings
            cookies["user_id"] = str(get_new_user_id())
            cookies["current_index"] = "0"
            cookies.save()
            st.rerun()

    # Final Page
    elif cookies.get("final_page", False):
        user_id = int(cookies["user_id"])
        eval_batch_size = get_eval_batch_size()

        saved_responses_count = get_user_eval_count(user_id)
        expected_responses = eval_batch_size
        remaining_responses = expected_responses - saved_responses_count

        success_final_page(user_id)
        # st.caption(f"If you are completing another set of evaluations, please click below. Only do this if you are confident that you have already claimed the job.")
        # if st.button("Start new set"):
        #     del cookies["user_id"]
        #     del cookies["final_page"]
        #     cookies.save()
        #     st.rerun()

    # Video eval page
    else:
        user_id = int(cookies["user_id"])
        current_index = int(cookies["current_index"])

        st.caption(f"User-{user_id:03d} - Index-{current_index:03d})")

        eval = get_sample_from_pool(user_id)
        eval = None

        # If user completed all their evaluations/pool is empty
        if eval is None:
            cookies["final_page"] = True
            cookies.save()
            st.rerun()

        prompt_id, criteria_id, combo_id, turn_id = eval

        if (
            "current_index" not in st.session_state
            or current_index != st.session_state.current_index
            or "current_index_start_time" not in st.session_state
        ):
            st.session_state.current_index_start_time = time.time()
        st.session_state.current_index = current_index

        left_model, right_model, rating = show_videos_page(eval)
        warning_placeholder = st.empty()
        button_placeholder = st.empty()

        if (
            "reviewed_before_duration" in cookies
            and cookies["reviewed_before_duration"] == "true"
        ):
            with warning_placeholder:
                st.warning(
                    f"WARNING: In order to get the submission code, please spend at least {MIN_REVIEW_DURATION_IN_SEC} seconds accurately reviewing."
                )

        with button_placeholder:
            if st.button("Next", disabled=(rating is None)):
                review_duration = int(
                    time.time() - st.session_state.current_index_start_time
                )
                if review_duration < MIN_REVIEW_DURATION_IN_SEC:
                    cookies["reviewed_before_duration"] = "true"
                else:
                    cookies["reviewed_before_duration"] = "false"
                    save_response(
                        current_index=current_index,
                        prompt_id=prompt_id,
                        criteria_id=criteria_id,
                        turn_id=turn_id,
                        combo_id=combo_id,
                        left_model=left_model,
                        right_model=right_model,
                        rating=rating,
                        user_id=user_id,
                        review_duration=review_duration,
                    )

                saved_responses_count = get_user_eval_count(user_id)
                expected_responses = get_eval_batch_size()
                remaining_responses = expected_responses - saved_responses_count

                if remaining_responses == 0:
                    cookies["final_page"] = True

                cookies["current_index"] = saved_responses_count

                cookies.save()
                st.rerun()

    st.caption(f"If you have any questions, please contact kdalal@berkeley.edu")
