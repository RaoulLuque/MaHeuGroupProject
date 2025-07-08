import os
import shutil

DESTINATION = "tmp"

# Use absolute paths relative to the script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
base_results = os.path.join(SCRIPT_DIR, "..", "results")
notable_base = os.path.join(base_results, "notable", DESTINATION)

folders = ["deterministic", "real_time"]


def main():
    for folder in folders:
        src = os.path.join(base_results, folder)
        dst = os.path.join(notable_base, folder)

        # Remove target directory and all its contents if it exists
        if os.path.exists(dst):
            shutil.rmtree(dst)
        os.makedirs(dst, exist_ok=True)

        # Move all contents from src to dst
        if os.path.exists(src):
            for item in os.listdir(src):
                s = os.path.join(src, item)
                d = os.path.join(dst, item)
                shutil.move(s, d)


if __name__ == "__main__":
    main()
