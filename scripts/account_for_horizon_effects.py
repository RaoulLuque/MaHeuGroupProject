#!/usr/bin/env python3
"""
Script to process vehicle and truck assignment data and account for horizon effects.
This script reads serialized vehicle and truck assignments, applies horizon removal,
and calculates objective function values for the processed data.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Add the src directory to the Python path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from maheu_group_project.serialization import deserialize_vehicle_assignments, deserialize_truck_assignments
from maheu_group_project.solution.evaluate import remove_horizon, objective_function
from maheu_group_project.parsing import read_data

# Configuration
TARGET_DIR = "final_q_0_5"

# Number of days to consider for the horizon effect
NUM_DAYS_FOR_HORIZON = 7

# Number of realizations to process
NUM_REALIZATIONS = 10


def process_case_data(case_num: str, heuristic_name: str, data_type: str,
                     source_dir: Path, output_dir: Path) -> None:
    """
    Process a single case's vehicle and truck assignment data for multiple realizations.

    Args:
        case_num: Case number (e.g., "01", "02", etc.)
        heuristic_name: Name of the heuristic used
        data_type: Either "deterministic" or "real_time"
        source_dir: Source directory containing the data files
        output_dir: Output directory for processed results
    """
    # Define result file path to check if the case exists
    result_file = source_dir / f"Case_{case_num}_{data_type}_{heuristic_name}_result.txt"

    # Check if result file exists
    if not result_file.exists():
        print(f"Warning: Result file not found: {result_file}")
        return

    # Check if the realization directory exists
    realization_dir = source_dir / f"Case_{case_num}_{data_type}_{heuristic_name}"
    if not realization_dir.exists():
        print(f"Warning: Realization directory not found: {realization_dir}")
        return

    print(f"Processing Case {case_num} - {heuristic_name} ({data_type})")

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    horizon_output_file = output_dir / f"Case_{case_num}_{data_type}_{heuristic_name}_horizon.txt"
    output_file = output_dir / f"Case_{case_num}_{data_type}_{heuristic_name}_result.txt"
    open(output_file, 'w').close()

    # Open the output file to store all realization results
    with open(horizon_output_file, 'w') as f:
        f.write(f"Case {case_num} - {heuristic_name} ({data_type})\n")
        f.write(f"Horizon removal with front_horizon={NUM_DAYS_FOR_HORIZON} days\n\n")

        # Process each realization
        for realization in range(1, NUM_REALIZATIONS + 1):
            realization_num = f"{realization:03d}"

            # Define the vehicles and trucks file paths for this realization
            vehicles_file = realization_dir / f"realised_capacity_data_{realization_num}_vehicles.json"
            trucks_file = realization_dir / f"realised_capacity_data_{realization_num}_trucks.json"

            if not vehicles_file.exists() or not trucks_file.exists():
                print(f"  -> Skipping realization {realization_num}: Files not found")
                f.write(f"Realization {realization_num}: Files not found\n")
                continue

            # Deserialize vehicle and truck assignments
            vehicle_assignments = deserialize_vehicle_assignments(str(vehicles_file))
            truck_assignments = deserialize_truck_assignments(str(trucks_file))

            # Load actual data for this realization
            dataset_dir_name = f"CaseMaHeu25_{case_num}"
            realised_capacity_file_name = f"realised_capacity_data_{realization_num}.csv"

            # Read the actual data
            _, vehicles, trucks_realised, trucks_planned = read_data(dataset_dir_name, realised_capacity_file_name)

            original_objective_value = objective_function(
                vehicle_assignments=vehicle_assignments,
                truck_assignments=truck_assignments,
                trucks=trucks_realised,
            )

            # Apply horizon removal
            filtered_vehicles, filtered_trucks = remove_horizon(
                vehicle_assignments=vehicle_assignments,
                vehicles=vehicles,  # Using actual vehicles data
                truck_assignments=truck_assignments,
                trucks_realised=trucks_realised,
                trucks_planned=trucks_planned,
                front_horizon=NUM_DAYS_FOR_HORIZON,
                back_horizon=NUM_DAYS_FOR_HORIZON
            )

            # Calculate objective function
            all_trucks = {**trucks_realised, **trucks_planned}
            objective_value = objective_function(
                vehicle_assignments=filtered_vehicles,
                truck_assignments=filtered_trucks,
                trucks=all_trucks
            )

            # Write results for this realization
            f.write(f"Realization {realization_num}:\n")
            f.write(f"  Original vehicles: {len(vehicle_assignments)}\n")
            f.write(f"  Filtered vehicles: {len(filtered_vehicles)}\n")
            f.write(f"  Original trucks: {len(truck_assignments)}\n")
            f.write(f"  Filtered trucks: {len(filtered_trucks)}\n")
            f.write(f"  Original objective value: {original_objective_value:.2f}\n")
            f.write(f"  Objective value after horizon removal: {objective_value:.2f}\n\n")

            with open(output_file, 'a') as result_file:
                output = f"Cost of solution for {dataset_dir_name}/{realised_capacity_file_name}: {objective_value:.2f} \n"
                result_file.write(output)

    print(f"  -> Saved all realization results to: {horizon_output_file}")


def extract_heuristic_names(directory: Path) -> list[str]:
    """
    Extract unique heuristic names from the files in a directory.
    """
    heuristics = set()

    for file in directory.glob("Case_*_result.txt"):
        # Parse filename to extract heuristic name
        parts = file.stem.split('_')
        if len(parts) >= 4:
            # Expected format: Case_DD_deterministic_HEURISTIC_NAME_result.txt
            # or Case_DD_real_time_HEURISTIC_NAME_result.txt

            # Find the position where the heuristic name starts
            if "deterministic" in parts:
                deterministic_idx = parts.index("deterministic")
                heuristic_start = deterministic_idx + 1
            elif "real" in parts and "time" in parts:
                # Handle real_time case
                real_idx = parts.index("real")
                if real_idx + 1 < len(parts) and parts[real_idx + 1] == "time":
                    heuristic_start = real_idx + 2
                else:
                    continue  # Skip if format is unexpected
            else:
                continue  # Skip if format is unexpected

            # Extract heuristic name parts (everything between data_type and "result")
            heuristic_parts = parts[heuristic_start:-1]  # Exclude "result"
            if heuristic_parts:  # Only add if we have a heuristic name
                heuristic_name = '_'.join(heuristic_parts)
                heuristics.add(heuristic_name)

    return sorted(list(heuristics))


def main():
    """
    Main function to process all cases and heuristics.
    """
    # Define paths
    base_dir = Path(__file__).parent.parent
    source_base_dir = base_dir / "results" / "notable" / TARGET_DIR
    output_base_dir = base_dir / "results" / "notable" / f"{TARGET_DIR}_horizon"

    # Process both deterministic and real_time subdirectories
    for data_type in ["deterministic", "real_time"]:
        source_dir = source_base_dir / data_type
        output_dir = output_base_dir / data_type

        if not source_dir.exists():
            print(f"Warning: Source directory not found: {source_dir}")
            continue

        print(f"\nProcessing {data_type} data...")

        # Extract heuristic names from the directory
        heuristic_names = extract_heuristic_names(source_dir)

        if not heuristic_names:
            print(f"No heuristics found in {source_dir}")
            continue

        print(f"Found heuristics: {heuristic_names}")

        # Process each case (01-04) and each heuristic
        for case_num in ["01", "02", "03", "04"]:
            for heuristic_name in heuristic_names:
                process_case_data(case_num, heuristic_name, data_type, source_dir, output_dir)

    print(f"\nProcessing complete. Results saved to: {output_base_dir}")


if __name__ == "__main__":
    main()
