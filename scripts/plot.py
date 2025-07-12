import matplotlib
# # For Latex
matplotlib.use('Agg')

import matplotlib.pyplot as plt
# For Latex
plt.style.use('plotstyle.mplstyle')

from matplotlib.image import imread
import os
import re

# Use latex
os.environ["PATH"] += os.pathsep + '/usr/local/texlive/2024/bin/x86_64-linux'

# Directories involved
RESULTS_BASE_DIR = "../results/notable/final_q_0_horizon_DIFF_final_q_0_5_horizon"
SUBFOLDERS = ["deterministic", "real_time"]

# Plot settings
LINE_MARKER = ['o', 'v', 's', 'x', 'h', 'p', '*', '+']
COLOR_LIST = ['mediumseagreen', 'goldenrod', 'dodgerblue', 'crimson', 'slategray', 'darkorchid', 'darkorange', 'teal']
NUMBER_OF_COLUMNS_IN_LEGEND = 4
Y_OFFSET_LEGEND = 1.095

# Regex patterns to match heuristic names and case numbers
HEURISTIC_PATTERN_OBJECTIVE = re.compile(r"Case_\d+_[^_]+_(.+)_result\.txt")
HEURISTIC_PATTERN_RUNNING_TIME = re.compile(r"Case_\d+_[^_]+_(.+)_running_time\.txt")
CASE_PATTERN = re.compile(r"Case_(\d+)_")


# Fixed mapping from heuristic names to colors for consistency
HEURISTIC_COLOR_MAP = {
    'FLOW': 'mediumseagreen',
    'FLOW_MIP': 'goldenrod',
    'GREEDY': 'dodgerblue',
    'GREEDY_CAN_PATHS': 'crimson',
    'LOWER_BOUND': 'darkorchid',
}

