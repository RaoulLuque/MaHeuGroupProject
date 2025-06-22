from maheu_group_project.solution.encoding import Location, Vehicle, TruckIdentifier, Truck, TruckAssignment, \
    VehicleAssignment
from datetime import date, timedelta


def greedy_candidate_path_solver(requested_vehicles: list[Vehicle], expected_trucks: dict[TruckIdentifier, Truck],
                                 LocationList: list[Location],
                                 realised_trucks: dict[TruckIdentifier, Truck],
                                 candidate_paths: dict[tuple[Location, Location], list[list[Location]]]) \
        -> tuple[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment]]:
    """
    A greedy solver that attempts to assign vehicles to trucks in a way that minimizes the total cost.
    On every day, at every location, it sends all vehicles to their respective next location using the cheapest
    available truck, while prioritizing vehicles with the soonest due-date. It completely ignores delay status
    of vehicles, doesn't report any delays itself and, when having to choose a truck with nonzero cost, doesn't
    try to find the most cost-efficient truck for the amount of vehicles it needs to send. It also always tries
    to send all vehicles, never letting them stay at a location unless all available trucks to their next location
    are full or the realised capacity of a truck turns out to be smaller. As of now, in that case, it is not able
    to reassign those vehicles to another truck, so they will remain at their location until the next day.

    :param requested_vehicles: List of Vehicle objects representing the vehicles to be assigned.
    :param expected_trucks: Dictionary mapping TruckIdentifier to Truck objects representing expected trucks.
    :param realised_trucks: Dictionary mapping TruckIdentifier to Truck objects representing realised trucks.
    :param candidate_paths: Dictionary mapping pairs of Location and DEALER to the list of candidate paths between them.
    :return: A tuple containing the updated vehicle and truck assignments.
    """
    vehicle_assignments: list[VehicleAssignment] = [VehicleAssignment(vehicle.id, [], False, timedelta(0)) for vehicle
                                                    in requested_vehicles]
    truck_assignments: dict[TruckIdentifier, TruckAssignment] = {truck_id: TruckAssignment() for truck_id in
                                                                 expected_trucks.keys()}
    first_day: date = min(min(requested_vehicles, key=lambda vehicle: vehicle.available_date).available_date,
                          min(expected_trucks.values(), key=lambda truck: truck.departure_date).departure_date)
    last_day: date = max(max(requested_vehicles, key=lambda vehicle: vehicle.available_date).available_date,
                         max(expected_trucks.values(), key=lambda truck: truck.arrival_date).arrival_date)

    number_of_days = (last_day - first_day).days + 1
    days = [first_day + timedelta(days=i) for i in range(number_of_days)]
    # Location_indices: dict[Location, int] = {loc: i for i, loc in enumerate(LocationList)}
    vehicles_at_loc_at_time: dict[tuple[Location, date], list[int]] = {}
    planned_delayed_vehicles: list[Vehicle] = []
    unplanned_delayed_vehicles: list[Vehicle] = []
    for day in days:  # days from start_date to end_date
        for loc in LocationList:  # This could be PlantList
            # for every day and every location, if that location is a PLANT, add vehicles that become available there
            if loc.type == "PLANT":  # This could be removed if LocationList only contains PLANTs
                vehicles_at_loc_at_time[(loc, day)] += [vehicle.id for vehicle in requested_vehicles if
                                                        vehicle.origin == loc and vehicle.available_date == day]
            for vehicle_id in vehicles_at_loc_at_time[(loc, day)]:
                vehicle = requested_vehicles[vehicle_id]
                # Generate truck sequences for that vehicle from candidate paths

                for truck_sequence in truck_sequences[(vehicle.origin, vehicle.destination)]:
                    # Take first path that has capacity
                    if truck_sequence.capacity() > 0:
                        # assign vehicle to candidate_path
                        for truck_id in candidate_path.truck_ids:
                            vehicle_assignments[vehicle_id].paths_taken.append(truck_id)
                            truck_assignments[truck_id].load.append(vehicle_id)
                        break
    return vehicle_assignments, truck_assignments
