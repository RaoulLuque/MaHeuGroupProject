import networkx as nx
from networkx import MultiDiGraph

from maheu_group_project.heuristics.common import get_first_last_and_days, convert_trucks_to_dict_by_day
from maheu_group_project.heuristics.flow.types import NodeIdentifier, NodeType, \
    dealership_to_commodity_group, PlannedVehicleAssignment, AssignmentToday, NoAssignmentToday
from maheu_group_project.heuristics.flow.visualize import visualize_flow_network
from maheu_group_project.solution.encoding import Vehicle, TruckIdentifier, Truck, Location, LocationType, \
    TruckAssignment, \
    VehicleAssignment, \
    convert_vehicle_assignments_to_truck_assignments
from datetime import timedelta, date

# Multiplier used to artificially increase the cost of edges that correspond to later trucks, to incentivize earlier
# transportation.
ARTIFICIAL_EDGE_COST_MULTIPLIER = 1


def solve_flow_in_real_time(flow_network: MultiDiGraph, commodity_groups: dict[str, set[int]],
                            locations: list[Location], vehicles: list[Vehicle],
                            trucks_planned: dict[TruckIdentifier, Truck],
                            trucks_realised: dict[TruckIdentifier, Truck]) -> \
        tuple[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment]]:
    """
    Solves the multicommodity min-cost flow problem heuristically by solving multiple single commodity min-cost flow
    problems for each DEALER location and day in the flow network.

    This function iterates over each day (in ascending order) and each DEALER location, solving a min-cost flow problem
    for the vehicles that are due on that day and at that location. The flow network is expected to have been created
    with the `create_flow_network` function.

    In the real-time version,

    Args:
        flow_network (MultiDiGraph[NodeIdentifier]): The flow network to solve.
        commodity_groups (dict[str, set[int]]): A dictionary mapping each commodity group to the set of vehicles (their ids)
        that belong to it.
        locations (list[Location]): List of locations involved in the transportation.
        vehicles (list[Vehicle]): List of vehicles to be transported.
        trucks_planned (dict[TruckIdentifier, Truck]): Dictionary of trucks planned to be available for transportation.
        trucks_realised (dict[TruckIdentifier, Truck]): Dictionary of trucks that have actually been realized.

    Returns:
        tuple: A tuple containing the list of locations, vehicles, and trucks. The trucks and vehicles are adjusted
        to contain their respective plans.
    """
    # Ensure the correct type for flow_network
    flow_network: MultiDiGraph[NodeIdentifier] = flow_network

    # Get the days involved in the flow network
    first_day, last_day, days = get_first_last_and_days(vehicles=vehicles, trucks=trucks_planned)

    # Convert the realized trucks to a dictionary indexed by their departure date
    trucks_realised_by_day: dict[date, dict[TruckIdentifier, Truck]] = convert_trucks_to_dict_by_day(trucks_realised)

    # For each commodity group, find the earliest available date for the vehicles in that group. This way, we can ignore
    # most commodity groups at the beginning.
    earliest_day_in_commodity_groups: dict[str, date] = {}
    for commodity_group, vehicle_ids in commodity_groups.items():
        # Find the earliest available date for the vehicles in the current commodity group
        earliest_day = min(vehicles[vehicle_id].available_date for vehicle_id in vehicle_ids)
        earliest_day_in_commodity_groups[commodity_group] = earliest_day

    # Create variables for final assignments of vehicles and trucks
    final_vehicle_assignments: list[VehicleAssignment] = []
    final_truck_assignments: dict[TruckIdentifier, TruckAssignment] = {}

    visualize_flow_network(flow_network, locations)

    # We iterate over the days from first to last; then those locations which are DEALER locations
    # The current day is the day for which we know the realized trucks. However, before looking
    for current_day in days:
        # Create a variable to store the flows planned for each commodity group
        flow_dict: dict[str, dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]]] = {}

        # Create a variable to store the vehicle assignments planned for the current_day
        current_day_planned_truck_assignments: dict[TruckIdentifier, TruckAssignment] = {}
        current_day_planned_vehicle_assignments: dict[int, PlannedVehicleAssignment] = {}

        # Create a copy of the flow network capacities. These will be loaded after computing all flows for the current day
        capacities_copy = {edge: data['capacity'] for edge, data in flow_network.edges.items()}

        # Iterate over all days and DEALER locations. Note that this flow_day is different to current_day. In the sense that
        # current_day is the day for which we know the realized trucks, while flow_day is the day for which we are currently
        # solving the (single commodity) min-cost flow problem for. That is, for each current_day, we iterate over all days.
        for flow_day in days:
            for location in locations:
                if location.type == LocationType.DEALER:
                    # For each DEALER location, solve a min-cost flow problem with the commodity group corresponding to
                    # the current day and location.
                    commodity_group = dealership_to_commodity_group(NodeIdentifier(flow_day, location, NodeType.NORMAL))

                    # First, check whether there is actually any demand for this commodity group (day and location)
                    target_node = NodeIdentifier(flow_day, location, NodeType.NORMAL)
                    if flow_network.nodes[target_node].get(commodity_group, 0) != 0:
                        # Leave this check out for now
                        # # Check whether vehicles are actually already available at the current day
                        # if current_day >= earliest_day_in_commodity_groups[commodity_group]:

                        # Compute the single commodity min-cost flow for the current commodity group
                        flow = nx.min_cost_flow(flow_network, demand=commodity_group, capacity='capacity',
                                                weight='weight')

                        # Copy the flow to the flow_dict for the current commodity group
                        flow_dict[commodity_group] = copy_flow_and_filter(flow)

                        # Extract the solution from the flow and update the flow network. This only updates the capacities
                        # in the flow network.
                        extract_flow_and_update_network(flow_network=flow_network, flow=flow_dict[commodity_group],
                                                        vehicles_from_current_commodity=commodity_groups[
                                                            commodity_group],
                                                        vehicles=vehicles, current_day=current_day,
                                                        truck_assignments=current_day_planned_truck_assignments,
                                                        vehicle_assignments=current_day_planned_vehicle_assignments)

        # Load the capacities back into the flow network after all flows for the current day have been computed
        for edge, capacity in capacities_copy.items():
            flow_network.edges[edge]['capacity'] = capacity

        # After all days have been processed, we have the planned vehicle assignments for the current day.
        # We now need to try our best to make them work with the realized trucks.

        # First, we check if there are any realized trucks which for the day which have a higher capacity than planned
        trucks_realised_additional_capacity: dict[TruckIdentifier, int] = {}
        for truck_identifier, realised_truck in trucks_realised_by_day.get(current_day, {}).items():
            capacity_difference = compare_capacities_of_trucks(realised_truck, trucks_planned.get(truck_identifier, None))
            if capacity_difference > 0:
                # If so, we add it to the additional capacity dict
                trucks_realised_additional_capacity[realised_truck.get_identifier()] = capacity_difference

        # To this end, we iterate over the realized trucks for the current day and try to assign the vehicles.
        # If there are no realized trucks for the current day, we loop 0 times.
        for realised_truck_identifier, realised_truck in trucks_realised_by_day.get(current_day, {}).items():
            # Iterate over all commodity groups and their vehicles
            for day in days:
                for location in locations:
                    if location.type == LocationType.DEALER:
                        commodity_group = dealership_to_commodity_group(NodeIdentifier(day, location, NodeType.NORMAL))

                        # Get the vehicles from the current commodity group
                        vehicles_from_current_commodity = commodity_groups.get(commodity_group, set())

                        for vehicle_id in vehicles_from_current_commodity:
                            vehicle = current_day_planned_vehicle_assignments.get(vehicle_id, None)
                            if vehicle is not None:
                                match vehicle:
                                    case AssignmentToday(assignment):
                                        if check_if_truck_can_take_another_vehicle(realised_truck_identifier, realised_truck, final_truck_assignments):
                                            assign_vehicle_to_truck
                                    case NoAssignmentToday(next_planned_assignment):
                                        a = 0
                                    case _:
                                        raise TypeError(f"Unexpected type of vehicle assignment: {type(vehicle)}")




    # Return the list of vehicle assignments indexed by their id
    final_vehicle_assignments.sort(key=lambda va: va.id)

    final_truck_assignments = convert_vehicle_assignments_to_truck_assignments(vehicle_assignments=final_vehicle_assignments,
                                                                         trucks=trucks_planned)

    return final_vehicle_assignments, final_truck_assignments


