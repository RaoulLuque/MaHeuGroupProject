import datetime

from maheu_group_project.solution.encoding import VehicleAssignment, TruckIdentifier, Truck, TruckAssignment, Vehicle


def verify_vehicle_path(vehicle: Vehicle, vehicle_assignment: VehicleAssignment, trucks: dict[TruckIdentifier, Truck],
                        truck_assignments: dict[TruckIdentifier, TruckAssignment]) -> bool | int:
    """
    Tests if a vehicle departs from a location after it arrives there, the segments form a path from origin to destination,
    delay information is consistent with the vehicle's arrival date at the destination, and the vehicle is part of the truck's load.

    Args:
        vehicle (Vehicle): The vehicle to verify.
        vehicle_assignment (VehicleAssignment): The assignment of the vehicle to verify.
        trucks (dict[TruckIdentifier, Truck]): Dictionary of trucks available for transportation.
        truck_assignments (dict[TruckIdentifier, TruckAssignment]): Dictionary mapping truck identifiers to their
            assignments.

    Returns:
        bool: True if the vehicle's path is valid, False otherwise.
    """
    # Check if start and end locations and dates are correct
    # Take the first truck in the path and its assignment
    vehicle_path = vehicle_assignment.paths_taken
    if vehicle_path == []:
        print(f"The vehicle {vehicle_assignment.id} has no trucks assigned.")
        return True  # No path taken, nothing to verify
    truck = trucks[vehicle_path[0]]
    truck_assignment = truck_assignments[vehicle_path[0]]
    if not (truck.start_location == vehicle.origin):
        # The first truck should start at the vehicle's origin
        print(
            f"The truck with ID {vehicle_path[0]} needs to start at origin of vehicle {vehicle_assignment.id}, but it doesn't.")
        return False
    if not (truck.departure_date >= vehicle.available_date):
        # The first truck should depart after the vehicle is available
        print(
            f"The truck with ID {vehicle_path[0]} needs to start after availability date of vehicle {vehicle_assignment.id}, but it doesn't.")
        return False
    if vehicle_assignment.id not in truck_assignment.load:
        print(
            f"The vehicle {vehicle_assignment.id} should be part of the load of the truck with ID {vehicle_path[0]}, but it isn't.")
        return False
    for truck_id in vehicle_path[1:]:
        # Check if trucks are in the correct order, dates are consistent and vehicle is part of the truck's load
        truck = trucks[truck_id]
        truck_assignment = truck_assignments[truck_id]
        previous_truck = trucks[vehicle_path[vehicle_path.index(truck_id) - 1]]
        if not (truck.departure_date >= previous_truck.arrival_date):
            print(
                f"In delivering of vehicle {vehicle_assignment.id}, the truck with ID {truck_id} departs before the previous truck arrives.")
            return False
        if not (truck.start_location == previous_truck.end_location):
            print(
                f"In delivering of vehicle {vehicle_assignment.id}, the truck with ID {truck_id} does not start at the end location of the previous truck.")
            return False
        if vehicle_assignment.id not in truck_assignment.load:
            # The vehicle should be part of the truck's load
            print(
                f"The vehicle {vehicle_assignment.id} should be part of the load of the truck with ID {truck_id}, but it isn't.")
            return False
    truck = trucks[vehicle_path[-1]]  # The last truck in the path
    if not (truck.end_location == vehicle.destination):
        # The last truck should end at the vehicle's destination
        print(
            f"The truck with ID {vehicle_path[-1]} needs to end at destination of vehicle {vehicle_assignment.id}, but it doesn't.")
        return 1  # Return 1 to indicate that the vehicle did not reach its destination
    if not (vehicle_assignment.delayed_by >= datetime.timedelta(0)):  # The delay should be non-negative
        print(f"The vehicle {vehicle_assignment.id} has a negative delay.")
        return False
    if not (truck.arrival_date <= vehicle.due_date and vehicle_assignment.delayed_by == datetime.timedelta(
            0)):
        # The last truck should arrive before the vehicle's due date if there is no delay
        if not (truck.arrival_date == vehicle.due_date + vehicle_assignment.delayed_by):
            # If there is a delay, the truck's arrival date should match the due date plus the delay
            print(
                f"Delay information for vehicle {vehicle_assignment.id} is inconsistent with actual arrival time at destination.")
            return False
    return True


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
    if total_load > truck.capacity:
        print(
            f"The truck with ID {truck_id} has a load of {total_load}, which exceeds its capacity of {truck.capacity}.")
        return False
    for vehicle in vehicle_assignments:
        # Check if every vehicle whose ID is in the truck's load actually uses the truck
        if vehicle.id in truck_assignment.load:
            if truck_id not in vehicle.paths_taken:
                print(
                    f"The vehicle {vehicle.id} does not use the truck with ID {truck_id}, but it is part of the truck's load.")
                return False
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
        bool: True if the solution is valid, False otherwise.
        int: If the solution is valid, but some vehicles did not reach their destination, returns the number of such vehicles.
    """
    # Check if every vehicle uses a valid path with correct delay
    number_of_cars_which_did_not_reach_destination = 0
    for i in range(len(vehicle_assignments)):
        if verify_vehicle_path(vehicles[i], vehicle_assignments[i], trucks, truck_assignments) is 1:
            number_of_cars_which_did_not_reach_destination += 1
        elif not verify_vehicle_path(vehicles[i], vehicle_assignments[i], trucks, truck_assignments):
            print(f"Vehicle {vehicles[i].id} has an invalid path.")
            return False
    # Check if every truck has a valid load
    for truck_id in trucks.keys():
        if truck_id not in truck_assignments:
            print(f"Truck {truck_id} has no assignment.")
        else:
            if not verify_truck_load(trucks[truck_id], truck_assignments[truck_id], vehicle_assignments):
                print(f"Truck {truck_id} has an invalid load.")
                return False
    if number_of_cars_which_did_not_reach_destination > 0:
        # Return number_of_cars_which_did_not_reach_destination to indicate that the solution is valid, but some vehicles have reached their destination
        print(f"{number_of_cars_which_did_not_reach_destination} vehicles did not reach their destination.")
        return number_of_cars_which_did_not_reach_destination
    return True
