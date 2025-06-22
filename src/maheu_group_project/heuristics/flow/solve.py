import networkx as nx
from networkx import MultiDiGraph

from maheu_group_project.heuristics.common import get_first_last_and_days
from maheu_group_project.heuristics.flow.types import vehicle_to_commodity_group, NodeIdentifier, NodeType, \
    dealership_to_commodity_group
from maheu_group_project.heuristics.flow.visualize import visualize_flow_network
from maheu_group_project.solution.encoding import Vehicle, TruckIdentifier, Truck, Location, LocationType, \
    TruckAssignment, \
    VehicleAssignment, \
    FIXED_UNPLANNED_DELAY_COST, FIXED_PLANNED_DELAY_COST, COST_PER_UNPLANNED_DELAY_DAY, COST_PER_PLANNED_DELAY_DAY, \
    convert_vehicle_assignments_to_truck_assignments
from datetime import timedelta, date

# Multiplier used to artificially increase the cost of edges that correspond to later trucks, to incentivize earlier
# transportation.
ARTIFICIAL_EDGE_COST_MULTIPLIER = 1


def create_flow_network(vehicles: list[Vehicle], trucks: dict[TruckIdentifier, Truck], locations: list[Location]) -> tuple[MultiDiGraph, dict[str, set[int]]]:
    """
    Creates a flow network for the transportation problem based on the provided vehicles, trucks, and locations.

    The flow network is a directed graph containing a node for each day and each location. Edges between different locations
    represent the transportation of vehicles by trucks. There are also edges between nodes of the same location to represent
    the option of waiting for the next day.

    Additionally, helper nodes are created for DEALER locations to account for the possibility of delays. These helper nodes
    make it possible to 'go back in time' and account for the costs associated with unplanned and planned delays.

    The network is a multicommodity flow network, that is, it contains multiple commodities to be transported. Each
    commodity corresponds to a group of vehicles that have the same destination and due date.

    Args:
        vehicles (list[Vehicle]): List of vehicles to be transported.
        trucks (dict[TruckIdentifier, Truck]): Dictionary of trucks available for transportation.
        locations (list[Location]): List of locations involved in the transportation.

    Returns:
        MultiDiGraph: A directed graph representing the flow network for the transportation problem
        dict[str, set[int]]: A dictionary mapping each commodity group to the set of vehicles (their ids) that belong to it.
    """
    # Set a parameter representing unbounded capacity
    # UNBOUNDED = float('inf')
    UNBOUNDED = len(vehicles)

    first_day, last_day, days = get_first_last_and_days(vehicles=vehicles, trucks=trucks)

    current_day = first_day

    # Create a Network to model the flow
    flow_network: MultiDiGraph[NodeIdentifier] = MultiDiGraph()

    # Create a dictionary mapping each commodity group to the set of vehicles (their ids) that belong to it
    commodity_groups: dict[str, set[int]] = {}

    # Create the vertices of the flow network
    # Create a node for each day and each location
    for day in days:
        for location in locations:
            node = NodeIdentifier(day, location, NodeType.NORMAL)
            flow_network.add_node(node)

    # Iterate over the vehicles and add demand in their respective commodity group for each vehicle to the flow network
    for vehicle in vehicles:
        add_commodity_demand_to_node(flow_network, vehicle)

        commodity_group = vehicle_to_commodity_group(vehicle)
        if commodity_group not in commodity_groups:
            commodity_groups[commodity_group] = set()
        commodity_groups[commodity_group].add(vehicle.id)

    # Create the edges of the flow network for the trucks
    for truck in trucks.values():
        start_node = NodeIdentifier(truck.departure_date, truck.start_location, NodeType.NORMAL)
        end_node = NodeIdentifier(truck.arrival_date, truck.end_location, NodeType.NORMAL)

        # We add a symbolic cost to the edge, to make the flow network prefer earlier edges. These costs will be
        # ignored when computing the actual objective value of the solution.
        day_price = (truck.arrival_date - first_day).days * ARTIFICIAL_EDGE_COST_MULTIPLIER
        price = truck.price if truck.price != 0 else day_price

        # Add an edge from the start node to the end node with the truck's capacity, price and truck number as a key.
        # The key of the edge is the truck_number to distinguish parallel edges. These will be the keys in the resulting
        # flow dict.
        flow_network.add_edge(start_node, end_node, capacity=truck.capacity, weight=price, key=truck.truck_number)

    # Create the helper edges for the flow network connecting the columns
    for day in days:
        for location in locations:
            current_node = NodeIdentifier(day, location, NodeType.NORMAL)
            # Add edges to the next day for each location
            if day < last_day:
                # Create an edge to the next day node
                next_day_node = NodeIdentifier(day + timedelta(days=1), location, NodeType.NORMAL)
                flow_network.add_edge(current_node, next_day_node, capacity=UNBOUNDED, weight=0)

    # Create the helper nodes for each DEALER location
    for day in days:
        for location in locations:
            if location.type == LocationType.DEALER:
                # Add the first helper node
                current_helper_node_one = NodeIdentifier(day, location, NodeType.HELPER_NODE_ONE)
                flow_network.add_node(current_helper_node_one)

                # Distinguish case of first 7 days including current_day
                if day < current_day + timedelta(days=7):
                    # Add edges to first helper node (UNPLANNED DELAY, since we are in the first 7 days)
                    current_normal_node = NodeIdentifier(day, location, NodeType.NORMAL)
                    flow_network.add_edge(current_normal_node, current_helper_node_one, capacity=UNBOUNDED,
                                          weight=FIXED_UNPLANNED_DELAY_COST)
                    flow_network.add_edge(current_helper_node_one, current_normal_node, capacity=UNBOUNDED, weight=0)
                    if day != first_day:
                        # Add an edge to the HELPER_NODE_ONE above
                        previous_helper_node_one = NodeIdentifier(day - timedelta(days=1), location,
                                                                  NodeType.HELPER_NODE_ONE)
                        flow_network.add_edge(current_helper_node_one, previous_helper_node_one, capacity=UNBOUNDED,
                                              weight=COST_PER_UNPLANNED_DELAY_DAY)
                else:
                    # Add edges to first helper node (PLANNED DELAY, since we are after the first 7 days)
                    current_normal_node = NodeIdentifier(day, location, NodeType.NORMAL)
                    flow_network.add_edge(current_normal_node, current_helper_node_one, capacity=UNBOUNDED,
                                          weight=FIXED_PLANNED_DELAY_COST)
                    flow_network.add_edge(current_helper_node_one, current_normal_node, capacity=UNBOUNDED, weight=0)

                    # Add the second helper node and an edge to it
                    current_helper_node_two = NodeIdentifier(day, location, NodeType.HELPER_NODE_TWO)
                    flow_network.add_edge(current_normal_node, current_helper_node_two, capacity=UNBOUNDED,
                                          weight=FIXED_UNPLANNED_DELAY_COST)

                    # Distinguish 8th day or not
                    if day != current_day + timedelta(days=7):
                        # Add edges connecting current HELPER_NODE_ONE and _TWO to the previous days' nodes respectively
                        previous_helper_node_one = NodeIdentifier(day - timedelta(days=1), location,
                                                                  NodeType.HELPER_NODE_ONE)
                        previous_helper_node_two = NodeIdentifier(day - timedelta(days=1), location,
                                                                  NodeType.HELPER_NODE_TWO)
                        flow_network.add_edge(current_helper_node_one, previous_helper_node_one, capacity=UNBOUNDED,
                                              weight=COST_PER_PLANNED_DELAY_DAY)
                        flow_network.add_edge(current_helper_node_two, previous_helper_node_two, capacity=UNBOUNDED,
                                              weight=COST_PER_UNPLANNED_DELAY_DAY)

                    else:
                        # Add only an edge from the current HELPER_NODE_TWO to the HELPER_NODE_ONE from the previous day
                        previous_helper_node_one = NodeIdentifier(day - timedelta(days=1), location,
                                                                  NodeType.HELPER_NODE_ONE)
                        flow_network.add_edge(current_helper_node_two, previous_helper_node_one, capacity=UNBOUNDED,
                                              weight=COST_PER_UNPLANNED_DELAY_DAY)

    return flow_network, commodity_groups


