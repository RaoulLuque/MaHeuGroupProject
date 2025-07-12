import copy

import networkx as nx
from networkx import MultiDiGraph

from maheu_group_project.heuristics.common import get_first_last_and_days, convert_trucks_to_dict_by_day
from maheu_group_project.heuristics.flow.handle_flows import copy_flow_and_filter, \
    extract_flow_update_network_and_obtain_planned_assignment
from maheu_group_project.heuristics.flow.mip.solve_mip import solve_mip
from maheu_group_project.heuristics.flow.mip.translation import translate_flow_network_to_mip, \
    translate_mip_solution_to_flow
from maheu_group_project.heuristics.flow.network import remove_trucks_from_network, update_delay_nodes_in_flow_network
from maheu_group_project.heuristics.flow.types import NodeIdentifier, NodeType, \
    PlannedVehicleAssignment, AssignmentToday, NoAssignmentToday, \
    get_day_and_location_for_commodity_group, vehicle_to_commodity_group, InfeasibleAssignment, \
    get_current_location_of_vehicle_as_node, get_start_and_end_nodes_for_truck
from maheu_group_project.heuristics.flow.visualize import visualize_flow_network
from maheu_group_project.solution.encoding import Vehicle, TruckIdentifier, Truck, Location, \
    TruckAssignment, VehicleAssignment
from datetime import timedelta, date

# Multiplier used to artificially increase the cost of edges that correspond to later trucks, to incentivize earlier
# transportation.
ARTIFICIAL_EDGE_COST_MULTIPLIER = 1

UPDATE_DELAY_NODES_IN_FLOW_NETWORK = True


