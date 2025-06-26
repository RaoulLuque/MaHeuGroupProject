from datetime import timedelta
from enum import Enum

from maheu_group_project.solution.encoding import VehicleAssignment, TruckIdentifier, Truck, TruckAssignment, Vehicle


class VerifyVehiclePathResult(Enum):
    """
    Class to represent the possible results of verifying a vehicle's path.
    """
    VALID = 0
    NOT_REACHED_DESTINATION = 1


def verify_vehicle_path(vehicle: Vehicle, vehicle_assignment: VehicleAssignment, trucks: dict[TruckIdentifier, Truck],
                        truck_assignments: dict[TruckIdentifier, TruckAssignment]) -> VerifyVehiclePathResult:
    """
    Tests if a vehicle path is valid.

    That is, checks the following: \n
    - The first truck in the path starts at the vehicle's origin, departs after the vehicle is available, and is part of the truck's load.
    - For each truck in the path, it leaves earliest one day after the previous truck arrives, starts at the end location of the previous truck, and the vehicle is part of the truck's load.
    - The last truck in the path ends at the vehicle's destination.
    - The delay information is consistent with the actual arrival date of the last truck in the path.

    Args:
        vehicle (Vehicle): The vehicle to verify.
        vehicle_assignment (VehicleAssignment): The assignment of the vehicle to verify.
        trucks (dict[TruckIdentifier, Truck]): Dictionary of trucks available for transportation.
        truck_assignments (dict[TruckIdentifier, TruckAssignment]): Dictionary mapping truck identifiers to their
            assignments.

    Returns:
        - VerifyVehiclePathResult.VALID if the path is valid.
        - VerifyVehiclePathResult.INVALID if the path is invalid.
        - VerifyVehiclePathResult.NOT_REACHED_DESTINATION if the vehicle did not reach its destination.
    """
    # Get the path taken by the vehicle
    vehicle_path = vehicle_assignment.paths_taken

    # Check if the vehicle actually took any trucks
    if len(vehicle_path) == 0:
        print(f"The vehicle {vehicle_assignment.id} has no trucks assigned.")
        return VerifyVehiclePathResult.NOT_REACHED_DESTINATION

    # Check if the first truck in the path starts at the vehicle's origin, departs after the vehicle is available
    # and is part of the truck's load
    first_truck = trucks[vehicle_path[0]]
    first_truck_assignment = truck_assignments[vehicle_path[0]]
    # Check origin
    if not (first_truck.start_location == vehicle.origin):
        assert False, f"The truck with ID {vehicle_path[0]} needs to start at origin of vehicle {vehicle_assignment.id}, but it doesn't."
    # Check the availability date
    if not (first_truck.departure_date >= vehicle.available_date):
        assert False, f"The truck with ID {vehicle_path[0]} needs to start after availability date of vehicle {vehicle_assignment.id}, but it doesn't."
    # Check if the vehicle is part of the truck's load
    if vehicle_assignment.id not in first_truck_assignment.load:
        assert False, f"The vehicle {vehicle_assignment.id} should be part of the load of the truck with ID {vehicle_path[0]}, but it isn't."

    # For each truck in the path, check if it departs earliest one day after the previous truck arrives,
    # starts at the end location of the previous truck, and the vehicle is part of the truck's load
    for current_truck_id in vehicle_path[1:]:
        current_truck = trucks[current_truck_id]
        current_truck_assignment = truck_assignments[current_truck_id]
        previous_truck = trucks[vehicle_path[vehicle_path.index(current_truck_id) - 1]]
        # Check the departure date
        if not (current_truck.departure_date >= previous_truck.arrival_date + timedelta(1)):
            assert False, f"In delivering of vehicle {vehicle_assignment.id}, the truck with ID {current_truck_id} departs too early. That is, the vehicle departs on the same day it arrives and does not respect the obligatory rest-day 💪"
        # Check locations
        if not (current_truck.start_location == previous_truck.end_location):
            assert False, f"In delivering of vehicle {vehicle_assignment.id}, the truck with ID {current_truck_id} does not start at the end location of the previous truck."
        # Check load
        if vehicle_assignment.id not in current_truck_assignment.load:
            assert False, f"The vehicle {vehicle_assignment.id} should be part of the load of the truck with ID {current_truck_id}, but it isn't."

    # Check if the last truck in the path ends at the vehicle's destination
    last_truck = trucks[vehicle_path[-1]]
    if not (last_truck.end_location == vehicle.destination):
        print(
            f"The truck with ID {vehicle_path[-1]} needs to end at destination of vehicle {vehicle_assignment.id}, but it doesn't.")
        return VerifyVehiclePathResult.NOT_REACHED_DESTINATION

    # Check delay information
    if not (vehicle_assignment.delayed_by >= timedelta(0)):
        assert False, f"The vehicle {vehicle_assignment.id} has a negative delay."
    # Check if the last truck's arrival date is consistent with the vehicle's due date and delay information
    if last_truck.arrival_date > vehicle.due_date:
        # The vehicle is delayed, check if this is consistent with the assignment data
        if vehicle_assignment.delayed_by == timedelta(0):
            assert False, f"The vehicle {vehicle_assignment.id} is actually delayed: {(last_truck.arrival_date - vehicle.due_date).days} days, but this is not consistent with the vehicle assignment: {vehicle_assignment}."
        else:
            if last_truck.arrival_date != vehicle.due_date + vehicle_assignment.delayed_by:
                assert False, f"Delay information for vehicle {vehicle_assignment.id}: {vehicle_assignment.delayed_by.days} days is inconsistent with actual arrival delay of: {(last_truck.arrival_date - vehicle.due_date).days} days"
    return VerifyVehiclePathResult.VALID


