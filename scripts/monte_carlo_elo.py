import math
import random
import sqlite3
import statistics
from collections import defaultdict


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
        WHERE ep.status = 'completed' and e.deleted_at IS NULL
        """
    )
    rows = c.fetchall()
    column_names = [desc[0] for desc in c.description]

    conn.close()

    return rows, column_names


def percentile(data, p):
    """Calculate the specified percentile of a list of numbers."""
    data_sorted = sorted(data)
    k = (len(data_sorted) - 1) * (p / 100)
    f = math.floor(k)
    c = math.ceil(k)

    if f == c:
        return data_sorted[int(k)]

    d0 = data_sorted[int(f)] * (c - k)
    d1 = data_sorted[int(c)] * (k - f)
    return d0 + d1


def calculate_monte_carlo_elo(
    battles, num_simulations=1000, initial_elo=1500, k_factor=32
):
    """
    Calculate Elo scores using Monte Carlo simulation.

    Args:
        battles (list): List of tuples (model_a, model_b, outcome) where outcome is 0 (model_a won),
                        1 (tie), or 2 (model_b won)
        num_simulations (int): Number of Monte Carlo simulations to run
        initial_elo (int): Initial Elo rating for all models
        k_factor (int): K-factor for Elo calculation

    Returns:
        dict: Dictionary mapping model names to their final Elo scores
    """
    # Get unique models
    models = set()
    for model_a, model_b, _ in battles:
        models.add(model_a)
        models.add(model_b)

    # Initialize results dictionary to store all simulation results
    all_results = {model: [] for model in models}

    # Run Monte Carlo simulations
    for _ in range(num_simulations):
        # Shuffle the battles to randomize the order
        shuffled_battles = battles.copy()
        random.shuffle(shuffled_battles)

        # Initialize Elo ratings
        elo_ratings = {model: initial_elo for model in models}

        # Process each battle
        for model_a, model_b, outcome in shuffled_battles:
            # Calculate expected scores
            rating_a = elo_ratings[model_a]
            rating_b = elo_ratings[model_b]

            # Expected score using the Elo formula
            expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
            expected_b = 1 / (1 + 10 ** ((rating_a - rating_b) / 400))

            # Calculate actual scores based on outcome
            if outcome == 0:  # model_a won
                actual_a = 1
                actual_b = 0
            elif outcome == 1:  # tie
                actual_a = 0.5
                actual_b = 0.5
            else:  # model_b won
                actual_a = 0
                actual_b = 1

            # Update Elo ratings
            elo_ratings[model_a] += k_factor * (actual_a - expected_a)
            elo_ratings[model_b] += k_factor * (actual_b - expected_b)

        # Store the results of this simulation
        for model in models:
            all_results[model].append(elo_ratings[model])

    # Calculate mean Elo ratings across all simulations
    final_elo = {
        model: statistics.mean(scores) for model, scores in all_results.items()
    }

    # Calculate confidence intervals (95%)
    confidence_intervals = {
        model: (percentile(scores, 2.5), percentile(scores, 97.5))
        for model, scores in all_results.items()
    }

    return final_elo, confidence_intervals


def get_criteria_name(criteria_id):
    """Get the name of a criteria by its ID from the predefined mapping."""
    criteria_mapping = {
        0: "Text Following",
        1: "Motion Smoothness",
        2: "Aesthetics",
        3: "Scene Consistency",
    }

    return criteria_mapping.get(criteria_id, f"Unknown Criteria ({criteria_id})")


def main(db_path):
    """Calculate and return Monte Carlo Elo scores for all criteria."""
    print("Fetching data from database...")
    # Fetch evaluation data
    rows, column_names = fetch_completed_responses(db_path)

    # Convert rows to a more usable format
    data = []
    for row in rows:
        data_row = {}
        for i, col_name in enumerate(column_names):
            data_row[col_name] = row[i]
        data.append(data_row)

    # Group battles by criteria
    criteria_battles = defaultdict(list)

    print("Processing battles by criteria...")
    for row in data:
        criteria_id = row["criteria_id"]
        left_model = row["left_model"]
        right_model = row["right_model"]
        rating = row["rating"]

        # Add to the appropriate criteria group
        criteria_battles[criteria_id].append((left_model, right_model, rating))

    # Calculate Elo scores for each criteria
    results = {}

    print("Running Monte Carlo simulations for each criteria...")
    for criteria_id, battles in criteria_battles.items():
        if len(battles) >= 10:  # Only calculate if we have enough data
            criteria_name = get_criteria_name(criteria_id)
            print(f"  - Processing {criteria_name} ({len(battles)} battles)...")
            elo_scores, confidence_intervals = calculate_monte_carlo_elo(battles)
            results[criteria_name] = (elo_scores, confidence_intervals)

    return results


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Calculate Monte Carlo Elo scores for models grouped by criteria."
    )
    parser.add_argument("--db_path", type=str, help="Path to the SQLite database file.")

    args = parser.parse_args()

    try:
        results = main(args.db_path)

        # Print the results in a clean tabular format
        print("\nMonte Carlo Elo Scores by Criteria")
        print("=====================================")

        # Sort criteria in the predefined order
        criteria_order = [
            "Text Following",
            "Motion Smoothness",
            "Aesthetics",
            "Scene Consistency",
        ]
        sorted_criteria = sorted(
            results.items(),
            key=lambda x: criteria_order.index(x[0]) if x[0] in criteria_order else 999,
        )

        for criteria_name, (elo_scores, confidence_intervals) in sorted_criteria:
            print(f"\n{criteria_name}")
            print("-" * 50)

            # Sort models by Elo score
            sorted_models = sorted(elo_scores.items(), key=lambda x: x[1], reverse=True)

            # Find the longest model name for alignment
            max_name_length = max(len(model) for model, _ in sorted_models)

            # Formatted table header
            print(
                f"{'Model':<{max_name_length+2}}{'Score':>8}  {'95% Confidence Interval':>25}"
            )
            print("-" * 50)

            # Print each model with its score and confidence interval
            for model, score in sorted_models:
                lower, upper = confidence_intervals[model]
                print(
                    f"{model:<{max_name_length+2}}{score:>8.1f}  {lower:>10.1f} - {upper:<10.1f}"
                )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