def solve_flow_in_real_time(flow_network: MultiDiGraph, commodity_groups: dict[str, set[int]],
                            locations: list[Location], vehicles: list[Vehicle],
                            trucks_planned: dict[TruckIdentifier, Truck],
                            trucks_realised: dict[TruckIdentifier, Truck],
                            solve_as_mip: bool) -> \
        tuple[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment]]:
    """
    Solves the multicommodity min-cost flow problem heuristically by solving multiple single commodity min-cost flow
    problems for each DEALER location and day in the flow network.

    If solve_as_mip == False:
    This function iterates over the days on which vehicles might be transported (current_day), and for each of these
    days, over all commodities. For each commodity, it solves the single commodity min-cost flow problem and extracts
    an assignment of vehicles to trucks from the resulting flow. This is then compared with the realized trucks for the
    current day, and the assignments are adjusted accordingly.

    If solve_as_mip == True:
    The multicommodity min-cost flow problem is solved using a MIP formulation.

    Args:
        flow_network (MultiDiGraph[NodeIdentifier]): The flow network to solve.
        commodity_groups (dict[str, set[int]]): A dictionary mapping each commodity group to the set of vehicles (their ids)
        that belong to it.
        locations (list[Location]): List of locations involved in the transportation.
        vehicles (list[Vehicle]): List of vehicles to be transported.
        trucks_planned (dict[TruckIdentifier, Truck]): Dictionary of trucks planned to be available for transportation.
        trucks_realised (dict[TruckIdentifier, Truck]): Dictionary of trucks that have actually been realized.
        solve_as_mip (bool): If True, the flow network is solved using a MIP formulation. If False, it is solved using a heuristic

    Returns:
            A tuple containing:
            - A list of VehicleAssignment objects representing the assignments of vehicles to trucks.
            - A dictionary mapping TruckIdentifiers to TruckAssignment objects representing the assignments of trucks.
    """
    # Ensure the correct type for flow_network
    flow_network: MultiDiGraph[NodeIdentifier] = flow_network

    # Get the days involved in the flow network
    first_day, last_day, days = get_first_last_and_days(vehicles=vehicles, trucks=trucks_planned)

    # Convert the planned trucks to a dictionary indexed by their departure date
    trucks_planned_by_day: dict[date, dict[TruckIdentifier, Truck]] = convert_trucks_to_dict_by_day(trucks_planned)
    # Convert the realized trucks to a dictionary indexed by their departure date
    trucks_realised_by_day: dict[date, dict[TruckIdentifier, Truck]] = convert_trucks_to_dict_by_day(trucks_realised)
    # This dictionary will hold all realized trucks for the days we know about (the past).
    trucks_realised_by_day_known: dict[date, dict[TruckIdentifier, Truck]] = {}

    # Keep track of which commodity groups have been satisfied, that is, all vehicles in that group have arrived
    remaining_commodity_groups: dict[str, set[int]] = copy.deepcopy(commodity_groups)

    # For each commodity group, find the earliest available date for the vehicles in that group. This way, we can ignore
    # most commodity groups at the beginning.
    earliest_day_in_commodity_groups: dict[str, date] = {}
    for commodity_group, vehicle_ids in commodity_groups.items():
        # Find the earliest available date for the vehicles in the current commodity group
        earliest_day = min(vehicles[vehicle_id].available_date for vehicle_id in vehicle_ids)
        earliest_day_in_commodity_groups[commodity_group] = earliest_day

    # Create variables for final assignments of vehicles and trucks
    vehicle_assignments: dict[int, VehicleAssignment] = {}
    truck_assignments: dict[TruckIdentifier, TruckAssignment] = {}

    # We iterate over the days from first to last; then those locations which are DEALER locations
    # The current day is the day for which we know the realized trucks. However, before looking
    for current_day in days:
        # Create a variable to store the vehicle assignments planned for the current_day
        current_day_planned_vehicle_assignments: dict[int, PlannedVehicleAssignment] = {}

        # Create a copy of the flow network capacities. These will be loaded after computing all flows for the current day
        capacities_copy = {edge: data['capacity'] for edge, data in flow_network.edges.items()}

        # Visualize
        # visualize_flow_network(flow_network, locations, current_commodity='2025-06-08_FRA01')

        if not solve_as_mip:
            # Iterate over all commodity groups and solve the single commodity flow problem for each of them.
            for commodity_group in remaining_commodity_groups.keys():
                commodity_group_day, commodity_group_location = get_day_and_location_for_commodity_group(
                    commodity_group)

                # First, check whether there is actually any demand for this commodity group (day and location)
                target_node = NodeIdentifier(commodity_group_day, commodity_group_location, NodeType.NORMAL)
                if flow_network.nodes[target_node].get(commodity_group, 0) != 0:
                    # Leave this check out for now
                    # # Check whether vehicles are actually already available at the current day
                    # if current_day >= earliest_day_in_commodity_groups[commodity_group]:

                    # Compute the single commodity min-cost flow for the current commodity group
                    try:
                        flow = nx.min_cost_flow(flow_network, demand=commodity_group, capacity='capacity',
                                                weight='weight')

                        # Copy the flow to the flow_dict for the current commodity group
                        filtered_flow = copy_flow_and_filter(flow)

                        # Extract the solution from the flow and update the flow network. This updates the capacities
                        # in the flow network as well as add the next planned vehicle assignments for the current day
                        # to the current_day_planned_vehicle_assignments.
                        current_day_planned_vehicle_assignments = extract_flow_update_network_and_obtain_planned_assignment(
                            flow_network=flow_network,
                            flow=filtered_flow,
                            vehicles_from_current_commodity=remaining_commodity_groups[commodity_group],
                            vehicles=vehicles,
                            current_day=current_day,
                            planned_vehicle_assignments=current_day_planned_vehicle_assignments,
                            vehicle_assignments=vehicle_assignments,
                            trucks_realised_by_day_known=trucks_realised_by_day_known)
                    except nx.NetworkXUnfeasible:
                        # If the flow is unfeasible, this means that in the planned setting, the vehicles would not be able
                        # to reach their destination. However, we note this in the planned_vehicle_assignments and hope
                        # that the realized trucks can help us out.
                        for vehicle_id in remaining_commodity_groups[commodity_group]:
                            vehicle = vehicles[vehicle_id]
                            # Only assign the InfeasibleAssignment if the vehicle has not already arrived at its destination
                            if get_current_location_of_vehicle_as_node(vehicle, vehicle_assignments,
                                                                       trucks_realised_by_day_known).location != vehicle.destination:
                                current_day_planned_vehicle_assignments[vehicle_id] = InfeasibleAssignment()

        else:
            # visualize_flow_network(flow_network, locations, set(commodity_groups.keys()))

            # We solve the multicommodity min-cost flow problem using a MIP formulation.
            model, flow_vars, node_mapping = translate_flow_network_to_mip(flow_network,
                                                                           set(remaining_commodity_groups.keys()))
            solve_mip(model)
            flow_solution = translate_mip_solution_to_flow(model, flow_vars)

            for commodity_group in remaining_commodity_groups.keys():
                # Extract the solution for the current commodity group
                commodity_flow = flow_solution.get(commodity_group, {})
                if commodity_flow:
                    # Extract the solution from the flow and update the flow network. This updates the capacities
                    # in the flow network as well as add the next planned vehicle assignments for the current day
                    # to the current_day_planned_vehicle_assignments.
                    current_day_planned_vehicle_assignments = extract_flow_update_network_and_obtain_planned_assignment(
                        flow_network=flow_network,
                        flow=commodity_flow,
                        vehicles_from_current_commodity=remaining_commodity_groups[commodity_group],
                        vehicles=vehicles,
                        current_day=current_day,
                        planned_vehicle_assignments=current_day_planned_vehicle_assignments,
                        vehicle_assignments=vehicle_assignments,
                        trucks_realised_by_day_known=trucks_realised_by_day_known)

        # Load the capacities back into the flow network after all flows for the current day have been computed
        for edge, capacity in capacities_copy.items():
            flow_network.edges[edge]['capacity'] = capacity

        # After all days have been processed, we have the planned vehicle assignments for the current day.
        # We now need to try our best to make them work with the realized trucks.
        realised_trucks_today = trucks_realised_by_day.get(current_day, {})
        trucks_realised_by_day_known[current_day] = realised_trucks_today

        # First, we check if there are any realized trucks which for current day have a higher capacity than planned
        trucks_realised_additional_capacity: dict[TruckIdentifier, int] = {}
        for truck_identifier, realised_truck in realised_trucks_today.items():
            capacity_difference = compare_capacities_of_trucks(realised_truck,
                                                               trucks_planned.get(truck_identifier, None))
            if capacity_difference > 0:
                # If so, we add it to the additional capacity dict
                trucks_realised_additional_capacity[realised_truck.get_identifier()] = capacity_difference

        # To this end, we iterate over the commodity groups, their vehicles and then the realized trucks for the current day.
        # Then, we try to assign the vehicles to the realized trucks based on current_day_planned_vehicle_assignments.

        # This dict keeps track of the vehicles that arrived at their destination today, to delete them from the
        # remaining_commodity_groups after the iteration (can't edit a dict while iterating over it).
        vehicles_arrived_today: dict[str, set[int]] = {}

        # First, check if there are any realized trucks for the current day. Otherwise, we can skip this day.
        if len(realised_trucks_today) != 0:
            # Iterate over all commodity groups and their vehicles
            for commodity_group, vehicles_in_commodity_group in remaining_commodity_groups.items():
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
                        match next_vehicle_assignment:
                            case AssignmentToday(planned_assignment):
                                # If the vehicle is planned to be assigned to a truck today, we check if there is a truck
                                # on that route today (it might have less capacity than planned, or it might have been
                                # canceled entirely).
                                if check_if_planned_truck_exists_and_has_capacity(planned_assignment,
                                                                                  realised_trucks_today,
                                                                                  truck_assignments):
                                    assign_vehicle_to_truck(flow_network, vehicle,
                                                            realised_trucks_today[planned_assignment],
                                                            vehicle_assignments,
                                                            truck_assignments,
                                                            trucks_realised_by_day_known,
                                                            vehicles_arrived_today)

                            case NoAssignmentToday(next_planned_assignment):
                                # If there are no trucks which have unexpected additional capacity, we cannot explore this option.
                                if len(trucks_realised_additional_capacity) != 0:
                                    # We first need to check, if the vehicle is currently enjoying its rest day.
                                    earliest_day_vehicle_is_available = get_current_location_of_vehicle_as_node(vehicle,
                                                                                                                vehicle_assignments,
                                                                                                                trucks_realised_by_day_known).day
                                    if current_day < earliest_day_vehicle_is_available:
                                        continue

                                    # If the vehicle is not planned to be assigned to a truck today, we check if coincidentally
                                    # there is a truck on that route today that has more capacity than planned.
                                    next_planned_assignment_is_not_free = trucks_planned[
                                                                              next_planned_assignment].price > 0
                                    truck_identifier = check_if_there_is_a_suitable_truck_before_schedule(
                                        next_planned_assignment, next_planned_assignment_is_not_free,
                                        realised_trucks_today,
                                        trucks_realised_additional_capacity)

                                    if truck_identifier is not None:
                                        # We subtract one from the additional capacity of the truck, since we are assigning a
                                        # vehicle to it.
                                        trucks_realised_additional_capacity[truck_identifier] -= 1
                                        assign_vehicle_to_truck(flow_network, vehicle,
                                                                realised_trucks_today[truck_identifier],
                                                                vehicle_assignments,
                                                                truck_assignments,
                                                                trucks_realised_by_day_known,
                                                                vehicles_arrived_today)

                            case InfeasibleAssignment():
                                # This can only happen, if the flow of the respective commodity group was infeasible.
                                # That is, there were no planned trucks available and in the planned setting the vehicle
                                # would not be able to arrive its destination. We now hope that there is a realised truck
                                # available that can take the vehicle.
                                # TODO: Make this more general and not only check for trucks that do the last segment

                                # Get the current location of the vehicle
                                current_location_of_vehicle = get_current_location_of_vehicle_as_node(vehicle,
                                                                                                      vehicle_assignments,
                                                                                                      trucks_realised_by_day_known)

                                # Make sure that the vehicle is available already (might need a rest day)
                                if current_day < current_location_of_vehicle.day:
                                    continue

                                # Check if there is a truck in the realised trucks with additional capacity that can take the vehicle
                                # directly to its destination
                                # TODO: Sort this iteration by departure date of the truck and then price
                                for truck_identifier, capacity in trucks_realised_additional_capacity.items():
                                    if capacity > 0:
                                        if truck_identifier.start_location == current_location_of_vehicle and \
                                                truck_identifier.end_location == vehicle.destination:
                                            if solve_as_mip:
                                                raise (ValueError,
                                                       "InfeasibleAssignment should not occur in the solve_as_mip case")
                                            # We found a truck that can take the vehicle directly to its destination
                                            trucks_realised_additional_capacity[truck_identifier] -= 1
                                            assign_vehicle_to_truck(flow_network, vehicle,
                                                                    realised_trucks_today[truck_identifier],
                                                                    vehicle_assignments,
                                                                    truck_assignments,
                                                                    trucks_realised_by_day_known,
                                                                    vehicles_arrived_today)
                                            # We can break here, since we only want to assign the vehicle to one truck
                                            break

                            case _:
                                raise TypeError(
                                    f"Unexpected type of vehicle assignment: {type(next_vehicle_assignment)}")

                    else:
                        # In this case, the vehicle has arrived at its destination already, so we can just continue
                        continue

            # Remove the vehicles that arrived today from the remaining_commodity_groups
            for commodity_group, set_of_vehicles_arrived_today in vehicles_arrived_today.items():
                remaining_commodity_groups[commodity_group].difference_update(set_of_vehicles_arrived_today)

                if len(remaining_commodity_groups[commodity_group]) == 0:
                    # If the remaining commodity group is empty, we can remove it from the remaining_commodity_groups
                    del remaining_commodity_groups[commodity_group]

            # visualize_flow_network(flow_network, locations, set(commodity_groups.keys()))

        # Remove edges for the current day from the flow network, so that they are not accidentally used in the
        # next iteration.
        remove_trucks_from_network(flow_network, trucks_planned_by_day.get(current_day, {}))

        # Visualize
        # visualize_flow_network(flow_network, locations, current_commodity='2025-06-08_FRA01')

        # Depending on UPDATE_DELAY_NODES_IN_FLOW_NETWORK, we update the delay nodes in the flow network.
        if UPDATE_DELAY_NODES_IN_FLOW_NETWORK:
            if current_day + timedelta(days=7) <= last_day:
                update_delay_nodes_in_flow_network(flow_network, current_day, locations)

    # Convert the vehicle_assignments to a list and sort them by their id
    vehicle_assignments: list[VehicleAssignment] = list(vehicle_assignments.values())
    vehicle_assignments.sort(key=lambda va: va.id)

    # Make sure the truck assignments contains all trucks
    for truck_identifier in trucks_realised.keys():
        if truck_identifier not in truck_assignments:
            truck_assignments[truck_identifier] = TruckAssignment(load=[])

    return vehicle_assignments, truck_assignments


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
                            truck_assignments: dict[TruckIdentifier, TruckAssignment],
                            trucks_realised_by_day_known: dict[date, dict[TruckIdentifier, Truck]],
                            vehicles_arrived_today: dict[str, set[int]]) -> None:
    """
    Assigns a vehicle to a truck and updates the vehicle and truck assignments.
    Also updates the flow network to reflect the assignment. That is, adapt the demand on the node the vehicle is
    currently at and the end node of the edge / truck taken by the vehicle.

    Args:
        flow_network (MultiDiGraph[NodeIdentifier]): The flow network we are working with.
        vehicle (Vehicle): The vehicle to be assigned to the truck.
        truck (Truck): The truck object to which the vehicle is assigned.
        vehicle_assignments (dict[int, VehicleAssignment]): A dictionary mapping vehicle ids to their assignments.
        truck_assignments (dict[TruckIdentifier, TruckAssignment]): A dictionary mapping truck identifiers to their assignments.
        trucks_realised_by_day_known (dict[date, dict[TruckIdentifier, Truck]]): A dictionary mapping each day to the realized trucks for that day.
            Note that this dict only contains entries for days earlier than current_day.
        vehicles_arrived_today (dict[str, set[int]]): A dictionary that keeps track of the vehicles that arrived at
            their destination today. This is used to remove them from the remaining_commodity_groups afterwards.
    """
    # Ensure the correct type for flow_network
    flow_network: MultiDiGraph[NodeIdentifier] = flow_network

    # Get the truck identifier from the truck object
    truck_identifier = truck.get_identifier()

    # Get the vehicle id from the vehicle object
    vehicle_id = vehicle.id

    # If the truck is not already assigned, we create a new TruckAssignment
    if truck_identifier not in truck_assignments:
        truck_assignments[truck_identifier] = TruckAssignment(load=[])

    # Check capacity before assignment to prevent race conditions
    if truck_assignments[truck_identifier].get_capacity_left(truck) <= 0:
        raise RuntimeError(f"Cannot assign vehicle {vehicle_id} to truck {truck_identifier}: "
                           f"truck has no capacity left (current load: {len(truck_assignments[truck_identifier].load)}, "
                           f"truck capacity: {truck.capacity})")

    # Adapt the flow network to reflect the assignment
    _, edge_end_node = get_start_and_end_nodes_for_truck(truck)
    edge_start_node = get_current_location_of_vehicle_as_node(vehicle, vehicle_assignments,
                                                              trucks_realised_by_day_known)
    vehicle_destination_node = NodeIdentifier(day=vehicle.due_date, location=vehicle.destination, type=NodeType.NORMAL)

    # Adapt the demand on the nodes.
    commodity_group = vehicle_to_commodity_group(vehicle)

    # Negative demand means that the node is a source, positive demand means that the node is a sink.
    assert flow_network.nodes[edge_start_node][commodity_group] < 0
    flow_network.nodes[edge_start_node][commodity_group] += 1

    # The end node of the edge is only supposed to have a positive value, if it is the destination of the vehicle.
    # In fact, it might not even have an entry for the current commodity group at all.
    if edge_end_node.location == vehicle.destination:
        # The vehicle has arrived at its destination
        assert flow_network.nodes[vehicle_destination_node][commodity_group] > 0
        flow_network.nodes[vehicle_destination_node][commodity_group] -= 1

        # Take care of delays
        if edge_end_node.day > vehicle.due_date:
            if vehicle_id not in vehicle_assignments:
                # Create a new VehicleAssignment if not present yet
                vehicle_assignments[vehicle_id] = VehicleAssignment(id=vehicle_id)

            vehicle_assignments[vehicle_id].delayed_by = max(timedelta(days=0), edge_end_node.day - vehicle.due_date)

        if commodity_group not in vehicles_arrived_today:
            vehicles_arrived_today[commodity_group] = set()

        # Update remaining_commodity_groups
        vehicles_arrived_today[commodity_group].add(vehicle_id)

    else:
        if commodity_group not in flow_network.nodes[edge_end_node]:
            flow_network.nodes[edge_end_node][commodity_group] = 0
        flow_network.nodes[edge_end_node][commodity_group] -= 1

    # Adapt the truck and vehicle assignments
    # Adapt the vehicle assignment
    if vehicle_id not in vehicle_assignments:
        # Create a new VehicleAssignment if not present yet
        vehicle_assignments[vehicle_id] = VehicleAssignment(id=vehicle_id)
    vehicle_assignments[vehicle_id].paths_taken.append(truck_identifier)

    # Add the vehicle to the truck's load
    truck_assignments[truck_identifier].load.append(vehicle_id)
