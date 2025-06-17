from datetime import date

import networkx as nx
from matplotlib import pyplot as plt
from matplotlib.patches import FancyArrowPatch
from networkx import MultiDiGraph

from maheu_group_project.heuristics.flow.types import NodeIdentifier, NodeType
from maheu_group_project.solution.encoding import Location, LocationType


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
