from datetime import date

import gurobipy as gp
from gurobipy import GRB
from networkx import MultiDiGraph

from maheu_group_project.heuristics.flow.handle_flows import extract_flow_update_network_and_obtain_final_assignment
from maheu_group_project.heuristics.flow.types import NodeIdentifier
from maheu_group_project.heuristics.flow.visualize import visualize_flow_network
from maheu_group_project.solution.encoding import VehicleAssignment, Vehicle, \
    convert_vehicle_assignments_to_truck_assignments, TruckIdentifier, Truck, Location


def solve_mip(
    model: gp.Model,
):
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


def extract_complete_assignment_from_multi_commodity_flow(flow: dict[str, dict[NodeIdentifier, dict[NodeIdentifier, dict[int, int]]]],
                                                          commodity_groups: dict[str, set[int]],
                                                          vehicles: list[Vehicle],
                                                          trucks: dict[TruckIdentifier, Truck],
                                                          current_day: date,
                                                          flow_network: MultiDiGraph, locations: list[Location]):
    # Create a list to store the vehicle assignments
    vehicle_assignments: list[VehicleAssignment] = []

    # Iterate over each commodity and extract its flow
    for commodity, commodity_flow in flow.items():
        vehicles_in_current_commodity = commodity_groups[commodity]

        visualize_flow_network(flow_network, locations, commodity_groups=set(commodity_groups.keys()), flow=commodity_flow, only_show_flow_nodes=commodity)

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
