# # For Latex
# matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.image import imread
import os
import re

# # Use latex
# os.environ["PATH"] += os.pathsep + '/usr/local/texlive/2024/bin/x86_64-linux'

# Directories involved
RESULTS_BASE_DIR = "../results/notable/02_07"
SUBFOLDERS = ["deterministic", "real_time"]

# Plot settings
LINE_MARKER = ['o', 'v', 's', 'x', 'h', 'p', '*', '+']
COLOR_LIST = ['mediumseagreen', 'goldenrod', 'dodgerblue', 'crimson', 'darkorchid', 'darkorange', 'teal', 'slategray']
NUMBER_OF_COLUMNS_IN_LEGEND = 4
Y_OFFSET_LEGEND = 1.09

# Regex patterns to match heuristic names and case numbers
HEURISTIC_PATTERN_OBJECTIVE = re.compile(r"Case_\d+_[^_]+_(.+)_result\.txt")
HEURISTIC_PATTERN_RUNNING_TIME = re.compile(r"Case_\d+_[^_]+_(.+)_running_time\.txt")
CASE_PATTERN = re.compile(r"Case_(\d+)_")


def read_data(filepath: str) -> tuple[list[int], list[float]]:
    """
    Reads the result file and extracts realisation indices and their corresponding costs / running times.

    Args:
        filepath (str): Path to the result file.

    Returns:
        tuple[list[int], list[float]]: Lists of realisation indices and corresponding costs / running times.
    """
    costs = []
    realisations = []
    with open(filepath, 'r') as f:
        for line in f:
            match = re.search(r"realised_capacity_data_(\d+)\.csv: ([\d.]+)", line)
            if match:
                realisations.append(int(match.group(1)))
                costs.append(float(match.group(2)))
    return realisations, costs


