import datetime
import glob
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from maheu_group_project.solution.evaluate import objective_function
from maheu_group_project.parsing import read_data
from maheu_group_project.heuristics.flow.solve import solve_as_flow


def run_on_all_data_from_first_dataset():
    results_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
    os.makedirs(results_dir, exist_ok=True)
    current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    with open(os.path.join(results_dir, f"{current_time}_result.txt"), 'w') as result_file:
        dataset_dir = "CaseMaHeu25_01"
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', dataset_dir))
        pattern = os.path.join(data_dir, 'realised_capacity_data_*.csv')
        files = sorted(glob.glob(pattern))
        for file in files:
            file = os.path.join(dataset_dir, file)
            locations, vehicles, trucks = read_data(realised_capacity_file_name=file)
            vehicle_assignment, truck_assignment = solve_as_flow(vehicles, trucks, locations)
            cost = objective_function(vehicle_assignment, truck_assignment, trucks)
            output = f"Cost of solution for {os.path.basename(file)}: {cost:.2f} \n"
            result_file.write(output)
            print(output)


if __name__ == '__main__':
    run_on_all_data_from_first_dataset()
