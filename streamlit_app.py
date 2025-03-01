import time

import streamlit as st
from streamlit_cookies_manager import CookieManager

from response_handler import create_db, save_response, count_valid_user_responses
from video_display import DEBUG_MODE, MODEL_LIST, show_videos, start_page
from batch_manager import create_batches, NUM_PROMPTS_PER_GROUP


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
    

    if cookies["batch_id"] == "None":

        try:
            user_id = int(st.query_params["user_id"])
        except KeyError:
            if DEBUG_MODE: user_id = 2
            else:
                st.error(
                    "Assigned URL error: this is an invalid url. Please use the assigned URL or contact ujinsong@stanford.edu"
                )
                st.stop()

        ready = start_page(user_id)

        batch_id = user_id % 10

        if st.button("Start", disabled=not ready):
            # cookies must be strings
            cookies["batch_id"] = str(batch_id)
            cookies["user_id"] = str(user_id)
            cookies["current_index"] = "0"
            cookies.save()
            st.rerun()

    elif cookies.get("final_page", False):
        count, missing_index = count_valid_user_responses(int(cookies["user_id"]))
        if count == NUM_PROMPTS_PER_GROUP:
            st.success("You have completed all evaluations! Thanks for your participation!")
        else:
            st.warning(f"You have evaluated {count} prompts. Please complete all evaluations.")
    else:
        batch_id = int(cookies["batch_id"])
        user_id = int(cookies["user_id"])
        current_index = int(cookies["current_index"])

        st.session_state.scores = {
            criterion: {model: 0 for model in MODEL_LIST} for criterion in range(6)
        }
        st.session_state.scores["evaluated_prompts"] = []

        vc_ids = batches[batch_id]
    
        prompt_id, criterion_id = vc_ids[current_index]
        st.session_state.current_index = current_index
        rankings = show_videos((prompt_id, criterion_id))
        button_placeholder = st.empty()
        start_time = time.time()

        with button_placeholder:
            if st.button("Next", disabled=(rankings is None)):
                review_duration = int(time.time() - start_time)

                save_response(
                    prompt_id,
                    criterion_id,
                    rankings,
                    batch_id,
                    user_id,
                    current_index,
                    review_duration,
                )

                saved_responses = count_valid_user_responses(user_id)
                if saved_responses >= current_index + 1:
                    cookies["current_index"] = current_index + 1
                print(f'current_index: {current_index}, number of saved responses: {saved_responses}')
                    
                st.rerun()  # cookie will be saved on rerun

            if current_index >= len(vc_ids) - 1:
                print(current_index, len(vc_ids))
                if st.button("Submit", disabled=(rankings is None)):
                    review_duration = int(time.time() - start_time)
                    save_response(
                        prompt_id,
                        criterion_id,
                        rankings,
                        batch_id,
                        user_id,
                        current_index,
                        review_duration,
                    )
                    cookies["final_page"] = True
                    st.success("All evaluations in this batch are completed!")
                    st.rerun()
    st.caption(f"If you have any questions, please contact ujinsong@stanford.edu")