# Fixed mapping from heuristic names to markers for consistency
HEURISTIC_MARKER_MAP = {
    'FLOW': 'o',
    'FLOW_MIP': 'v',
    'GREEDY': 's',
    'GREEDY_CAN_PATHS': 'x',
    'LOWER_BOUND': 'h',
}


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
            match = re.search(r"realised_capacity_data_(\d+)\.csv: (-?[\d.]+)", line)
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
            plt.figure(figsize=(11, 7))
            plotted_heuristics = {}
            all_costs = []  # Collect all cost values for y-axis scaling

            # Load deterministic FLOW_MIP data for normalization (for all plots except deterministic)
            deterministic_mip_data = {}
            if subfolder == 'real_time' or subfolder == 'deterministic':
                det_dir = os.path.join(RESULTS_BASE_DIR, 'deterministic')
                if os.path.isdir(det_dir):
                    det_files = [f for f in os.listdir(det_dir) if f.endswith(file_ending) and 'FLOW_MIP' in f]
                    for det_file in det_files:
                        det_case_match = CASE_PATTERN.search(det_file)
                        if not det_case_match:
                            continue
                        det_case = det_case_match.group(1)
                        if det_case == case:  # Only load data for the current case
                            realisations, values = read_data(os.path.join(det_dir, det_file))
                            deterministic_mip_data = dict(zip(realisations, values))
                            break

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

                # Normalize values by dividing by deterministic FLOW_MIP (except for deterministic plots)
                if subfolder != 'deterministic' and deterministic_mip_data:
                    normalized_costs = []
                    normalized_realisations = []
                    for real, cost in zip(realisations, costs):
                        if real in deterministic_mip_data and deterministic_mip_data[real] != 0:
                            normalized_costs.append(cost / deterministic_mip_data[real])
                            normalized_realisations.append(real)
                    costs = normalized_costs
                    realisations = normalized_realisations

                all_costs.extend(costs)  # Collect costs for scaling
                # Plot the costs for this heuristic
                # Use fixed color and marker mapping for heuristics
                color = HEURISTIC_COLOR_MAP.get(heuristic, COLOR_LIST[idx % len(COLOR_LIST)])
                marker = HEURISTIC_MARKER_MAP.get(heuristic, LINE_MARKER[idx % len(LINE_MARKER)])
                line, = plt.plot(
                    realisations, costs, label=heuristic,
                    marker=marker,
                    markersize=7.5, color=color
                )
                plotted_heuristics[heuristic] = line

            # Add deterministic FLOW_MIP line for real_time plots
            if subfolder == 'real_time' and deterministic_mip_data:
                det_realisations = sorted(deterministic_mip_data.keys())
                det_costs = [deterministic_mip_data[r] / deterministic_mip_data[r] for r in det_realisations]  # This will be 1.0 for all
                all_costs.extend(det_costs)  # Include in cost scaling

                # Plot deterministic FLOW_MIP with distinctive style (but don't add to legend)
                plt.plot(
                    det_realisations, det_costs,
                    marker='D',  # Diamond marker for distinction
                    markersize=7.5,
                    color='darkgray',
                    linestyle='--'  # Dashed line for distinction
                )
                # Note: We don't store this line in plotted_heuristics to exclude it from legend

            plt.xlabel('Realization', fontsize=18)
            # Determine subfolder for plot type
            if file_ending == '_result.txt':
                plot_type_folder = 'objective_value'
                if subfolder == 'deterministic':
                    ylabel = 'Cost'
                else:
                    ylabel = 'Cost / Deterministic FLOW_MIP Cost'
                # Explicitly set y-axis lower limit to include negative values
                if all_costs:
                    min_value = min(all_costs)
                    max_value = max(all_costs)
                    margin = (max_value - min_value) * 0.05 if max_value > min_value else 1.0
                    if min_value >= 0.0:
                        min_value = 0
                        margin = 0
                    plt.ylim(bottom=min_value - margin)
            elif file_ending == '_running_time.txt':
                plot_type_folder = 'running_time'
                if subfolder == 'deterministic':
                    ylabel = 'Running Time (s)'
                else:
                    ylabel = 'Running Time / Deterministic FLOW_MIP Running Time'
                plt.yscale('log')  # Use logarithmic scale for running time

                # Set y-axis limits to ensure there's a label above the highest data point
                if all_costs:
                    max_value = max(all_costs)
                    min_value = min(all_costs)
                    # Set upper limit to be at least one order of magnitude higher than max value
                    upper_limit = max_value * 10
                    plt.ylim(bottom=min_value * 0.1, top=upper_limit)
            plt.ylabel(ylabel, fontsize=18)
            # Ensure legend order is consistent across all plots
            handles = [plotted_heuristics[h] for h in all_heuristics if h in plotted_heuristics]
            labels = [h for h in all_heuristics if h in plotted_heuristics]
            plt.legend(handles, labels, ncol=NUMBER_OF_COLUMNS_IN_LEGEND, loc='upper center', bbox_to_anchor=(0.5, Y_OFFSET_LEGEND))
            plt.tight_layout()
            # Create subfolder for plot type with line_chart subdirectory
            plot_dir = os.path.join(RESULTS_BASE_DIR, "plots", plot_type_folder, "line_chart")
            os.makedirs(plot_dir, exist_ok=True)
            # Maintain filename differences for objective and running_time plots
            if file_ending == '_result.txt':
                out_name = f"line_chart_case_{case}_value_{subfolder}"
            elif file_ending == '_running_time.txt':
                out_name = f"line_chart_case_{case}_running_time_{subfolder}"
            plt.savefig(os.path.join(plot_dir, out_name) + ".png", bbox_inches='tight')
            plt.savefig(os.path.join(plot_dir, out_name) + ".pdf", bbox_inches='tight')
            plt.close()


