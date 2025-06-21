from maheu_group_project.heuristics.flow.solve import create_flow_network
from maheu_group_project.heuristics.flow.visualize import visualize_flow_graph
from maheu_group_project.parsing import read_data
from maheu_group_project.heuristics.old_flow.solve import solve_as_flow


def main():
    locations, vehicles, trucks_realised, trucks_planned = read_data(dataset_dir_name="CaseMaHeu25_01", realised_capacity_file_name="realised_capacity_data_001.csv")
    flow_network = create_flow_network(vehicles=vehicles, trucks=trucks_realised, locations=locations)
    visualize_flow_graph(flow_network, locations)


if __name__ == '__main__':
    main()
