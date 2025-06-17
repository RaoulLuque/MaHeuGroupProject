from platform import mac_ver

from maheu_group_project.solution.encoding import Location, Vehicle, TruckIdentifier, Truck, TruckAssignment, \
    VehicleAssignment
from datetime import date, timedelta


def greedySolver(requested_vehicles: list[Vehicle], expected_trucks: dict[TruckIdentifier, Truck],
                 realised_trucks: dict[TruckIdentifier, Truck],
                 shortest_paths: dict[tuple[Location, Location], list[Location]]) \
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
    :param shortest_paths: Dictionary mapping pairs of PLANT and DEALER to the shortest path between them.
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
    min_truck_number: int = min(truck_id.truck_number for truck_id in expected_trucks.keys())
    max_truck_number: int = max(truck_id.truck_number for truck_id in expected_trucks.keys())

    number_of_days = (last_day - first_day).days + 1
    days = [first_day + timedelta(days=i) for i in range(number_of_days)]
    LocationList: list[Location] = list(set(loc for path in shortest_paths.values() for loc in path))
    Location_indices: dict[Location, int] = {loc: i for i, loc in enumerate(LocationList)}
    vehicles_at_loc_at_time: dict[tuple[Location, date], list[int]] = {}
    planned_delayed_vehicles: list[Vehicle] = []
    unplanned_delayed_vehicles: list[Vehicle] = []
    for day in days:  # days from start_date to end_date
        for loc in LocationList:
            # for every day and every location, if that location is a PLANT, add vehicles that become available there
            if loc.type == "PLANT":
                vehicles_at_loc_at_time[(loc, day)] += [vehicle.id for vehicle in requested_vehicles if
                                                        vehicle.origin == loc and vehicle.available_date == day]
            nextloc_partitions = {}  # Partition of the list of vehicles at the current location by their next location
            for vehicle_id in vehicles_at_loc_at_time[(loc, day)]:
                # sort vehicles by next loc
                vehicle = requested_vehicles[vehicle_id]
                vehicle_path = shortest_paths[vehicle.origin, vehicle.destination]
                next_loc = vehicle_path[vehicle_path.index(loc) + 1]
                if next_loc not in nextloc_partitions:
                    # If the next location for a vehicle is not yet a key in the partition, add it
                    nextloc_partitions[next_loc] = []
                nextloc_partitions[next_loc].append(vehicle)  # Add the vehicle to the partition for its next location
            for next_loc, partition in nextloc_partitions.items():
                # For every next location create a list of trucks that is expected to depart today from the current location to the next location
                truck_id_list = []
                for truck_number in range(min_truck_number, max_truck_number):
                    truck_id = TruckIdentifier(loc, next_loc, truck_number, day)
                    if truck_id in expected_trucks:
                        truck_id_list.append(truck_id)
                sorted_truck_id_list = sorted(truck_id_list, key=lambda truck_id: expected_trucks[
                    truck_id].price)  # sort trucks by price
                sorted_partition = sorted(partition, key=lambda vehicle: vehicle.due_date)  # sort vehicles by due date
                # assign all vehicles in the current partition to trucks
                vehicle_index = 0
                stop_index = len(sorted_partition)
                for truck_id in sorted_truck_id_list:
                    truck = expected_trucks[truck_id]
                    current_truck_load = len(
                        truck_assignments[truck_id].load)  # This should always be 0, so maybe unnecessary
                    capacity = truck.capacity
                    real_capacity = realised_trucks[truck_id].capacity if truck_id in realised_trucks else 0
                    while current_truck_load < capacity:
                        # If the truck is expected to not be full, try to assign vehicles to it
                        vehicle_id = sorted_partition[vehicle_index].id
                        if current_truck_load < real_capacity:
                            # If the truck is really not full, actually assign the vehicle
                            truck_assignments[truck_id].load.append(vehicle_id)
                            vehicle_assignments[vehicle_id].paths_taken.append(truck_id)
                            vehicles_at_loc_at_time[(next_loc, truck.arrival_date)].append(vehicle_id)
                        else:
                            # otherwise the vehicle stays at the location for another day
                            vehicles_at_loc_at_time[(loc, day + timedelta(1))].append(vehicle_id)
                        vehicle_index += 1
                        current_truck_load += 1
                        if vehicle_index >= stop_index:
                            break
                    if vehicle_index >= stop_index:
                        break
                while vehicle_index < stop_index:
                    vehicles_at_loc_at_time[(loc, day + timedelta(1))].append(sorted_partition[vehicle_index].id)
                    vehicle_index += 1
    return vehicle_assignments, truck_assignments
