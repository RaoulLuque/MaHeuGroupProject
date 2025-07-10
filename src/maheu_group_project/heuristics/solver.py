import time
from enum import Enum

from maheu_group_project.heuristics.flow.solve_deterministically import solve_flow_deterministically, \
    solve_flow_as_mip_deterministically
from maheu_group_project.heuristics.flow.network import create_flow_network
from maheu_group_project.heuristics.flow.solve_in_real_time import solve_flow_in_real_time
from maheu_group_project.heuristics.greedy.candidate_paths_calculator import create_logistics_network, \
    calculate_candidate_paths
from maheu_group_project.heuristics.greedy.greedy_candidate_paths import greedy_candidate_path_solver
from maheu_group_project.heuristics.old_flow.old_solve import old_solve_as_flow
from maheu_group_project.heuristics.greedy.greedy import greedy_solver
from maheu_group_project.lower_bounds.flow.uncapacitated_flow import lower_bound_uncapacitated_flow
from maheu_group_project.parsing import read_data, get_shortest_paths
from maheu_group_project.solution.encoding import VehicleAssignment, TruckIdentifier, TruckAssignment, Vehicle, Truck, \
    Location
from maheu_group_project.uncertainty.adjust_planned import assign_quantile_based_planned_capacities


class SolverType(Enum):
    """
    Enum to represent the type of solver used in the optimization process.


    FLOW: A solver that uses a flow-based approach to optimize the assignment of vehicles to trucks. \n
    GREEDY: A solver that uses a greedy algorithm to assign vehicles to trucks based on the cheapest available options.
    """
    FLOW = 0
    GREEDY = 1
    OLD_FLOW = 2
    LOWER_BOUND_UNCAPACITATED_FLOW = 3
    GREEDY_CANDIDATE_PATHS = 4
    FLOW_MIP = 5

    def __str__(self) -> str:
        """
        Returns a string representation of the solver type.
        """
        return self.name


def solve_deterministically(solver_type: SolverType, dataset_dir_name: str, realised_capacity_file_name: str) -> \
        tuple[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment]]:
    """
    Solves the vehicle assignment problem deterministically (directly using the realized data) using the specified
    solver type and dataset.

    Args:
        solver_type (SolverType): The type of solver to use.
        dataset_dir_name (str): The name of the directory containing the dataset files.
        realised_capacity_file_name (str): The name of the CSV file containing truck capacity data.

    Returns:
        tuple: A tuple containing:
            - list[VehicleAssignment]: List of vehicle assignments.
            - dict[TruckIdentifier, TruckAssignment]: Dictionary mapping truck identifiers to their assignments.
    """
    vehicle_assignments, truck_assignments, _, _, _, _, _ = solve_deterministically_and_return_data(
        solver_type, dataset_dir_name, realised_capacity_file_name)
    return vehicle_assignments, truck_assignments


