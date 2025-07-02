import gurobipy as gp
from gurobipy import GRB
from typing import Dict, Tuple

from maheu_group_project.heuristics.flow.types import NodeIdentifier


def solve_mip_and_extract_flow(
    model: gp.Model,
    flow_vars: Dict[Tuple[NodeIdentifier, NodeIdentifier, int, str], gp.Var],
    commodity_groups: set[str]
) -> Dict[NodeIdentifier, Dict[NodeIdentifier, Dict[int, Dict[str, int]]]]:
    """
    Solves the MIP model and extracts the flow solution.

    Args:
        model (gp.Model): The Gurobi model to solve
        flow_vars (dict[tuple[NodeIdentifier, NodeIdentifier, int, str], gp.Var]): Flow variables from the MIP formulation
        commodity_groups (set[str]): Set of commodity group names

    Returns:
        Dict[NodeIdentifier, dict[NodeIdentifier, Dict[int, Dict[str, int]]]]: Flow solution in the same format as NetworkX min_cost_flow
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

    # Extract flow solution
    flow_solution: Dict[NodeIdentifier, Dict[NodeIdentifier, Dict[int, Dict[str, int]]]] = {}

    for (u, v, key, commodity), var in flow_vars.items():
        flow_value = var.X
        if flow_value > 1e-6:  # Only include positive flows
            if u not in flow_solution:
                flow_solution[u] = {}
            if v not in flow_solution[u]:
                flow_solution[u][v] = {}
            if key not in flow_solution[u][v]:
                flow_solution[u][v][key] = {}

            flow_solution[u][v][key][commodity] = int(round(flow_value))

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
