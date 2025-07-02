import networkx as nx
from networkx import MultiDiGraph

from maheu_group_project.heuristics.common import get_first_last_and_days
from maheu_group_project.heuristics.flow.mip.translation import translate_flow_network_to_mip
from maheu_group_project.heuristics.flow.mip.solve_mip import solve_mip_and_extract_flow
from maheu_group_project.heuristics.flow.types import NodeIdentifier, NodeType, \
    dealership_to_commodity_group
from maheu_group_project.heuristics.flow.visualize import visualize_flow_network
from maheu_group_project.solution.encoding import Vehicle, TruckIdentifier, Truck, Location, LocationType, \
    TruckAssignment, \
    VehicleAssignment, \
    convert_vehicle_assignments_to_truck_assignments
from datetime import timedelta, date

# Multiplier used to artificially increase the cost of edges that correspond to later trucks, to incentivize earlier
# transportation.
ARTIFICIAL_EDGE_COST_MULTIPLIER = 1


def solve_flow_deterministically(flow_network: MultiDiGraph, commodity_groups: dict[str, set[int]],
                                 locations: list[Location], vehicles: list[Vehicle], trucks: dict[TruckIdentifier, Truck]) -> \
        (
                tuple)[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment]]:
    """
    Solves the multicommodity min-cost flow problem heuristically by solving multiple single commodity min-cost flow
    problems for each DEALER location and day in the flow network.

    This function iterates over each day (in ascending order) and each DEALER location, solving a min-cost flow problem
    for the vehicles that are due on that day and at that location. The flow network is expected to have been created
    with the `create_flow_network` function.

    Args:
        flow_network (MultiDiGraph[NodeIdentifier]): The flow network to solve.
        commodity_groups (dict[str, set[int]]): A dictionary mapping each commodity group to the set of vehicles (their ids)
        that belong to it.
        locations (list[Location]): List of locations involved in the transportation.
        vehicles (list[Vehicle]): List of vehicles to be transported.
        trucks (dict[TruckIdentifier, Truck]): Dictionary of trucks available for transportation.

    Returns:
        tuple: A tuple containing the list of locations, vehicles, and trucks. The trucks and vehicles are adjusted
        to contain their respective plans.
    """
    # Ensure the correct type for flow_network
    flow_network: MultiDiGraph[NodeIdentifier] = flow_network

    # Get the days involved in the flow network
    first_day, last_day, days = get_first_last_and_days(vehicles=vehicles, trucks=trucks)
    current_day = first_day

    # Create a list to store the vehicle assignments
    vehicle_assignments: list[VehicleAssignment] = []

    # We iterate over the days from first to last, then those locations which are DEALER locations
    for day in days:
        for location in locations:
            if location.type == LocationType.DEALER:
                # For each DEALER location, solve a min-cost flow problem with the commodity group corresponding to
                # the current day and location.
                commodity_group = dealership_to_commodity_group(NodeIdentifier(day, location, NodeType.NORMAL))

                # First, check whether there is actually any demand for this commodity group (day and location)
                target_node = NodeIdentifier(day, location, NodeType.NORMAL)
                if flow_network.nodes[target_node].get(commodity_group, 0) != 0:
                    # Compute the single commodity min-cost flow for the current commodity group
                    flow = nx.min_cost_flow(flow_network, demand=commodity_group, capacity='capacity', weight='weight')

                    # visualize_flow_network(flow_network, locations, commodity_groups=set(commodity_groups.keys()), flow=flow, only_show_flow_nodes=commodity_group)

                    # Extract the solution from the flow and update the flow network
                    extract_flow_update_network_and_obtain_final_assignment(flow_network=flow_network, flow=flow,
                                                                            vehicles_from_current_commodity=commodity_groups[commodity_group],
                                                                            vehicles=vehicles, current_day=current_day,
                                                                            vehicle_assignments=vehicle_assignments)

                    # visualize_flow_network(flow_network, locations)

    # Return the list of vehicle assignments indexed by their id
    vehicle_assignments.sort(key=lambda va: va.id)

    truck_assignments = convert_vehicle_assignments_to_truck_assignments(vehicle_assignments=vehicle_assignments,
                                                                         trucks=trucks)

    return vehicle_assignments, truck_assignments


def extract_flow_update_network_and_obtain_final_assignment(flow_network: MultiDiGraph,
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
    filtered_flow = {}
    for src, targets in flow.items():
        filtered_targets = {}
        for dst, keys in targets.items():
            filtered_keys = {k: v for k, v in keys.items() if v > 0}
            if filtered_keys:
                filtered_targets[dst] = filtered_keys
        if filtered_targets:
            filtered_flow[src] = filtered_targets
    flow = filtered_flow

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


def solve_flow_as_mip_deterministically(flow_network: MultiDiGraph, commodity_groups: set[str], locations: list[Location]) -> None:
    # Ensure the correct type for flow_network
    flow_network: MultiDiGraph[NodeIdentifier] = flow_network

    # visualize_flow_network(flow_network, locations, commodity_groups)

    model, flow_vars, node_mapping = translate_flow_network_to_mip(flow_network, commodity_groups)
    flow_solution = solve_mip_and_extract_flow(model, flow_vars, commodity_groups)
    print(flow_solution)
