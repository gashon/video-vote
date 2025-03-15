import streamlit as st
from streamlit_sortables import sort_items
import random
import os.path as osp
import io
from fpdf import FPDF
import json
from batch_manager import NUM_PROMPTS_PER_GROUP, NUM_BATCHES, NUM_EVALUATORS
from response_handler import fetch_all_responses

VIDEO_LENGTH = 9
VIDEO_ROOT = "video/3sec"
DEBUG_MODE = True if osp.exists("/home/yusu/new_home/code/y/video-vote") else False
MODEL_LIST = ["attn", 'mamba2', 'm1', 'm2']
CRITERIA = {
    0: ["Text Following",
        "How close does the video follow the text prompt, including the key elements and actions?",
        "If the prompt says Tom should be in the kitchen but the video shows him somewhere else, like the living room, this means the video doesn't follow the text."],
    1: ["Motion Smoothness",
        "Does the motion of characters look smooth and consistent throughout the video? It checks that movements are clear, fluid, and don't have strange jumps or visual glitches.",
        "If Jerry suddenly appears somewhere else, moves in jerky steps, or his shape distorts randomly, this shows poor motion smoothness."],
    2: ["Aesthetics",
        "How pleasing does the video look? It checks the quality of colors, lighting, camera angles, and how everything fits together visually.",
        "If the colors clash, lighting changes abruptly, or scenes look messy and unattractive, the video has poor visual appeal."],
    3: ["Scene Consistency",
        "Do characters and settings stay the same across scenes? It checks if characters, objects, and locations remain consistent, even if there's a gap between scenes.",
        "If Jerry has a red scarf in one scene but suddenly doesn't have it in the next scene without explanation, the video has poor scene consistency."
        ],
    4: ["Character Emotions",
        "Does the video clearly show the emotions of characters through their facial expressions and body language? It checks if characters display feelings that match the described actions or situations.",
        "If Jerry is supposed to look scared but instead seems calm or happy, that's a violation."
        ]
}

def get_rankings(sorted_videos):
    scores = {model: 0 for model in MODEL_LIST}
    for i, video in enumerate(sorted_videos):
        scores[video] = i+1
    return scores

def start_page(user_id):
    st.title("TTT Video-evaluation")
    st.markdown(f"#### Welcome, user-{user_id:03d}!")
    st.markdown("Please follow the instructions below to complete the evaluation.")
    
    st.markdown(f"""
                * You will make **{NUM_PROMPTS_PER_GROUP} comparisons** by watching `4`x {VIDEO_LENGTH}-second videos generated from the same text prompt.
                * You will rank them based on the specific criterion assigned for the comparison.

                The estimated time for this task is 2 to 3 hours. Criterion will be randomly selected from the following five options:""")

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


    st.write("*The description of the criterion will be displayed again, no need to worry about memorizing it.*")
    st.markdown("### Instructions")
    st.markdown("""
                1. Watch all four videos considering the given criteria. *Our monitoring system will flag your submission if you do not watch the entire duration of all four videos.* 

                2. If necessary for evaluation based on the criteria(e.g. Text following), the prompts that generated the four videos will be displayed. Please read the prompts carefully

                3. Rank them based on the provided criterion; **focus strictly on this criterion** WITHOUT taking into account any other criteria or personal preferences. **1 for the best video and 4 for the worst video**.

                4. Feel free to watch the videos as many times as you need to make the best choice. However, you will NOT be able to return to the previous question after pressing the **[ Next ]** button.

                """)
    st.markdown("Please confirm the following:")

    checked = [False]*3
    checked[0] = st.checkbox("I am aware that marking a **smaller** number means a **better** video: 1 is the best, 4 is the worst.")
    checked[1] = st.checkbox("I will watch all videos in their entirety and read the text prompt before making a decision.")
    checked[2] = st.checkbox("I will be thoughtful and make my best judgment before finalizing any decisions.")

    st.markdown("If you are ready, click the **[ Start ]** button below to begin.")
    return all(checked)

def success_final_page(rows):
        user_id = rows[0][0]
        batch_id = rows[0][1]
        assert batch_id == user_id % NUM_BATCHES, f"Batch id mismatch: {batch_id} != {user_id % NUM_BATCHES}"
        st.success(f"User-{user_id:03d} have completed all evaluations.\n To download your receipt as **proof of completion**, simply click the button below. Thank you for your participation!")
        rows = sorted(rows, key=lambda x: x[2])

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(0, 10, f"Receipt for user{user_id:03d}-batch{batch_id:03d}", ln=True)
        for row in rows:
            pdf.cell(0, 10, " ".join([str(item) for item in row[2:]]), ln=True)

        pdf_buffer = io.BytesIO()
        pdf_buffer.write(pdf.output(dest='S').encode('latin1'))
        pdf_buffer.seek(0)

        st.download_button(
            label="📥 Download Receipt",
            data=pdf_buffer,
            file_name=f"user{user_id:03d}-batch{batch_id:03d}.pdf",
            mime="application/pdf"
        )

