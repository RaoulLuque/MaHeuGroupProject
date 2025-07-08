from networkx import MultiDiGraph
import gurobipy as gp
from gurobipy import GRB

from maheu_group_project.heuristics.flow.types import NodeIdentifier


def translate_flow_network_to_mip(flow_network: MultiDiGraph, commodity_groups: set[str]) -> tuple[
    gp.Model,
    dict[tuple[NodeIdentifier, NodeIdentifier, int, str], gp.Var],
    dict[int, NodeIdentifier]
]:
    """
    Translates a flow network into a Mixed Integer Programming (MIP) formulation. The flow network models a multi-commodity
    integer flow problem, where each commodity has its own sources and sink nodes (multiple sources and one sink per commodity).

    Args:
        flow_network (MultiDiGraph): The flow network to be translated.
        commodity_groups (set[str]): A set of strings representing the commodity groups in the flow network.

    Returns:
        tuple[gp.Model, dict[tuple[NodeIdentifier, NodeIdentifier, int, str], gp.Var], dict[int, NodeIdentifier]]: A tuple containing:
            - gp.Model: The Gurobi model representing the MIP formulation
            - dict[tuple[NodeIdentifier, NodeIdentifier, int, str], gp.Var]: Flow variables indexed by (source_node, target_node, edge_key, commodity)
            - dict[int, NodeIdentifier]: Node mapping for easy access
    """
    # Ensure the correct type for flow_network
    flow_network: MultiDiGraph[NodeIdentifier] = flow_network

    # Create Gurobi model
    try:
        model = gp.Model("MultiCommodityFlow")
        print("Gurobi model created successfully")
    except Exception as e:
        print(f"Error creating Gurobi model: {e}")
        raise

    # Collect all nodes and edges
    nodes = list(flow_network.nodes())
    edges = []

    # Collect all edges with their keys (for parallel edges in MultiDiGraph)
    for u, v, key in flow_network.edges(keys=True):
        edges.append((u, v, key))


    # Create flow variables for each commodity on each edge
    # x[u, v, key, commodity] = flow of commodity on edge (u, v) with key
    flow_vars: dict[tuple[NodeIdentifier, NodeIdentifier, int, str], gp.Var] = {}
    for u, v, key in edges:
        for commodity in commodity_groups:
            var_name = f"flow_{node_to_str(u)}_{node_to_str(v)}_{key}_commodity_{commodity}"
            flow_vars[u, v, key, commodity] = model.addVar(
                vtype=GRB.INTEGER,
                lb=0,
                ub=flow_network[u][v][key]['capacity'],
                # Objective coefficients are set later in the model objective function
                # obj=flow_network[u][v][key]['weight'],
                name=var_name
            )

    # Add flow conservation constraints for each node and commodity
    for node in nodes:
        for commodity in commodity_groups:
            # Get demand for this commodity at this node (default to 0 if not present)
            demand = flow_network.nodes[node].get(commodity, 0)

            # Calculate inflow - outflow
            inflow = gp.quicksum(
                flow_vars[(u, node, key, commodity)]
                for u, v, key in edges if v == node
            )

            outflow = gp.quicksum(
                flow_vars[(node, v, key, commodity)]
                for u, v, key in edges if u == node
            )

            # Flow conservation: inflow - outflow = demand
            # Positive demand means sink (inflow > outflow)
            # Negative demand means source (outflow > inflow)
            model.addConstr(
                inflow - outflow == demand,
                name=f"flow_conservation_{node_to_str(node)}_{commodity}"
            )

    # Add capacity constraints for each edge (sum over all commodities)
    for u, v, key in edges:
        edge_capacity = flow_network[u][v][key]['capacity']
        total_flow = gp.quicksum(
            flow_vars[u, v, key, commodity]
            for commodity in commodity_groups
        )
        model.addConstr(
            total_flow <= edge_capacity,
            name=f"capacity_{node_to_str(u)}_{node_to_str(v)}_{key}"
        )

    # Set objective to minimize total cost
    model.setObjective(
        gp.quicksum(
            flow_vars[u, v, key, commodity] * flow_network[u][v][key]['weight']
            for u, v, key in edges
            for commodity in commodity_groups
        ),
        GRB.MINIMIZE
    )

    # Create node mapping for easier access
    node_mapping = {i: node for i, node in enumerate(nodes)}

    return model, flow_vars, node_mapping


def translate_mip_solution_to_flow(
        model: gp.Model,
        flow_vars: dict[tuple[NodeIdentifier, NodeIdentifier, int, str], gp.Var]) -> dict[str, dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]]]:

    # Extract flow solution. The flow_solution contains the individual flows for each commodity
    flow_solution: dict[str, dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]]] = {}

    for (u, v, key, commodity), var in flow_vars.items():
        flow_value = var.X
        if flow_value > 1e-6:
            if commodity not in flow_solution:
                flow_solution[commodity] = {}
            if u not in flow_solution[commodity]:
                flow_solution[commodity][u] = {}
            if v not in flow_solution[commodity][u]:
                flow_solution[commodity][u][v] = {}
            if key not in flow_solution[commodity][u][v]:
                flow_solution[commodity][u][v][key] = int(round(flow_value))

    return flow_solution


def node_to_str(node: NodeIdentifier) -> str:
    """
    Converts a NodeIdentifier to a useful string representation.

    Args:
        node (NodeIdentifier): The node to convert.

    Returns:
        str: A string representation of the node in the format "location_name_day".
    """
    return f"{node.location.name}_{node.day.isoformat()}"
