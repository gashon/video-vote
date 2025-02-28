import streamlit as st
from streamlit_sortables import sort_items
import random
import os.path as osp

NUM_PROMPTS = 15
VIDEO_ROOT = "video/3sec"
DEBUG_MODE = True if osp.exists("/home/yusu/new_home/code/y/video-vote") else False
MODEL_LIST = ["attn", 'mamba2', 'm1', 'm2']
CRITERIA = {
    0: ["Text alignment",
        "Measures how closely the generated video aligns with the provided prompt, ensuring accurate representation of key elements and actions described.",
        "The content of the video does not accurately reflect the details specified in the prompt e.g. If the prompt specifies that Tom should be in the kitchen, but the video depicts him in a living room, this would represent a violation."],
    1: ["Frame Stability",
        " Assesses the stability and coherence of frames throughout the video, contributing to a smooth viewing experience.",
        "Morphing artifacts, blurred or distorted objects, or abrupt appearances or disappearances of content"],
    2: ["Motion Naturalness",
        "Reflects the fluidity and realism of motion in the generated video. It indicates the model’s understanding of real-world physics while ensuring characters and objects move naturally within the scene.",
        "Unnatural motion can occur if characters move in jerky or unrealistic ways that don't reflect typical physical behavior. e.g. If Tom runs with an exaggerated, unrealistic motion that defies gravity, this would indicate poor motion naturalness."
        ],
    3: ["Aesthetics",
        "Evaluates the visual appeal of the generated videos, considering factors such as composition, lighting, color schemes, and camera effects. Strong aesthetics contribute to more engaging and captivating content.",
        "Colors clash, lighting is inconsistent, or the overall composition is unappealing"],
    4: ["Contextual Coherence",
        "Measures the uniformity of characters across different segments of the video, ensuring continuity in their appearance and actions.",
        "Inconsistencies occur when characters display different clothing or features in various scenes without explanation. e.g. If Jerry is shown wearing a red scarf in one scene and appears without it in the next without any narrative justification, this would represent a violation."
        ],
    5: ["Emotion Conveyance",
        "Assesses how effectively the model conveys the emotions of each character, which is essential for a cartoon like Tom and Jerry",
        "Characters’ expressions do not align with the actions they are portraying. e,g. If the prompt states that Jerry should look 'frightened,' but his facial expression appears neutral or confused, this would indicate a violation."
        ]
}

def get_rankings(sorted_videos):
    scores = {model: 0 for model in MODEL_LIST}
    for i, video in enumerate(sorted_videos):
        scores[video] = i+1
    return scores

def show_videos(vc_id):
    video_id, criteria_id = vc_id
    st.subheader(f'{st.session_state.current_index+1}/300')
    st.progress(st.session_state.current_index / 300)
    st.caption(f"Prompt id: {video_id:03d} - Criteria id: {criteria_id}")

    with open(osp.join(VIDEO_ROOT, MODEL_LIST[0]+"_newtest", "step-8000", f"{video_id:03d}.txt")) as f:
        prompt = f.read()
    st.markdown("#### Prompt:")
    st.markdown(f"{prompt}")
    st.divider()

    # Initialize counters in session state
    if "clicked_video_count" not in st.session_state:
        st.session_state.clicked_video_count = 0
    if "clicked_video_ids" not in st.session_state:
        st.session_state.clicked_video_ids = set()

    marks = ["A", "B", "C", "D"]
    st.markdown("#### Generated Videos:")

    if 'video_id' not in st.session_state or st.session_state.video_id != video_id:
        if video_id not in st.session_state.clicked_video_ids:
            st.session_state.clicked_video_ids.add(video_id)

        st.session_state.clicked_video_count += 1
        
        video_list = [(model, osp.join(VIDEO_ROOT, model+"_newtest", "step-8000", f"{video_id:03d}-00.mp4")) for model in MODEL_LIST]

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
    
    st.markdown(f"#### Criteria - `{CRITERIA[criteria_id][0]}`:")
    st.markdown(f"{CRITERIA[criteria_id][1]}")
    st.caption(CRITERIA[criteria_id][2])
        
    rankings = {}
    cols = st.columns(4)
    for i, mark in enumerate(marks):
        with cols[i]:
            rankings[mark] = st.pills(f"Video {mark}", options=[1, 2, 3, 4], default=None, key=f"rank_{mark}")
    
    st.divider()
    if None in rankings.values():
        st.markdown(f"🚀 Assign ranks to the videos by selecting a rank for **each one** that aligns with the criteria explained above. ‼️ Please note that a *higher rank* corresponds to a *smaller number* .")
        return None

    elif set(rankings.values()) != {1, 2, 3, 4}:
        st.warning(f"Each rank must be unique")
        return None
    
    else:
        sorted_marks = sorted(rankings, key=lambda x: rankings[x])
        rankings = get_rankings([video_list[a][0] for a in sorted_marks])
        st.markdown(f"You sorted: {' ➡️ '.join(sorted_marks)}")
        if DEBUG_MODE:
            st.write(" > ".join([video_list[a][0] for a in sorted_marks]))
        return list(rankings.values())

def fetch_batches(version):
    batches = {k:[] for k in range(10)}
    for criteria in range(3):
        batch_index = criteria
        for video_index in range(NUM_PROMPTS):
            batch_index = (batch_index) % 5
            batches[batch_index].append((video_index, criteria))
            batch_index += 1
    
    for criteria in range(3):
        batch_index = criteria
        for video_index in range(NUM_PROMPTS):
            batch_index = (batch_index) % 5
            batches[batch_index+5].append((video_index, criteria+3))
            batch_index += 1

    for batch_idx, batch in batches.items():
        batches[batch_idx] = sorted(batch)

    return batches.get(version, [])
