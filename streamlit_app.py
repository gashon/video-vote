import streamlit as st
from video_display import show_videos, fetch_batches, MODEL_LIST
from response_handler import save_response, create_db

if __name__ == "__main__":
    #  streamlit run streamlit_app.py 
    create_db()

    if 'batch_id' not in st.session_state:
        st.session_state.batch_id = None

    if st.session_state.batch_id is None:
        st.title("Select Batch")
        batch_options = [f"Batch {i}" for i in range(10)]
        selected_batch = st.radio("Choose a batch:", batch_options)
        
        if st.button("Start"):
            st.session_state.batch_id = batch_options.index(selected_batch)
            st.session_state.scores = {criterion:{model:0 for model in MODEL_LIST} for criterion in range(6)}
            st.session_state.scores["evaluated_prompts"]= []
            st.session_state.current_index = 0
            st.rerun()
    
    else:
        batch_id = st.session_state.batch_id
        vc_ids = fetch_batches(batch_id)

        prompt_id, criterion_id = vc_ids[st.session_state.current_index]
        rankings = show_videos((prompt_id, criterion_id))
        button_placeholder = st.empty()

        with button_placeholder:
            if st.button("Next", disabled=(0 in rankings)):
                save_response(prompt_id, criterion_id, rankings)
                st.session_state.current_index += 1
                st.rerun()

            if st.session_state.current_index >= len(vc_ids) - 1:
                if st.button("Submit", disabled=(0 in rankings)):
                    save_response(prompt_id, criterion_id, rankings)
                    st.success("All evaluations in this batch are completed!")
        