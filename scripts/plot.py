import numpy as np
import matplotlib

# # For Latex
# matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import os
import re

# # Use latex
# os.environ["PATH"] += os.pathsep + '/usr/local/texlive/2024/bin/x86_64-linux'

LINE_MARKER = ['o', 'v', 's', 'x', 'h', 'p', '*', '+']
NUMBER_OF_COLUMNS_IN_LEGEND = 4
Y_OFFSET_LEGEND = 1.09

RESULTS_BASE_DIR = "../results/notable/28_06"  # Change this to your target directory
SUBFOLDERS = ["deterministic", "real_time"]

# Helper to extract heuristic name from filename
HEURISTIC_PATTERN = re.compile(r"Case_\d+_[^_]+_(.+)_result\.txt")
CASE_PATTERN = re.compile(r"Case_(\d+)_")


# Helper to read costs from a result file
def read_costs(filepath):
    costs = []
    realisations = []
    with open(filepath, 'r') as f:
        for line in f:
            match = re.search(r"realised_capacity_data_(\d+)\.csv: ([\d.]+)", line)
            if match:
                realisations.append(int(match.group(1)))
                costs.append(float(match.group(2)))
    return realisations, costs


if __name__ == '__main__':
    for subfolder in SUBFOLDERS:
        dir_path = os.path.join(RESULTS_BASE_DIR, subfolder)
        if not os.path.isdir(dir_path):
            continue
        files = [f for f in os.listdir(dir_path) if f.endswith('_result.txt') and not f.endswith('_pretty.txt')]
        cases = {}
        for f in files:
            case_match = CASE_PATTERN.search(f)
            if not case_match:
                continue
            case = case_match.group(1)
            if case not in cases:
                cases[case] = []
            cases[case].append(f)
        for case, case_files in cases.items():
            plt.figure(figsize=(8, 5))
            for idx, filename in enumerate(case_files):
                heuristic_match = HEURISTIC_PATTERN.search(filename)
                if not heuristic_match:
                    continue
                heuristic = heuristic_match.group(1)
                # Remove 'time_' prefix if present
                if heuristic.startswith('time_'):
                    heuristic = heuristic[len('time_'):]
                # Rename LOWER_BOUND_UNCAPACITATED_FLOW to LOWER_BOUND
                if heuristic == 'LOWER_BOUND_UNCAPACITATED_FLOW':
                    heuristic = 'LOWER_BOUND'
                realisations, costs = read_costs(os.path.join(dir_path, filename))
                plt.plot(realisations, costs, label=heuristic, marker=LINE_MARKER[idx % len(LINE_MARKER)], markersize=7.5)
            plt.xlabel('Realisation')
            plt.ylabel('Cost')
            plt.title(f'Case {case} - {subfolder}', pad=25)
            plt.legend(ncol=NUMBER_OF_COLUMNS_IN_LEGEND, loc='upper center', bbox_to_anchor=(0.5, Y_OFFSET_LEGEND))
            plt.tight_layout()
            out_name = f"plot_case_{case}_{subfolder}.png"
            os.makedirs(os.path.join(RESULTS_BASE_DIR, "plots"), exist_ok=True)
            plt.savefig(os.path.join(RESULTS_BASE_DIR, "plots", out_name))
            plt.close()
