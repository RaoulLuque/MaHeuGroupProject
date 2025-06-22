from maheu_group_project.heuristics.flow.solve import create_flow_network, solve_deterministically
from maheu_group_project.parsing import read_data
from maheu_group_project.solution.encoding import VehicleAssignment, TruckIdentifier, TruckAssignment


def lower_bound_uncapacitated_flow(dataset_dir_name: str, realised_capacity_file_name: str) -> (
        tuple)[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment]]:
    locations, vehicles, trucks_realised, trucks_planned = read_data(dataset_dir_name, realised_capacity_file_name)

    number_of_vehicles = len(vehicles)
    for truck in trucks_realised.values():
        # Set the capacity of each truck to number of vehicles to make them uncapacitated
        truck.capacity = number_of_vehicles

    # Adapt trucks to make them uncapacitated

    flow_network, commodity_groups = create_flow_network(vehicles=vehicles, trucks=trucks_realised,
                                                         locations=locations)
    vehicle_assignments, truck_assignments = solve_deterministically(flow_network=flow_network,
                                                                     commodity_groups=commodity_groups,
                                                                     locations=locations, vehicles=vehicles,
                                                                     trucks=trucks_realised)
    return vehicle_assignments, truck_assignments
