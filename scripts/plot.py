# # For Latex
# matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.image import imread
import os
import re

# # Use latex
# os.environ["PATH"] += os.pathsep + '/usr/local/texlive/2024/bin/x86_64-linux'

# Directories involved
RESULTS_BASE_DIR = "../results/notable/28_06"
SUBFOLDERS = ["deterministic", "real_time"]

# Plot settings
LINE_MARKER = ['o', 'v', 's', 'x', 'h', 'p', '*', '+']
COLOR_LIST = ['mediumseagreen', 'goldenrod', 'dodgerblue']
NUMBER_OF_COLUMNS_IN_LEGEND = 4
Y_OFFSET_LEGEND = 1.09

# Regex patterns to match heuristic names and case numbers
HEURISTIC_PATTERN = re.compile(r"Case_\d+_[^_]+_(.+)_result\.txt")
CASE_PATTERN = re.compile(r"Case_(\d+)_")


def read_costs(filepath):
    """
    Reads the cost values for each realisation from a result file.

    Args:
        filepath (str): Path to the result file.

    Returns:
        tuple[list[int], list[float]]: Lists of realisation indices and corresponding costs.
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


if __name__ == '__main__':
    # Collect all heuristics globally to ensure consistent color/marker/legend order
    all_heuristics = set()
    heuristic_file_map = {}
    for subfolder in SUBFOLDERS:
        dir_path = os.path.join(RESULTS_BASE_DIR, subfolder)
        if not os.path.isdir(dir_path):
            continue
        files = [f for f in os.listdir(dir_path) if f.endswith('_result.txt') and not f.endswith('_pretty.txt')]
        for f in files:
            heuristic_match = HEURISTIC_PATTERN.search(f)
            if not heuristic_match:
                continue
            heuristic = heuristic_match.group(1)
            # Normalize heuristic names for consistency
            if heuristic.startswith('time_'):
                heuristic = heuristic[len('time_'):]
            if heuristic == 'LOWER_BOUND_UNCAPACITATED_FLOW':
                heuristic = 'LOWER_BOUND'
            all_heuristics.add(heuristic)
            heuristic_file_map.setdefault(subfolder, {}).setdefault(heuristic, []).append(f)

    # Sort heuristics for consistent order in plots and legends
    all_heuristics = sorted(all_heuristics)
    heuristic_to_idx = {h: i for i, h in enumerate(all_heuristics)}

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
            plotted_heuristics = {}
            for filename in case_files:
                heuristic_match = HEURISTIC_PATTERN.search(filename)
                if not heuristic_match:
                    continue
                heuristic = heuristic_match.group(1)
                # Normalize heuristic names for consistency
                if heuristic.startswith('time_'):
                    heuristic = heuristic[len('time_'):]
                if heuristic == 'LOWER_BOUND_UNCAPACITATED_FLOW':
                    heuristic = 'LOWER_BOUND'
                idx = heuristic_to_idx[heuristic]
                realisations, costs = read_costs(os.path.join(dir_path, filename))
                # Plot the costs for this heuristic
                line, = plt.plot(
                    realisations, costs, label=heuristic,
                    marker=LINE_MARKER[idx % len(LINE_MARKER)],
                    markersize=7.5, color=COLOR_LIST[idx % len(COLOR_LIST)]
                )
                plotted_heuristics[heuristic] = line
            plt.xlabel('Realisation')
            plt.ylabel('Cost')
            plt.title(f'Case {case} - {subfolder}', pad=25)
            # Ensure legend order is consistent across all plots
            handles = [plotted_heuristics[h] for h in all_heuristics if h in plotted_heuristics]
            labels = [h for h in all_heuristics if h in plotted_heuristics]
            plt.legend(handles, labels, ncol=NUMBER_OF_COLUMNS_IN_LEGEND, loc='upper center', bbox_to_anchor=(0.5, Y_OFFSET_LEGEND))
            plt.tight_layout()
            out_name = f"plot_case_{case}_{subfolder}.png"
            os.makedirs(os.path.join(RESULTS_BASE_DIR, "plots"), exist_ok=True)
            plt.savefig(os.path.join(RESULTS_BASE_DIR, "plots", out_name))
            plt.close()


# Create combined plots
PLOTS_DIR = os.path.join(RESULTS_BASE_DIR, "plots")

CASES = ["01", "02", "03", "04"]

for subfolder in ["deterministic", "real_time"]:
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"{subfolder.capitalize()} Results", fontsize=18, y=0.98)
    for idx, case in enumerate(CASES):
        row, col = divmod(idx, 2)
        plot_path = os.path.join(PLOTS_DIR, f"plot_case_{case}_{subfolder}.png")
        if os.path.exists(plot_path):
            img = imread(plot_path)
            axes[row, col].imshow(img)
            axes[row, col].axis('off')
            axes[row, col].set_title(f"Case {case}")
        else:
            axes[row, col].set_visible(False)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out_path = os.path.join(PLOTS_DIR, f"all_cases_{subfolder}.png")
    plt.savefig(out_path)
    plt.close()
