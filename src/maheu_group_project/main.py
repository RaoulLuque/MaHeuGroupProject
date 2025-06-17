from maheu_group_project.parsing import read_data
from maheu_group_project.heuristics.flow.solve import solve_as_flow


def main():
    locations, vehicles, trucks = read_data()
    solve_as_flow(vehicles, trucks, locations)


if __name__ == '__main__':
    main()