def add_commodity_demand_to_node(flow_network: MultiDiGraph, vehicle: Vehicle):
    """
    Adds the demand for a vehicle to the flow network.

    Args:
        flow_network (MultiDiGraph[NodeIdentifier]): The flow network to which the demand should be added.
        vehicle (Vehicle): The vehicle for which the demand should be added.
    """
    # Ensure the correct type for flow_network
    flow_network: MultiDiGraph[NodeIdentifier] = flow_network

    start_node = NodeIdentifier(vehicle.available_date, vehicle.origin, NodeType.NORMAL)
    end_node = NodeIdentifier(vehicle.due_date, vehicle.destination, NodeType.NORMAL)
    commodity_group = vehicle_to_commodity_group(vehicle)
    # We check if the respective nodes already have a demand for this commodity group and adjust it accordingly to avoid
    # key errors.
    if flow_network.nodes[start_node].get(commodity_group) is None:
        flow_network.nodes[start_node][commodity_group] = -1
    else:
        flow_network.nodes[start_node][commodity_group] -= 1
    if flow_network.nodes[end_node].get(commodity_group) is None:
        flow_network.nodes[end_node][commodity_group] = 1
    else:
        flow_network.nodes[end_node][commodity_group] += 1


def solve_deterministically(flow_network: MultiDiGraph, commodity_groups: dict[str, set[int]], locations: list[Location], vehicles: list[Vehicle], trucks: dict[TruckIdentifier, Truck]) -> (
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
                    visualize_flow_network(flow_network, locations, flow)

                    # Extract the solution from the flow and update the flow network
                    extract_flow_and_update_network(flow_network=flow_network, flow=flow,
                                                    vehicles_from_current_commodity=commodity_groups[commodity_group],
                                                    vehicles=vehicles, current_day=current_day,
                                                    vehicle_assignments=vehicle_assignments)

                    visualize_flow_network(flow_network, locations)

    # Return the list of vehicle assignments indexed by their id
    vehicle_assignments.sort(key=lambda va: va.id)

    truck_assignments = convert_vehicle_assignments_to_truck_assignments(vehicle_assignments=vehicle_assignments, trucks=trucks)

    return vehicle_assignments, truck_assignments


def extract_flow_and_update_network(flow_network: MultiDiGraph, flow: dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]],
                                    vehicles_from_current_commodity: set[int], vehicles: list[Vehicle], current_day: date,
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
            VehicleAssignment(id=vehicle_id, paths_taken=paths_taken, planned_delayed=planned_delayed, delayed_by=delayed_by))