def show_videos_page(vc_id):
    video_id, criteria_id = vc_id
    st.subheader(f'{st.session_state.current_index+1}/{NUM_PROMPTS_PER_GROUP}')
    st.progress(st.session_state.current_index / NUM_PROMPTS_PER_GROUP)
    st.caption(f"Prompt id: {video_id:03d} - Criteria id: {criteria_id}")
    
    # Initialize counters in session state
    if "clicked_video_count" not in st.session_state:
        st.session_state.clicked_video_count = 0
    if "clicked_video_ids" not in st.session_state:
        st.session_state.clicked_video_ids = set()
    
    st.divider()
    marks = ["A", "B", "C", "D"]
    st.markdown("#### Videos:")

    if 'video_id' not in st.session_state or st.session_state.video_id != video_id:
        if video_id not in st.session_state.clicked_video_ids:
            st.session_state.clicked_video_ids.add(video_id)

        st.session_state.clicked_video_count += 1
        
        video_list = [(model, osp.join(VIDEO_ROOT, model+"_newtest", "step-8000", f"{video_id%15:03d}-00.mp4")) for model in MODEL_LIST]

        random.shuffle(video_list)
        video_list = {mark: video for mark, video in zip(marks, video_list)}
        st.session_state.video_list = video_list
        st.session_state.video_id = video_id
    else:
        video_list = st.session_state.video_list
    

    cols = st.columns(2)
    for i, video in enumerate(video_list.values()):
        with cols[i%2]:
            if DEBUG_MODE:
                st.caption(f"Video {marks[i]} ({video[0]})")
            else:
                st.caption(f"Video {marks[i]}")
            st.video(video[1], autoplay=(i==0))
    
    if CRITERIA[criteria_id][0] in ["Text Following", "Character Emotions"]:
        with open(osp.join(VIDEO_ROOT, MODEL_LIST[0]+"_newtest", "step-8000", f"{video_id%15:03d}.txt")) as f:
            prompt = f.read()
        st.markdown("#### Prompt:")
        st.markdown(f"{prompt}")
    st.divider()

    cols = st.columns([0.7, 0.3])
    with cols[0]:
        st.markdown(f"#### Criteria - `{CRITERIA[criteria_id][0]}`:")
        st.markdown(f"{CRITERIA[criteria_id][1]}")
        st.caption(f"*Example violation: {CRITERIA[criteria_id][2]}")
    with cols[1]:
        rankings = {}
        for i, mark in enumerate(marks):
            rankings[mark] = st.pills(f"Video {mark}'s rank", options=[1, 2, 3, 4], key=f"vid-{video_id}-{mark}")
    
    if None in rankings.values():
        st.warning(f"‼️ Rank the videos. **1 is the best video** and **4 is the worst** video, as judged by the criterion.")
        return None

    elif set(rankings.values()) != {1, 2, 3, 4}:
        st.warning(f"‼️ Each rank must be unique")
        return None
    
    else:
        sorted_marks = sorted(rankings, key=lambda x: rankings[x])
        rankings = get_rankings([video_list[a][0] for a in sorted_marks])
        with cols[0]:
            st.container(border=True).markdown(f"###### Your ranking: (best)`{sorted_marks[0]}` -> `{sorted_marks[1]}` -> `{sorted_marks[2]}` -> `{sorted_marks[3]}` (worst)")
        st.info(f"💡If you are satisfied with your ranking, click on the **[ Next ]** button to proceed.")
        if DEBUG_MODE:
            st.write(" > ".join([video_list[a][0] for a in sorted_marks]))
        return list(rankings.values())

def admin_page():
    st.title("Admin Page")
    password = st.text_input("Enter admin password:", type="password")
    if password == "lakeside6pm":
        st.success("Access granted!")
        
        report_data = io.StringIO()
        entries = fetch_all_responses()
        entries = sorted(entries, key=lambda x: (x[1], x[3]))
        for entry in entries:
            json.dump(entry, report_data)
            report_data.write("\n")
        
        report_data.seek(0)
        
        st.download_button(
            label="📥 Download Admin Report",
            data=report_data.getvalue(),
            file_name="admin_report.jsonl",
            mime="application/jsonl"
        )
    else:
        if password:
            st.error("Access denied! Incorrect password.")