def solve_deterministically_and_return_data(solver_type: SolverType, dataset_dir_name: str,
                                            realised_capacity_file_name: str) -> \
        tuple[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment], list[Location], list[Vehicle], dict[
            TruckIdentifier, Truck], dict[TruckIdentifier, Truck], float]:
    """
    Solves the vehicle assignment problem deterministically (directly using the realized data) using the specified
    solver type and dataset, and returns additional data.

    Args:
        solver_type (SolverType): The type of solver to use.
        dataset_dir_name (str): The name of the directory containing the dataset files.
        realised_capacity_file_name (str): The name of the CSV file containing truck capacity data.

    Returns:
        tuple: A tuple containing:
            - list[VehicleAssignment]: List of vehicle assignments.
            - dict[TruckIdentifier, TruckAssignment]: Dictionary mapping truck identifiers to their assignments.
            - list[Location]: List of unique locations.
            - list[Vehicle]: List of vehicles with their details.
            - dict[TruckIdentifier, Truck]: Dictionary mapping truck identifiers to Truck objects with realised capacity data.
            - dict[TruckIdentifier, Truck]: Dictionary mapping truck identifiers to Truck objects with planned capacity data.
            - float: The time taken to solve the problem in seconds.
    """
    locations, vehicles, trucks_realised, trucks_planned = read_data(dataset_dir_name, realised_capacity_file_name)

    # Start timer
    start_time = time.time()

    match solver_type:
        case SolverType.FLOW:
            flow_network, commodity_groups = create_flow_network(vehicles=vehicles, trucks=trucks_realised,
                                                                 locations=locations)
            vehicle_assignments, truck_assignments = solve_flow_deterministically(flow_network=flow_network,
                                                                                  commodity_groups=commodity_groups,
                                                                                  locations=locations,
                                                                                  vehicles=vehicles,
                                                                                  trucks=trucks_realised)
            end_time = time.time() - start_time
            return vehicle_assignments, truck_assignments, locations, vehicles, trucks_realised, trucks_planned, end_time
        case SolverType.GREEDY:
            shortest_paths = get_shortest_paths(dataset_dir_name, locations)
            vehicle_assignments, truck_assignments = greedy_solver(vehicles, trucks_realised, trucks_realised,
                                                                   shortest_paths)
            end_time = time.time() - start_time
            return vehicle_assignments, truck_assignments, locations, vehicles, trucks_realised, trucks_planned, end_time
        case SolverType.OLD_FLOW:
            vehicle_assignments, truck_assignments = old_solve_as_flow(vehicles, trucks_realised, locations)
            end_time = time.time() - start_time
            return vehicle_assignments, truck_assignments, locations, vehicles, trucks_realised, trucks_planned, end_time
        case SolverType.LOWER_BOUND_UNCAPACITATED_FLOW:
            vehicle_assignments, truck_assignments, trucks_realised = lower_bound_uncapacitated_flow(dataset_dir_name,
                                                                                                     realised_capacity_file_name)
            end_time = time.time() - start_time
            return vehicle_assignments, truck_assignments, locations, vehicles, trucks_realised, trucks_planned, end_time
        case SolverType.GREEDY_CANDIDATE_PATHS:
            logistics_network = create_logistics_network(locations, trucks_realised)
            candidate_paths = calculate_candidate_paths(logistics_network)
            vehicle_assignments, truck_assignments = greedy_candidate_path_solver(vehicles, trucks_realised, locations,
                                                                                  trucks_realised, candidate_paths)
            end_time = time.time() - start_time
            return vehicle_assignments, truck_assignments, locations, vehicles, trucks_realised, trucks_planned, end_time
        case SolverType.FLOW_MIP:
            flow_network, commodity_groups = create_flow_network(vehicles=vehicles, trucks=trucks_realised,
                                                                 locations=locations)
            vehicle_assignments, truck_assignments = solve_flow_as_mip_deterministically(flow_network=flow_network,
                                                                                         commodity_groups=commodity_groups,
                                                                                         vehicles=vehicles,
                                                                                         trucks=trucks_realised,
                                                                                         locations=locations)
            end_time = time.time() - start_time
            return vehicle_assignments, truck_assignments, locations, vehicles, trucks_realised, trucks_planned, end_time
        case _:
            raise ValueError(f"Unknown solver type: {solver_type}")


def solve_real_time(solver_type: SolverType, dataset_dir_name: str, realised_capacity_file_name: str) -> \
        tuple[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment]]:
    """
    Solves the vehicle assignment problem in real-time (only using the realized data as available) using the specified
    solver type and dataset.

    Args:
        solver_type (SolverType): The type of solver to use.
        dataset_dir_name (str): The name of the directory containing the dataset files.
        realised_capacity_file_name (str): The name of the CSV file containing truck capacity data.

    Returns:
        tuple: A tuple containing:
            - list[VehicleAssignment]: List of vehicle assignments.
            - dict[TruckIdentifier, TruckAssignment]: Dictionary mapping truck identifiers to their assignments.
    """
    vehicle_assignments, truck_assignments, _, _, _, _, _ = solve_deterministically_and_return_data(
        solver_type, dataset_dir_name, realised_capacity_file_name)
    return vehicle_assignments, truck_assignments