def compare_capacities_of_trucks(this: Truck, other: Truck | None) -> int:
    """
    Compares the capacities of two trucks.

    Args:
        this (Truck): The first truck to compare.
        other (Truck | None): The second truck to compare. If None, the other truck is considered to have capacity 0.

    Returns:
        int: The difference in capacities between the two trucks.
    """
    if other is None:
        return this.capacity
    return this.capacity - other.capacity


def check_if_truck_can_take_another_vehicle(truck_identifier: TruckIdentifier, truck: Truck, truck_assignments: dict[TruckIdentifier, TruckAssignment]) -> bool:
    if truck_identifier not in truck_assignments and truck.capacity > 0:
        # If the truck is not already assigned, we can assign it
        return True
    else:
        # If the truck is already assigned, we check if it has capacity left
        return truck_assignments[truck_identifier].get_capacity_left(truck) > 0


def extract_flow_and_update_network(flow_network: MultiDiGraph,
                                    flow: dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]],
                                    vehicles_from_current_commodity: set[int], vehicles: list[Vehicle],
                                    current_day: date,
                                    truck_assignments: dict[TruckIdentifier, TruckAssignment],
                                    vehicle_assignments: dict[int, PlannedVehicleAssignment]) -> None:
    """
    Extracts the solution in terms of vehicle and truck assignments from a provided flow in a flow network.

    This function adjusts the flow such that it should be empty at the end.
    Furthermore, it adjusts the capacities of the edges used by the flow in the flow network,
    to make them unavailable for the next flows.

    Args:
        flow_network (MultiDiGraph[NodeIdentifier]): The flow network on which the flow is based. The capacities of the
        edges of the flow are adjusted to reflect extracting the solution.
        flow (dict[NodeIdentifier, dict[NodeIdentifier, float]]): The flow from which to extract the solution for the
        vehicles from the current commodity group.
        vehicles_from_current_commodity (set[int]): The set of vehicle ids that belong to the current commodity group.
        vehicles (list[Vehicle]): List of vehicles to be transported to look up their properties using the ids.
        current_day (date): The current day in the flow network, used to determine delays.
        truck_assignments (dict[TruckIdentifier, TruckAssignment]): A dictionary to store the truck assignments for the vehicles.
        vehicle_assignments (dict[int, PlannedVehicleAssignment]): A dictionary to store the planned vehicle assignments

    Returns:
        tuple: A tuple containing the list of locations, vehicles, and trucks. The trucks and vehicles are adjusted
        to contain their respective plans.
    """
    # Ensure the correct type for flow_network
    flow_network: MultiDiGraph[NodeIdentifier] = flow_network

    # Filter out edges which have flow of 0, i.e. no flow was assigned to them.
    flow = copy_flow_and_filter(flow)

    # Loop over the vehicles and extract the assignments
    # For each vehicle, heuristically find the fastest path from its origin to its destination
    for vehicle_id in vehicles_from_current_commodity:
        # Get the actual vehicle from the list of vehicles
        vehicle = vehicles[vehicle_id]

        current_node = NodeIdentifier(day=vehicle.available_date, location=vehicle.origin, type=NodeType.NORMAL)

        # In the following loop, we skip letting the vehicle stay at the same location. Thus, if the vehicle is already
        # at its destination location (possibly not correct date), we will skip this loop.
        while current_node.location != vehicle.destination:
            # Greedily find the next edge from the current node in the flow that has a positive flow value
            next_node = None

            # Get the possible next nodes from the current node in the flow (these will all have non-zero flow)
            possible_next_nodes: list[tuple[NodeIdentifier, dict[int, int]]] = list(flow[current_node].items())

            # Sort the possible next nodes by the day of the node to ensure we always take the earliest possible next node
            possible_next_nodes.sort(key=lambda x: x[0].day)
            for identifier, flows in possible_next_nodes:
                if identifier.location == current_node.location:
                    # We want to skip letting the vehicle stay at the same location for now and only consider moving
                    # it forward
                    continue
                else:
                    # If the next node is a different location, we can take it
                    # This also means, that we are currently 'looking' at an edge that corresponds to a truck
                    next_node = identifier

                    # Find the edge index for this edge
                    edge_index = next(iter(flows.keys()))

                    # We subtract one from the flow of this edge to make it unavailable for the next vehicles
                    flow[current_node][next_node][edge_index] -= 1
                    flow_network[current_node][next_node][edge_index]['capacity'] -= 1

                    # If the flow of this edge is now 0, we remove it from the flow dict
                    if flow[current_node][next_node][edge_index] == 0:
                        del flow[current_node][next_node][edge_index]
                        if not flow[current_node][next_node]:
                            del flow[current_node][next_node]

                    # Update the paths taken, if the edge_number is not 0
                    # Explanation: edge_index starts at 0 by default and increments for parallel edges or are set with
                    # `key` when adding an edge. For trucks, this is set as the truck id which starts at 1, and other
                    # edges cannot have parallel edges (which would result in edge_numbers bigger than 0).
                    if edge_index != 0:
                        # Here, we would usually append the truck to the paths taken of the vehicle.
                        # However, since we are working in the real-time setting, we check if the truck departs on
                        # the current day and then add the vehicle to the trucks' load.
                        if current_node.day == current_day:
                            truck_identifier = TruckIdentifier(start_location=current_node.location,
                                                               end_location=next_node.location,
                                                               truck_number=edge_index,
                                                               departure_date=current_node.day)
                            if truck_identifier not in truck_assignments:
                                # If the truck is not already assigned, we create a new TruckAssignment
                                truck_assignments[truck_identifier] = TruckAssignment(
                                    load=[],
                                )
                            # Add the vehicle to the truck's load
                            truck_assignments[truck_identifier].load.append(vehicle_id)



                    # Set the current node to the next node
                    current_node = next_node

                    break
            if next_node is None:
                # If we have not found a next node, that means we should wait at the current location
                current_node = NodeIdentifier(day=current_node.day + timedelta(days=1),
                                              location=current_node.location,
                                              type=current_node.type)


def copy_flow_and_filter(flow: dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]]) -> dict[
    NodeIdentifier, dict[NodeIdentifier, dict[int, int]]]:
    """
    Creates a copy of the flow and filters out edges that have a flow of 0.

    Args:
        flow (dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]]): The flow to filter.

    Returns:
        dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]]: The filtered flow with only edges that have a
        positive flow.
    """
    # Filter out edges which have flow of 0, i.e. no flow was assigned to them.
    new_filtered_flow = {}
    for src, targets in flow.items():
        filtered_targets = {}
        for dst, keys in targets.items():
            filtered_keys = {k: v for k, v in keys.items() if v > 0}
            if filtered_keys:
                filtered_targets[dst] = filtered_keys
        if filtered_targets:
            new_filtered_flow[src] = filtered_targets
    return new_filtered_flow
