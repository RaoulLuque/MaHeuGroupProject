# Most of the code in this file is duplicated from scripts/run_all.py, but only altered slightly to fit the needs of
# finding the best quantile value.

import argparse
import glob
import os
import sys
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from maheu_group_project.serialization import serialize_truck_assignments, serialize_vehicle_assignments

from maheu_group_project.heuristics.solver import SolverType, solve_deterministically_and_return_data, \
    solve_real_time_and_return_data, solver_type_from_string
from maheu_group_project.solution.metrics import get_pretty_metrics
from maheu_group_project.solution.verifying import verify_solution
from maheu_group_project.solution.evaluate import objective_function

# This is the default configuration of the script. It can be overridden by command line arguments.
SOLVERS: list[SolverType] = [SolverType.FLOW]#SolverType.GREEDY, SolverType.GREEDY_CANDIDATE_PATHS]#, SolverType.FLOW]
DETERMINISTIC = False  # If True, runs the deterministic solver; if False, runs the real-time solver.
DATASET_INDICES = [1, 2, 3, 4]
QUANTILE_VALUE = 0.0


def run_on_all_data_from_first_dataset():
    for solver in SOLVERS:
        results_dir = os.path.join(os.path.dirname(__file__), '..', 'results', 'notable', 'tmp', 'quantiles' , f"Quantile{QUANTILE_VALUE}")
        os.makedirs(results_dir, exist_ok=True)
        #current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        deterministic_name_tag = "deterministic" if DETERMINISTIC else "real_time"
        results_dir = os.path.join(results_dir, deterministic_name_tag)
        os.makedirs(results_dir, exist_ok=True)
        for dataset_index in DATASET_INDICES:
            dataset_dir = f"CaseMaHeu25_0{dataset_index}"
            #result_filename = f"{current_time}_Case_0{dataset_index}_{deterministic_name_tag}_{solver}"
            result_filename = f"Case_0{dataset_index}_{deterministic_name_tag}_{solver}"
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
            #config_filename = f"{current_time}_config.txt"
            config_filename = "_config.txt"
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

def run_all_for_quantiles():
    """
    Run run_on_all_data_from_first_dataset for all quantile values from 0.0 to 1.0 in steps of 0.05.
    """
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

    # Run run_on_all_data_from_first_dataset for all quantile values from 0.0 to 1.0 in steps of 0.05
    #for i in [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]:
    for i in [0.25, 0.5, 0.75, 1.0]:
        QUANTILE_VALUE = i
        run_on_all_data_from_first_dataset()



#BASE_DIR = os.path.join("..", "results", "notable", 'temp', "DATASET_INDICES_12")
#BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results", "notable", "temp", "DATASET_INDICES_12"))
BASE_DIR = r"C:\Users\julia\Uni\Master\Semester\SoSe25\MaHeu\Project\GitHub\results\notable\tmp\quantiles"
#SUBFOLDERS = ["deterministic", "real_time"]
SUBFOLDERS = ["real_time"]
RESULT_SUFFIX = "_result.txt"

# Regex to extract the cost value from a line like:
# Cost of solution for ...: 123.45
COST_LINE_REGEX = re.compile(r"(Cost of solution for [^:]+: )([\d.]+)")


def get_result_files(folder):
    result_files = {}
    for subfolder in SUBFOLDERS:
        dir_path = os.path.join(BASE_DIR, folder, subfolder)
        if not os.path.isdir(dir_path):
            print(f"Directory {dir_path} does not exist, skipping.")
            continue
        for fname in os.listdir(dir_path):
            if fname.endswith(RESULT_SUFFIX):
                result_files.setdefault(subfolder, []).append(fname)
    return result_files

def read_costs(filepath):
    costs = {}
    print(f"Parsed costs from {filepath}: {costs}")
    with open(filepath, 'r') as f:
        for line in f:
            m = COST_LINE_REGEX.search(line)
            if m:
                key = m.group(1)
                value = float(m.group(2))
                costs[key] = value
    return costs

