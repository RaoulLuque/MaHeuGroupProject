import datetime
import glob
import os
import sys

from maheu_group_project.heuristics.solver import SolverType, solve_and_return_data
from maheu_group_project.solution.metrics import get_pretty_metrics

from maheu_group_project.solution.verifying import verify_solution

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from maheu_group_project.solution.evaluate import objective_function

# This is the solver to be used/tested
SOLVER = SolverType.FLOW


def run_on_all_data_from_first_dataset():
    results_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
    os.makedirs(results_dir, exist_ok=True)
    current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    with open(os.path.join(results_dir, f"{current_time}_result.txt"), 'w') as result_file:
        with open(os.path.join(results_dir, f"{current_time}_result_pretty.txt"), 'w') as pretty_result_file:
            dataset_dir = "CaseMaHeu25_01"
            data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', dataset_dir))
            pattern = os.path.join(data_dir, 'realised_capacity_data_*.csv')
            files = sorted(glob.glob(pattern))
            for file in files:
                vehicle_assignments, truck_assignments, _, vehicles, trucks_realised, _ = solve_and_return_data(SOLVER,
                                                                                                                dataset_dir,
                                                                                                                os.path.basename(
                                                                                                                    file))
                is_valid = verify_solution(vehicles, vehicle_assignments, trucks_realised, truck_assignments)
                assert is_valid, "The solution is invalid"
                cost = objective_function(vehicle_assignments, truck_assignments, trucks_realised)
                output = f"Cost of solution for {dataset_dir}/{os.path.basename(file)}: {cost:.2f} \n"
                result_file.write(output)
                metrics = get_pretty_metrics(trucks_realised, truck_assignments, vehicle_assignments)
                output += metrics + "\n" + "\n"
                pretty_result_file.write(output)
                print(output)


if __name__ == '__main__':
    run_on_all_data_from_first_dataset()
