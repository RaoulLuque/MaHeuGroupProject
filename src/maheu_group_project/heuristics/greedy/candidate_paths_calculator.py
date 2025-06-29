import networkx as nx
from networkx import MultiDiGraph
import statistics
from matplotlib.patches import FancyArrowPatch
import matplotlib.pyplot as plt
import numpy as np
import heapq
from itertools import count
from maheu_group_project.solution.encoding import TruckIdentifier, Truck, Location, LocationType

c = 50  # additional cost for each edge


def create_logistics_network(locations: list[Location], trucks: dict[TruckIdentifier, Truck]) -> MultiDiGraph:
    logistics_network = MultiDiGraph()

    # Add nodes for each location
    for location in locations:
        logistics_network.add_node(location)

    # Create the edges of the flow network for the trucks
    nonfree_truck_prices: dict[tuple[Location, Location], dict] = {}

    for truck in trucks.values():
        start_node = truck.start_location
        end_node = truck.end_location
        truck_number = truck.truck_number

        if truck.price > 0:
            if (start_node, end_node) not in nonfree_truck_prices:
                nonfree_truck_prices[(start_node, end_node)] = {'prices': [], 'truck_number': truck_number}
            nonfree_truck_prices[(start_node, end_node)]['prices'].append(truck.price)
        else:
            if not logistics_network.has_edge(start_node, end_node):
                edge_cost = 0 + c
                logistics_network.add_edge(start_node, end_node, weight=edge_cost, truck_number=truck_number)

    for (start_node, end_node) in nonfree_truck_prices:
        edge_cost = statistics.mean(nonfree_truck_prices[(start_node, end_node)]['prices']) + c
        truck_number = nonfree_truck_prices[(start_node, end_node)]['truck_number']

        logistics_network.add_edge(start_node, end_node, weight=edge_cost, truck_number=truck_number)

    return logistics_network


def calculate_candidate_paths(logistics_network: MultiDiGraph) -> dict[
    tuple[Location, Location], list[dict]]:
    candidate_paths = {}

    for source in logistics_network.nodes:
        if source.type == LocationType.DEALER:
            continue
        for target in logistics_network.nodes:
            if target.type != LocationType.DEALER or source == target:
                continue

            seen_edges = set()
            for path, is_free, total_weight, length in shortest_paths(logistics_network, source, target):
                if not path:
                    continue
                u, v, key, data = path[0]
                if (u, v, key) in seen_edges:
                    continue
                seen_edges.add((u, v, key))
                next_location = v
                truck_number = data.get("truck_number")
                candidate_paths.setdefault((source, target), []).append({
                    'next_location': next_location,
                    'truck_number': truck_number,
                    'is_free': is_free,
                    'length': length,
                    'total_cost': total_weight
                })

    return candidate_paths


def shortest_paths(network: MultiDiGraph, start_location: Location, end_location: Location) -> list[
    tuple[list[tuple[Location, Location, int, dict]], bool, float, int]]:
    """
    Finds the k shortest paths between two locations in a logistics network.

    :param network: The logistics network represented as a MultiDiGraph.
    :param start_location: The starting location for the paths.
    :param end_location: The destination location for the paths.
    :return: A list of tuples, each containing a path (list of edges) and a boolean indicating if the path is free.
    """
    k = 10  # max number of shortest paths to find

    def dijkstra_edge_path(G: MultiDiGraph, source: Location, target: Location) -> list[
        tuple[Location, Location, int, dict]]:
        counter = count()
        queue = [(0, next(counter), source, [])]
        visited = set()

        while queue:
            cost, _, node, path = heapq.heappop(queue)
            if node == target:
                return path
            if node in visited:
                continue
            visited.add(node)
            for neighbor in G.successors(node):
                for key, data in G.get_edge_data(node, neighbor).items():
                    if data.get("weight", float("inf")) is not None:
                        heapq.heappush(queue, (
                            cost + data["weight"],
                            next(counter),
                            neighbor,
                            path + [(node, neighbor, key, data)]
                        ))
        raise nx.NetworkXNoPath(f"No path between {source} and {target}")

    def total_path_weight(edge_path: list[tuple[Location, Location, int, dict]]) -> float:
        return sum(data.get("weight", 0) for (_, _, _, data) in edge_path)

    A = []
    B = []

    try:
        first_path = dijkstra_edge_path(network, start_location, end_location)
        A.append(first_path)
    except nx.NetworkXNoPath:
        return []

    for k_idx in range(1, k):
        for i in range(len(A[-1])):
            spur_node = A[-1][i][0]
            root_path = A[-1][:i]

            removed_edges = []
            for path in A:
                if len(path) > i and path[:i] == root_path:
                    u, v, key, _ = path[i]
                    if network.has_edge(u, v, key):
                        data = network[u][v][key]
                        removed_edges.append((u, v, key, data))
                        network.remove_edge(u, v, key)

            try:
                spur_path = dijkstra_edge_path(network, spur_node, end_location)
                total_path = root_path + spur_path
                if total_path not in B:
                    B.append(total_path)
            except nx.NetworkXNoPath:
                pass

            for u, v, key, data in removed_edges:
                network.add_edge(u, v, key=key, **data)

        if not B:
            break
        B.sort(key=total_path_weight)
        A.append(B.pop(0))

    return [
        (
            path,
            all(edge[3].get("weight", 0) == c for edge in path),
            total_path_weight(path),
            len(path)
        )
        for path in A
    ]


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

            weight = int(data.get('weight', 0))
            truck_number = data.get('truck_number', 'N/A')
            label = f"{weight}  (#{truck_number})"
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
