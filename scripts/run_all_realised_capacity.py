import datetime
import glob
import os
import sys
import time

from maheu_group_project.heuristics.solver import SolverType, solve_deterministically_and_return_data, \
    solve_real_time_and_return_data
from maheu_group_project.solution.metrics import get_pretty_metrics

from maheu_group_project.solution.verifying import verify_solution

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from maheu_group_project.solution.evaluate import objective_function

# This is the solver to be used/tested
SOLVERS: list[SolverType] = [ SolverType.GREEDY ]
DETERMINISTIC = True
DATASETS = [ "CaseMaHeu25_02"]


def run_on_all_data_from_first_dataset():
    for solver in SOLVERS:
        results_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
        os.makedirs(results_dir, exist_ok=True)
        current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        for dataset_dir in DATASETS:
            with open(os.path.join(results_dir, f"{current_time}_{dataset_dir}_{solver}_result.txt"), 'w') as result_file:
                with open(os.path.join(results_dir, f"{current_time}_{dataset_dir}_{solver}_result_pretty.txt"),
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

                        # Write the results to the files
                        output = f"Cost of solution for {dataset_dir}/{os.path.basename(file)}: {cost:.2f} \n"
                        if number_of_vehicles_that_did_not_arrived != 0:
                            output += f"Number of vehicles that did not arrive: {number_of_vehicles_that_did_not_arrived} \n"
                        result_file.write(output)
                        if number_of_vehicles_that_did_not_arrived == 0:
                            output += f"Number of vehicles that did not arrive: {number_of_vehicles_that_did_not_arrived} \n"
                        metrics = get_pretty_metrics(trucks_realised, truck_assignments, vehicle_assignments)
                        output += metrics + "\n" + f"Running time in seconds: {end_time:.2f}" + "\n" + "\n"
                        pretty_result_file.write(output)
                        print(output)


if __name__ == '__main__':
    run_on_all_data_from_first_dataset()
