import networkx as nx
from networkx import MultiDiGraph

from maheu_group_project.heuristics.common import get_first_last_and_days, convert_trucks_to_dict_by_day
from maheu_group_project.heuristics.flow.network import remove_trucks_from_network, get_start_and_end_nodes_for_truck
from maheu_group_project.heuristics.flow.types import NodeIdentifier, NodeType, \
    dealership_to_commodity_group, PlannedVehicleAssignment, AssignmentToday, NoAssignmentToday, \
    get_day_and_location_for_commodity_group, vehicle_to_commodity_group
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

    # Convert the planned trucks to a dictionary indexed by their departure date
    trucks_planned_by_day: dict[date, dict[TruckIdentifier, Truck]] = convert_trucks_to_dict_by_day(trucks_planned)

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
    final_vehicle_assignments: dict[int, VehicleAssignment] = {}
    final_truck_assignments: dict[TruckIdentifier, TruckAssignment] = {}

    visualize_flow_network(flow_network, locations, commodity_groups)

    # We iterate over the days from first to last; then those locations which are DEALER locations
    # The current day is the day for which we know the realized trucks. However, before looking
    for current_day in days:
        # Create a variable to store the flows planned for each commodity group
        flow_dict: dict[str, dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]]] = {}

        # Create a variable to store the vehicle assignments planned for the current_day
        current_day_planned_vehicle_assignments: dict[int, PlannedVehicleAssignment] = {}

        # Create a copy of the flow network capacities. These will be loaded after computing all flows for the current day
        capacities_copy = {edge: data['capacity'] for edge, data in flow_network.edges.items()}

        # Iterate over all commodity groups solve the single commodity flow problem for them.
        for commodity_group in commodity_groups.keys():
            commodity_group_day, commodity_group_location = get_day_and_location_for_commodity_group(commodity_group)

            # First, check whether there is actually any demand for this commodity group (day and location)
            target_node = NodeIdentifier(commodity_group_day, commodity_group_location, NodeType.NORMAL)
            if flow_network.nodes[target_node].get(commodity_group, 0) != 0:
                # Leave this check out for now
                # # Check whether vehicles are actually already available at the current day
                # if current_day >= earliest_day_in_commodity_groups[commodity_group]:

                # Compute the single commodity min-cost flow for the current commodity group
                flow = nx.min_cost_flow(flow_network, demand=commodity_group, capacity='capacity',
                                        weight='weight')

                # Copy the flow to the flow_dict for the current commodity group
                flow_dict[commodity_group] = copy_flow_and_filter(flow)

                # visualize_flow_network(flow_network, locations, set(commodity_groups.keys()), flow)

                # Extract the solution from the flow and update the flow network. This updates the capacities
                # in the flow network as well as add the next planned vehicle assignments for the current day
                # to the current_day_planned_vehicle_assignments.
                # Note that trucks_realised_by_day is passed to this function, however, only the trucks earlier
                # than the current day are looked at, so no cheating here 🤝 (see get_current_location_of_vehicle_as_node).
                current_day_planned_vehicle_assignments = extract_flow_and_update_network(flow_network=flow_network,
                                                                                          flow=flow_dict[commodity_group],
                                                                                          vehicles_from_current_commodity=commodity_groups[commodity_group],
                                                                                          vehicles=vehicles,
                                                                                          current_day=current_day,
                                                                                          planned_vehicle_assignments=current_day_planned_vehicle_assignments,
                                                                                          final_vehicle_assignments=final_vehicle_assignments,
                                                                                          trucks_realised_by_day=trucks_realised_by_day)

        # Load the capacities back into the flow network after all flows for the current day have been computed
        for edge, capacity in capacities_copy.items():
            flow_network.edges[edge]['capacity'] = capacity

        # After all days have been processed, we have the planned vehicle assignments for the current day.
        # We now need to try our best to make them work with the realized trucks.

        # First, we check if there are any realized trucks which for current day have a higher capacity than planned
        trucks_realised_additional_capacity: dict[TruckIdentifier, int] = {}
        for truck_identifier, realised_truck in trucks_realised_by_day.get(current_day, {}).items():
            capacity_difference = compare_capacities_of_trucks(realised_truck,
                                                               trucks_planned.get(truck_identifier, None))
            if capacity_difference > 0:
                # If so, we add it to the additional capacity dict
                trucks_realised_additional_capacity[realised_truck.get_identifier()] = capacity_difference

        # To this end, we iterate over the commodity groups, their vehicles and then the realized trucks for the current day.
        # Then, we try to assign the vehicles to the realized trucks based on current_day_planned_vehicle_assignments.

        # First, check if there are any realized trucks for the current day. Otherwise, we can skip this day.
        if len(trucks_realised_by_day.get(current_day, {})) != 0:
            # Iterate over all commodity groups and their vehicles
            for commodity_group, vehicles_in_commodity_group in commodity_groups.items():
                if earliest_day_in_commodity_groups[commodity_group] > current_day:
                    # If the earliest day in the commodity group is later than the current day, we skip this commodity group
                    # since there are no vehicles available yet.
                    continue

                for vehicle_id in vehicles_in_commodity_group:
                    # Get the vehicle object from the list of vehicles
                    vehicle = vehicles[vehicle_id]

                    # Get what the vehicle is planned to do today / where it is supposed to move to next
                    next_vehicle_assignment = current_day_planned_vehicle_assignments.get(vehicle_id, None)
                    if next_vehicle_assignment is not None:
                        realised_trucks_today = trucks_realised_by_day[current_day]
                        match next_vehicle_assignment:
                            case AssignmentToday(planned_assignment):
                                # If the vehicle is planned to be assigned to a truck today, we check if there is a truck
                                # on that route today (it might have less capacity than planned, or it might have been
                                # canceled entirely).
                                if check_if_planned_truck_exists_and_has_capacity(planned_assignment,
                                                                                  realised_trucks_today,
                                                                                  final_truck_assignments):
                                    assign_vehicle_to_truck(flow_network, vehicle,
                                                            realised_trucks_today[planned_assignment],
                                                            final_vehicle_assignments, final_truck_assignments)

                            case NoAssignmentToday(next_planned_assignment):
                                # If the vehicle is not planned to be assigned to a truck today, we check if coincidentally
                                # there is a truck on that route today that has more capacity than planned.
                                next_planned_assignment_is_not_free = trucks_planned[next_planned_assignment].price > 0
                                truck_identifier = check_if_there_is_a_suitable_truck_before_schedule(
                                    next_planned_assignment, next_planned_assignment_is_not_free, realised_trucks_today,
                                    trucks_realised_additional_capacity)

                                if truck_identifier is not None:
                                    # We subtract one from the additional capacity of the truck, since we are assigning a
                                    # vehicle to it.
                                    trucks_realised_additional_capacity[truck_identifier] -= 1
                                    assign_vehicle_to_truck(flow_network, vehicle,
                                                            realised_trucks_today[truck_identifier],
                                                            final_vehicle_assignments, final_truck_assignments)

                            case _:
                                raise TypeError(
                                    f"Unexpected type of vehicle assignment: {type(next_vehicle_assignment)}")

            # Remove edges for the current day from the flow network, so that they are not accidentally used in the
            # next iteration.
            remove_trucks_from_network(flow_network, trucks_planned_by_day.get(current_day, {}))

            visualize_flow_network(flow_network, locations, set(commodity_groups.keys()))

    # Convert the final_vehicle_assignments to a list and sort them by their id
    final_vehicle_assignments: list[VehicleAssignment] = list(final_vehicle_assignments.values())
    final_vehicle_assignments.sort(key=lambda va: va.id)

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


