from enum import Enum

from maheu_group_project.heuristics.flow.solve_deterministically import solve_flow_deterministically
from maheu_group_project.heuristics.flow.network import create_flow_network
from maheu_group_project.heuristics.flow.solve_in_real_time import solve_flow_in_real_time
from maheu_group_project.heuristics.old_flow.old_solve import old_solve_as_flow
from maheu_group_project.heuristics.greedy.greedy import greedy_solver
from maheu_group_project.lower_bounds.flow.uncapacitated_flow import lower_bound_uncapacitated_flow
from maheu_group_project.parsing import read_data, get_shortest_paths
from maheu_group_project.solution.encoding import VehicleAssignment, TruckIdentifier, TruckAssignment, Vehicle, Truck, \
    Location


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

    def __str__(self) -> str:
        """
        Returns a string representation of the solver type.
        """
        return self.name


def solve_deterministically(solver_type: SolverType, dataset_dir_name: str, realised_capacity_file_name: str) -> (
        tuple)[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment]]:
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
    vehicle_assignments, truck_assignments, _, _, _, _ = solve_deterministically_and_return_data(
        solver_type, dataset_dir_name, realised_capacity_file_name)
    return vehicle_assignments, truck_assignments


def solve_deterministically_and_return_data(solver_type: SolverType, dataset_dir_name: str,
                                            realised_capacity_file_name: str) -> (
        tuple)[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment], list[Location], list[Vehicle], dict[
    TruckIdentifier, Truck], dict[TruckIdentifier, Truck]]:
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
    """
    locations, vehicles, trucks_realised, trucks_planned = read_data(dataset_dir_name, realised_capacity_file_name)

    match solver_type:
        case SolverType.FLOW:
            flow_network, commodity_groups = create_flow_network(vehicles=vehicles, trucks=trucks_realised,
                                                                 locations=locations)
            vehicle_assignments, truck_assignments = solve_flow_deterministically(flow_network=flow_network,
                                                                                  commodity_groups=commodity_groups,
                                                                                  locations=locations,
                                                                                  vehicles=vehicles,
                                                                                  trucks=trucks_realised)
            return vehicle_assignments, truck_assignments, locations, vehicles, trucks_realised, trucks_planned
        case SolverType.GREEDY:
            shortest_paths = get_shortest_paths(dataset_dir_name, locations)
            vehicle_assignments, truck_assignments = greedy_solver(vehicles, trucks_realised, trucks_realised,
                                                                   shortest_paths)
            return vehicle_assignments, truck_assignments, locations, vehicles, trucks_realised, trucks_planned
        case SolverType.OLD_FLOW:
            vehicle_assignments, truck_assignments = old_solve_as_flow(vehicles, trucks_realised, locations)
            return vehicle_assignments, truck_assignments, locations, vehicles, trucks_realised, trucks_planned
        case SolverType.LOWER_BOUND_UNCAPACITATED_FLOW:
            vehicle_assignments, truck_assignments, trucks_realised = lower_bound_uncapacitated_flow(dataset_dir_name,
                                                                                                     realised_capacity_file_name)
            return vehicle_assignments, truck_assignments, locations, vehicles, trucks_realised, trucks_planned
        case _:
            raise ValueError(f"Unknown solver type: {solver_type}")


def solve_real_time(solver_type: SolverType, dataset_dir_name: str, realised_capacity_file_name: str) -> (
        tuple)[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment]]:
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
    vehicle_assignments, truck_assignments, _, _, _, _ = solve_deterministically_and_return_data(
        solver_type, dataset_dir_name, realised_capacity_file_name)
    return vehicle_assignments, truck_assignments


def solve_real_time_and_return_data(solver_type: SolverType, dataset_dir_name: str, realised_capacity_file_name: str) -> \
(
        tuple)[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment], list[Location], list[Vehicle], dict[
    TruckIdentifier, Truck], dict[TruckIdentifier, Truck]]:
    """
    Solves the vehicle assignment problem in real-time (only using the realized data as available) using the specified
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
    """
    locations, vehicles, trucks_realised, trucks_planned = read_data(dataset_dir_name, realised_capacity_file_name)

    match solver_type:
        case SolverType.FLOW:
            flow_network, commodity_groups = create_flow_network(vehicles=vehicles, trucks=trucks_planned,
                                                                 locations=locations)
            vehicle_assignments, truck_assignments = solve_flow_in_real_time(flow_network=flow_network,
                                                                             commodity_groups=commodity_groups,
                                                                             locations=locations, vehicles=vehicles,
                                                                             trucks_planned=trucks_planned,
                                                                             trucks_realised=trucks_realised)
            return vehicle_assignments, truck_assignments, locations, vehicles, trucks_realised, trucks_planned
        case SolverType.GREEDY:
            shortest_paths = get_shortest_paths(dataset_dir_name, locations)
            vehicle_assignments, truck_assignments = greedy_solver(requested_vehicles=vehicles,
                                                                   trucks_planned=trucks_planned,
                                                                   trucks_realised=trucks_realised,
                                                                   shortest_paths=shortest_paths)
            return vehicle_assignments, truck_assignments, locations, vehicles, trucks_realised, trucks_planned
        # case SolverType.LOWER_BOUND_UNCAPACITATED_FLOW:
        #     vehicle_assignments, truck_assignments, trucks_realised = lower_bound_uncapacitated_flow(dataset_dir_name,
        #                                                                                              realised_capacity_file_name)
        #     return vehicle_assignments, truck_assignments, locations, vehicles, trucks_realised, trucks_planned
        case _:
            raise ValueError(f"This solver type is not supported: {solver_type}")
