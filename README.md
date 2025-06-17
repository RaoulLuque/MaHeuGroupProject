# MaHeu Group Project

## Encoding of solutions

Solutions will be stored in a list of type `list[Vehicle]`. Each
`Vehicle` object
contains fields which indicate which Trucks / Transportation Vehicles
are used,
to transport the respective `Vehicle`.

TODO: Explain this more thoroughly

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

### Run the script using the command line

To run the script using the command line, run:

```commandline
PYTHONPATH=src python -m maheu_group_project.main
```

### Run the script using PyCharm

To run the script using PyCharm, first open the project in PyCharm.
Next right-click the src folder and
`Mark Directory as -> Sources Root`.

Now the script can be run by opening the
`src/maheu_group_project/main.py`
file and clicking the green run button to the left of

```python 
if __name__ == '__main__':
```