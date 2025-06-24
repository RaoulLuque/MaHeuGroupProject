from maheu_group_project.solution.encoding import Location, Vehicle, TruckIdentifier, Truck, TruckAssignment, \
    VehicleAssignment
from datetime import date, timedelta
from maheu_group_project.solution.encoding import location_type_from_string


def greedy_solver(requested_vehicles: list[Vehicle], trucks_planned: dict[TruckIdentifier, Truck],
                  trucks_realised: dict[TruckIdentifier, Truck],
                  shortest_paths: dict[tuple[Location, Location], list[Location]]) \
        -> tuple[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment]]:
    """
    A greedy solver that attempts is best to assign vehicles to trucks in a way that minimizes the total cost.
    On every day, at every location, it sends all vehicles to their respective next location using the cheapest
    available truck, while prioritizing vehicles with the soonest due-date. It decides how many trucks it needs to book
    based on their expected capacity and then only uses these booked trucks, but makes use of additional capacity on a
    truck, if available. It completely ignores knowledge more than one day in the future (via expected trucks), delay status of vehicles and doesn't report any delays itself. It also
    always tries to send all vehicles, never letting them stay at a location unless all booked trucks to their next
    location are full.

    Args:
        requested_vehicles (list[Vehicle]): List of Vehicle objects representing the vehicles to be assigned.
        trucks_planned (dict[TruckIdentifier, Truck]): Dictionary mapping TruckIdentifier to Truck objects representing the planned trucks.
        trucks_realised (dict[TruckIdentifier, Truck]): Dictionary mapping TruckIdentifier to Truck objects representing the realized trucks.
        shortest_paths (dict[tuple[Location, Location], list[Location]]): Dictionary mapping pairs of PLANT and DEALER to the shortest path between them.

    Returns:
        tuple: A tuple containing:
            - list[VehicleAssignment]: List of VehicleAssignment objects representing the assignments of vehicles to trucks.
            - dict[TruckIdentifier, TruckAssignment]: Dictionary mapping TruckIdentifier to TruckAssignment objects representing the assignments of trucks.
    """

    first_day: date = min(min(requested_vehicles, key=lambda vehicle: vehicle.available_date).available_date,
                          min(trucks_planned.values(), key=lambda truck: truck.departure_date).departure_date)
    last_day: date = max(max(requested_vehicles, key=lambda vehicle: vehicle.available_date).available_date,
                         max(trucks_planned.values(), key=lambda truck: truck.arrival_date).arrival_date)
    day_of_planning = first_day
    number_of_days = (last_day - first_day).days + 1
    days = [first_day + timedelta(days=i) for i in range(number_of_days)]
    LocationList: list[Location] = list(set(loc for path in shortest_paths.values() for loc in path))
    vehicles_at_loc_at_time: dict[tuple[Location, date], list[int]] = {(loc, day): [] for loc in LocationList for day in
                                                                       (days + [(last_day + timedelta(
                                                                           1))])}  # Include the next day to allow for vehicles to stay at a location for another day
    # Run first with only expected trucks to preview delays
    planned_vehicle_assignments: list[VehicleAssignment] = [
        VehicleAssignment(vehicle.id, [], False, timedelta(0)) for vehicle
        in requested_vehicles]
    for day in days:  # days from start_date to end_date)
        for loc in LocationList:
            # for every day and every location, if that location is a PLANT, add vehicles that become available there
            if loc.type == location_type_from_string("PLANT"):
                vehicles_at_loc_at_time[(loc, day)] += [vehicle.id for vehicle in requested_vehicles if
                                                        vehicle.origin == loc and vehicle.available_date == day]
            nextloc_partitions = {}  # Partition the list of vehicles at the current location by what their next location is
            for vehicle_id in vehicles_at_loc_at_time[(loc, day)]:
                # sort vehicles by next loc
                vehicle = requested_vehicles[vehicle_id]
                if vehicle.destination != loc:
                    # If the vehicle's destination is not the current location, it needs to be sent onwards
                    vehicle_path = shortest_paths[vehicle.origin, vehicle.destination]
                    next_loc = vehicle_path[vehicle_path.index(loc) + 1]
                    if next_loc not in nextloc_partitions:
                        # If the next location for a vehicle is not yet a key in the partition, add it
                        nextloc_partitions[next_loc] = []
                    # Add the vehicle to the partition for its next location
                    nextloc_partitions[next_loc].append(vehicle)
            for next_loc, partition in nextloc_partitions.items():
                # For every next location create a list of trucks that is expected to depart today from the current location to the next location
                truck_id_list = []
                for truck_id in trucks_planned.keys():
                    if truck_id.start_location == loc and truck_id.end_location == next_loc and truck_id.departure_date == day:
                        truck_id_list.append(truck_id)
                # sort trucks by price
                sorted_truck_id_list = sorted(truck_id_list, key=lambda truck_id: trucks_planned[truck_id].price)
                # sort vehicles by due date
                sorted_partition = sorted(partition, key=lambda vehicle: vehicle.due_date)
                vehicle_amount = len(sorted_partition)
                # decide how many trucks to book based on expected truck list
                total_capacity = 0
                final_truck_id = None
                for truck_id in sorted_truck_id_list:
                    total_capacity += trucks_planned[truck_id].capacity
                    if total_capacity >= vehicle_amount:
                        final_truck_id = truck_id
                        break
                # assign all vehicles in the current partition to trucks
                vehicle_index = 0
                for truck_id in sorted_truck_id_list:
                    truck = trucks_planned[truck_id]
                    current_truck_load = 0  # len(truck_assignments[truck_id].load)
                    capacity = truck.capacity
                    while current_truck_load < capacity:
                        # While the truck is not full, assign vehicles to it
                        vehicle_id = sorted_partition[vehicle_index].id
                        planned_vehicle_assignments[vehicle_id].paths_taken.append(truck_id)
                        vehicles_at_loc_at_time[(next_loc, truck.arrival_date + timedelta(1))].append(vehicle_id)
                        current_truck_load += 1
                        vehicle_index += 1
                        if vehicle_index >= vehicle_amount:
                            # If all vehicles in the partition are assigned, break
                            break
                    if vehicle_index >= vehicle_amount:
                        # If all vehicles in the partition are assigned, break
                        break
                    if final_truck_id == truck_id:
                        # If we have loaded the final truck that was booked, break
                        break
                while vehicle_index < vehicle_amount:
                    # All remaining vehicles remain at the current location for another day
                    vehicles_at_loc_at_time[(loc, day + timedelta(1))].append(sorted_partition[vehicle_index].id)
                    vehicle_index += 1
    planned_delayed_vehicles: list[bool] = [False for _ in requested_vehicles]
    # Check which vehicles are delayed based on the planned vehicle assignments
    for vehicle_assignment in planned_vehicle_assignments:
        vehicle = requested_vehicles[vehicle_assignment.id]
        vehicle_path = vehicle_assignment.paths_taken
        final_truck = trucks_planned[vehicle_path[-1]]
        if vehicle.due_date - day_of_planning >= timedelta(7):
            if vehicle_path != [] and final_truck.end_location == vehicle.destination:
                delay = final_truck.arrival_date - vehicle.due_date
                if delay > timedelta(0):
                    planned_delayed_vehicles[vehicle_assignment.id] = True

    # Now determine actual assignments
    vehicle_assignments: list[VehicleAssignment] = [
        VehicleAssignment(vehicle.id, [], False, timedelta(0)) for vehicle
        in requested_vehicles]
    truck_assignments: dict[TruckIdentifier, TruckAssignment] = {truck_id: TruckAssignment() for truck_id in
                                                                 (trucks_planned.keys() | trucks_realised.keys())}
    vehicles_at_loc_at_time: dict[tuple[Location, date], list[int]] = {(loc, day): [] for loc in LocationList for day in
                                                                       (days + [(last_day + timedelta(
                                                                           1))])}

    for day in days:  # days from start_date to end_date
        for loc in LocationList:
            # for every day and every location, if that location is a PLANT, add vehicles that become available there
            if loc.type == location_type_from_string("PLANT"):
                vehicles_at_loc_at_time[(loc, day)] += [vehicle.id for vehicle in requested_vehicles if
                                                        vehicle.origin == loc and vehicle.available_date == day]
            nextloc_partitions = {}  # Partition the list of vehicles at the current location by what their next location is
            for vehicle_id in vehicles_at_loc_at_time[(loc, day)]:
                # sort vehicles by next loc
                vehicle = requested_vehicles[vehicle_id]
                if vehicle.destination == loc:
                    # If the vehicle's destination is the current location, we can measure its delay
                    vehicle_assignments[vehicle_id].delayed_by = max(timedelta(0),
                                                                     day - timedelta(1) - vehicle.due_date)
                else:
                    vehicle_path = shortest_paths[vehicle.origin, vehicle.destination]
                    next_loc = vehicle_path[vehicle_path.index(loc) + 1]
                    if next_loc not in nextloc_partitions:
                        # If the next location for a vehicle is not yet a key in the partition, add it
                        nextloc_partitions[next_loc] = []
                    # Add the vehicle to the partition for its next location
                    nextloc_partitions[next_loc].append(vehicle)
            for next_loc, partition in nextloc_partitions.items():
                # For every next location create a list of trucks that is expected to depart today from the current location to the next location
                truck_id_list = []
                for truck_id in trucks_planned.keys():
                    if truck_id.start_location == loc and truck_id.end_location == next_loc and truck_id.departure_date == day:
                        truck_id_list.append(truck_id)
                # sort trucks by price
                sorted_truck_id_list = sorted(truck_id_list, key=lambda truck_id: trucks_planned[truck_id].price)
                # sort vehicles by due date
                sorted_partition = sorted(partition, key=lambda vehicle: vehicle.due_date)
                vehicle_amount = len(sorted_partition)
                # decide how many trucks to book based on expected truck list
                total_capacity = 0
                final_truck_id = None
                for truck_id in sorted_truck_id_list:
                    total_capacity += trucks_planned[truck_id].capacity
                    if total_capacity >= vehicle_amount:
                        final_truck_id = truck_id
                        break
                # assign all vehicles in the current partition to trucks
                vehicle_index = 0
                for truck_id in sorted_truck_id_list:
                    # Check if the truck actually exists
                    if truck_id in trucks_realised:
                        truck = trucks_realised[truck_id]
                        current_truck_load = 0  # len(truck_assignments[truck_id].load)
                        capacity = truck.capacity
                        while current_truck_load < capacity:
                            # While the truck is not full, assign vehicles to it
                            vehicle_id = sorted_partition[vehicle_index].id
                            truck_assignments[truck_id].load.append(vehicle_id)
                            vehicle_assignments[vehicle_id].paths_taken.append(truck_id)
                            vehicles_at_loc_at_time[(next_loc, truck.arrival_date + timedelta(1))].append(vehicle_id)
                            current_truck_load += 1
                            vehicle_index += 1
                            if vehicle_index >= vehicle_amount:
                                # If all vehicles in the partition are assigned, break
                                break
                    if vehicle_index >= vehicle_amount:
                        # If all vehicles in the partition are assigned, break
                        break
                    if final_truck_id == truck_id:
                        # If we have loaded the final truck that was booked, break
                        break
                while vehicle_index < vehicle_amount:
                    # All remaining vehicles remain at the current location for another day
                    vehicles_at_loc_at_time[(loc, day + timedelta(1))].append(sorted_partition[vehicle_index].id)
                    vehicle_index += 1
    return vehicle_assignments, truck_assignments
