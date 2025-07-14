# MaHeu Group Project

This repository contains the code for a group project for the course
on Mathematical Heuristic Methods (MaHeu) at the RWTH Aachen University
in the Summer Semester 2025.

## Problem description

The project is revolves around solving a distribution problem for a car manufacturer.
A scenario of a logistic network is given with vehicles which need to
be transported from plants to several dealerships via a set of
transports. The goal is to find a solution which minimizes the total
transportation costs, while respecting the constraints of the problem.

## Encoding of solutions

The solutions are encoded as a list of VehicleAssignment objects, which
encode the information necessary to know which route a vehicle is
supposed to take. This list is indexed by the index of the vehicle
in the dataset (-1, since we are using 0-based indexing in Python).

Furthermore, a dictionary of TruckAssignment objects is provided, which
encodes the information necessary to know which truck is supposed to
transport which vehicle(s). This is redundant information, but can
be useful in practice to quickly look up if a truck has spare space
available.

For details, please see [`src/maheu_group_project/solution/encoding.py`](src/maheu_group_project/solution/encoding.py).

## Running the script

There are two possible ways to run the script:

- [Using the command line](#run-the-script-using-the-command-line)
- [Using PyCharm](#run-the-script-using-pycharm)

In both cases, the project dependencies will need to be installed.
This can either be done using [`uv`](https://github.com/astral-sh/uv):

```commandline
uv sync
```

or using pip:

```commandline
pip install .
```

The scripts are all located in the [`scripts`](scripts) directory.
The main script to run is [`run_all.py`](scripts/run_all.py), which
can be configured to run different heuristics on the different datasets/
instances. At the top of the file, one can configure the arguments.
Otherwise, one can also provide command line arguments, in which case
the arguments in the script will be ignored/overwritten.

### Run the script from the command line

To run the script using the command line, run:

```commandline
python3 scripts/run_all.py
```

Optionally, one can provide command line arguments to the script.
For example, to run the script with all available heuristics on all
datasets in the uncertain / real_time setting, one can run:

```commandline
python3 scripts/run_all.py --deterministic FALSE --solvers GREEDY GREEDY_CANDIDATE_PATHS FLOW FLOW_MIP --dataset_indices 1 2 3 4
```

### Run the script using PyCharm

To run the script using PyCharm, first open the project in PyCharm.
Next right-click the src folder and
`Mark Directory as -> Sources Root`.

Now the script(s) can be run by opening the respective file (e.g. [`run_all.py`](scripts/run_all.py))
and clicking the green run button in the top right corner of the editor,
after selecting `Current File` in the dropdown menu next to it.

```python 
if __name__ == '__main__':
```


### Retrieve the results

The results of the script will be written to the `results` directory.
In particular, the results are written to the subdirectory `deterministic`
or `real_time`, depending on the setting used. We store the objective
values of the heuristics, their running time as well as other metrics,
where the files ending with `result_pretty.txt` contain the most
meaningful information in a human-readable format.

These results can then be automatically edited by running the
`scripts/remove_timestamp_from_result_files.py` script and then moving
the files to the `notable` subdirectory of the `results` directory.
After this, one can adjust the `scripts/plot.py` script to plot the results.

All results, including the final results for the project can be found
in the `results/notable` directory. In particular, the final results are
stored in `results/notable/final_*`.
