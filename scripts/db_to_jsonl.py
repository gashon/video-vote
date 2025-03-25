import argparse
import json
import os
import os.path as osp
import sqlite3


def fetch_completed_responses(db_path):
    """
    Fetch all completed evaluations with their corresponding metadata.

    Args:
        db_path (str): Path to the SQLite database file

    Returns:
        tuple: (rows, column_names) - fetched data and column names
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        """SELECT 
            e.id, e.evaluation_pool_id, e.user_id, e.current_index, 
            e.left_model, e.right_model, e.rating, e.review_duration, 
            e.clicked_video_count, e.clicked_video_unrepeated_count, e.created_at,
            ep.id AS pool_id, ep.prompt_id, ep.criteria_id, ep.turn_id, ep.combo_id, 
            ep.user_id AS pool_user_id, ep.status, ep.assigned_at, ep.created_at AS pool_created_at
        FROM evaluations e
        JOIN evaluation_pool ep ON e.evaluation_pool_id = ep.id
        WHERE ep.status = 'completed'"""
    )
    rows = c.fetchall()
    column_names = [desc[0] for desc in c.description]

    conn.close()

    return rows, column_names


def save_as_jsonl(rows, column_names, output_path):
    """
    Save the fetched data as a JSONL file with each evaluation on a new line.

    Args:
        rows (list): List of tuples containing the evaluation data
        column_names (list): List of column names
        output_path (str): Path to save the JSONL file
    """
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        for row in rows:
            # Create a dictionary for each row
            evaluation = {column_names[i]: value for i, value in enumerate(row)}
            # Write each evaluation as a JSON object on a new line
            f.write(json.dumps(evaluation) + "\n")

    print(f"Successfully wrote {len(rows)} evaluations to {output_path}")


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Fetch completed evaluations and export to JSONL"
    )
    parser.add_argument(
        "--db_path", required=True, help="Path to the SQLite database file"
    )
    parser.add_argument(
        "--output_file", required=True, help="Path to save the output JSONL file"
    )

    # Parse arguments
    args = parser.parse_args()

    # Fetch the data
    rows, column_names = fetch_completed_responses(args.db_path)

    # Save as JSONL
    save_as_jsonl(rows, column_names, args.output_file)


if __name__ == "__main__":
    main()
