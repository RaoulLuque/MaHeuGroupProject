import networkx as nx
from networkx import MultiDiGraph

from maheu_group_project.heuristics.flow.types import NodeIdentifier, NodeType
from maheu_group_project.heuristics.flow.visualize import visualize_flow_graph
from maheu_group_project.solution.encoding import Vehicle, TruckIdentifier, Truck, Location, LocationType, \
    TruckAssignment, \
    VehicleAssignment, \
    FIXED_UNPLANNED_DELAY_COST, FIXED_PLANNED_DELAY_COST, COST_PER_UNPLANNED_DELAY_DAY, COST_PER_PLANNED_DELAY_DAY
from datetime import timedelta, date


def solve_as_flow(vehicles: list[Vehicle], trucks: dict[TruckIdentifier, Truck], locations: list[Location]) -> (
        tuple)[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment]]:
    """
    Translates the given vehicles and trucks into a MIP (Mixed Integer Programming) format string.

    Args:
        vehicles (list[Vehicle]): List of vehicles to be transported.
        trucks (dict[TruckIdentifier, Truck]): Dictionary of trucks available for transportation.
        locations (list[Location]): List of locations involved in the transportation.

    Returns:
        tuple: A tuple containing the list of locations, vehicles, and trucks. The trucks and vehicles are adjusted
        to contain their respective plans.
    """
    # Set a parameter representing unbounded capacity
    # UNBOUNDED = float('inf')
    UNBOUNDED = len(vehicles)

    # Create a list of all days we are considering. The first day is day 0 and the day when the first vehicle is available
    first_day: date = min(min(vehicles, key=lambda vehicle: vehicle.available_date).available_date,
                          min(trucks.values(), key=lambda truck: truck.departure_date).departure_date)
    last_day: date = max(max(vehicles, key=lambda vehicle: vehicle.available_date).available_date,
                         max(trucks.values(), key=lambda truck: truck.arrival_date).arrival_date)
    current_day = first_day

    number_of_days = (last_day - first_day).days + 1
    days = [first_day + timedelta(days=i) for i in range(number_of_days)]

    # Create a Network to model the flow
    flow_network: MultiDiGraph[NodeIdentifier] = MultiDiGraph()

    # Create the vertices of the flow network behind the MIP
    # Create a node for each day and each location
    for day in days:
        for location in locations:
            flow_network.add_node(NodeIdentifier(day, location, NodeType.NORMAL), demand=0)

    # Adjust the flow of each node according to the vehicles produced and expected on that day
    for vehicle in vehicles:
        # A positive demand indicates that flow should end there, reverse for negative
        flow_network.nodes[NodeIdentifier(vehicle.available_date, vehicle.origin, NodeType.NORMAL)]['demand'] -= 1
        flow_network.nodes[NodeIdentifier(vehicle.due_date, vehicle.destination, NodeType.NORMAL)]['demand'] += 1

    # Create the edges of the flow network for the trucks
    for truck in trucks.values():
        start_node = NodeIdentifier(truck.departure_date, truck.start_location, NodeType.NORMAL)
        end_node = NodeIdentifier(truck.arrival_date, truck.end_location, NodeType.NORMAL)

        # Add an edge from the start node to the end node with the truck's capacity as the flow.
        # The key of the edge is the truck_number to distinguish parallel edges. These will be the keys in the flow
        # dict.
        flow_network.add_edge(start_node, end_node, capacity=truck.capacity, weight=truck.price, key=truck.truck_number)
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

    visualize_flow_graph(flow_network, first_day, locations)
    flow = nx.min_cost_flow(flow_network)
    # print(nx.min_cost_flow(flow_network))
    # print(nx.min_cost_flow_cost(flow_network))
    # return extract_solution_from_flow(flow, vehicles), {}