def solve_real_time_and_return_data(solver_type: SolverType, dataset_dir_name: str, realised_capacity_file_name: str,
                                    quantile: float) -> \
        tuple[
            list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment], list[Location], list[Vehicle], dict[
                TruckIdentifier, Truck], dict[TruckIdentifier, Truck], float]:
    """
    Solves the vehicle assignment problem in real-time (only using the realized data as available) using the specified
    solver type and dataset, and returns additional data.

    Args:
        solver_type (SolverType): The type of solver to use.
        dataset_dir_name (str): The name of the directory containing the dataset files.
        realised_capacity_file_name (str): The name of the CSV file containing truck capacity data.
        quantile (float): The quantile value to adjust the planned truck capacities with. Default is 1.0.

    Returns:
        tuple: A tuple containing:
            - list[VehicleAssignment]: List of vehicle assignments.
            - dict[TruckIdentifier, TruckAssignment]: Dictionary mapping truck identifiers to their assignments.
            - list[Location]: List of unique locations.
            - list[Vehicle]: List of vehicles with their details.
            - dict[TruckIdentifier, Truck]: Dictionary mapping truck identifiers to Truck objects with realised capacity data.
            - dict[TruckIdentifier, Truck]: Dictionary mapping truck identifiers to Truck objects with planned capacity data.
            - float: The time taken to solve the problem in seconds.
    """
    locations, vehicles, trucks_realised, trucks_planned = read_data(dataset_dir_name, realised_capacity_file_name)

    if quantile != 0.0:
        print(f"Adjusting planned truck capacities with quantile: {quantile}")
        trucks_planned = assign_quantile_based_planned_capacities(trucks_planned, dataset_dir_name, quantile)

    # Start timer
    start_time = time.time()

    match solver_type:
        case SolverType.FLOW:
            flow_network, commodity_groups = create_flow_network(vehicles=vehicles, trucks=trucks_planned,
                                                                 locations=locations)
            vehicle_assignments, truck_assignments = solve_flow_in_real_time(flow_network=flow_network,
                                                                             commodity_groups=commodity_groups,
                                                                             locations=locations, vehicles=vehicles,
                                                                             trucks_planned=trucks_planned,
                                                                             trucks_realised=trucks_realised,
                                                                             solve_as_mip=False)
            end_time = time.time() - start_time
            return vehicle_assignments, truck_assignments, locations, vehicles, trucks_realised, trucks_planned, end_time
        case SolverType.FLOW_MIP:
            flow_network, commodity_groups = create_flow_network(vehicles=vehicles, trucks=trucks_planned,
                                                                 locations=locations)
            vehicle_assignments, truck_assignments = solve_flow_in_real_time(flow_network=flow_network,
                                                                             commodity_groups=commodity_groups,
                                                                             locations=locations, vehicles=vehicles,
                                                                             trucks_planned=trucks_planned,
                                                                             trucks_realised=trucks_realised,
                                                                             solve_as_mip=True)
            end_time = time.time() - start_time
            return vehicle_assignments, truck_assignments, locations, vehicles, trucks_realised, trucks_planned, end_time
        case SolverType.GREEDY:
            shortest_paths = get_shortest_paths(dataset_dir_name, locations)
            vehicle_assignments, truck_assignments = greedy_solver(requested_vehicles=vehicles,
                                                                   trucks_planned=trucks_planned,
                                                                   trucks_realised=trucks_realised,
                                                                   shortest_paths=shortest_paths)
            end_time = time.time() - start_time
            return vehicle_assignments, truck_assignments, locations, vehicles, trucks_realised, trucks_planned, end_time
        case SolverType.GREEDY_CANDIDATE_PATHS:
            logistics_network = create_logistics_network(locations, trucks_realised)
            candidate_paths = calculate_candidate_paths(logistics_network)
            vehicle_assignments, truck_assignments = greedy_candidate_path_solver(vehicles, trucks_planned, locations,
                                                                                  trucks_realised, candidate_paths)
            end_time = time.time() - start_time
            return vehicle_assignments, truck_assignments, locations, vehicles, trucks_realised, trucks_planned, end_time
        case _:
            raise ValueError(f"This solver type is not supported: {solver_type}")


def solver_type_from_string(solver_type_str: str) -> SolverType:
    """
    Converts a string representation of a solver type to the corresponding SolverType enum.

    Args:
        solver_type_str (str): The string representation of the solver type.

    Returns:
        SolverType: The corresponding SolverType enum.
    """
    if solver_type_str == "FLOW":
        return SolverType.FLOW
    elif solver_type_str == "GREEDY":
        return SolverType.GREEDY
    elif solver_type_str == "OLD_FLOW":
        return SolverType.OLD_FLOW
    elif solver_type_str == "LOWER_BOUND":
        return SolverType.LOWER_BOUND_UNCAPACITATED_FLOW
    elif solver_type_str == "LOWER_BOUND_UNCAPACITATED_FLOW":
        return SolverType.LOWER_BOUND_UNCAPACITATED_FLOW
    elif solver_type_str == "GREEDY_CANDIDATE_PATHS":
        return SolverType.GREEDY_CANDIDATE_PATHS
    elif solver_type_str == "CANDIDATE_PATHS":
        return SolverType.GREEDY_CANDIDATE_PATHS
    elif solver_type_str == "FLOW_MIP":
        return SolverType.FLOW_MIP
    elif solver_type_str == "MIP":
        return SolverType.FLOW_MIP
    else:
        raise ValueError(
            f"Unknown solver type: {solver_type_str}. Expected one of: {[str(solver) for solver in SolverType]}")
