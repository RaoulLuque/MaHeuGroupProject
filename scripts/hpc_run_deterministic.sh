#!/usr/bin/zsh

### Job Parameters
#SBATCH --ntasks=8              # MPI tasks
#SBATCH --time=00:01:00         # Running time until timeout
#SBATCH --job-name=maheu_deterministic_job  # Job name
#SBATCH --output=stdout.txt     # redirects stdout and stderr to stdout.txt

### Navigate to working directory
cd /hpcwork/xh700552/MaHeuGroupProject

### Load Modules
module purge
module load GCCcore/14.2.0
module load Python/3.13.1

### Update pip and install dependencies
pip install --upgrade pip
pip install networkx==3.5
pip install matplotlib==3.10.3

### Run the script
python3 scripts/run_all.py --deterministic --solvers GREEDY GREEDY_CANDIDATE_PATHS FLOW LOWER_BOUND --dataset_indices 1 2 3 4
