import networkx as nx
from networkx import MultiDiGraph
import statistics
from matplotlib.patches import FancyArrowPatch
from matplotlib.path import Path
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

from maheu_group_project.heuristics.flow.types import NodeIdentifier
from maheu_group_project.solution.encoding import Vehicle, TruckIdentifier, Truck, Location, LocationType, \
    TruckAssignment, \
    VehicleAssignment, \
    FIXED_UNPLANNED_DELAY_COST, FIXED_PLANNED_DELAY_COST, COST_PER_UNPLANNED_DELAY_DAY, COST_PER_PLANNED_DELAY_DAY, \
    convert_vehicle_assignments_to_truck_assignments
from datetime import timedelta, date
from networkx.algorithms.simple_paths import shortest_simple_paths


def create_logistics_network(locations: list[Location], trucks: dict[TruckIdentifier, Truck]) -> MultiDiGraph:
    logistics_network = MultiDiGraph()

    # Add nodes for each location
    for location in locations:
        logistics_network.add_node(location)

    # Create the edges of the flow network for the trucks
    nonfree_truck_prices: dict[tuple[Location, Location], list[float]] = {}
    free_trucks: set[tuple[Location, Location]] = set()
    for truck in trucks.values():
        start_node = truck.start_location
        end_node = truck.end_location

        if truck.price > 0:
            if (start_node, end_node) not in nonfree_truck_prices:
                nonfree_truck_prices[(start_node, end_node)] = []
            nonfree_truck_prices[(start_node, end_node)].append(truck.price)
        else:
            free_trucks.add((start_node, end_node))

    for (start_node, end_node) in free_trucks:
        # TODO: Define edge cost based on truck parameters
        edge_cost = 0

        logistics_network.add_edge(start_node, end_node, weight=edge_cost)

    for (start_node, end_node) in nonfree_truck_prices:
        # TODO: Define edge cost based on truck parameters
        edge_cost = statistics.mean(nonfree_truck_prices[(start_node, end_node)])

        logistics_network.add_edge(start_node, end_node, weight=edge_cost)
    return logistics_network


def calculate_candidate_paths(logistics_network: MultiDiGraph) -> dict[tuple[Location, Location], list[list[Location]]]:
    k = 3  # Number of shortest paths to compute
    candidate_paths = {}

    for source in logistics_network.nodes:
        if source.type == LocationType.DEALER:
            continue
        for target in logistics_network.nodes:
            if target.type != LocationType.DEALER:
                continue
            try:
                paths_generator = shortest_simple_paths(logistics_network, source, target, weight='weight')
                candidate_paths[(source, target)] = [path for _, path in zip(range(k), paths_generator)]
            except nx.NetworkXNoPath:
                print(f"No path found from {source} to {target}.")
                candidate_paths[(source, target)] = []

    return candidate_paths


def visualize_logistics_network(network: MultiDiGraph):
    # Assign fixed x positions per node type
    x_pos_map = {
        'PLANT': 0,
        'TERMINAL': 1,
        'DEALER': 2
    }

    # Group nodes by type for y positioning
    nodes_by_type = {'PLANT': [], 'TERMINAL': [], 'DEALER': []}
    for node in network.nodes():
        nodes_by_type[node.type.name].append(node)

    pos = {}
    for loc_type, nodes in nodes_by_type.items():
        x = x_pos_map[loc_type]
        n = len(nodes)
        if n == 1:
            y_positions = [0.5]
        else:
            y_positions = [i / (n - 1) for i in range(n)]
        for node, y in zip(nodes, y_positions):
            pos[node] = (x, y)

    labels = {node: node.name for node in network.nodes()}

    # Assign colors based on node type
    type_to_color = {
        'PLANT': 'green',
        'TERMINAL': 'orange',
        'DEALER': 'red'
    }
    node_colors = [type_to_color.get(node.type.name, 'gray') for node in network.nodes()]

    nx.draw_networkx_nodes(network, pos, node_size=200, node_color=node_colors)
    nx.draw_networkx_labels(network, pos, labels=labels, font_size=7)

    ax = plt.gca()

    for u, v in network.edges():
        edge_dict = network.get_edge_data(u, v)
        if edge_dict is None:
            continue
        for idx, (k, data) in enumerate(edge_dict.items()):
            rad = 0.2 * (2 * idx - 1)
            arrow = FancyArrowPatch(
                posA=pos[u], posB=pos[v],
                connectionstyle=f"arc3,rad={rad}",
                arrowstyle='-|>', color='gray',
                mutation_scale=15, lw=1,
                shrinkA=5, shrinkB=5
            )
            ax.add_patch(arrow)

            label = f"{int(data.get('weight', 0))}"
            # Extract only the arc portion before the arrow head
            path = arrow.get_path()
            codes = path.codes
            verts = path.vertices
            trans = arrow.get_patch_transform()

            start = np.array(pos[u])
            end = np.array(pos[v])
            midpoint = (start + end) / 2

            # Vector from start to end
            vec = end - start
            # Normalize perpendicular vector (rotate by 90°)
            perp_vec = np.array([-vec[1], vec[0]])
            perp_vec = perp_vec / np.linalg.norm(perp_vec)

            # Alternate direction for offset based on idx (up/down)
            offset_magnitude = 0.1  # adjust to fit your graph scale
            direction = 1 if idx % 2 == 0 else -1
            offset = direction * offset_magnitude * perp_vec

            label_pos = midpoint + offset
            x_mid, y_mid = label_pos

            ax.text(x_mid, y_mid, label, fontsize=7, color='blue',
                    ha='center', va='center', backgroundcolor='white')

    plt.axis('off')
    plt.tight_layout()
    plt.title("Logistics Network with Costs")
    plt.show()
