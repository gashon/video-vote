import streamlit as st
from streamlit_sortables import sort_items
import random
import os.path as osp
from batch_manager import NUM_PROMPTS_PER_GROUP

VIDEO_LENGTH = 9
VIDEO_ROOT = "video/3sec"
DEBUG_MODE = True if osp.exists("/home/yusu/new_home/code/y/video-vote") else False
MODEL_LIST = ["attn", 'mamba2', 'm1', 'm2']
CRITERIA = {
    0: ["Text alignment",
        "Measures how closely the generated video aligns with the provided prompt, ensuring accurate representation of key elements and actions described.",
        "The content of the video not accurately reflecting the details specified in the prompt e.g. If the prompt specifies that Tom should be in the kitchen, but the video depicts him in a living room, this would represent a violation."],
    1: ["Frame Stability",
        " Assesses the stability and coherence of frames throughout the video, contributing to a smooth viewing experience.",
        "Morphing artifacts, blurred or distorted objects, or abrupt appearances or disappearances of content"],
    2: ["Motion Naturalness",
        "Reflects the fluidity and realism of motion in the generated video. It indicates the model’s understanding of real-world physics while ensuring characters and objects move naturally within the scene.",
        "Characters moving in jerky or unrealistic ways that don't reflect typical physical behavior. e.g. If Tom runs with an exaggerated, unrealistic motion that defies gravity, this would indicate poor motion naturalness."
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
        "Characters’ expressions not aligning with the actions they are portraying. e,g. If the prompt states that Jerry should look 'frightened,' but his facial expression appears neutral or confused, this would indicate a violation."
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
    st.markdown("Thank you for taking on the qualitative evaluation task. Your feedback is crucial for evaluating the quality of the generated videos. Please follow the instructions below to complete the evaluation.")
    
    st.markdown(f"You will make **{NUM_PROMPTS_PER_GROUP} comparison** evaluations by watching four {VIDEO_LENGTH}-second videos generated from the same input prompts, and then rank them based on the criterion assigned to you. Estimated time for the task is 3 hours. One criterion will be randomly selected from the following six options:")
    st.divider()
    for i, criterion in CRITERIA.items():
        st.markdown(f"{i+1}. **{criterion[0]}**: {criterion[1]}")
    st.markdown("The description of the criterion will be displayed again when you need to make a judgment, so there's no need to worry about memorizing it!")
    st.divider()

    st.markdown("First, read the prompt that generated those videos. After watching all four videos, please rank them based on the given criterion. Note that you should click a smaller number for a better video, since you are ***relatively ranking*** them rather than  scoring them. Additionally, you will NOT be able to return to the previous question, so the **[ Next ]** button serves as the submission for that set of videos. Please confirm the following:")

    checked = [False]*2
    checked[0] = st.checkbox("I am aware that marking as **smaller number** means a higher ranked, **better** video.")
    checked[1] = st.checkbox("I will be thoughtful and make my best judgment before making any decisions.")

    st.markdown("If you are ready, click the **[ Start ]** button below to begin.")
    return all(checked)

def show_videos(vc_id):
    video_id, criteria_id = vc_id
    st.subheader(f'{st.session_state.current_index+1}/{NUM_PROMPTS_PER_GROUP}')
    st.progress(st.session_state.current_index / NUM_PROMPTS_PER_GROUP)
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
    st.caption(f"*Violation could be: {CRITERIA[criteria_id][2]}")
        
    rankings = {}
    cols = st.columns(4)
    for i, mark in enumerate(marks):
        with cols[i]:                
            rankings[mark] = st.pills(f"Video {mark}'s rank", options=[1, 2, 3, 4], key=f"vid-{video_id}-{mark}")
    
    if None in rankings.values():
        st.warning(f"‼️ Assign ranks to the videos by selecting a **rank** for **each one** that aligns with the criteria explained above.  Please note that a *higher rank* corresponds to a *smaller number* .")
        return None

    elif set(rankings.values()) != {1, 2, 3, 4}:
        st.warning(f"‼️ Each rank must be unique")
        return None
    
    else:
        sorted_marks = sorted(rankings, key=lambda x: rankings[x])
        rankings = get_rankings([video_list[a][0] for a in sorted_marks])
        st.markdown(f"💡 You ranked (best) {' -> '.join([f'`{m}`'for m in sorted_marks])} (worst) for `{CRITERIA[criteria_id][0].lower()}` criteria. If you are satisfied with your ranking, click on the **[ Next ]** button to proceed.")
        if DEBUG_MODE:
            st.write(" > ".join([video_list[a][0] for a in sorted_marks]))
        return list(rankings.values())