def plot(file_ending: str):
    # Collect all heuristics globally to ensure consistent color/marker/legend order
    all_heuristics = set()
    heuristic_file_map = {}
    for subfolder in SUBFOLDERS:
        dir_path = os.path.join(RESULTS_BASE_DIR, subfolder)
        if not os.path.isdir(dir_path):
            continue
        files = [f for f in os.listdir(dir_path) if f.endswith(file_ending)]
        for f in files:
            if file_ending == "_result.txt":
                heuristic_match = HEURISTIC_PATTERN_OBJECTIVE.search(f)
            elif file_ending == "_running_time.txt":
                heuristic_match = HEURISTIC_PATTERN_RUNNING_TIME.search(f)
            if not heuristic_match:
                continue
            heuristic = heuristic_match.group(1)
            # Normalize heuristic names for consistency
            if heuristic.startswith('time_'):
                heuristic = heuristic[len('time_'):]
            if heuristic == 'LOWER_BOUND_UNCAPACITATED_FLOW':
                heuristic = 'LOWER_BOUND'
            if heuristic == 'GREEDY_CANDIDATE_PATHS':
                heuristic = 'GREEDY_CAN_PATHS'
            all_heuristics.add(heuristic)
            heuristic_file_map.setdefault(subfolder, {}).setdefault(heuristic, []).append(f)

    # Sort heuristics for consistent order in plots and legends
    all_heuristics = sorted(all_heuristics)
    heuristic_to_idx = {h: i for i, h in enumerate(all_heuristics)}

    for subfolder in SUBFOLDERS:
        dir_path = os.path.join(RESULTS_BASE_DIR, subfolder)
        if not os.path.isdir(dir_path):
            continue
        files = [f for f in os.listdir(dir_path) if f.endswith(file_ending) ]
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
            plotted_heuristics = {}
            for filename in case_files:
                if file_ending == "_result.txt":
                    heuristic_match = HEURISTIC_PATTERN_OBJECTIVE.search(filename)
                elif file_ending == "_running_time.txt":
                    heuristic_match = HEURISTIC_PATTERN_RUNNING_TIME.search(filename)
                if not heuristic_match:
                    continue
                heuristic = heuristic_match.group(1)
                # Normalize heuristic names for consistency
                if heuristic.startswith('time_'):
                    heuristic = heuristic[len('time_'):]
                if heuristic == 'LOWER_BOUND_UNCAPACITATED_FLOW':
                    heuristic = 'LOWER_BOUND'
                if heuristic == 'GREEDY_CANDIDATE_PATHS':
                    heuristic = 'GREEDY_CAN_PATHS'
                idx = heuristic_to_idx[heuristic]
                realisations, costs = read_data(os.path.join(dir_path, filename))
                # Plot the costs for this heuristic
                line, = plt.plot(
                    realisations, costs, label=heuristic,
                    marker=LINE_MARKER[idx % len(LINE_MARKER)],
                    markersize=7.5, color=COLOR_LIST[idx % len(COLOR_LIST)]
                )
                plotted_heuristics[heuristic] = line
            plt.xlabel('Realisation')
            # Determine subfolder for plot type
            if file_ending == '_result.txt':
                plot_type_folder = 'objective_value'
                ylabel = 'Cost'
            elif file_ending == '_running_time.txt':
                plot_type_folder = 'running_time'
                ylabel = 'Running Time (s)'
            plt.ylabel(ylabel)
            plt.title(f'Case {case} - {subfolder}', pad=25)
            # Ensure legend order is consistent across all plots
            handles = [plotted_heuristics[h] for h in all_heuristics if h in plotted_heuristics]
            labels = [h for h in all_heuristics if h in plotted_heuristics]
            plt.legend(handles, labels, ncol=NUMBER_OF_COLUMNS_IN_LEGEND, loc='upper center', bbox_to_anchor=(0.5, Y_OFFSET_LEGEND))
            plt.tight_layout()
            # Create subfolder for plot type
            plot_dir = os.path.join(RESULTS_BASE_DIR, "plots", plot_type_folder)
            os.makedirs(plot_dir, exist_ok=True)
            # Maintain filename differences for objective and running_time plots
            if file_ending == '_result.txt':
                out_name = f"plot_case_{case}_value_{subfolder}.png"
            elif file_ending == '_running_time.txt':
                out_name = f"plot_case_{case}_running_time_{subfolder}.png"
            plt.savefig(os.path.join(plot_dir, out_name))
            plt.close()


def create_combined_plots(file_ending: str):
    CASES = ["01", "02", "03", "04"]
    if file_ending == '_result.txt':
        plot_type_folder = 'objective_value'
        suffix = '_objective.png'
    elif file_ending == '_running_time.txt':
        plot_type_folder = 'running_time'
        suffix = '_running_time.png'
    PLOTS_DIR = os.path.join(RESULTS_BASE_DIR, "plots", plot_type_folder)
    for subfolder in ["deterministic", "real_time"]:
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f"{subfolder.capitalize()} Results", fontsize=18, y=0.98)
        for idx, case in enumerate(CASES):
            row, col = divmod(idx, 2)
            if file_ending == '_result.txt':
                plot_filename = f"plot_case_{case}_value_{subfolder}.png"
            elif file_ending == '_running_time.txt':
                plot_filename = f"plot_case_{case}_running_time_{subfolder}.png"
            plot_path = os.path.join(PLOTS_DIR, plot_filename)
            if os.path.exists(plot_path):
                img = imread(plot_path)
                axes[row, col].imshow(img)
                axes[row, col].axis('off')
                axes[row, col].set_title(f"Case {case}")
            else:
                axes[row, col].set_visible(False)
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        # Ensure the output directory exists before saving
        os.makedirs(PLOTS_DIR, exist_ok=True)
        out_path = os.path.join(PLOTS_DIR, f"all_cases_{subfolder}{suffix}")
        plt.savefig(out_path)
        plt.close()


if __name__ == '__main__':
    plot('_result.txt')
    create_combined_plots('_result.txt')
    plot('_running_time.txt')
    create_combined_plots('_running_time.txt')
