import gurobipy as gp
from gurobipy import GRB

from maheu_group_project.heuristics.flow.types import NodeIdentifier


def solve_mip_and_extract_flow(
    model: gp.Model,
    flow_vars: dict[tuple[NodeIdentifier, NodeIdentifier, int, str], gp.Var],
) -> dict[str, dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]]]:
    """
    Solves the MIP model and extracts the flow solution.

    Args:
        model (gp.Model): The Gurobi model to solve
        flow_vars (dict[tuple[NodeIdentifier, NodeIdentifier, int, str], gp.Var]): Flow variables from the MIP formulation

    Returns:
        dict[str, dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]]]: Flow solution in the same format as NetworkX min_cost_flow,
        for each individual commodity.
    """
    # Solve the model
    model.optimize()

    # Check if solution was found
    if model.status != GRB.OPTIMAL:
        if model.status == GRB.INFEASIBLE:
            raise Exception("MIP model is infeasible")
        elif model.status == GRB.UNBOUNDED:
            raise Exception("MIP model is unbounded")
        else:
            raise Exception(f"MIP solver failed with status {model.status}")

    # Extract flow solution. The flow_solution contains the individual flows for each commodity
    flow_solution: dict[str, dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]]] = {}

    for (u, v, key, commodity), var in flow_vars.items():
        flow_value = var.X
        if flow_value > 1e-6:
            if commodity not in flow_solution:
                flow_solution[commodity] = {}
            if u not in flow_solution:
                flow_solution[commodity][u] = {}
            if v not in flow_solution[commodity][u]:
                flow_solution[commodity][u][v] = {}
            if key not in flow_solution[commodity][u][v]:
                print("Flow Value: {flow_value}")
                flow_solution[commodity][u][v][key] = int(flow_value)

    return flow_solution


def get_mip_solution_info(model: gp.Model) -> dict:
    """
    Extracts solution information from the solved MIP model.

    Args:
        model (gp.Model): The solved Gurobi model

    Returns:
        dict: Dictionary containing solution information
    """
    if model.status != GRB.OPTIMAL:
        return {"status": "not_optimal", "objective": None}

    return {
        "status": "optimal",
        "objective_value": model.objVal,
        "solve_time": model.runtime,
        "num_variables": model.numVars,
        "num_constraints": model.numConstrs
    }