def verify_truck_load(truck: Truck, truck_assignment: TruckAssignment,
                      vehicle_assignments: list[VehicleAssignment]) -> bool:
    """
    Verifies that the load on the truck does not exceed its capacity and is consistent with the vehicles assigned to it.

    Args:
        truck (Truck): The truck to verify.
        truck_assignment (TruckAssignment): The assignment of the truck to verify.
        vehicle_assignments (list[VehicleAssignment]): The list of vehicles assigned to the solution.

    Returns:
        bool: True if the truck's load is valid, False otherwise.
    """
    # Get the truck's identifier and load
    truck_id = truck.get_identifier()
    total_load = len(truck_assignment.load)

    # Check if the total load exceeds the truck's capacity
    if total_load > truck.capacity:
        assert False, f"The truck with ID {truck_id} has a load of {total_load}, which exceeds its capacity of {truck.capacity}."

    # For each vehicle in the truck's load, check if the truck is actually used in the vehicle's paths_taken
    for vehicle in vehicle_assignments:
        if vehicle.id in truck_assignment.load:
            if truck_id not in vehicle.paths_taken:
                assert False, f"The vehicle {vehicle.id} does not use the truck with ID {truck_id}, but it is part of the truck's load."
    return True


def verify_solution(vehicles: list[Vehicle], vehicle_assignments: list[VehicleAssignment],
                    trucks: dict[TruckIdentifier, Truck],
                    truck_assignments: dict[TruckIdentifier, TruckAssignment]) -> bool | int:
    """
    Verifies if a given assignment of trucks and vehicles is valid.

    Args:
        vehicles (list[Vehicle]): List of vehicles to be transported.
        vehicle_assignments (list[VehicleAssignment]): List containing assignments of the vehicles.
        trucks (dict[TruckIdentifier, Truck]): Dictionary of all trucks.
        truck_assignments (dict[TruckIdentifier, TruckAssignment]): Dictionary containing the assignments of the truck

    Returns:
        int: If the solution is valid, but some vehicles did not reach their destination, returns the number of such vehicles.
        bool: True if the solution is (entirely) valid, False otherwise.
    """
    # Check if every vehicle uses a valid path
    number_of_vehicles_which_did_not_reach_destination: int = 0
    for i in range(len(vehicle_assignments)):
        vehicle_path_is_valid = verify_vehicle_path(vehicles[i], vehicle_assignments[i], trucks, truck_assignments)
        match vehicle_path_is_valid:
            case VerifyVehiclePathResult.NOT_REACHED_DESTINATION:
                number_of_vehicles_which_did_not_reach_destination += 1

    # Check if every truck has a valid load
    for truck_id in trucks.keys():
        if truck_id not in truck_assignments:
            assert False, f"Truck {truck_id} is not contained in the truck assignments."
        else:
            if not verify_truck_load(trucks[truck_id], truck_assignments[truck_id], vehicle_assignments):
                assert False, f"Truck {truck_id} has an invalid load."
    if number_of_vehicles_which_did_not_reach_destination > 0:
        # Return number_of_cars_which_did_not_reach_destination to indicate that the solution is valid, but some vehicles have not reached their destination
        print(f"{number_of_vehicles_which_did_not_reach_destination} vehicles did not reach their destination.")
        return number_of_vehicles_which_did_not_reach_destination
    else:
        return True
