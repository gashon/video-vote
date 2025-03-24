import glob
import json
import os
import time

import requests

SYSTEM_PROMPT = """Generate an extremely detailed 3-4 sentence summary of the following video prompt. 

Capture all intricate and minor details visible in the scene, including:
- Subtle character actions (facial expressions, hand gestures, sticking out tongues)
- Background elements and environmental conditions
- Clothing details and accessories
- Object positioning and orientation
- Color schemes and lighting
- Fleeting movements or micro-expressions
- Any text or symbols visible in the scene

Do not use phrases like 'In this video' or 'The video shows'; instead, present the information as a comprehensive scene description. 

Every seemingly insignificant detail matters—nothing is too small to include. Balance capturing these intricate details with maintaining narrative coherence so the summary reads as both exhaustively detailed and naturally flowing.
"""

# Define tokens if needed
SCENE_START_TOKEN = ""
SCENE_END_TOKEN = ""


def parse_jsonl_prompts_from_file(
    path: str, key_prefix: str = "text_"
) -> list[list[str]]:
    import json

    prompt_list = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            assert (
                f"{key_prefix}0" in data
            ), "Only scene-scene prompts are supported with jsonl input_type"

            prompts = []
            while True:
                counter = len(prompts)
                key = f"{key_prefix}{counter}"

                if key not in data:
                    break

                prompt = data[key]
                if "scene_start" in data and data["scene_start"][counter] == True:
                    prompt = SCENE_START_TOKEN + prompt
                if "scene_end" in data and data["scene_end"][counter] == True:
                    prompt = prompt + SCENE_END_TOKEN

                prompts.append(prompt)

            prompt_list.append(prompts)

    return prompt_list


def generate_summary(prompt_text, api_key):
    """
    Generate a summary of the video prompt using Claude API
    """
    url = "https://api.anthropic.com/v1/messages"

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": "claude-3-7-sonnet-20250219",
        "max_tokens": 15000,
        "temperature": 0.7,
        "messages": [{"role": "user", "content": prompt_text}],
        "system": SYSTEM_PROMPT,
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        # Parse response
        summary = response.json()["content"][0]["text"].strip()
        return summary

    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        return None


def process_jsonl_files(base_dir, output_dir, api_key):
    """
    Process all JSONL files in the directory and generate summaries
    """
    # Get all JSONL files in the directory
    jsonl_files = glob.glob(os.path.join(base_dir, "*.jsonl"))

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    total_files = len(jsonl_files)
    print(f"Found {total_files} JSONL files to process")

    for i, jsonl_file in enumerate(sorted(jsonl_files)):
        file_basename = os.path.basename(jsonl_file)
        jsonl_index = file_basename.split("_")[-1].split(".")[
            0
        ]  # Extract index from filename

        # Create subdirectory for this JSONL file
        jsonl_dir = os.path.join(output_dir, f"jsonl_{jsonl_index}")
        os.makedirs(jsonl_dir, exist_ok=True)

        print(f"\nProcessing [{i+1}/{total_files}]: {file_basename}")

        try:
            # Parse the JSONL file
            prompt_list = parse_jsonl_prompts_from_file(jsonl_file)

            # Process each prompt sequence in the file
            for j, prompts in enumerate(prompt_list):
                print(f"  Processing prompt sequence {j+1}/{len(prompt_list)}")

                # Join all prompts into a single text
                full_prompt = "\n".join(prompts)

                # Create directory for this prompt if needed
                prompt_dir = os.path.join(jsonl_dir, f"prompt_{j}")
                os.makedirs(prompt_dir, exist_ok=True)

                # Generate path for the summary
                summary_path = os.path.join(prompt_dir, "summary.txt")

                # Check if we've already processed this prompt
                if os.path.exists(summary_path):
                    print(f"  Reading existing summary from {summary_path}")
                    with open(summary_path, "r", encoding="utf-8") as f:
                        summary = f.read().strip()
                else:
                    # Generate summary
                    print(f"  Generating summary for prompt sequence {j+1}")
                    summary = generate_summary(full_prompt, api_key)

                    if not summary:
                        print(f"  Failed to generate summary for prompt sequence {j+1}")
                        continue

                    # Write summary to file
                    with open(summary_path, "w", encoding="utf-8") as f:
                        f.write(summary)

                    print(f"  Saved summary to {summary_path}")

                    # Add delay to avoid rate limiting
                    time.sleep(1)

        except Exception as e:
            print(f"Error processing {jsonl_file}: {e}")

    print("\nProcessing complete!")


if __name__ == "__main__":
    # Replace with your Claude API key
    API_KEY = os.environ["ANTHROPIC_API_KEY"]

    # Base directory with JSONL files
    BASE_DIR = "jsonl/60sec"

    # Output directory for summaries
    OUTPUT_DIR = "generated_summaries"

    # Process all JSONL files and generate summaries
    process_jsonl_files(BASE_DIR, OUTPUT_DIR, API_KEY)
