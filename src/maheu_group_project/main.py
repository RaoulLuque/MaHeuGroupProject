import sys
import os

# Add the project's 'src' directory to the Python path to resolve the module not found error.
# This allows for absolute imports starting from 'maheu_group_project'.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#from maheu_group_project.heuristics.flow.network import create_flow_network
#from maheu_group_project.heuristics.flow.visualize import visualize_flow_graph
#from maheu_group_project.parsing import read_data
from maheu_group_project.stochastics.absoluteDifference import absDif, test, cDiff, allDiffs2, standardabweichung, standardabweichung_perDay





def main():
    #locations, vehicles, trucks_realised, trucks_planned = read_data(dataset_dir_name="CaseMaHeu25_01", realised_capacity_file_name="realised_capacity_data_001.csv")
    #flow_network = create_flow_network(vehicles=vehicles, trucks=trucks_realised, locations=locations)
    #visualize_flow_graph(flow_network, locations)
    test()
    #allDiffs2()
    standardabweichung()
    standardabweichung_perDay()
    






if __name__ == '__main__':
    main()
