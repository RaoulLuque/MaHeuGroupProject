import argparse
import datetime
import glob
import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from maheu_group_project.heuristics.solver import SolverType, solve_deterministically_and_return_data, \
    solve_real_time_and_return_data, solver_type_from_string
from maheu_group_project.solution.metrics import get_pretty_metrics
from maheu_group_project.solution.verifying import verify_solution
from maheu_group_project.solution.evaluate import objective_function

# This is the default configuration of the script. It can be overridden by command line arguments.
SOLVERS: list[SolverType] = [SolverType.FLOW]
DETERMINISTIC = True
DATASET_INDICES = [1, 2, 3, 4]


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
            with open(os.path.join(results_dir, result_filename + "_result.txt"), 'w') as result_file:
                with open(os.path.join(results_dir, result_filename + "_running_time.txt"), 'w') as running_time_file:
                    with open(os.path.join(results_dir, result_filename + "_result_pretty.txt"),
                              'w') as pretty_result_file:
                        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', dataset_dir))
                        pattern = os.path.join(data_dir, 'realised_capacity_data_*.csv')
                        files = sorted(glob.glob(pattern))
                        for file in files:
                            start_time = time.time()
                            # Get solutions from the solver
                            if DETERMINISTIC:
                                vehicle_assignments, truck_assignments, _, vehicles, trucks_realised, _ = solve_deterministically_and_return_data(
                                    solver,
                                    dataset_dir,
                                    os.path.basename(file)
                                )
                            else:
                                vehicle_assignments, truck_assignments, _, vehicles, trucks_realised, _ = solve_real_time_and_return_data(
                                    solver,
                                    dataset_dir,
                                    os.path.basename(file)
                                )
                            end_time = time.time() - start_time

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
                            result_file.write(output)

                            running_time_output = f"Running time for {dataset_dir}/{os.path.basename(file)}: {running_time} \n"
                            running_time_file.write(running_time_output)

                            # And then to the pretty result file
                            if number_of_vehicles_that_did_not_arrived == 0:
                                output += "Number of vehicles that did not arrive: 0 \n"
                            output += f"Solver: {solver.name} \n"
                            metrics = get_pretty_metrics(trucks_realised, truck_assignments, vehicle_assignments)
                            output += metrics + "\n" + f"Running time in seconds: {running_time}" + "\n" + "\n"
                            pretty_result_file.write(output)
                            print(output)


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
    return parser.parse_args()


def main():
    args = parse_args()
    global SOLVERS, DETERMINISTIC, DATASET_INDICES
    if args.solvers is not None:
        SOLVERS = [solver_type_from_string(string_input.upper()) for string_input in args.solvers]
    if args.deterministic is not None:
        DETERMINISTIC = args.deterministic.lower() == 'true'
    if args.dataset_indices is not None:
        DATASET_INDICES = args.dataset_indices
    run_on_all_data_from_first_dataset()


if __name__ == '__main__':
    main()