def check_if_planned_truck_exists_and_has_capacity(planned_assignment: TruckIdentifier,
                                                   realised_trucks: dict[TruckIdentifier, Truck],
                                                   truck_assignments: dict[TruckIdentifier, TruckAssignment]) -> bool:
    """
    Checks if a planned truck exists in the realized trucks and if it has capacity left.

    Args:
        planned_assignment (TruckIdentifier): The identifier of the planned truck.
        realised_trucks (dict[TruckIdentifier, Truck]): A dictionary of realized trucks indexed by their identifiers. This is used
            to check if the planned truck actually travels today.
        truck_assignments (dict[TruckIdentifier, TruckAssignment]): A dictionary of truck assignments indexed by their identifiers.
            This is used to check if the truck has capacity left.

    Returns:
        bool: True if the planned truck exists in the realized trucks and has capacity left, False otherwise.
    """
    if planned_assignment not in realised_trucks:
        # If the planned truck does not exist in the realized trucks, we return None
        return False
    else:
        # If the truck does not exist yet, we just check if it has capacity greater than 0.
        if planned_assignment not in truck_assignments:
            return realised_trucks[planned_assignment].capacity > 0
        else:
            # If the truck is already assigned, we check if it has capacity left
            return truck_assignments[planned_assignment].get_capacity_left(realised_trucks[planned_assignment]) > 0