def create_combined_plots(file_ending: str):
    CASES = ["01", "02", "03", "04"]
    if file_ending == '_result.txt':
        plot_type_folder = 'objective_value'
        suffix = '_objective'
    elif file_ending == '_running_time.txt':
        plot_type_folder = 'running_time'
        suffix = '_running_time'
    PLOTS_DIR = os.path.join(RESULTS_BASE_DIR, "plots", plot_type_folder, "line_chart")
    for subfolder in ["deterministic", "real_time"]:
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f"{subfolder.capitalize()} Results", fontsize=18, y=0.98)
        for idx, case in enumerate(CASES):
            row, col = divmod(idx, 2)
            if file_ending == '_result.txt':
                plot_filename = f"line_chart_case_{case}_value_{subfolder}.png"
            elif file_ending == '_running_time.txt':
                plot_filename = f"line_chart_case_{case}_running_time_{subfolder}.png"
            plot_path = os.path.join(PLOTS_DIR, plot_filename)
            if os.path.exists(plot_path):
                img = imread(plot_path)
                axes[row, col].imshow(img)
                axes[row, col].axis('off')
                axes[row, col].set_title(f"Case {case}")
            else:
                axes[row, col].set_visible(False)
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        # Ensure the output directory exists before saving - save combined plots at the parent level
        combined_plots_dir = os.path.join(RESULTS_BASE_DIR, "plots", plot_type_folder)
        os.makedirs(combined_plots_dir, exist_ok=True)
        out_path = os.path.join(combined_plots_dir, f"all_cases_{subfolder}{suffix}")
        plt.savefig(out_path + ".png", bbox_inches='tight')
        plt.savefig(out_path + ".pdf", bbox_inches='tight')
        plt.close()


