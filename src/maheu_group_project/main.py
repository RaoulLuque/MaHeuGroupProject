from maheu_group_project.parsing import read_data
from maheu_group_project.heuristics.translate_to_mip import solve_as_mip


def main():
    locations, vehicles, trucks = read_data()
    solve_as_mip(vehicles, trucks, locations)


if __name__ == '__main__':
    main()
