import streamlit as st
from streamlit_sortables import sort_items
import random
import os.path as osp

NUM_PROMPTS = 15
VIDEO_ROOT = "video/3sec"
# VIDEO_ROOT = "/home/yusu/new_home/code/y/video-vote/video/3sec"
MODEL_LIST = ["attn", 'mamba2', 'm1', 'm2']
CRITERIA = {
    0: ["Text alignment", "how well a generated video aligns with the provided prompt."],
    1: ["Frame Consistency", "how well the generated video maintains the same scene across frames. Violations of frame consistency can manifest as morphing-like artifacts, blurred or distorted objects, or content that abruptly appears or disappears."],
    2: ["Motion Naturalness", "how model is capable of generating natural and realistic motion."],
    3: ["Aesthetics", "measures which of the generated videos has more interesting and compelling content, lighting, color, and camera effects"],
    4: ["Scene consistency", "measures how consistent characters are across different parts of the video. Violations can manifest as characters wearing apparel in one scene, but not in the next."],
    5: ["Amusement / Emotion", "The metric assesses “cartoon specific” emotions"]
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
    st.caption(f"Prompt id: #{video_id}")
    st.write(st.session_state.scores)
    st.divider()

    marks = ["A", "B", "C", "D"]

    if 'video_id' not in st.session_state or st.session_state.video_id != video_id:
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
            st.caption(f"Video {marks[i]} ({video[0]})")
            st.video(video[1], autoplay=True, loop=True)
    
    st.subheader(f"[{criteria_id}] {CRITERIA[criteria_id][0]}:")
    st.caption(f" {CRITERIA[criteria_id][1]}")

    if 'previous_sorted_items' not in st.session_state:
        st.session_state.previous_sorted_items = marks
    rankcols = st.columns(3)
    with rankcols[0]:
        st.markdown(r"<div style='text-align: right;'>Better</div>", unsafe_allow_html=True)
        st.markdown(r"<div style='text-align: right;'>← 👍</div>", unsafe_allow_html=True)
    with rankcols[1]:
        sorted_items = sort_items(marks)
    with rankcols[2]:
        st.markdown(r"<div style='text-align: left;'>Worse </div>", unsafe_allow_html=True)
        st.markdown(r"<div style='text-align: left;'>👎 →</div>", unsafe_allow_html=True)

    rankings = get_rankings([video_list[a][0] for a in sorted_items])
    st.write(" - ".join([video_list[a][0] for a in sorted_items]))

    ret=list(rankings.values())
    if st.session_state.previous_sorted_items == sorted_items:
        st.warning("⚠️ You have not changed the ranking. Please adjust the rankings before proceeding. Even if you want to keep the same ranking as before, you must change it first and then change it back.")
        ret.append(0)

    st.session_state.previous_sorted_items = sorted_items    
    return ret

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