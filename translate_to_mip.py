from dataclasses import dataclass
from enum import Enum

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.patches import FancyArrowPatch
from networkx import MultiDiGraph

from encoding import Vehicle, TruckIdentifier, Truck, Location, LocationType, TruckAssignment, VehicleAssignment, \
    FIXED_UNPLANNED_DELAY_COST, FIXED_PLANNED_DELAY_COST, COST_PER_UNPLANNED_DELAY_DAY, COST_PER_PLANNED_DELAY_DAY
from datetime import timedelta, date


class NodeType(Enum):
    """
    Enum to represent the type of node in the flow network.
    Nodes may be of type NORMAL, which represent a regular node with a day and location,
    or HELPER_NODE which only appear next to DEALER locations to allow for delays.
    """
    NORMAL = 0
    HELPER_NODE_ONE = 1
    HELPER_NODE_TWO = 2

    def to_string(self) -> str:
        """
        Returns a string representation of the node type.
        """
        match self:
            case NodeType.NORMAL:
                return "NORMAL"
            case NodeType.HELPER_NODE_ONE:
                return "HELPER_ONE"
            case NodeType.HELPER_NODE_TWO:
                return "HELPER_TWO"
        # Should be unreachable, just here to make the linter happy
        raise ValueError(f"Invalid NodeType: {self}")


@dataclass(frozen=True)
class NodeIdentifier:
    """

    """
    day: date
    location: Location
    type: NodeType


def solve_as_mip(vehicles: list[Vehicle], trucks: dict[TruckIdentifier, Truck], locations: list[Location]) -> (
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
    UNBOUNDED = float('inf')

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

        # Add an edge from the start node to the end node with the truck's capacity as the flow
        flow_network.add_edge(start_node, end_node, capacity=truck.capacity, weight=truck.price)

    # Create the helper edges for the flow network connecting the columns
    for day in days:
        for location in locations:
            current_node = NodeIdentifier(day, location, NodeType.NORMAL)
            # Add edges to the next day for each location
            if day < last_day:
                # Create an edge to the next day node
                next_day_node = NodeIdentifier(day + timedelta(days=1), location, NodeType.NORMAL)
                flow_network.add_edge(current_node, next_day_node, capacity=UNBOUNDED, weight=0)

            # Add helper edges at dealer locations to allow for delays
            if location.type == LocationType.DEALER:
                # Create an edge to the next day node with a delay of 1 day
                next_day_node = NodeIdentifier(day + timedelta(days=1), location, NodeType.NORMAL)
                flow_network.add_edge(next_day_node, current_node, capacity=UNBOUNDED, weight=0)

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
    print(nx.min_cost_flow(flow_network))
    print(nx.min_cost_flow_cost(flow_network))
    return [], {}


def visualize_flow_graph(flow_network: MultiDiGraph, first_day: date, locations: list[Location]):
    """
    Visualizes the flow network using matplotlib and networkx.

    Args:
        flow_network (DiGraph[NodeIdentifier]): The flow network to visualize.
        first_day (date): The first day in the planning horizon.
        locations (list[Location]): List of all locations in the network.
    """
    # Ensure correct type for flow_network
    flow_network: MultiDiGraph[NodeIdentifier] = flow_network

    pos = {}
    scale = 100  # Controls spacing between nodes in the plot

    # Assign a 2D position to each node for visualization
    for node in flow_network.nodes:
        day = node.day
        location = node.location
        # NORMAL nodes are aligned in columns by location
        if node.type == NodeType.NORMAL:
            pos[node] = (locations.index(location) * scale, -(day.toordinal() - first_day.toordinal()) * scale)
        else:
            # HELPER nodes are offset horizontally to avoid overlap
            pos[node] = ((locations.index(location) + node.type.value * 0.5) * scale,
                         -(day.toordinal() - first_day.toordinal()) * scale)

    plt.figure(figsize=(16, 64), dpi=150)
    ax = plt.gca()

    # Draw all nodes as white circles with black borders
    nx.draw_networkx_nodes(
        flow_network, pos,
        node_size=150,
        node_color='white',
        edgecolors='black',
        linewidths=1.0,
        ax=ax
    )

    # Annotate each node with its demand (capacity) in red
    for node, (x, y) in pos.items():
        demand = flow_network.nodes[node].get('demand', 0)
        ax.text(x, y, str(demand), fontsize=6, color='red', ha='center', va='center')

    # Draw all edges, using curvature to distinguish parallel edges
    for u, v in flow_network.edges():
        edge_dict = flow_network.get_edge_data(u, v)
        if edge_dict is None:
            continue
        n = len(edge_dict)  # Number of parallel edges between u and v
        for idx, (k, data) in enumerate(edge_dict.items()):
            # Default curvature for parallel edges
            rad = 0.0 if n == 1 else 0.2 * ((idx - (n - 1) / 2))

            # Special curvatures for DEALER to HELPER_NODE edges to avoid overlap
            if (
                    u.location.type == LocationType.DEALER
                    and (
                    (u.type == NodeType.NORMAL and v.type == NodeType.HELPER_NODE_ONE)
                    or (u.type == NodeType.NORMAL and v.type == NodeType.HELPER_NODE_TWO)
                    or (u.type == NodeType.HELPER_NODE_ONE and v.type == NodeType.HELPER_NODE_TWO))
            ):
                if u.type == NodeType.NORMAL and v.type == NodeType.HELPER_NODE_ONE:
                    rad = 0.25
                elif u.type == NodeType.NORMAL and v.type == NodeType.HELPER_NODE_TWO:
                    rad = -0.25
                elif u.type == NodeType.HELPER_NODE_ONE and v.type == NodeType.HELPER_NODE_TWO:
                    rad = 0.0

            # Draw the edge as a curved arrow
            arrow = FancyArrowPatch(
                posA=pos[u], posB=pos[v],
                connectionstyle=f"arc3,rad={rad}",
                arrowstyle='-|>', color='gray', mutation_scale=14, lw=1  # Increased mutation_scale
            )
            ax.add_patch(arrow)

            # Label each edge with its capacity and weight (cost)
            label = f"{data.get('capacity', '')}/{data.get('weight', '')}"
            # Compute midpoint for label placement
            mx, my = (pos[u][0] + pos[v][0]) / 2, (pos[u][1] + pos[v][1]) / 2
            dx, dy = pos[v][0] - pos[u][0], pos[v][1] - pos[u][1]
            length = (dx ** 2 + dy ** 2) ** 0.5 or 1
            # Offset label perpendicular to the edge, scaled by curvature
            perp_x, perp_y = -dy / length, dx / length
            offset = rad * 0.5 * length
            label_x = mx + perp_x * offset
            label_y = my + perp_y * offset
            ax.text(label_x, label_y, label, fontsize=7, color='blue', ha='center', va='center',
                    backgroundcolor='white')

    # Optionally, draw node labels (commented out for clarity)
    # labels = {node: f"{node.location.name[:5]}_Day{node.day}_{node.type.to_string()}" for node in flow_network.nodes}
    # nx.draw_networkx_labels(flow_network, pos, labels=labels, font_size=5, font_color='black', ax=ax)

    plt.axis('off')  # Hide axes for cleaner visualization
    plt.tight_layout()
    plt.show()
