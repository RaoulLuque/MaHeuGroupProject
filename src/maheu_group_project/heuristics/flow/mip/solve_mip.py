from datetime import date

import gurobipy as gp
from gurobipy import GRB

from maheu_group_project.heuristics.flow.solve_deterministically import \
    extract_flow_update_network_and_obtain_final_assignment
from maheu_group_project.heuristics.flow.types import NodeIdentifier
from maheu_group_project.solution.encoding import VehicleAssignment, Vehicle, \
    convert_vehicle_assignments_to_truck_assignments, TruckIdentifier, Truck


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


def extract_complete_assignment_from_multi_commodity_flow(flow: dict[str, dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]]],
                                                          commodity_groups: dict[str, set[int]],
                                                          vehicles: list[Vehicle],
                                                          trucks: dict[TruckIdentifier, Truck],
                                                          current_day: date):
    # Create a list to store the vehicle assignments
    vehicle_assignments: list[VehicleAssignment] = []

    # Iterate over each commodity and extract its flow
    for commodity, commodity_flow in flow.items():
        vehicles_in_current_commodity = commodity_groups[commodity]
        extract_flow_update_network_and_obtain_final_assignment(flow_network=None,
                                                                flow=commodity_flow,
                                                                vehicles_from_current_commodity=vehicles_in_current_commodity,
                                                                vehicles=vehicles,
                                                                current_day=current_day,
                                                                vehicle_assignments=vehicle_assignments)

    # Return the list of vehicle assignments indexed by their id
    vehicle_assignments.sort(key=lambda va: va.id)

    truck_assignments = convert_vehicle_assignments_to_truck_assignments(vehicle_assignments=vehicle_assignments,
                                                                         trucks=trucks)

    return vehicle_assignments, truck_assignments


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