def check_if_there_is_a_suitable_truck_before_schedule(planned_assignment: TruckIdentifier,
                                                       planned_assignment_is_not_free: bool,
                                                       realised_trucks_today: dict[TruckIdentifier, Truck],
                                                       trucks_realised_additional_capacity: dict[
                                                           TruckIdentifier, int]) -> TruckIdentifier | None:
    """
    Checks if there is a suitable truck for the planned assignment before the scheduled assignment.
    A truck is considered suitable if it travels on the same route as the planned assignment, has additional capacity,
    and either has a price of 0 or does not but the planned assignment is also not free.


    Args:
        planned_assignment (TruckIdentifier): The identifier of the planned truck assignment.
        planned_assignment_is_not_free (bool): Whether the planned assignment is not free (i.e., has a price > 0).
        realised_trucks_today (dict[TruckIdentifier, Truck]): A dictionary of realized trucks for today indexed by their identifiers.
        trucks_realised_additional_capacity (dict[TruckIdentifier, int]): A dictionary of realized trucks for today with additional capacity indexed by their identifiers.

    Returns:
        TruckIdentifier | None: The identifier of the suitable truck if found, None otherwise.
    """
    for realised_truck_identifier, realised_truck in realised_trucks_today.items():
        # First, we check if the truck has additional capacity compared to the planned assignment
        if trucks_realised_additional_capacity.get(realised_truck_identifier, 0) > 0:
            if realised_truck_identifier.start_location == planned_assignment.start_location and \
                    realised_truck_identifier.end_location == planned_assignment.end_location:
                # At last, we check if the costs match the planned assignment
                if realised_truck.price == 0 or planned_assignment_is_not_free:
                    # We found a suitable truck and return its truck identifier.
                    return realised_truck_identifier
    return None


