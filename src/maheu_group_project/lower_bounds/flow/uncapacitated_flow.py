from maheu_group_project.heuristics.flow.solve import create_flow_network, solve_deterministically
from maheu_group_project.parsing import read_data
from maheu_group_project.solution.encoding import VehicleAssignment, TruckIdentifier, TruckAssignment


def lower_bound_uncapacitated_flow(dataset_dir_name: str, realised_capacity_file_name: str) -> (
        tuple)[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment]]:
    """
    Solves the vehicle assignment problem using a flow-based approach with uncapacitated trucks.

    Edits the trucks to make them all have practically infinite capacity and then uses the flow network approach from
    `maheu_group_project.heuristics.heuristics.flow` to compute an assignment.

    Args:
        dataset_dir_name (str): The name of the directory containing the dataset files.
        realised_capacity_file_name (str): The name of the CSV file containing truck capacity data.

    Returns:
        tuple: A tuple containing:
            - list[VehicleAssignment]: List of vehicle assignments.
            - dict[TruckIdentifier, TruckAssignment]: Dictionary mapping truck identifiers to their assignments.
    """
    locations, vehicles, trucks_realised, trucks_planned = read_data(dataset_dir_name, realised_capacity_file_name)

    # Adapt trucks to make them uncapacitated
    number_of_vehicles = len(vehicles)
    for truck in trucks_realised.values():
        # Set the capacity of each truck to number of vehicles to make them practically uncapacitated
        truck.capacity = number_of_vehicles

    flow_network, commodity_groups = create_flow_network(vehicles=vehicles, trucks=trucks_realised,
                                                         locations=locations)
    vehicle_assignments, truck_assignments = solve_deterministically(flow_network=flow_network,
                                                                     commodity_groups=commodity_groups,
                                                                     locations=locations, vehicles=vehicles,
                                                                     trucks=trucks_realised)
    return vehicle_assignments, truck_assignments
