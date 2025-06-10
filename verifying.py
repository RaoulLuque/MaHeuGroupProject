from encoding import Location, TruckIdentifier, Vehicle, Truck


def verifyVehiclePath(vehicle, truck_assignment):
    """Tests if a vehicle departs from a location after it arrives there, the segments form a path from origin to destination,
    delay information is consistent with the vehicle's arrival date at destination and the vehicle is part of the truck's load.
    :param vehicle: The vehicle to verify.
    :param truck_assignment: The truck assignment dictionary.
    :return: True if the vehicle's paths are valid, False otherwise.
    """
    # Check if start and end locations and dates are correct
    truck = truck_assignment[vehicle.paths_taken[0]]  # The first truck in the path
    if not (truck.start_location == vehicle.origin):
        # The first truck should start at the vehicle's origin
        print(
            f"The truck with ID {vehicle.paths_taken[0]} needs to start at origin of vehicle {vehicle.id}, but it doesn't.")
        return False
    if not (truck.departure_date >= vehicle.available_date):
        # The first truck should depart after the vehicle is available
        print(
            f"The truck with ID {vehicle.paths_taken[0]} needs to start after availability date of vehicle {vehicle.id}, but it doesn't.")
        return False
    if not (vehicle.id in truck.load):
        print(
            f"The vehicle {vehicle.id} should be part of the load of the truck with ID {vehicle.paths_taken[0]}, but it isn't.")
        return False
    truck = truck_assignment[vehicle.paths_taken[-1]]  # The last truck in the path
    if not (truck.end_location == vehicle.destination):
        # The last truck should end at the vehicle's destination
        print(
            f"The truck with ID {vehicle.paths_taken[-1]} needs to end at destination of vehicle {vehicle.id}, but it doesn't.")
        return False
    if not (vehicle.delayed_by >= 0):  # The delay should be non-negative
        print(f"The vehicle {vehicle.id} has a negative delay.")
        return False
    if not (truck.arrival_date <= vehicle.due_date and vehicle.delayed_by == 0):
        # The last truck should arrive before the vehicle's due date if there is no delay
        if not (truck.arrival_date == vehicle.due_date + vehicle.delayed_by):
            # If there is a delay, the truck's arrival date should match the due date plus the delay
            print(
                f"Delay information for vehicle {vehicle.id} is inconsistent with actual arrival time at destination.")
            return False
    for truck_id in vehicle.paths_taken[1:]:
        # Check if trucks are in the correct order, dates are consistent and vehicle is part of the truck's load
        truck = truck_assignment[truck_id]
        previous_truck = truck_assignment[vehicle.paths_taken[vehicle.paths_taken.index(truck_id) - 1]]
        if not (truck.departure_date >= previous_truck.arrival_date):
            print(
                f"In delivering of vehicle {vehicle.id}, the truck with ID {truck_id} departs before the previous truck arrives.")
            return False
        if not (truck.start_location == previous_truck.end_location):
            print(
                f"In delivering of vehicle {vehicle.id}, the truck with ID {truck_id} does not start at the end location of the previous truck.")
            return False
        if not (vehicle.id in truck.load):  # The vehicle should be part of the truck's load
            print(f"The vehicle {vehicle.id} should be part of the load of the truck with ID {truck_id}, but it isn't.")
            return False
    return True


def verifyTruckLoad(truck, truck_id, vehicle_assignment):
    """
    Verifies that the load on the truck does not exceed its capacity and is consistent with the vehicles assigned to it.
    :param truck: The truck to verify.
    :param truck_id: The identifier of the truck.
    :param vehicle_assignment: The list of vehicles assigned to the solution.
    :return: True if the truck's load is valid, False otherwise.
    """
    total_load = len(truck.load)
    if total_load > truck.capacity:
        print(
            f"The truck with ID {truck_id} has a load of {total_load}, which exceeds its capacity of {truck.capacity}.")
        return False
    for vehicle in vehicle_assignment:
        # Check if every vehicle whose ID is in the truck's load actually uses the truck
        if (vehicle.id in truck.load):
            if not (truck_id in vehicle_assignment[vehicle].paths_taken):
                print(
                    f"The vehicle {vehicle.id} does not use the truck with ID {truck_id}, but it is part of the truck's load.")
                return False
    return True


def verifySolution(vehicle_assignment, truck_assignment, locations):
    # datatypes of input: list[Vehicle], dict[TruckIdentifier, Truck], list[Location]
    """
    Verifies if a given solution is valid.
    :param vehicle_assignment: The list of vehicles assigned to the solution.
    :param truck_assignment: The dictionary of trucks assigned to the solution.
    :param locations: The list of locations.
    :return: True if the solution is valid, False otherwise.
    """
    for vehicle in vehicle_assignment:  # checks if every vehicle uses a valid path with correct delay
        if not verifyVehiclePath(vehicle, truck_assignment):
            print(f"Vehicle {vehicle.id} has an invalid path.")
            return False
    for truck_id in truck_assignment:  # checks if every truck has a valid load
        truck = truck_assignment[truck_id]
        if not verifyTruckLoad(truck, truck_id, vehicle_assignment):
            print(f"Truck {truck_id} has an invalid load.")
            return False
    return True
