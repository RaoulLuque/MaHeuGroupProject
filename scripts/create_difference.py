import os
import re

OLD = "final_q_0_horizon"
NEW = "final_q_0_5_horizon"
BASE_DIR = os.path.join("..", "results", "notable")
SUBFOLDERS = ["deterministic", "real_time"]
RESULT_SUFFIX = "_result.txt"

# Regex to extract the cost value from a line like:
# Cost of solution for ...: 123.45
COST_LINE_REGEX = re.compile(r"(Cost of solution for [^:]+: )([\d.]+)")


def get_result_files(folder):
    result_files = {}
    for subfolder in SUBFOLDERS:
        dir_path = os.path.join(BASE_DIR, folder, subfolder)
        if not os.path.isdir(dir_path):
            continue
        for fname in os.listdir(dir_path):
            if fname.endswith(RESULT_SUFFIX):
                result_files.setdefault(subfolder, []).append(fname)
    return result_files


def read_costs(filepath):
    costs = {}
    with open(filepath, 'r') as f:
        for line in f:
            m = COST_LINE_REGEX.search(line)
            if m:
                key = m.group(1)
                value = float(m.group(2))
                costs[key] = value
    return costs


def main():
    old_files = get_result_files(OLD)
    new_files = get_result_files(NEW)
    diff_folder = f"{OLD}_DIFF_{NEW}"
    for subfolder in SUBFOLDERS:
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


if __name__ == "__main__":
    main()
