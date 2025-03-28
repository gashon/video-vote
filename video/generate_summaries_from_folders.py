import glob
import json
import os
import time

import requests

SYSTEM_PROMPT = """Generate a straightforward 1-2 sentence summary of the following video prompt. 

Capture all intricate details visible in the scene, including:
- Subtle character actions (facial expressions, hand gestures, sticking out tongues)
- Background elements and environmental conditions
- Clothing details and accessories
- Object positioning and orientation
- Color schemes and lighting
- Fleeting movements or micro-expressions
- Any text or symbols visible in the scene

Do not use phrases like 'In this video' or 'The video shows'; instead, present the information as a comprehensive scene description. 

Focus on capturing the main narrative. The reader should have a clear understanding of the scene and its context.

Do not refer to Tom as a blue gray cat, only use his name. Likewise for Jerry, the brown mouse.

You should have a MAXIMUM OF 1-2 *SHORT* SENTENCES. If you find it impossible to include all details in one sentence, you may use two, but no more.
"""


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


def process_prompts(base_prefix, directories, api_key):
    """
    Process all prompts and write the summaries to all directories
    """
    # Use the first directory to find all prompt numbers
    first_dir = os.path.join(base_prefix, directories[0])
    prompt_dirs = glob.glob(os.path.join(first_dir, "prompt-*"))
    prompt_numbers = [os.path.basename(p) for p in prompt_dirs]

    total_prompts = len(prompt_numbers)
    print(f"Found {total_prompts} prompts to process")

    for i, prompt_number in enumerate(
        sorted(prompt_numbers, key=lambda x: int(x.split("-")[1]))
    ):
        print(f"\nProcessing [{i+1}/{total_prompts}]: {prompt_number}")

        # Read the prompt from the first directory
        prompt_path = os.path.join(
            base_prefix, directories[0], prompt_number, "prompt.txt"
        )

        if not os.path.exists(prompt_path):
            print(f"Warning: Prompt file not found at {prompt_path}")
            continue

        try:
            # Read the prompt
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_text = f.read().strip()

            # Check if we've already processed this prompt (check any directory)
            summary_path = os.path.join(
                base_prefix, directories[0], prompt_number, "summary.txt"
            )
            if os.path.exists(summary_path):
                print(f"Reading existing summary from {summary_path}")
                with open(summary_path, "r", encoding="utf-8") as f:
                    summary = f.read().strip()
            else:
                # Generate summary once
                print(f"Generating summary for {prompt_number}")
                summary = generate_summary(prompt_text, api_key)

                if not summary:
                    print(f"Failed to generate summary for {prompt_number}")
                    continue

                # Add delay to avoid rate limiting
                time.sleep(1)

            # Write the same summary to all directories
            for directory in directories:
                target_dir = os.path.join(base_prefix, directory, prompt_number)

                # Ensure the directory exists
                if not os.path.exists(target_dir):
                    print(f"Warning: Directory not found: {target_dir}")
                    continue

                summary_file = os.path.join(target_dir, "summary.txt")

                with open(summary_file, "w", encoding="utf-8") as f:
                    f.write(summary)

                print(f"Saved summary to {summary_file}")

        except Exception as e:
            print(f"Error processing {prompt_number}: {e}")

    print("\nProcessing complete!")


if __name__ == "__main__":
    # Replace with your Claude API key
    API_KEY = os.environ["ANTHROPIC_API_KEY"]

    # Base directory prefix
    BASE_PREFIX = "63sec"

    # All directories to process
    DIRECTORIES = [
        "sliding-window",
        "ttt-mlp",
        "deltanet",
        "mamba",
    ]

    # Process all prompts and write summaries to all directories
    process_prompts(BASE_PREFIX, DIRECTORIES, API_KEY)