def write_allQuantileDiffs():
    # Loop over all options of OLD and NEW
    # Loop over all pairs of elements in [Quantile0.1, Quantile0.2, ..., Quantile1.0]
    for i in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        for j in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            if j <= i:
                continue
            OLD = f"Quantile{i}"
            NEW = f"Quantile{j}"
            old_files = get_result_files(OLD)
            new_files = get_result_files(NEW)
            diff_folder = f"DIFF_old_{OLD}_new_{NEW}"
            for subfolder in SUBFOLDERS:
                
                path = os.path.join(BASE_DIR, OLD, subfolder)
                print("Checking path:", path, "Exists:", os.path.isdir(path))

                old_dir = os.path.join(BASE_DIR, OLD, subfolder)
                new_dir = os.path.join(BASE_DIR, NEW, subfolder)
                diff_dir = os.path.join(BASE_DIR, diff_folder, subfolder)
                os.makedirs(diff_dir, exist_ok=True)
                for fname in old_files.get(subfolder, []):
                    old_path = os.path.join(old_dir, fname)
                    new_path = os.path.join(new_dir, fname)
                    diff_path = os.path.join(diff_dir, fname)
                    if not os.path.exists(new_path):
                        print(f"Skipping {fname} in {subfolder}: not found in NEW")
                        continue
                    # Skip if NEW file is empty
                    if os.path.getsize(new_path) == 0:
                        print(f"Skipping {fname} in {subfolder}: NEW file is empty")
                        continue
                    old_costs = read_costs(old_path)
                    new_costs = read_costs(new_path)
                    # Write diff file
                    print(f"Writing to: {diff_path}")
                    with open(diff_path, 'w') as out:
                        with open(old_path, 'r') as oldf:
                            for line in oldf:
                                m = COST_LINE_REGEX.search(line)
                                if m:
                                    key = m.group(1)
                                    old_val = old_costs.get(key)
                                    new_val = new_costs.get(key)
                                    if old_val is not None and new_val is not None:
                                        diff_val = old_val - new_val
                                        out.write(f"{key}{diff_val:.2f}\n")
                                    else:
                                        out.write(line)
                                else:
                                    out.write(line)

    
def better_quantile_all_cases(old_quantile, new_quantile, case_files=None):
    """
    Determines if the new quantile is better than the old quantile.
    A quantile is considered better if its costs over all configurations given in case_files are lower.

    :param old_quantile: The old quantile to compare.
    :param new_quantile: The new quantile to compare against the old one.
    :return: True if the new quantile is better than the old quantile, False otherwise.
    """

    diff_folder = f"ZZZ_kannweg_DIFF_old_{old_quantile}_new_{new_quantile}"
    diff_values = []

    for subfolder in SUBFOLDERS:
        old_dir = os.path.join(BASE_DIR, old_quantile, subfolder)
        new_dir = os.path.join(BASE_DIR, new_quantile, subfolder)
        diff_dir = os.path.join(BASE_DIR, diff_folder, subfolder)
        os.makedirs(diff_dir, exist_ok=True)

        for fname in case_files:
            old_path = os.path.join(old_dir, fname)
            new_path = os.path.join(new_dir, fname)
            diff_path = os.path.join(diff_dir, fname)

            if not os.path.exists(new_path):
                print(f"Skipping {fname} in {subfolder}: not found in NEW")
                continue

            if os.path.getsize(new_path) == 0:
                print(f"Skipping {fname} in {subfolder}: NEW file is empty")
                continue

            old_costs = read_costs(old_path)
            new_costs = read_costs(new_path)

            print(f"Writing diff for {fname} to {diff_path}")
            with open(diff_path, 'w') as out, open(old_path, 'r') as oldf:
                for line in oldf:
                    m = COST_LINE_REGEX.search(line)
                    if not m:
                        continue

                    key = m.group(1)
                    old_val = old_costs.get(key)
                    new_val = new_costs.get(key)
                    if old_val is None or new_val is None:
                        continue

                    diff_val = old_val - new_val
                    diff_values.append(diff_val)
                    out.write(f"{key}\t{old_val:.2f}\t{new_val:.2f}\t{diff_val:.2f}\n")
                    print(f"  {key}: {old_val:.2f} → {new_val:.2f} diff {diff_val:.2f}")

    total_diff = sum(diff_values)
    if total_diff == 0:
        print(f"{new_quantile} is equal to {old_quantile}")
        return False

    if total_diff > 0:
        print(f"{new_quantile} is better than {old_quantile} (total diff {total_diff:.2f})")
        return True
    else:
        print(f"{old_quantile} is better than {new_quantile} (total diff {abs(total_diff):.2f})")
        return False