def create_boxplots(file_ending: str, subtract_mip: bool = False):
    """
    Creates boxplots for each case showing running times by heuristic.

    Args:
        file_ending (str): The file ending to work with (e.g., '_running_time.txt')
        subtract_mip (bool): If True, subtract MIP solution values from other heuristics and exclude MIP from visualization
    """
    # Collect all heuristics globally to ensure consistent order
    all_heuristics = set()

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

    # Sort heuristics for consistent order
    all_heuristics = sorted(all_heuristics)

    # If subtract_mip is True, filter out FLOW_MIP from the display heuristics
    display_heuristics = [h for h in all_heuristics]

    for subfolder in SUBFOLDERS:
        dir_path = os.path.join(RESULTS_BASE_DIR, subfolder)
        if not os.path.isdir(dir_path):
            continue
        files = [f for f in os.listdir(dir_path) if f.endswith(file_ending)]
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
            plt.figure(figsize=(10, 6))

            # Load deterministic FLOW_MIP solution for normalization/subtraction
            deterministic_mip_data = {}
            det_dir = os.path.join(RESULTS_BASE_DIR, 'deterministic')
            if os.path.isdir(det_dir):
                det_files = [f for f in os.listdir(det_dir) if f.endswith(file_ending) and 'FLOW_MIP' in f]
                for det_file in det_files:
                    det_case_match = CASE_PATTERN.search(det_file)
                    if not det_case_match:
                        continue
                    det_case = det_case_match.group(1)
                    if det_case == case:  # Only load data for the current case
                        realisations, values = read_data(os.path.join(det_dir, det_file))
                        deterministic_mip_data = dict(zip(realisations, values))
                        break

            # Collect data for each heuristic
            heuristic_data = {}
            mip_data = {}  # Store MIP data separately for subtraction
            real_time_mip_data = {}  # Store real_time FLOW_MIP for plotting

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

                realisations, values = read_data(os.path.join(dir_path, filename))

                if heuristic == 'FLOW_MIP':
                    # Always store real_time MIP data for plotting (even if not subtracting)
                    for real, val in zip(realisations, values):
                        real_time_mip_data[real] = val
                    # Also add to heuristic_data as 'FLOW_MIP' for real_time plots
                    if subfolder == 'real_time':
                        if 'FLOW_MIP' not in heuristic_data:
                            heuristic_data['FLOW_MIP'] = {}
                        for real, val in zip(realisations, values):
                            heuristic_data['FLOW_MIP'][real] = val
                if subtract_mip and heuristic == 'FLOW_MIP':
                    # Store MIP data indexed by realization for subtraction (real_time)
                    for real, val in zip(realisations, values):
                        mip_data[real] = val
                else:
                    if heuristic not in heuristic_data:
                        heuristic_data[heuristic] = {}
                    # Store data indexed by realization for potential MIP subtraction
                    for real, val in zip(realisations, values):
                        heuristic_data[heuristic][real] = val

            # Normalize values by dividing by deterministic FLOW_MIP (for all boxplots)
            if deterministic_mip_data:
                for heuristic in heuristic_data:
                    normalized_data = {}
                    for real, val in heuristic_data[heuristic].items():
                        if real in deterministic_mip_data and deterministic_mip_data[real] != 0:
                            normalized_data[real] = val / deterministic_mip_data[real]
                    heuristic_data[heuristic] = normalized_data

            if subtract_mip:
                # For real_time FLOW_MIP, store difference as well
                if real_time_mip_data and deterministic_mip_data:
                    heuristic_data['FLOW_MIP_REAL_TIME'] = {}
                    for real, val in real_time_mip_data.items():
                        if real in deterministic_mip_data and deterministic_mip_data[real] != 0:
                            heuristic_data['FLOW_MIP_REAL_TIME'][real] = (val / deterministic_mip_data[real]) - 1.0
            else:
                # If not subtracting, just add normalized real_time FLOW_MIP as a heuristic
                if real_time_mip_data and deterministic_mip_data:
                    heuristic_data['FLOW_MIP_REAL_TIME'] = {}
                    for real, val in real_time_mip_data.items():
                        if real in deterministic_mip_data and deterministic_mip_data[real] != 0:
                            heuristic_data['FLOW_MIP_REAL_TIME'][real] = val / deterministic_mip_data[real]

            # Convert to lists for boxplot
            final_heuristic_data = {}
            for heuristic in heuristic_data:
                if heuristic_data[heuristic]:  # Only include if there's data
                    final_heuristic_data[heuristic] = list(heuristic_data[heuristic].values())

            # Prepare data for boxplot in the order of display_heuristics
            boxplot_data = []
            boxplot_labels = []
            for heuristic in display_heuristics:
                if heuristic in final_heuristic_data and final_heuristic_data[heuristic]:
                    boxplot_data.append(final_heuristic_data[heuristic])
                    boxplot_labels.append(heuristic)

            if boxplot_data:
                # Create boxplot
                bp = plt.boxplot(boxplot_data, tick_labels=boxplot_labels, patch_artist=True)

                # Color the boxes using the same color scheme
                for i, box in enumerate(bp['boxes']):
                    color_idx = all_heuristics.index(boxplot_labels[i])
                    box.set_facecolor(COLOR_LIST[color_idx % len(COLOR_LIST)])
                    box.set_alpha(0.7)

                plt.xlabel('Heuristic', labelpad=10)

                # Determine plot type and ylabel
                if file_ending == '_result.txt':
                    plot_type_folder = 'objective_value'
                    if subtract_mip:
                        ylabel = 'Cost Difference / Det. FLOW_MIP Cost'
                    else:
                        ylabel = 'Cost / Deterministic FLOW_MIP Cost'
                elif file_ending == '_running_time.txt':
                    plot_type_folder = 'running_time'
                    if subtract_mip:
                        ylabel = 'Running Time Ratio - 1 (relative to Deterministic FLOW_MIP)'
                    else:
                        ylabel = 'Running Time / Deterministic FLOW_MIP Running Time'

                plt.ylabel(ylabel)
                plt.xticks()
                plt.tight_layout()

                # Create subfolder for boxplots
                plot_dir = os.path.join(RESULTS_BASE_DIR, "plots", plot_type_folder, "boxplots")
                os.makedirs(plot_dir, exist_ok=True)

                # Save the boxplot
                if file_ending == '_result.txt':
                    if subtract_mip:
                        out_name = f"boxplot_case_{case}_value_{subfolder}_diff_from_mip"
                    else:
                        out_name = f"boxplot_case_{case}_value_{subfolder}"
                elif file_ending == '_running_time.txt':
                    if subtract_mip:
                        out_name = f"boxplot_case_{case}_running_time_{subfolder}_diff_from_mip"
                    else:
                        out_name = f"boxplot_case_{case}_running_time_{subfolder}"

                plt.savefig(os.path.join(plot_dir, out_name) + ".png", bbox_inches='tight')
                plt.savefig(os.path.join(plot_dir, out_name) + ".pdf", bbox_inches='tight')
                plt.close()