def extract_solution_from_flow(flow: dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]],
                               vehicles: list[Vehicle]) -> list[VehicleAssignment]:
    """
    Extracts the solution in terms of vehicle and truck assignments from a provided flow.

    Args:
        flow (dict[NodeIdentifier, dict[NodeIdentifier, float]]): The flow from which to extract the solution.
        vehicles (list[Vehicle]): List of vehicles to be transported.

    Returns:
        tuple: A tuple containing the list of locations, vehicles, and trucks. The trucks and vehicles are adjusted
        to contain their respective plans.
    """
    vehicle_assignments: list[VehicleAssignment] = []

    # Loop over the vehicles and extract the assignments
    for vehicle in vehicles:
        # For each vehicle, heuristically find the fastest path from its origin to its destination
        current_node = NodeIdentifier(day=vehicle.available_date, location=vehicle.origin, type=NodeType.NORMAL)
        destination = NodeIdentifier(day=vehicle.due_date, location=vehicle.destination, type=NodeType.NORMAL)

        # Create a vehicle assignment
        id = vehicle.id
        paths_taken = []
        planned_delayed = False
        delayed_by: timedelta = timedelta(0)

        while current_node != destination:
            # Greedily find the next edge from the current node in the flow that has a positive flow value
            next_node = None
            # Filter out the possible next nodes which don't have any positive flow
            possible_next_nodes = [(neighbor, flows) for (neighbor, flows) in flow[current_node].items() if
                                   (sum(flows.values()) > 0)]
            # Sort the possible next nodes by the day of the node to ensure we always take the earliest possible next node
            possible_next_nodes.sort(key=lambda x: x[0].day)

            # In the following loop we skip letting the vehicle stay at the same location. Thus, if the vehicle is already
            # at its destination, we will skip this loop.
            if current_node.location != vehicle.destination:
                for identifier, flows in possible_next_nodes:
                    if identifier.location == current_node.location:
                        # We want to skip letting the vehicle stay at the same location for now and only allow consider moving
                        # it forward in this loop
                        continue
                    else:
                        # If the next node is not the same location, we can take it
                        next_node = identifier

                        # Find the edge index for this edge
                        edge_index = next(iter(flows.keys()))

                        # We subtract one from the flow of this edge to make it unavailable for the next vehicles
                        flow[current_node][next_node][edge_index] -= 1

                        # Update the paths taken, if the edge_number is not 0
                        # Explanation: edge_index starts at 0 by default and increments for parallel edges or are set with
                        # `key` when adding an edge. For trucks, this is set as the truck id which starts at 1, and other
                        # edges cannot have parallel edges (which would result in edge_numbers bigger than 0).
                        if edge_index != 0:
                            paths_taken.append(
                                TruckIdentifier(start_location=current_node.location, end_location=next_node.location,
                                                truck_number=edge_index, departure_date=current_node.day))

                        # Check if the next node is a HELPER_NODE, if so, we need to set a planned delay
                        if next_node.type != NodeType.NORMAL:
                            # Check if the vehicle is already planned to be delayed in which case we already took care of
                            # setting the delay variables
                            if delayed_by == timedelta(0):
                                delayed_by = current_node.day - vehicle.due_date

                        break
            if next_node is None:
                # If next_node is none, the only option seems to be letting the vehicle stay at the current node
                next_day_node = NodeIdentifier(day=current_node.day + timedelta(days=1), location=current_node.location,
                                               type=current_node.type)
                if flow[current_node][next_day_node][0] > 0:
                    next_node = next_day_node

                    # The edge index for this edge is supposed to be 0, since no parallel edges should exist here
                    edge_index = 0

                    # We subtract one from the flow of this edge to make it unavailable for the next vehicles
                    flow[current_node][next_node][edge_index] -= 1

                else:
                    raise ValueError(
                        f"No valid segment with positive flow found for vehicle {vehicle.id} from {current_node} to {vehicle.destination}. \n Entire flow is: {flow}")

        # Insert the vehicle assignment into the list
        vehicle_assignments.append(
            VehicleAssignment(id=id, paths_taken=paths_taken, planned_delayed=planned_delayed, delayed_by=delayed_by))
    a = 0

    return [], {}
