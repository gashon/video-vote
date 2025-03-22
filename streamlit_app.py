import time
from config import get_eval_batch_count, get_eval_batch_size, get_global_index

import streamlit as st
from streamlit_cookies_manager import CookieManager

from response_handler import create_db, save_response, get_valid_user_response_indices, get_new_user_id
from streamlit_pages import show_videos_page, start_page, success_final_page, admin_page
from batch_manager import create_batches
from config import DEBUG_MODE


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


    if int(st.query_params.get("user_id", "-1")) >= 0 and cookies.get("user_id", None) is None:
        cookies["user_id"] = st.query_params["user_id"]
        cookies["current_index"] = "0"
        cookies.save()
        st.rerun()


    # Admin page
    if st.query_params.get("admin", "") == "true":
        admin_page()

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

        saved_responses, evals = get_valid_user_response_indices(user_id)
        expected_responses = set(range(eval_batch_size))
        missing_responses = expected_responses - saved_responses

        count = len(saved_responses)
        if count == eval_batch_size:
            success_final_page(user_id, evals)
            # st.caption(f"If you are completing another set of evaluations, please click below. Only do this if you are confident that you have already claimed the job.")
            # if st.button("Start new set"):
            #     del cookies["user_id"]
            #     del cookies["final_page"]
            #     cookies.save()
            #     st.rerun()
        else: 
            st.warning(f"You have evaluated {count} prompts and {len(missing_responses)} missing. Missing indices: {missing_responses}")
            with st.spinner("Redirecting to the missing prompt in 5 second..."):
                time.sleep(5)
            cookies["final_page"] = False
            cookies["current_index"] = min(missing_responses)
            cookies.save()
            st.rerun()

    # Video eval page
    else:
        user_id = int(cookies["user_id"])
        current_index = int(cookies["current_index"])

        st.caption(f"User-{user_id:03d} - Index-{current_index:03d})")

        eval_id = batches[user_id % get_eval_batch_count()][current_index]
        global_index = get_global_index(user_id, current_index)

        prompt_id, criteria_id, combo_id, turn_id = eval_id

        if "current_index" not in st.session_state or current_index!=st.session_state.current_index or "current_index_start_time" not in st.session_state:
            st.session_state.current_index_start_time = time.time()
        st.session_state.current_index = current_index

        left_model, right_model, rating = show_videos_page(eval_id)
        button_placeholder = st.empty()

        with button_placeholder:
            if st.button("Next", disabled=(rating is None)):
                review_duration = int(time.time() - st.session_state.current_index_start_time)
                save_response(
                    global_index=global_index,
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

                saved_responses, _ = get_valid_user_response_indices(user_id)
                expected_responses = set(range(get_eval_batch_size()))
                missing_responses = expected_responses - saved_responses
                
                if len(missing_responses) == 0:
                    cookies["final_page"] = True
                elif current_index in saved_responses:
                    cookies["current_index"] = min(missing_responses)
                else: # should not happen
                    st.warning(f"Error: Your response for prompt {current_index} was not saved. Try again.")
                    
                cookies.save()
                st.rerun()

    st.caption(f"If you have any questions, please contact kdalal@berkeley.edu")