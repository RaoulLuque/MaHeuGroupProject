from maheu_group_project.heuristics.flow.solve_deterministically import solve_flow_deterministically
from maheu_group_project.heuristics.flow.network import create_flow_network
from maheu_group_project.parsing import read_data
from maheu_group_project.solution.encoding import VehicleAssignment, TruckIdentifier, TruckAssignment, Truck


def lower_bound_uncapacitated_flow(dataset_dir_name: str, realised_capacity_file_name: str) -> (
        tuple)[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment], dict[TruckIdentifier, Truck]]:
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
            - dict[TruckIdentifier, Truck]: Dictionary mapping truck identifiers to Truck objects with uncapped
            capacities.
    """
    locations, vehicles, trucks_realised, trucks_planned = read_data(dataset_dir_name, realised_capacity_file_name)

    # Adapt trucks to make them uncapacitated
    number_of_vehicles = len(vehicles)
    for truck_identifier, truck in trucks_realised.items():
        current_capacity = truck.capacity
        current_price = truck.price
        factor = (number_of_vehicles // current_capacity) + 1
        # Set the capacity of each truck to number of vehicles to make them practically uncapacitated
        trucks_realised[truck_identifier] = truck.new_from_self(capacity=current_capacity * factor, price=current_price * factor)

    flow_network, commodity_groups = create_flow_network(vehicles=vehicles, trucks=trucks_realised,
                                                         locations=locations)
    vehicle_assignments, truck_assignments = solve_flow_deterministically(flow_network=flow_network,
                                                                          commodity_groups=commodity_groups,
                                                                          locations=locations, vehicles=vehicles,
                                                                          trucks=trucks_realised)
    return vehicle_assignments, truck_assignments, trucks_realised
