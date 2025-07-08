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

from maheu_group_project.serialization import (
    deserialize_vehicle_assignments,
    deserialize_truck_assignments
)
from maheu_group_project.solution.evaluate import (
    remove_horizon,
    objective_function
)
from maheu_group_project.solution.encoding import (
    TruckIdentifier,
    TruckAssignment,
    VehicleAssignment,
    Vehicle,
    Truck
)

# Configuration
TARGET_DIR = "06_07"

# Number of days to consider for the horizon effect
NUM_DAYS_FOR_HORIZON = 7


def process_case_data(case_num: str, heuristic_name: str, data_type: str,
                     source_dir: Path, output_dir: Path) -> None:
    """
    Process a single case's vehicle and truck assignment data.

    Args:
        case_num: Case number (e.g., "01", "02", etc.)
        heuristic_name: Name of the heuristic used
        data_type: Either "deterministic" or "real_time"
        source_dir: Source directory containing the data files
        output_dir: Output directory for processed results
    """
    # Define file paths
    vehicles_file = source_dir / f"Case_{case_num}_{data_type}_{heuristic_name}_vehicles.json"
    trucks_file = source_dir / f"Case_{case_num}_{data_type}_{heuristic_name}_trucks.json"
    result_file = source_dir / f"Case_{case_num}_{data_type}_{heuristic_name}_result.txt"

    # Check if input files exist
    if not vehicles_file.exists():
        print(f"Warning: Vehicles file not found: {vehicles_file}")
        return

    if not trucks_file.exists():
        print(f"Warning: Trucks file not found: {trucks_file}")
        return

    if not result_file.exists():
        print(f"Warning: Result file not found: {result_file}")
        return

    try:
        # Deserialize vehicle and truck assignments
        print(f"Processing Case {case_num} - {heuristic_name} ({data_type})")
        vehicle_assignments = deserialize_vehicle_assignments(str(vehicles_file))
        truck_assignments = deserialize_truck_assignments(str(trucks_file))

        # For now, we'll create placeholder data for the required parameters
        # In a real implementation, you would load this data from your data files
        requested_vehicles = create_placeholder_vehicles(vehicle_assignments)
        trucks_realised = create_placeholder_trucks(truck_assignments)
        trucks_planned = {}  # Empty for now

        # Apply horizon removal
        filtered_vehicles, filtered_trucks = remove_horizon(
            vehicle_assignments=vehicle_assignments,
            requested_vehicles=requested_vehicles,
            truck_assignments=truck_assignments,
            trucks_realised=trucks_realised,
            trucks_planned=trucks_planned,
            front_horizon=0,
            back_horizon=0
        )

        # Calculate objective function
        all_trucks = {**trucks_realised, **trucks_planned}
        objective_value = objective_function(
            vehicle_assignments=filtered_vehicles,
            truck_assignments=filtered_trucks,
            trucks=all_trucks
        )

        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save results
        output_file = output_dir / f"Case_{case_num}_{data_type}_{heuristic_name}_horizon_result.txt"
        with open(output_file, 'w') as f:
            f.write(f"Case {case_num} - {heuristic_name} ({data_type})\n")
            f.write(f"Original vehicles: {len(vehicle_assignments)}\n")
            f.write(f"Filtered vehicles: {len(filtered_vehicles)}\n")
            f.write(f"Original trucks: {len(truck_assignments)}\n")
            f.write(f"Filtered trucks: {len(filtered_trucks)}\n")
            f.write(f"Objective value after horizon removal: {objective_value}\n")

        print(f"  -> Saved results to: {output_file}")

    except Exception as e:
        print(f"Error processing Case {case_num} - {heuristic_name} ({data_type}): {str(e)}")


def create_placeholder_vehicles(vehicle_assignments: List[VehicleAssignment]) -> List[Vehicle]:
    """
    Create placeholder Vehicle objects based on VehicleAssignment data.
    In a real implementation, this would load actual vehicle data.
    """
    from datetime import date
    from maheu_group_project.solution.encoding import Vehicle, Location, LocationType

    vehicles = []
    for va in vehicle_assignments:
        # Create placeholder vehicle with basic data
        vehicle = Vehicle(
            id=va.id,
            available_date=date.today(),  # Placeholder
            destination=Location("PLACEHOLDER", LocationType.DEALER),  # Placeholder
            origin=Location("PLACEHOLDER", LocationType.PLANT)  # Placeholder
        )
        vehicles.append(vehicle)

    return vehicles


def create_placeholder_trucks(truck_assignments: Dict[TruckIdentifier, TruckAssignment]) -> Dict[TruckIdentifier, Truck]:
    """
    Create placeholder Truck objects based on TruckAssignment data.
    In a real implementation, this would load actual truck data.
    """
    trucks = {}
    for truck_id, assignment in truck_assignments.items():
        # Create placeholder truck with basic data
        truck = Truck(
            start_location=truck_id.start_location,
            end_location=truck_id.end_location,
            truck_number=truck_id.truck_number,
            departure_date=truck_id.departure_date,
            capacity=10,  # Placeholder
            price=100.0   # Placeholder
        )
        trucks[truck_id] = truck

    return trucks


def extract_heuristic_names(directory: Path) -> List[str]:
    """
    Extract unique heuristic names from the files in a directory.
    """
    heuristics = set()

    for file in directory.glob("Case_*_result.txt"):
        # Parse filename to extract heuristic name
        parts = file.stem.split('_')
        if len(parts) >= 4:
            # Remove "Case", case number, data type, and "result"
            heuristic_parts = parts[3:-1]  # Everything between data_type and "result"
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
