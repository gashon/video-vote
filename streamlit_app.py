import json

import streamlit as st
from streamlit_cookies_manager import CookieManager

from response_handler import create_db, save_response
from video_display import MODEL_LIST, fetch_batches, show_videos


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

    if "batch_id" not in cookies:
        cookies["batch_id"] = "None"  # cookies must be string
        cookies.save()

    if cookies["batch_id"] == "None":
        st.title("TTT Video-evaluation")

        try:
            user_id = int(st.query_params["user_id"])
        except KeyError:
            st.error(
                "Assigned URL error: this is an invalid url. Please use the assigned URL or contact ujinsong@stanford.edu"
            )
            st.stop()

        batch_id = user_id % 10

        if st.button("Start"):
            # cookies must be strings
            cookies["batch_id"] = str(batch_id)
            cookies["user_id"] = str(user_id)
            cookies["current_index"] = "0"
            cookies.save()
            st.rerun()

    elif "final_page" in cookies:
        st.write("You are done")
        ## TODO

    else:
        batch_id = int(cookies["batch_id"])
        current_index = int(cookies["current_index"])

        st.session_state.scores = {
            criterion: {model: 0 for model in MODEL_LIST} for criterion in range(6)
        }
        st.session_state.scores["evaluated_prompts"] = []

        vc_ids = fetch_batches(batch_id)

        prompt_id, criterion_id = vc_ids[current_index]
        rankings = show_videos((prompt_id, criterion_id), current_index)
        button_placeholder = st.empty()

        with button_placeholder:
            if st.button("Next", disabled=(0 in rankings)):
                save_response(prompt_id, criterion_id, rankings, batch_id)
                cookies["current_index"] = current_index + 1
                st.rerun()  # cookie will be saved on rerun

            if current_index >= len(vc_ids) - 1:
                if st.button("Submit", disabled=(0 in rankings)):
                    save_response(prompt_id, criterion_id, rankings)
                    cookies["final_page"] = True
                    st.success("All evaluations in this batch are completed!")
                    st.rerun()