def best_quantile(case_files):
    """
    Finds the best quantile according to better_quantile_all_cases.
    :return: The best quantile as a string.
    """
    #quantiles = [f"Quantile{i:.1f}" for i in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]]
    #quantiles = [f"Quantile{i}" for i in [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]]
    quantiles = ["Quantile0.0", "Quantile0.25", "Quantile0.5", "Quantile0.75"]#, "Quantile1.0"]
    best_quantile = "Quantile0.0"
    for candidate in quantiles:
        if better_quantile_all_cases(best_quantile, candidate, case_files):
            best_quantile = candidate
    return best_quantile


def best_quantile_always_better_than_0(best_quantile):
    """ Checks if the best quantile is better than Quantile0.0 in every case.
    :return: True if the best quantile is always better than Quantile0.0, False otherwise.
    """
    #for i in range(1, 5):
    for i in range(2, 5):
        case_prefix = f"Case_{i:02d}"
        case_files = [
            f"{case_prefix}_real_time_GREEDY_result.txt",
            f"{case_prefix}_real_time_GREEDY_CANDIDATE_PATHS_result.txt",
            f"{case_prefix}_real_time_FLOW_result.txt"
        ]
        if better_quantile_all_cases(best_quantile, "Quantile0.0", case_files):
            print(f"Quantile0.0 is better than {best_quantile}, so it is not always better than Quantile0.0")
            return False
        
    # This point is only reached if Quantile0.0 is never better
    return True


def main():
    temp = 3
    match temp:
        case 1:
            run_all_for_quantiles()
            # "Quantile1.0" fails at Case_02 at realised data 007
        case 2:
            #write_allQuantileDiffs()
            case_files = [
                "Case_01_real_time_GREEDY_result.txt",
                "Case_02_real_time_GREEDY_result.txt",
                "Case_03_real_time_GREEDY_result.txt",
                "Case_04_real_time_GREEDY_result.txt",

                "Case_01_real_time_GREEDY_CANDIDATE_PATHS_result.txt",
                "Case_02_real_time_GREEDY_CANDIDATE_PATHS_result.txt",
                "Case_03_real_time_GREEDY_CANDIDATE_PATHS_result.txt",
                "Case_04_real_time_GREEDY_CANDIDATE_PATHS_result.txt",

                "Case_01_real_time_FLOW_result.txt",
                "Case_02_real_time_FLOW_result.txt",
                "Case_03_real_time_FLOW_result.txt",
                "Case_04_real_time_FLOW_result.txt"
            ]
            best = best_quantile(case_files)
            # "Quantile0.5" has lowest cost over all Cases and "Quantile0.75" if Case 1 is excluded
            print(f"The best quantile is: {best}")
        case 3:
            print(best_quantile_always_better_than_0("Quantile0.5"))
            # "Quantile0.5" has lowest cost for each individual Case except Case_01 (here "Quantile0.0" is better)
            # "Quantile0.75" has lowest cost for Case 02 und Case 03, but not for Case 01 and Case 04 (here "Quantile0.0" is better)
        case _:
            print("Unknown value for temp. Main function should not be called with this value.")



if __name__ == '__main__':
    main()
