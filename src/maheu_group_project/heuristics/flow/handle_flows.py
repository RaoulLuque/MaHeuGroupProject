from datetime import date, timedelta

from networkx import MultiDiGraph

from maheu_group_project.heuristics.flow.types import NodeIdentifier, NodeType, PlannedVehicleAssignment, \
    AssignmentToday, NoAssignmentToday, get_current_location_of_vehicle_as_node
from maheu_group_project.solution.encoding import Vehicle, VehicleAssignment, TruckIdentifier, Truck


def extract_flow_update_network_and_obtain_final_assignment(flow_network: MultiDiGraph | None,
                                                            flow: dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]],
                                                            vehicles_from_current_commodity: set[int], vehicles: list[Vehicle],
                                                            current_day: date,
                                                            vehicle_assignments: list[VehicleAssignment]) -> None:
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
        vehicle_assignments (list[VehicleAssignment]): The list of current vehicle assignments.

    Returns:
        tuple: A tuple containing the list of locations, vehicles, and trucks. The trucks and vehicles are adjusted
        to contain their respective plans.
    """
    if flow_network is not None:
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
        destination = NodeIdentifier(day=vehicle.due_date, location=vehicle.destination, type=NodeType.NORMAL)

        # Create a vehicle assignment
        paths_taken = []
        planned_delayed = False
        delayed_by: timedelta = timedelta(0)
        arrived = False

        while current_node != destination and not arrived:
            # Greedily find the next edge from the current node in the flow that has a positive flow value
            next_node = None

            # In the following loop, we skip letting the vehicle stay at the same location. Thus, if the vehicle is already
            # at its destination location (possibly not correct date), we will skip this loop.
            if current_node.location != vehicle.destination:
                # Get the possible next nodes from the current node in the flow (these will all have non-zero flow)
                possible_next_nodes = list(flow[current_node].items())

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
                        # We also update the capacity of the edge in the flow network, if it exists
                        if flow_network is not None:
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
                            paths_taken.append(
                                TruckIdentifier(start_location=current_node.location, end_location=next_node.location,
                                                truck_number=edge_index, departure_date=current_node.day))

                        # Set the current node to the next node
                        current_node = next_node

                        break
                if next_node is None:
                    # If we have not found a next node, that means we should wait at the current location
                    current_node = NodeIdentifier(day=current_node.day + timedelta(days=1),
                                                  location=current_node.location,
                                                  type=current_node.type)

            else:
                # We have reached the destination location. Either we have arrived early or we have delay to take care of.
                # Check if we have a delay
                if current_node.day > vehicle.due_date:
                    # Check if we have a planned delay
                    delay_notification_period = vehicle.due_date - current_day
                    delay_length = current_node.day - vehicle.due_date
                    if delay_notification_period <= timedelta(days=7):
                        # We have an unplanned delay
                        planned_delayed = False
                        delayed_by = delay_length
                    else:
                        # We have a planned delay
                        planned_delayed = True
                        delayed_by = delay_length
                break

        # Insert the vehicle assignment into the list
        vehicle_assignments.append(
            VehicleAssignment(id=vehicle_id, paths_taken=paths_taken, planned_delayed=planned_delayed,
                              delayed_by=delayed_by))


def extract_flow_update_network_and_obtain_planned_assignment(flow_network: MultiDiGraph,
                                                              flow: dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]],
                                                              vehicles_from_current_commodity: set[int], vehicles: list[Vehicle],
                                                              current_day: date,
                                                              planned_vehicle_assignments: dict[int, PlannedVehicleAssignment],
                                                              vehicle_assignments: dict[int, VehicleAssignment],
                                                              trucks_realised_by_day_known: dict[date, dict[TruckIdentifier, Truck]]) -> dict[int, PlannedVehicleAssignment]:
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
        vehicle_assignments (dict[int, VehicleAssignment]): A dictionary containing the final vehicle assignments.
        trucks_realised_by_day_known (dict[date, dict[TruckIdentifier, Truck]]): A dictionary mapping each day to the realized trucks for that day.
            Note that this dict only contains entries for days earlier than current_day.

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

        current_node = get_current_location_of_vehicle_as_node(vehicle, vehicle_assignments,
                                                               trucks_realised_by_day_known)
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

        # The vehicle has reached its destination location, we check if it is delayed and preemptively announce it
        # as delayed, if so.
        if current_node.day > vehicle.due_date:
            # We can only announce a delay if we are 7 days before the due date.
            if current_day + timedelta(days=7) <= vehicle.due_date:
                if vehicle_id not in vehicle_assignments:
                    # Create a new VehicleAssignment if not present yet
                    vehicle_assignments[vehicle_id] = VehicleAssignment(id=vehicle_id)

                # Set the planned delayed flag
                vehicle_assignments[vehicle_id].planned_delayed = True

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