def assign_vehicle_to_truck(flow_network: MultiDiGraph, vehicle: Vehicle, truck: Truck,
                            vehicle_assignments: dict[int, VehicleAssignment],
                            truck_assignments: dict[TruckIdentifier, TruckAssignment]):
    """
    Assigns a vehicle to a truck and updates the vehicle and truck assignments.
    Also updates the flow network to reflect the assignment. That is, adapt the demand on the start and end node of the
    edge/truck taken by the vehicle.

    Args:
        flow_network (MultiDiGraph[NodeIdentifier]): The flow network we are working with.
        vehicle (Vehicle): The vehicle to be assigned to the truck.
        truck (Truck): The truck object to which the vehicle is assigned.
        vehicle_assignments (dict[int, VehicleAssignment]): A dictionary mapping vehicle ids to their assignments.
        truck_assignments (dict[TruckIdentifier, TruckAssignment]): A dictionary mapping truck identifiers to their assignments.
    """
    # Ensure the correct type for flow_network
    flow_network: MultiDiGraph[NodeIdentifier] = flow_network

    # Get the truck identifier from the truck object
    truck_identifier = truck.get_identifier()

    # Get the vehicle id from the vehicle object
    vehicle_id = vehicle.id

    # Adapt the truck and vehicle assignments
    # Adapt the vehicle assignment
    if vehicle_id not in vehicle_assignments:
        # Create a new VehicleAssignment if not present yet
        vehicle_assignments[vehicle_id] = VehicleAssignment(id=vehicle_id)
    vehicle_assignments[vehicle_id].paths_taken.append(truck_identifier)

    if truck_identifier not in truck_assignments:
        # Create a new TruckAssignment if not present yet
        truck_assignments[truck_identifier] = TruckAssignment(load=[])
    truck_assignments[truck_identifier].load.append(vehicle_id)
    # If the truck is not already assigned, we create a new TruckAssignment
    if truck_identifier not in truck_assignments:
        truck_assignments[truck_identifier] = TruckAssignment(load=[])
    # Add the vehicle to the truck's load
    truck_assignments[truck_identifier].load.append(vehicle_id)

    # Adapt the flow network to reflect the assignment
    edge_start_node, edge_end_node = get_start_and_end_nodes_for_truck(truck)

    # Adapt the demand on the nodes.
    commodity_group = vehicle_to_commodity_group(vehicle)

    # Negative demand means that the node is a source, positive demand means that the node is a sink.
    assert flow_network.nodes[edge_start_node][commodity_group] < 0
    flow_network.nodes[edge_start_node][commodity_group] += 1

    # The end node of the edge is only supposed to have a positive value, if it is the destination of the vehicle.
    # In fact, it might not even have an entry for the current commodity group at all.
    if edge_end_node.location == vehicle.destination:
        assert flow_network.nodes[edge_end_node][commodity_group] > 0
    if commodity_group not in flow_network.nodes[edge_end_node]:
        flow_network.nodes[edge_end_node][commodity_group] = 0
    flow_network.nodes[edge_end_node][commodity_group] -= 1


