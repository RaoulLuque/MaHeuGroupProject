from datetime import timedelta

from networkx import MultiDiGraph

from maheu_group_project.heuristics.common import get_first_last_and_days
from maheu_group_project.heuristics.flow.solve_deterministically import ARTIFICIAL_EDGE_COST_MULTIPLIER
from maheu_group_project.heuristics.flow.types import NodeIdentifier, NodeType, vehicle_to_commodity_group
from maheu_group_project.solution.encoding import Vehicle, TruckIdentifier, Truck, Location, LocationType, \
    FIXED_UNPLANNED_DELAY_COST, COST_PER_UNPLANNED_DELAY_DAY, FIXED_PLANNED_DELAY_COST, COST_PER_PLANNED_DELAY_DAY


def create_flow_network(vehicles: list[Vehicle], trucks: dict[TruckIdentifier, Truck], locations: list[Location]) -> \
        tuple[MultiDiGraph, dict[str, set[int]]]:
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
        start_node, end_node = get_start_and_end_nodes_for_truck(truck)

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


def get_start_and_end_nodes_for_truck(truck: Truck) -> tuple[NodeIdentifier, NodeIdentifier]:
    """
    Returns the start and end nodes for a truck in the flow network.

    Args:
        truck (Truck): The truck for which to get the start and end nodes.

    Returns:
        tuple[NodeIdentifier, NodeIdentifier]: A tuple containing the start and end nodes for the truck.
    """
    start_node = NodeIdentifier(truck.departure_date, truck.start_location, NodeType.NORMAL)

    # If the truck's end location is not a DEALER, we delay the arrival date by one day to account for the
    # one day rest.
    truck_arrival_date = truck.arrival_date
    if truck.end_location.type != LocationType.DEALER:
        truck_arrival_date += timedelta(days=1)

    end_node = NodeIdentifier(truck_arrival_date, truck.end_location, NodeType.NORMAL)

    return start_node, end_node


def remove_trucks_from_network(flow_network: MultiDiGraph, trucks: dict[TruckIdentifier, Truck]):
    """
    Removes the trucks (their corresponding edges) from the flow network.

    Args:
        flow_network: MultiDiGraph[NodeIdentifier]: The flow network from which the trucks should be removed.
        trucks (dict[TruckIdentifier, Truck]): The dictionary of trucks to be removed from the network.
    """
    # Ensure the correct type for flow_network
    flow_network: MultiDiGraph[NodeIdentifier] = flow_network

    for truck in trucks.values():
        start_node, end_node = get_start_and_end_nodes_for_truck(truck)

        flow_network.remove_edge(start_node, end_node, key=truck.truck_number)
