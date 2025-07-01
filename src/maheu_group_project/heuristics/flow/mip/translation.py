from networkx import MultiDiGraph
import gurobipy as gp
from gurobipy import GRB

from maheu_group_project.heuristics.flow.types import NodeIdentifier


def translate_flow_network_to_mip(flow_network: MultiDiGraph, commodity_groups: set[str]):
    """
    Translates a flow network into a Mixed Integer Programming (MIP) formulation. The flow network models a multi-commodity
    integer flow problem, where each commodity has its own sources and sink nodes (multiple sources and one sink per commodity).

    Args:
        flow_network (MultiDiGraph): The flow network to be translated.
        commodity_groups (set[str]): A set of strings representing the commodity groups in the flow network.

    Returns:
        tuple: A tuple containing:
            - gp.Model: The Gurobi model representing the MIP formulation
            - dict: Flow variables indexed by (source_node, target_node, edge_key, commodity)
            - dict: Node mapping for easy access
    """
    # Ensure the correct type for flow_network
    flow_network: MultiDiGraph[NodeIdentifier] = flow_network

    # Create Gurobi model
    model = gp.Model("MultiCommodityFlow")

    # Collect all nodes and edges
    nodes = list(flow_network.nodes())
    edges = []

    # Collect all edges with their keys (for parallel edges in MultiDiGraph)
    for u, v, key in flow_network.edges(keys=True):
        edges.append((u, v, key))

    # Create flow variables for each commodity on each edge
    # x[u, v, key, commodity] = flow of commodity on edge (u, v) with key
    flow_vars = {}
    for u, v, key in edges:
        for commodity in commodity_groups:
            var_name = f"flow_{hash(u)}_{hash(v)}_{key}_{commodity}"
            flow_vars[u, v, key, commodity] = model.addVar(
                vtype=GRB.INTEGER,
                lb=0,
                ub=flow_network[u][v][key].get('capacity', float('inf')),
                obj=flow_network[u][v][key].get('weight', 0),
                name=var_name
            )

    # Add flow conservation constraints for each node and commodity
    for node in nodes:
        for commodity in commodity_groups:
            # Get demand for this commodity at this node (default to 0 if not present)
            demand = flow_network.nodes[node].get(commodity, 0)

            # Calculate inflow - outflow
            inflow = gp.quicksum(
                flow_vars.get((u, node, key, commodity), 0)
                for u, v, key in edges if v == node
            )

            outflow = gp.quicksum(
                flow_vars.get((node, v, key, commodity), 0)
                for u, v, key in edges if u == node
            )

            # Flow conservation: inflow - outflow = demand
            # Positive demand means sink (inflow > outflow)
            # Negative demand means source (outflow > inflow)
            model.addConstr(
                inflow - outflow == demand,
                name=f"flow_conservation_{hash(node)}_{commodity}"
            )

    # Add capacity constraints for each edge (sum over all commodities)
    for u, v, key in edges:
        edge_capacity = flow_network[u][v][key].get('capacity', float('inf'))
        if edge_capacity < float('inf'):
            total_flow = gp.quicksum(
                flow_vars[u, v, key, commodity]
                for commodity in commodity_groups
            )
            model.addConstr(
                total_flow <= edge_capacity,
                name=f"capacity_{hash(u)}_{hash(v)}_{key}"
            )

    # Set objective to minimize total cost
    model.setObjective(
        gp.quicksum(
            flow_vars[u, v, key, commodity] * flow_network[u][v][key].get('weight', 0)
            for u, v, key in edges
            for commodity in commodity_groups
        ),
        GRB.MINIMIZE
    )

    # Create node mapping for easier access
    node_mapping = {i: node for i, node in enumerate(nodes)}

    return model, flow_vars, node_mapping
