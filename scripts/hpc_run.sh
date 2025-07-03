#!/usr/bin/zsh

### Job Parameters
#SBATCH --ntasks=1                          # MPI tasks
#SBATCH --cpus-per-task=1                   # Number of CPU cores per task
#SBATCH --time=00:90:00                     # Running time until timeout
#SBATCH --job-name=maheu_deterministic_job  # Job name
#SBATCH --output=stdout.txt                 # redirects stdout and stderr to stdout.txt

### Navigate to working directory
cd /hpcwork/xh700552/MaHeuGroupProject

### Load Modules
module purge
module load GCCcore/14.2.0
module load Python/3.13.1

# Gurobi
module load GCCcore/13.3.0
module load Gurobi/12.0.0

### Update pip and install dependencies
pip install --upgrade pip
pip install networkx==3.5
pip install matplotlib==3.10.3

### Run the script (once for deterministic and once for real-time)
python3 scripts/run_all.py --deterministic --solvers GREEDY GREEDY_CANDIDATE_PATHS FLOW LOWER_BOUND --dataset_indices 1 2 3 4
python3 scripts/run_all.py --solvers GREEDY GREEDY_CANDIDATE_PATHS FLOW --dataset_indices 1 2 3 4
