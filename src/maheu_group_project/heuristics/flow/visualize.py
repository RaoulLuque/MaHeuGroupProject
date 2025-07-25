import hashlib
import datetime
import networkx as nx

from matplotlib import pyplot as plt
from matplotlib import lines
from matplotlib.patches import FancyArrowPatch
from networkx import MultiDiGraph

from maheu_group_project.heuristics.flow.types import dealership_to_commodity_group, NodeType, NodeIdentifier
from maheu_group_project.solution.encoding import Location, LocationType

FOR_REPORT = True
CUTOFF_DATE = datetime.date(2025, 6, 12)
NODE_TYPE_TO_COLOR = {
    'PLANT': 'green',
    'TERMINAL': 'orange',
    'DEALER': 'red',
    'HELPER': 'white'
}
NODE_SIZE = 750
FONTSIZE = 18


def visualize_flow_network(flow_network: MultiDiGraph, locations: list[Location],
                           commodity_groups: set[str] | None = None,
                           flow: dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]] = None,
                           current_commodity: str | None = None,
                           only_show_flow_nodes: bool = False):
    """
    Visualizes the flow network using matplotlib and networkx.

    Args:
        flow_network (DiGraph[NodeIdentifier]): The flow network to visualize.
        locations (list[Location]): List of all locations in the network.
        commodity_groups (set[str], optional): Set of commodity groups to consider for node annotations.
        flow (dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]], optional): Flow data for each edge.
        only_show_flow_nodes (bool): If True, only nodes involved in the flow will be shown.
    """
    # Ensure correct type for flow_network
    flow_network: MultiDiGraph[NodeIdentifier] = flow_network

    # Filter out nodes with a date later than 2025-06-16 if FOR_REPORT is True
    if FOR_REPORT:
        nodes_to_keep = [node for node in flow_network.nodes if node.day <= CUTOFF_DATE]
        flow_network = nx.MultiDiGraph(flow_network.subgraph(nodes_to_keep))

    # Get the first day in the flow network to align nodes vertically
    first_day = min(node.day for node in flow_network.nodes)

    # Check if flow data is provided
    flow_data_provided = flow is not None

    # Filter out edges which have flow of 0, i.e. no flow was assigned to them.
    filtered_flow = {}
    if flow_data_provided:
        for src, targets in flow.items():
            filtered_targets = {}
            for dst, keys in targets.items():
                filtered_keys = {k: v for k, v in keys.items() if v > 0}
                if filtered_keys:
                    filtered_targets[dst] = filtered_keys
            if filtered_targets:
                filtered_flow[src] = filtered_targets

    # If a flow is provided and only_show_flow_nodes is true, we want filter the graph to only contain the nodes involved in the flow
    if flow_data_provided and only_show_flow_nodes:
        involved_nodes = set(filtered_flow.keys())
        for targets in filtered_flow.values():
            involved_nodes.update(targets.keys())
        flow_network = nx.MultiDiGraph(flow_network.subgraph(involved_nodes))

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

    # Default plot size
    plot_size = (16, 64)
    if FOR_REPORT:
        # Adjust the plot size for report
        plot_size = (16, 24)
    dpi = 150
    if only_show_flow_nodes:
        # Adjust the plot size
        plot_size = (16, 16)
        dpi = 150

    if FOR_REPORT:
        # For report, we want a higher DPI
        dpi = 200

    plt.figure(figsize=plot_size, dpi=dpi)
    ax = plt.gca()

    # Assign colors to nodes based on their type
    node_colors = []
    for node in flow_network.nodes:
        node_type_str = "HELPER" if node.type != NodeType.NORMAL else node.location.type.name
        color = NODE_TYPE_TO_COLOR.get(node_type_str, 'gray')
        node_colors.append(color)

    # Draw all nodes as colored circles with black borders
    nx.draw_networkx_nodes(
        flow_network, pos,
        node_size=NODE_SIZE,
        node_color=node_colors,
        edgecolors='black',
        linewidths=1.0,
        ax=ax
    )

    # Annotate nodes
    for node, (x, y) in pos.items():
        if current_commodity is None:
            # Annotate the dealership nodes with their commodity group demand in different colors
            continue
            # if node.type == NodeType.NORMAL and node.location.type == LocationType.DEALER:
            #     commodity_group = dealership_to_commodity_group(node)
            #     demand = flow_network.nodes[node].get(commodity_group, 0)
            #     color = string_to_color(commodity_group)
            #     ax.text(x, y, str(demand), fontsize=FONTSIZE, color=color, ha='center', va='center')
            #
            # # Annotate nodes with the summarized demands
            # else:
            #     demand = get_demand_sum(flow_network, commodity_groups, node)
            #     ax.text(x, y, str(demand), fontsize=FONTSIZE, color='black', ha='center', va='center')

        else:
            # If a current commodity is specified, we only annotate nodes related to that commodity
            if node.type == NodeType.NORMAL and node.location.type == LocationType.DEALER:
                commodity_group = dealership_to_commodity_group(node)
                if commodity_group == current_commodity:
                    demand = flow_network.nodes[node].get(current_commodity, 0)
                    if demand != 0:
                        color = 'white'
                        ax.text(x, y, str(demand), fontsize=FONTSIZE, color=color, ha='center', va='center')

            # Annotate nodes with their demans for the current commodity group
            else:
                demand = flow_network.nodes[node].get(current_commodity, 0)
                if demand != 0:
                    color = 'white'
                    ax.text(x, y, str(demand), fontsize=FONTSIZE, color=color, ha='center', va='center')

        # We annotate the date to the left of PLANT nodes
        if node.location.type == LocationType.PLANT:
            ax.text(x - 0.25 * scale, y, node.day.strftime("%Y-%m-%d"), fontsize=FONTSIZE, color='black', ha='right',
                    va='center')

    # Draw all edges, using curvature to distinguish parallel edges
    for u, v in flow_network.edges():
        edge_dict = flow_network.get_edge_data(u, v)
        if edge_dict is None:
            continue
        for idx, (k, data) in enumerate(edge_dict.items()):
            # Default curvature for parallel edges
            rad = 0.1 * (idx + 1)

            # Determine edge color and style based on flow data
            edge_color = 'gray'
            lw = 1
            linestyle = 'solid'
            if flow_data_provided:
                flow_value = flow.get(u, {}).get(v, {}).get(k, 0)
                if flow_value > 0:
                    edge_color = 'red'
                    lw = 3
                    linestyle = (0, (5, 5))

            # Draw the edge as a curved arrow
            arrow = FancyArrowPatch(
                posA=pos[u], posB=pos[v],
                connectionstyle=f"arc3,rad={rad}",
                arrowstyle='-|>', color=edge_color, mutation_scale=25, lw=lw,
                shrinkA=15, shrinkB=15,
                linestyle=linestyle
            )
            ax.add_patch(arrow)

            # Label each edge with its capacity and weight (cost)
            weight = data.get('weight') / 100
            weight_correctly_formatted = str(int(weight)) if weight.is_integer() else f"{weight:.2f}"
            capacity = data.get('capacity', '')
            if FOR_REPORT:
                if capacity == 300:
                    capacity = 'inf'

            if not flow_data_provided:
                label = f"{capacity}/{weight_correctly_formatted}"
            else:
                # If flow data is provided, use it to label the edge
                flow_value = flow.get(u, {}).get(v, {}).get(k, 0)
                label = f"{flow_value}/{capacity}/{weight_correctly_formatted}"

            label_x = (pos[u][0] + pos[v][0]) / 2
            label_y = (pos[u][1] + pos[v][1]) / 2

            # Adjust label position slightly based on curvature and direction of edge
            if u.type == NodeType.HELPER_NODE_ONE and v.type == NodeType.NORMAL:
                label_y += abs(pos[u][0] - pos[v][0]) * rad * 2.5
            else:
                label_y -= abs(pos[u][0] - pos[v][0]) * rad * 2.5

            ax.text(label_x, label_y, label, fontsize=FONTSIZE, color='blue', ha='center', va='center',
                    backgroundcolor='white')

    # Optionally, draw node labels (commented out for clarity)
    # labels = {node: f"{node.location.name[:5]}_Day{node.day}_{node.type.to_string()}" for node in flow_network.nodes}
    # nx.draw_networkx_labels(flow_network, pos, labels=labels, font_size=5, font_color='black', ax=ax)

    plt.axis('off')  # Hide axes for cleaner visualization
    plt.tight_layout()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    legend_elements = [
        lines.Line2D([], [], color='green', marker='o', linestyle='None', markersize=10, label='Plant'),
        lines.Line2D([], [], color='orange', marker='o', linestyle='None', markersize=10, label='Terminal'),
        lines.Line2D([], [], color='red', marker='o', linestyle='None', markersize=10, label='Dealership'),
        lines.Line2D([], [], color='white', marker='o', linestyle='None', markersize=10, label='Helper Node',
                     markeredgecolor='black')
    ]
    plt.legend(handles=legend_elements, loc='upper center', fontsize=FONTSIZE, ncol=4)
    plt.show()


def string_to_color(label: str) -> tuple[float, float, float]:
    """
    Converts a string label to a color tuple based on its hash.

    Args:
        label (str): The string label to convert to a color.

    Returns:
        tuple[float, float, float]: A tuple representing the RGB color normalized to [0, 1].
    """

    # Hash the string and get the first 3 bytes
    hash_bytes = hashlib.md5(label.encode('utf-8')).digest()
    r, g, b = hash_bytes[0], hash_bytes[1], hash_bytes[2]
    # Normalize to [0, 1] for matplotlib
    return r / 255, g / 255, b / 255


def get_demand_sum(flow_network: MultiDiGraph, commodity_groups: set[str], node: NodeIdentifier) -> int:
    """
    Computes the sum of demands for a given node across specified commodity groups.

    Args:
        flow_network (MultiDiGraph): The flow network.
        commodity_groups (set[str]): Set of commodity groups to consider.
        node (NodeIdentifier): The node for which to compute the demand sum.

    Returns:
        int: The total demand for the specified commodity groups at the node.
    """
    if not commodity_groups:
        return 0
    return sum(flow_network.nodes[node].get(group, 0) for group in commodity_groups)
