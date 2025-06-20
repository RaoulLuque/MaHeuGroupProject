from platform import mac_ver

from maheu_group_project.solution.encoding import Location, Vehicle, TruckIdentifier, Truck, TruckAssignment, \
    VehicleAssignment
from datetime import date, timedelta
from maheu_group_project.solution.encoding import location_type_from_string


def greedy_solver(requested_vehicles: list[Vehicle], expected_trucks: dict[TruckIdentifier, Truck],
                  realised_trucks: dict[TruckIdentifier, Truck],
                  shortest_paths: dict[tuple[Location, Location], list[Location]]) \
        -> tuple[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment]]:
    """
    A greedy solver that attempts to assign vehicles to trucks in a way that minimizes the total cost.
    On every day, at every location, it sends all vehicles to their respective next location using the cheapest
    available truck, while prioritizing vehicles with the soonest due-date. It decides how many trucks it needs to book
    based on their expected capacity and then only uses these booked trucks, but makes use of additional capacity on a
    truck, if available. It completely ignores delay status of vehicles and doesn't report any delays itself. It also
    always tries to send all vehicles, never letting them stay at a location unless all booked trucks to their next
    location are full.

    :param requested_vehicles: List of Vehicle objects representing the vehicles to be assigned.
    :param expected_trucks: Dictionary mapping TruckIdentifier to Truck objects representing expected trucks.
    :param realised_trucks: Dictionary mapping TruckIdentifier to Truck objects representing realised trucks.
    :param shortest_paths: Dictionary mapping pairs of PLANT and DEALER to the shortest path between them.
    :return: A tuple containing the updated vehicle and truck assignments.
    """
    vehicle_assignments: dict[int, VehicleAssignment] = {
        vehicle.id: VehicleAssignment(vehicle.id, [], False, timedelta(0)) for vehicle
        in requested_vehicles}
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
    Vehicle_from_id: dict[int, Vehicle] = {vehicle.id: vehicle for vehicle in requested_vehicles}
    vehicles_at_loc_at_time: dict[tuple[Location, date], list[int]] = {(loc, day): [] for loc in LocationList for day in
                                                                       days}
    planned_delayed_vehicles: list[Vehicle] = []
    unplanned_delayed_vehicles: list[Vehicle] = []
    for day in days:  # days from start_date to end_date
        # print(f"Processing day {day}")
        for loc in LocationList:
            # print(f"Processing location {loc} on {day}")
            # for every day and every location, if that location is a PLANT, add vehicles that become available there
            if loc.type == location_type_from_string("PLANT"):
                # print(f"Location {loc} is a PLANT, adding available vehicles")
                vehicles_at_loc_at_time[(loc, day)] += [vehicle.id for vehicle in requested_vehicles if
                                                        vehicle.origin == loc and vehicle.available_date == day]
            nextloc_partitions = {}  # Partition the list of vehicles at the current location by what their next location is
            for vehicle_id in vehicles_at_loc_at_time[(loc, day)]:
                # sort vehicles by next loc
                vehicle = Vehicle_from_id[vehicle_id]
                if vehicle.destination == loc:
                    vehicle_assignments[vehicle_id].delayed_by = max(timedelta(0), day - vehicle.due_date)
                else:
                    # If the vehicle's destination is the current location, it doesn't need to be sent anywhere
                    vehicle_path = shortest_paths[vehicle.origin, vehicle.destination]
                    next_loc = vehicle_path[vehicle_path.index(loc) + 1]
                    if next_loc not in nextloc_partitions:
                        # If the next location for a vehicle is not yet a key in the partition, add it
                        nextloc_partitions[next_loc] = []
                    nextloc_partitions[next_loc].append(
                        vehicle)  # Add the vehicle to the partition for its next location
            for next_loc, partition in nextloc_partitions.items():
                # For every next location create a list of trucks that is expected to depart today from the current location to the next location
                # print(f"Processing {len(partition)} vehicles from {loc} to {next_loc} on {day}")
                truck_id_list = []
                for truck_id in expected_trucks.keys():
                    if truck_id.start_location == loc and truck_id.end_location == next_loc and \
                            truck_id.departure_date == day:
                        truck_id_list.append(truck_id)
                sorted_truck_id_list = sorted(truck_id_list, key=lambda truck_id: expected_trucks[
                    truck_id].price)  # sort trucks by price
                sorted_partition = sorted(partition, key=lambda vehicle: vehicle.due_date)  # sort vehicles by due date
                vehicle_amount = len(sorted_partition)
                # decide how many trucks to book based on expected truck list
                total_capacity = 0
                final_truck_id = None
                for truck_id in sorted_truck_id_list:
                    total_capacity += expected_trucks[truck_id].capacity
                    if total_capacity >= vehicle_amount:
                        final_truck_id = truck_id
                        break
                # assign all vehicles in the current partition to trucks
                vehicle_index = 0
                for truck_id in sorted_truck_id_list:
                    if truck_id in realised_trucks:  # If the truck actually exists
                        truck = realised_trucks[truck_id]
                        current_truck_load = len(
                            truck_assignments[truck_id].load)  # This should always be 0, so maybe unnecessary
                        capacity = truck.capacity
                        while current_truck_load < capacity:
                            # While the truck is not full, assign vehicles to it
                            vehicle_id = sorted_partition[vehicle_index].id
                            truck_assignments[truck_id].load.append(vehicle_id)
                            vehicle_assignments[vehicle_id].paths_taken.append(truck_id)
                            vehicles_at_loc_at_time[(next_loc, truck.arrival_date)].append(vehicle_id)
                            current_truck_load += 1
                            vehicle_index += 1
                            if vehicle_index >= vehicle_amount:  # If all vehicles in the partition are assigned, break
                                break
                    if vehicle_index >= vehicle_amount:  # If all vehicles in the partition are assigned, break
                        break
                    if final_truck_id == truck_id:  # If we have loaded the final truck that was booked, break
                        break
                while vehicle_index < vehicle_amount:  # All remaining vehicles remain at the current location for another day
                    vehicles_at_loc_at_time[(loc, day + timedelta(1))].append(sorted_partition[vehicle_index].id)
                    vehicle_index += 1
    v_assignments_list = list(vehicle_assignments.values())
    return v_assignments_list, truck_assignments