def create_barcharts(file_ending: str):
    """
    Creates bar charts for each case showing average objective values or running times by heuristic.

    Args:
        file_ending (str): The file ending to work with (e.g., '_result.txt' or '_running_time.txt')
    """
    # Collect all heuristics globally to ensure consistent order
    all_heuristics = set()

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

    # Sort heuristics for consistent order
    all_heuristics = sorted(all_heuristics)

    for subfolder in SUBFOLDERS:
        dir_path = os.path.join(RESULTS_BASE_DIR, subfolder)
        if not os.path.isdir(dir_path):
            continue
        files = [f for f in os.listdir(dir_path) if f.endswith(file_ending)]
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
            plt.figure(figsize=(10, 6))

            # Collect data for each heuristic and calculate averages
            heuristic_averages = {}

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

                realisations, values = read_data(os.path.join(dir_path, filename))

                if values:  # Only calculate average if we have data
                    heuristic_averages[heuristic] = sum(values) / len(values)

            # Prepare data for bar chart in the order of all_heuristics
            bar_heuristics = []
            bar_averages = []
            bar_colors = []

            for heuristic in all_heuristics:
                if heuristic in heuristic_averages:
                    bar_heuristics.append(heuristic)
                    bar_averages.append(heuristic_averages[heuristic])
                    color_idx = all_heuristics.index(heuristic)
                    bar_colors.append(COLOR_LIST[color_idx % len(COLOR_LIST)])

            if bar_heuristics:
                # Create bar chart
                bars = plt.bar(bar_heuristics, bar_averages, color=bar_colors, alpha=0.7)

                plt.xlabel('Heuristic', labelpad=10)

                # Determine plot type and ylabel
                if file_ending == '_result.txt':
                    plot_type_folder = 'objective_value'
                    ylabel = 'Average Cost'
                elif file_ending == '_running_time.txt':
                    plot_type_folder = 'running_time'
                    ylabel = 'Average Running Time (s)'
                    plt.yscale('log')  # Use logarithmic scale for running time

                    # Set y-axis limits to ensure there's a label above the highest data point
                    max_value = max(bar_averages)
                    # Set upper limit to be at least one order of magnitude higher than max value
                    upper_limit = max_value * 10
                    plt.ylim(bottom=min(bar_averages) * 0.1, top=upper_limit)

                plt.ylabel(ylabel)
                plt.xticks()
                plt.tight_layout()

                # Create subfolder for bar charts
                plot_dir = os.path.join(RESULTS_BASE_DIR, "plots", plot_type_folder, "barcharts")
                os.makedirs(plot_dir, exist_ok=True)

                # Save the bar chart
                if file_ending == '_result.txt':
                    out_name = f"barchart_case_{case}_value_{subfolder}"
                elif file_ending == '_running_time.txt':
                    out_name = f"barchart_case_{case}_running_time_{subfolder}"

                plt.savefig(os.path.join(plot_dir, out_name) + ".png", bbox_inches='tight')
                plt.savefig(os.path.join(plot_dir, out_name) + ".pdf", bbox_inches='tight')
                plt.close()


if __name__ == '__main__':
    plot('_result.txt')
    create_combined_plots('_result.txt')
    plot('_running_time.txt')
    create_combined_plots('_running_time.txt')
    create_boxplots('_running_time.txt')
    create_boxplots('_result.txt')
    create_boxplots('_running_time.txt', subtract_mip=True)
    create_boxplots('_result.txt', subtract_mip=True)
    create_barcharts('_result.txt')
    create_barcharts('_running_time.txt')