def extract_flow_and_update_network(flow_network: MultiDiGraph,
                                    flow: dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]],
                                    vehicles_from_current_commodity: set[int], vehicles: list[Vehicle],
                                    current_day: date,
                                    planned_vehicle_assignments: dict[int, PlannedVehicleAssignment],
                                    final_vehicle_assignments: dict[int, VehicleAssignment],
                                    trucks_realised_by_day: dict[date, dict[TruckIdentifier, Truck]]) -> dict[int, PlannedVehicleAssignment]:
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
        planned_vehicle_assignments (dict[int, PlannedVehicleAssignment]): A dictionary containing the planned vehicle assignments for current_day.
        final_vehicle_assignments (dict[int, VehicleAssignment]): A dictionary containing the final vehicle assignments.
        trucks_realised_by_day (dict[date, dict[TruckIdentifier, Truck]]): A dictionary mapping each day to the realized trucks for that day.
            Note that we only use entries in the dictionary that are earlier than the current day (see get_current_location_of_vehicle_as_node).

    Returns:
        dict[int, PlannedVehicleAssignment]: A dictionary containing the updated planned vehicle assignments for the
        current day. The keys are the vehicle ids and the values are the PlannedVehicleAssignment objects.
    """
    # Ensure the correct type for flow_network
    flow_network: MultiDiGraph[NodeIdentifier] = flow_network

    # Filter out edges which have a flow of 0, i.e. no flow was assigned to them.
    flow = copy_flow_and_filter(flow)

    # Loop over the vehicles and extract the assignments
    # For each vehicle, heuristically find the fastest path from its origin to its destination
    for vehicle_id in vehicles_from_current_commodity:
        # Get the actual vehicle from the list of vehicles
        vehicle = vehicles[vehicle_id]

        current_node = get_current_location_of_vehicle_as_node(vehicle, final_vehicle_assignments,
                                                               trucks_realised_by_day)
        planned_assignment_done = False

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

                    # This should be removable
                    # # Update the paths taken, if the edge_number is not 0
                    # # Explanation: edge_index starts at 0 by default and increments for parallel edges or are set with
                    # # `key` when adding an edge. For trucks, this is set as the truck id which starts at 1, and other
                    # # edges cannot have parallel edges (which would result in edge_numbers bigger than 0).
                    # if edge_index != 0:

                    # Here, we would usually append the truck to the paths taken of the vehicle.
                    # However, since we are in the real-time setting, we only store what the next planned truck is,
                    # that the vehicle is supposed to take. We distinguish whether the trucks is planned for today or
                    # a day after.
                    # We only want to do this for the first edge we find, hence the planned_assignment_done flag.
                    if not planned_assignment_done:
                        # Assert that the current node is not before current_day
                        assert current_node.day >= current_day

                        truck_identifier = TruckIdentifier(start_location=current_node.location,
                                                           end_location=next_node.location,
                                                           truck_number=edge_index,
                                                           departure_date=current_node.day)

                        if current_node.day == current_day:
                            planned_vehicle_assignments[vehicle_id] = AssignmentToday(assignment=truck_identifier)
                        elif current_node.day > current_day:
                            planned_vehicle_assignments[vehicle_id] = NoAssignmentToday(
                                next_planned_assignment=truck_identifier)

                        planned_assignment_done = True

                    # Set the current node to the next node
                    current_node = next_node

                    break
            if next_node is None:
                # If we have not found a next node, that means we should wait at the current location
                current_node = NodeIdentifier(day=current_node.day + timedelta(days=1),
                                              location=current_node.location,
                                              type=current_node.type)

    return planned_vehicle_assignments


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


def get_current_location_of_vehicle_as_node(vehicle: Vehicle, final_vehicle_assignments: dict[int, VehicleAssignment],
                                            trucks_realised_by_day: dict[
                                                date, dict[TruckIdentifier, Truck]]) -> NodeIdentifier:
    """
    Returns the current location of a vehicle as a NodeIdentifier. It is determined based on the vehicle's assignment.
    If an assignment exists, the last location in the paths taken is used to determine the current location. Otherwise,
    the origin of the vehicle is used.

    The current location is determined based on the vehicle's

    Args:
        vehicle (Vehicle): The vehicle for which to get the current location.
        final_vehicle_assignments (dict[int, VehicleAssignment]): A dictionary mapping vehicle ids to their final assignments.
        trucks_realised_by_day (dict[date, dict[TruckIdentifier, Truck]]): A dictionary mapping each day to the realized trucks for that day.

    Returns:
        NodeIdentifier: The current location of the vehicle.
    """
    if vehicle.id in final_vehicle_assignments:
        # If the vehicle has an assignment, we use the last location in the paths taken
        current_assignment = final_vehicle_assignments[vehicle.id]
        last_truck_identifier = current_assignment.paths_taken[-1]

        # This is where we access trucks_realised_by_day. We use last_truck_identifier, which has to be in the past,
        # since it was assigned in a previous loop of the solve_flow_in_real_time function.
        # We use get_start_and_end_nodes_for_truck, since this accounts for the one rest-day of the truck if it does
        # not arrive at a DEALER location.
        _, end_node = get_start_and_end_nodes_for_truck(
            trucks_realised_by_day[last_truck_identifier.departure_date][last_truck_identifier])
        arrival_date = end_node.day

        return NodeIdentifier(day=arrival_date,
                              location=last_truck_identifier.end_location,
                              type=NodeType.NORMAL)
    else:
        return NodeIdentifier(day=vehicle.available_date,
                              location=vehicle.origin,
                              type=NodeType.NORMAL)
