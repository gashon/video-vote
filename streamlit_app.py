import time

import streamlit as st
from streamlit_cookies_manager import CookieManager

from response_handler import create_db, save_response, count_valid_user_responses
from video_display import DEBUG_MODE, MODEL_LIST, show_videos, start_page
from batch_manager import create_batches, NUM_PROMPTS_PER_GROUP, NUM_BATCHES


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
            cookies["batch_id"] = "None"
            cookies["final_page"] = False
            cookies.save()
            st.rerun()

    if "batch_id" not in cookies or 'current_index' not in cookies:
        cookies["batch_id"] = "None"  # cookies must be string
        cookies.save()
    
    try:
        user_id = int(st.query_params["user_id"])
    except KeyError:
        if DEBUG_MODE:
            user_id = 67
        else:
            st.error(
                "Assigned URL error: this is an invalid url. Please use the assigned URL or contact ujinsong@stanford.edu"
            )
            st.stop()
    
    if cookies["batch_id"] == "None" or int(cookies["batch_id"]) != user_id%NUM_BATCHES:

        ready = start_page(user_id)

        batch_id = user_id % NUM_BATCHES

        if st.button("Start", disabled=not ready):
            # cookies must be strings
            cookies["batch_id"] = str(batch_id)
            cookies["user_id"] = str(user_id)
            cookies["current_index"] = "0"
            cookies.save()
            st.rerun()

    elif cookies.get("final_page", False):
        saved_responses = count_valid_user_responses(int(cookies["user_id"]))
        missing_responses = set(range(NUM_PROMPTS_PER_GROUP))-(saved_responses)
        count = len(saved_responses)
        if count == NUM_PROMPTS_PER_GROUP:
            st.success("You have completed all evaluations! Thanks for your participation!")
        else: 
            st.warning(f"You have evaluated {count} prompts and {len(missing_responses)} missing. Missing indices: {missing_responses}")
            with st.spinner("Redirecting to the missing prompt in 5 second..."):
                time.sleep(5)
            cookies["final_page"] = False
            cookies["current_index"] = min(missing_responses)
            cookies.save()
            assert cookies["batch_id"] != "None"
            st.rerun()
    else:
        batch_id = int(cookies["batch_id"])
        user_id = int(cookies["user_id"])
        current_index = int(cookies["current_index"])

        st.caption(f"User-{user_id:03d} (Batch-{batch_id:03d} - Index-{current_index:03d})")
        st.session_state.scores = {
            criterion: {model: 0 for model in MODEL_LIST} for criterion in range(6)
        }

        vc_ids = batches[batch_id]

        prompt_id, criterion_id = vc_ids[current_index]
        if "current_index" not in st.session_state or current_index!=st.session_state.current_index or "current_index_start_time" not in st.session_state:
            st.session_state.current_index_start_time = time.time()
        st.session_state.current_index = current_index
        rankings = show_videos((prompt_id, criterion_id))
        button_placeholder = st.empty()

        with button_placeholder:
            if st.button("Next", disabled=(rankings is None)):
                review_duration = int(time.time() - st.session_state.current_index_start_time)
                save_response(
                    prompt_id=prompt_id,
                    criteria_id=criterion_id,
                    rating=rankings,
                    batch_id=batch_id,
                    user_id=user_id,
                    current_index=current_index,
                    review_duration=review_duration,
                )

                saved_responses = count_valid_user_responses(user_id)
                missing_responses = set(range(NUM_PROMPTS_PER_GROUP))-(saved_responses)
                if len(saved_responses)==0:
                    cookies["batch_id"] = "None"
                    st.rerun()
                elif len(missing_responses) == 0:
                    cookies["final_page"] = True
                elif current_index in saved_responses:
                    cookies["current_index"] = min(missing_responses)
                else: # should not happen
                    st.warning(f"Error: Your response for prompt {current_index} was not saved. Try again.")
                    
                st.rerun()  # cookie will be saved on rerun

    st.caption(f"If you have any questions, please contact ujinsong@stanford.edu")