import os
import re

RESULT_DIRS = ['deterministic', 'real_time']


def main():
    timestamp_pattern = r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_'
    for result_dir in RESULT_DIRS:
        dir_path = f"../results/{result_dir}/"
        for filename in os.listdir(dir_path):
            if re.match(timestamp_pattern, filename):
                new_name = re.sub(timestamp_pattern, '', filename, count=1)
                src = os.path.join(dir_path, filename)
                dst = os.path.join(dir_path, new_name)
                os.rename(src, dst)


if __name__ == "__main__":
    main()
