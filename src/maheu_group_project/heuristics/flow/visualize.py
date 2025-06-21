from datetime import date

import networkx as nx
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import FancyArrowPatch
from networkx import MultiDiGraph

from maheu_group_project.heuristics.flow.types import dealership_to_commodity_group
from maheu_group_project.heuristics.old_flow.old_types import OldNodeIdentifier, OldNodeType
from maheu_group_project.solution.encoding import Location, LocationType


def visualize_flow_graph(flow_network: MultiDiGraph, locations: list[Location],
                         flow: dict[OldNodeIdentifier, dict[OldNodeIdentifier, dict[int, int]]] = None):
    """
    Visualizes the flow network using matplotlib and networkx.

    Args:
        flow_network (DiGraph[NodeIdentifier]): The flow network to visualize.
        locations (list[Location]): List of all locations in the network.
        flow (dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]], optional): Flow data for each edge.
    """
    # Ensure correct type for flow_network
    flow_network: MultiDiGraph[OldNodeIdentifier] = flow_network

    # Get the first day in the flow network to align nodes vertically
    first_day = min(node.day for node in flow_network.nodes)

    # Check if flow data is provided
    flow_data_provided = flow is not None

    pos = {}
    scale = 100  # Controls spacing between nodes in the plot

    # Assign a 2D position to each node for visualization
    for node in flow_network.nodes:
        day = node.day
        location = node.location
        # NORMAL nodes are aligned in columns by location
        if node.type == OldNodeType.NORMAL:
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
        if node.type == OldNodeType.NORMAL and node.location.type == LocationType.DEALER:
            commodity_group = dealership_to_commodity_group(node)
            demand = flow_network.nodes[node].get(commodity_group, 0)
            ax.text(x, y, str(demand), fontsize=6, color='red', ha='center', va='center')

    # Draw all edges, using curvature to distinguish parallel edges
    for u, v in flow_network.edges():
        edge_dict = flow_network.get_edge_data(u, v)
        if edge_dict is None:
            continue
        for idx, (k, data) in enumerate(edge_dict.items()):
            # Default curvature for parallel edges
            rad = 0.1 * (idx + 1)

            # Draw the edge as a curved arrow
            arrow = FancyArrowPatch(
                posA=pos[u], posB=pos[v],
                connectionstyle=f"arc3,rad={rad}",
                arrowstyle='-|>', color='gray', mutation_scale=14, lw=1  # Increased mutation_scale
            )
            ax.add_patch(arrow)

            # Label each edge with its capacity and weight (cost)
            if not flow_data_provided:
                label = f"{data.get('capacity', '')}/{data.get('weight', '')}"
            else:
                # If flow data is provided, use it to label the edge
                flow_value = flow.get(u, {}).get(v, {}).get(k, 0)
                label = f"{flow_value}/{data.get('capacity', '')}/{data.get('weight', '')}"

            label_x = (pos[u][0] + pos[v][0]) / 2
            label_y = (pos[u][1] + pos[v][1]) / 2

            # Adjust label position slightly based on curvature and direction of edge
            if u.type == OldNodeType.HELPER_NODE_ONE and v.type == OldNodeType.NORMAL:
                label_y += abs(pos[u][0] - pos[v][0]) * rad * 2.5
            else:
                label_y -= abs(pos[u][0] - pos[v][0]) * rad * 2.5

            ax.text(label_x, label_y, label, fontsize=7, color='blue', ha='center', va='center',
                    backgroundcolor='white')

    # Optionally, draw node labels (commented out for clarity)
    # labels = {node: f"{node.location.name[:5]}_Day{node.day}_{node.type.to_string()}" for node in flow_network.nodes}
    # nx.draw_networkx_labels(flow_network, pos, labels=labels, font_size=5, font_color='black', ax=ax)

    plt.axis('off')  # Hide axes for cleaner visualization
    plt.tight_layout()
    plt.show()
