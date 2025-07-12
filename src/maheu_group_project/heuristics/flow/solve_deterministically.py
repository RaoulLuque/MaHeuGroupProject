import networkx as nx
from networkx import MultiDiGraph

from maheu_group_project.heuristics.common import get_first_last_and_days
from maheu_group_project.heuristics.flow.handle_flows import extract_flow_update_network_and_obtain_final_assignment
from maheu_group_project.heuristics.flow.mip.translation import translate_flow_network_to_mip, \
    translate_mip_solution_to_flow
from maheu_group_project.heuristics.flow.mip.solve_mip import solve_mip, \
    extract_complete_assignment_from_multi_commodity_flow
from maheu_group_project.heuristics.flow.types import NodeIdentifier, NodeType, \
    dealership_to_commodity_group
from maheu_group_project.heuristics.flow.visualize import visualize_flow_network
from maheu_group_project.solution.encoding import Vehicle, TruckIdentifier, Truck, Location, LocationType, \
    TruckAssignment, \
    VehicleAssignment, \
    convert_vehicle_assignments_to_truck_assignments


def solve_flow_deterministically(flow_network: MultiDiGraph, commodity_groups: dict[str, set[int]],
                                 locations: list[Location], vehicles: list[Vehicle],
                                 trucks: dict[TruckIdentifier, Truck]) -> \
        (
                tuple)[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment]]:
    """
    Solves the multicommodity min-cost flow problem heuristically by solving multiple single commodity min-cost flow
    problems for each DEALER location and day in the flow network.

    This function iterates over each day (in ascending order) and each DEALER location, solving a min-cost flow problem
    for the vehicles that are due on that day and at that location. The flow network is expected to have been created
    with the `create_flow_network` function.

    Args:
        flow_network (MultiDiGraph[NodeIdentifier]): The flow network to solve.
        commodity_groups (dict[str, set[int]]): A dictionary mapping each commodity group to the set of vehicles (their ids)
        that belong to it.
        locations (list[Location]): List of locations involved in the transportation.
        vehicles (list[Vehicle]): List of vehicles to be transported.
        trucks (dict[TruckIdentifier, Truck]): Dictionary of trucks available for transportation.

    Returns:
        tuple: A tuple containing the list of locations, vehicles, and trucks. The trucks and vehicles are adjusted
        to contain their respective plans.
    """
    # Ensure the correct type for flow_network
    flow_network: MultiDiGraph[NodeIdentifier] = flow_network

    # Get the days involved in the flow network
    first_day, last_day, days = get_first_last_and_days(vehicles=vehicles, trucks=trucks)
    current_day = first_day

    # Create a list to store the vehicle assignments
    vehicle_assignments: list[VehicleAssignment] = []

    # visualize_flow_network(flow_network, locations)

    # We iterate over the days from first to last, then those locations which are DEALER locations
    for day in days:
        for location in locations:
            if location.type == LocationType.DEALER:
                # For each DEALER location, solve a min-cost flow problem with the commodity group corresponding to
                # the current day and location.
                commodity_group = dealership_to_commodity_group(NodeIdentifier(day, location, NodeType.NORMAL))

                # First, check whether there is actually any demand for this commodity group (day and location)
                target_node = NodeIdentifier(day, location, NodeType.NORMAL)
                if flow_network.nodes[target_node].get(commodity_group, 0) != 0:
                    # Compute the single commodity min-cost flow for the current commodity group
                    flow = nx.min_cost_flow(flow_network, demand=commodity_group, capacity='capacity', weight='weight')

                    # visualize_flow_network(flow_network, locations, commodity_groups=set(commodity_groups.keys()),
                    #                        flow=flow, current_commodity=commodity_group,
                    #                        only_show_flow_nodes=True)
                    # visualize_flow_network(flow_network, locations, commodity_groups=set(commodity_groups.keys()),
                    #                        current_commodity=commodity_group)
                    # visualize_flow_network(flow_network, locations, commodity_groups=set(commodity_groups.keys()),
                    #                        flow=flow, current_commodity=commodity_group)

                    # Extract the solution from the flow and update the flow network
                    extract_flow_update_network_and_obtain_final_assignment(flow_network=flow_network, flow=flow,
                                                                            vehicles_from_current_commodity=
                                                                            commodity_groups[commodity_group],
                                                                            vehicles=vehicles, current_day=current_day,
                                                                            vehicle_assignments=vehicle_assignments)

                    # visualize_flow_network(flow_network, locations)

    # Return the list of vehicle assignments indexed by their id
    vehicle_assignments.sort(key=lambda va: va.id)

    truck_assignments = convert_vehicle_assignments_to_truck_assignments(vehicle_assignments=vehicle_assignments,
                                                                         trucks=trucks)

    return vehicle_assignments, truck_assignments


def solve_flow_as_mip_deterministically(flow_network: MultiDiGraph,
                                        commodity_groups: dict[str, set[int]],
                                        vehicles: list[Vehicle],
                                        trucks: dict[TruckIdentifier, Truck],
                                        locations: list[Location]) -> tuple[
    list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment]]:
    first_day, _, _ = get_first_last_and_days(vehicles=vehicles, trucks=trucks)

    if False:
        visualize_flow_network(flow_network, locations, set(commodity_groups.keys()))

    model, flow_vars, node_mapping = translate_flow_network_to_mip(flow_network, set(commodity_groups.keys()))
    solve_mip(model)
    flow_solution = translate_mip_solution_to_flow(model, flow_vars)
    vehicle_assignments, truck_assignments = extract_complete_assignment_from_multi_commodity_flow(flow=flow_solution,
                                                                                                   commodity_groups=commodity_groups,
                                                                                                   vehicles=vehicles,
                                                                                                   trucks=trucks,
                                                                                                   current_day=first_day,
                                                                                                   flow_network=flow_network,
                                                                                                   locations=locations)
    return vehicle_assignments, truck_assignments
