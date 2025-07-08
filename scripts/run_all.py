import argparse
import datetime
import glob
import os
import sys

from maheu_group_project.serialization import serialize_truck_assignments, serialize_vehicle_assignments

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from maheu_group_project.heuristics.solver import SolverType, solve_deterministically_and_return_data, \
    solve_real_time_and_return_data, solver_type_from_string
from maheu_group_project.solution.metrics import get_pretty_metrics
from maheu_group_project.solution.verifying import verify_solution
from maheu_group_project.solution.evaluate import objective_function

# This is the default configuration of the script. It can be overridden by command line arguments.
SOLVERS: list[SolverType] = [SolverType.GREEDY, SolverType.GREEDY_CANDIDATE_PATHS, SolverType.FLOW]
DETERMINISTIC = False
DATASET_INDICES = [1, 2, 3, 4]
QUANTILE_VALUE = 0.4


def run_on_all_data_from_first_dataset():
    for solver in SOLVERS:
        results_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
        os.makedirs(results_dir, exist_ok=True)
        current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        deterministic_name_tag = "deterministic" if DETERMINISTIC else "real_time"
        results_dir = os.path.join(results_dir, deterministic_name_tag)
        os.makedirs(results_dir, exist_ok=True)
        for dataset_index in DATASET_INDICES:
            dataset_dir = f"CaseMaHeu25_0{dataset_index}"
            result_filename = f"{current_time}_Case_0{dataset_index}_{deterministic_name_tag}_{solver}"

            # Define file paths
            result_file_path = os.path.join(results_dir, result_filename + "_result.txt")
            running_time_file_path = os.path.join(results_dir, result_filename + "_running_time.txt")
            pretty_result_file_path = os.path.join(results_dir, result_filename + "_result_pretty.txt")
            serialized_data_dir_path = os.path.join(results_dir, result_filename)

            # Create empty files initially
            open(result_file_path, 'w').close()
            open(running_time_file_path, 'w').close()
            open(pretty_result_file_path, 'w').close()

            # Create folder for serialized data if it does not exist
            os.makedirs(serialized_data_dir_path, exist_ok=True)

            # Store configuration file
            config_filename = f"{current_time}_config.txt"
            config_file_path = os.path.join(results_dir, config_filename)
            with open(config_file_path, 'w') as config_file:
                config_file.write(f"SOLVERS: {[str(s) for s in SOLVERS]}\n")
                config_file.write(f"DETERMINISTIC: {DETERMINISTIC}\n")
                config_file.write(f"DATASET_INDICES: {DATASET_INDICES}\n")
                config_file.write(f"QUANTILE_VALUE: {QUANTILE_VALUE}\n")

            data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', dataset_dir))
            pattern = os.path.join(data_dir, 'realised_capacity_data_*.csv')
            files = sorted(glob.glob(pattern))
            for file in files:
                # Get solutions from the solver
                if DETERMINISTIC:
                    vehicle_assignments, truck_assignments, _, vehicles, trucks_realised, _, end_time = solve_deterministically_and_return_data(
                        solver,
                        dataset_dir,
                        os.path.basename(file)
                    )
                else:
                    vehicle_assignments, truck_assignments, _, vehicles, trucks_realised, _, end_time = solve_real_time_and_return_data(
                        solver_type=solver,
                        dataset_dir_name=dataset_dir,
                        realised_capacity_file_name=os.path.basename(file),
                        quantile=QUANTILE_VALUE,
                    )

                # Verify the solution
                is_valid = verify_solution(vehicles, vehicle_assignments, trucks_realised, truck_assignments)
                number_of_vehicles_that_did_not_arrived = 0
                match is_valid:
                    case bool():
                        assert is_valid, "The solution is invalid"
                    case int():
                        number_of_vehicles_that_did_not_arrived = is_valid
                    case _:
                        raise TypeError(f"Unexpected type of is_valid: {type(is_valid)}")

                # Compute the cost of the solution
                cost = objective_function(vehicle_assignments, truck_assignments, trucks_realised)
                running_time = f"{end_time:.2f}"

                # Write the results to the files
                # First to individual files
                output = f"Cost of solution for {dataset_dir}/{os.path.basename(file)}: {cost:.2f} \n"
                if number_of_vehicles_that_did_not_arrived != 0:
                    output += f"Number of vehicles that did not arrive: {number_of_vehicles_that_did_not_arrived} \n"

                with open(result_file_path, 'a') as result_file:
                    result_file.write(output)

                running_time_output = f"Running time for {dataset_dir}/{os.path.basename(file)}: {running_time} \n"
                with open(running_time_file_path, 'a') as running_time_file:
                    running_time_file.write(running_time_output)

                # And then to the pretty result file
                if number_of_vehicles_that_did_not_arrived == 0:
                    output += "Number of vehicles that did not arrive: 0 \n"
                output += f"Solver: {solver.name} \n"
                metrics = get_pretty_metrics(trucks_realised, truck_assignments, vehicle_assignments)
                output += metrics + "\n" + f"Running time in seconds: {running_time}" + "\n" + "\n"

                with open(pretty_result_file_path, 'a') as pretty_result_file:
                    pretty_result_file.write(output)
                print(output)

                # Serialize the results to JSON
                base_name = os.path.splitext(os.path.basename(file))[0]
                vehicles_serialized_file_path = os.path.join(serialized_data_dir_path, f"{base_name}_vehicles.json")
                trucks_serialized_file_path = os.path.join(serialized_data_dir_path, f"{base_name}_trucks.json")
                serialize_vehicle_assignments(vehicle_assignments, vehicles_serialized_file_path)
                serialize_truck_assignments(truck_assignments, trucks_serialized_file_path)


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments into an argparse.Namespace object.

    Returns:
        argparse.Namespace: Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(description="Run all realised capacity experiments.")
    parser.add_argument('--solvers', nargs='+', type=str, default=None, help='List of solvers (by name) to use')
    parser.add_argument('--deterministic', type=str, choices=['true', 'false', 'TRUE', 'FALSE'], default=None, help='Use deterministic mode (true/false)')
    parser.add_argument('--dataset_indices', nargs='+', type=int, default=None, help='List of dataset indices to use')
    parser.add_argument('--quantile_value', type=float, default=None, help='Quantile value to use for the solver')
    return parser.parse_args()


def main():
    args = parse_args()
    global SOLVERS, DETERMINISTIC, DATASET_INDICES, QUANTILE_VALUE
    if args.solvers is not None:
        SOLVERS = [solver_type_from_string(string_input.upper()) for string_input in args.solvers]
    if args.deterministic is not None:
        DETERMINISTIC = args.deterministic.lower() == 'true'
    if args.dataset_indices is not None:
        DATASET_INDICES = args.dataset_indices
    if args.quantile_value is not None:
        QUANTILE_VALUE = args.quantile_value
    run_on_all_data_from_first_dataset()


if __name__ == '__main__':
    main()
