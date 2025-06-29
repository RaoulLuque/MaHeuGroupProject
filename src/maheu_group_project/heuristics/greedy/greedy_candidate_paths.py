from maheu_group_project.solution.encoding import Location, Vehicle, TruckIdentifier, Truck, TruckAssignment, \
    VehicleAssignment
from datetime import date, timedelta
from maheu_group_project.solution.encoding import location_type_from_string
from maheu_group_project.heuristics.common import get_first_last_and_days


def greedy_candidate_path_solver(requested_vehicles: list[Vehicle], trucks_planned: dict[TruckIdentifier, Truck],
                                 location_list: list[Location], trucks_realised: dict[TruckIdentifier, Truck],
                                 candidate_paths: dict[tuple[Location, Location], list[tuple[Location, int, bool]]]) \
        -> tuple[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment]]:
    """
    :param location_list:
    :param requested_vehicles: List of Vehicle objects representing the vehicles to be assigned.
    :param trucks_planned: Dictionary mapping TruckIdentifier to Truck objects representing expected trucks.
    :param trucks_realised: Dictionary mapping TruckIdentifier to Truck objects representing realised trucks.
    :param candidate_paths: Dictionary mapping pairs of Location and DEALER to the list of candidate paths between them.
    :return: A tuple containing the updated vehicle and truck assignments.
    """
    first_day, last_day, days = get_first_last_and_days(vehicles=requested_vehicles, trucks=trucks_planned)
    day_of_planning = first_day  # today (is relevant for planned delay calculation)
    expected_travel_time: dict[tuple[Location, Location], timedelta] = {(loc, vehicle.destination): timedelta(5) for
                                                                        vehicle in requested_vehicles for loc in
                                                                        location_list}
    # TODO: expected_travel_time aus candidate_paths ziehen
    vehicles_at_loc_at_time: dict[tuple[Location, date], list[int]] = {(loc, day): [] for loc in location_list for day
                                                                       in (days + [(last_day + timedelta(1))])}
    # Run first with only expected trucks to preview delays
    planned_vehicle_assignments: list[VehicleAssignment] = [VehicleAssignment(vehicle.id, [],
                                                                              False, timedelta(0)) for vehicle in
                                                            requested_vehicles]
    planned_truck_assignments: dict[TruckIdentifier, TruckAssignment] = {truck_id: TruckAssignment() for truck_id in
                                                                         (
                                                                                 trucks_planned.keys() | trucks_realised.keys())}
    deterministic_expected_delayed_vehicles: list[bool] = [False for _ in requested_vehicles]
    for day in days:  # days from start_date to end_date
        for loc in location_list:
            # for every day and every location, if that location is a PLANT, add vehicles that become available there
            if loc.type == location_type_from_string("PLANT"):
                vehicles_at_loc_at_time[(loc, day)] += [vehicle.id for vehicle in requested_vehicles if
                                                        vehicle.origin == loc and vehicle.available_date == day]
            sorted_vehicles_at_loc_at_time = sorted(vehicles_at_loc_at_time[(loc, day)],
                                                    key=lambda vehicle_id: (requested_vehicles[vehicle_id].due_date -
                                                                            expected_travel_time[
                                                                                loc, requested_vehicles[
                                                                                    vehicle_id].destination] + timedelta(
                                                                4 * deterministic_expected_delayed_vehicles[
                                                                    vehicle_id])))  # TODO: updaten wenn unten geupdatet wird
            for vehicle_id in sorted_vehicles_at_loc_at_time:
                vehicle = requested_vehicles[vehicle_id]
                if vehicle.destination == loc:
                    # If the vehicle's destination is the current location, we can measure its delay
                    planned_vehicle_assignments[vehicle_id].delayed_by = max(timedelta(0),
                                                                             day - timedelta(1) - vehicle.due_date)
                else:
                    possible_paths = candidate_paths[loc, vehicle.destination]
                    # determine how patient we are
                    amount_of_paths = len(possible_paths)
                    urgency = amount_of_paths  # TODO: updaten wenn unten geupdatet wird
                    """if vehicle.due_date - day - expected_travel_time[loc, vehicle.destination] >= 0.2 * \
                            expected_travel_time[loc, vehicle.destination] + timedelta(2):
                        urgency = 0
                    elif deterministic_expected_delayed_vehicles[vehicle_id]:
                        urgency = 0
                        for truck_option in possible_paths: 
                            # truck_option_cost_per_vehicle ist neue Variable die aus candidate_paths kommt
                            if (truck_option_cost_per_vehicle < 50 and vehicle.planned_delayed) or (truck_option_cost_per_vehicle < 100 and not vehicle.planned_delayed):
                                urgency += 1 """
                    assigned = False
                    truck_option_index = 0
                    for truck_option in possible_paths:
                        # If the truck is free or the urgency is high enough, we take the truck
                        if truck_option[2] or urgency > truck_option_index:
                            truck_id = TruckIdentifier(loc, truck_option[0], truck_option[1], day)
                            if truck_id in trucks_planned.keys():
                                truck = trucks_planned[truck_id]
                                if len(planned_truck_assignments[truck_id].load) < truck.capacity:
                                    # If the truck is not full, assign the vehicle to it
                                    planned_truck_assignments[truck_id].load.append(vehicle_id)
                                    planned_vehicle_assignments[vehicle_id].paths_taken.append(truck_id)
                                    vehicles_at_loc_at_time[
                                        (truck_option[0], truck.arrival_date + timedelta(1))].append(vehicle_id)
                                    # TODO: Updaten wenn unten geupdatet wird
                                    # truck_option_travel_time ist neue Variable die aus candidate_paths kommt
                                    """if day + truck_option_travel_time > vehicle.due_date:
                                        planned_vehicle_assignments[vehicle.id].planned_delayed = True
                                        deterministic_expected_delayed_vehicles[vehicle.id] = True"""
                                    assigned = True
                                    break
                        truck_option_index += 1
                    if not assigned:
                        # If no truck was assigned, the vehicle remains at the current location for another day
                        vehicles_at_loc_at_time[(loc, day + timedelta(1))].append(vehicle_id)
    planned_delayed_vehicles: list[bool] = [False for _ in requested_vehicles]
    # Check which vehicles are delayed based on the planned vehicle assignments
    for vehicle_assignment in planned_vehicle_assignments:
        vehicle = requested_vehicles[vehicle_assignment.id]
        vehicle_path = vehicle_assignment.paths_taken
        if vehicle_path:
            final_truck = trucks_planned[vehicle_path[-1]]
            if vehicle.due_date - day_of_planning >= timedelta(7):
                if vehicle_path != [] and final_truck.end_location == vehicle.destination:
                    delay = final_truck.arrival_date - vehicle.due_date
                    if delay > timedelta(0):
                        planned_delayed_vehicles[vehicle_assignment.id] = True

    # Now determine actual assignments
    expected_delayed_vehicles: list[bool] = [False for _ in requested_vehicles]
    vehicle_assignments: list[VehicleAssignment] = [
        VehicleAssignment(vehicle.id, [], planned_delayed_vehicles[vehicle.id], timedelta(0)) for vehicle
        in requested_vehicles]
    truck_assignments: dict[TruckIdentifier, TruckAssignment] = {truck_id: TruckAssignment() for truck_id in
                                                                 (trucks_planned.keys() | trucks_realised.keys())}
    vehicles_at_loc_at_time: dict[tuple[Location, date], list[int]] = {(loc, day): [] for loc in location_list for day
                                                                       in (days + [(last_day + timedelta(1))])}
    for day in days:  # days from start_date to end_date
        for loc in location_list:
            # for every day and every location, if that location is a PLANT, add vehicles that become available there
            if loc.type == location_type_from_string("PLANT"):
                vehicles_at_loc_at_time[(loc, day)] += [vehicle.id for vehicle in requested_vehicles if
                                                        vehicle.origin == loc and vehicle.available_date == day]
            sorted_vehicles_at_loc_at_time = sorted(vehicles_at_loc_at_time[(loc, day)],
                                                    key=lambda vehicle_id: (requested_vehicles[vehicle_id].due_date -
                                                                            expected_travel_time[
                                                                                loc, requested_vehicles[
                                                                                    vehicle_id].destination] + timedelta(
                                                                4 * expected_delayed_vehicles[vehicle_id])))
            # TODO: delay time einbeziehen in urgency
            for vehicle_id in sorted_vehicles_at_loc_at_time:
                vehicle = requested_vehicles[vehicle_id]
                if vehicle.destination == loc:
                    # If the vehicle's destination is the current location, we can measure its delay
                    vehicle_assignments[vehicle_id].delayed_by = max(timedelta(0),
                                                                     day - timedelta(1) - vehicle.due_date)
                else:
                    possible_paths = candidate_paths[loc, vehicle.destination]
                    # determine how patient we are
                    amount_of_paths = len(possible_paths)
                    urgency = amount_of_paths  # TODO: Urgency Funktion schreiben
                    """if vehicle.due_date - day - expected_travel_time[loc, vehicle.destination] >= 0.2 * \
                            expected_travel_time[loc, vehicle.destination] + timedelta(2):
                        urgency = 0
                    elif expected_delayed_vehicles[vehicle_id]:
                        urgency = 0
                        for truck_option in possible_paths:
                            # truck_option_cost_per_vehicle ist neue Variable die aus candidate_paths kommt
                            if (truck_option_cost_per_vehicle < 50 and vehicle.planned_delayed) or (truck_option_cost_per_vehicle < 100 and not vehicle.planned_delayed):
                                urgency += 1 """
                    assigned = False
                    truck_option_index = 0
                    for truck_option in possible_paths:
                        # If the truck is free or the urgency is high enough, we take the truck
                        if truck_option[2] or urgency > truck_option_index:
                            truck_id = TruckIdentifier(loc, truck_option[0], truck_option[1], day)
                            if truck_id in (trucks_planned.keys() & trucks_realised.keys()):
                                truck = trucks_realised[truck_id]
                                if len(truck_assignments[truck_id].load) < truck.capacity:
                                    # If the truck is not full, assign the vehicle to it
                                    truck_assignments[truck_id].load.append(vehicle_id)
                                    vehicle_assignments[vehicle_id].paths_taken.append(truck_id)
                                    vehicles_at_loc_at_time[
                                        (truck_option[0], truck.arrival_date + timedelta(1))].append(vehicle_id)
                                    # TODO: Add delay if expected travel time is too long
                                    # truck_option_travel_time ist neue Variable die aus candidate_paths kommt
                                    """if day + truck_option_travel_time > vehicle.due_date:
                                        vehicle_assignments[vehicle.id].planned_delayed = True
                                        expected_delayed_vehicles[vehicle.id] = True"""
                                    assigned = True
                                    break
                        truck_option_index += 1
                    if not assigned:
                        # If no truck was assigned, the vehicle remains at the current location for another day
                        vehicles_at_loc_at_time[(loc, day + timedelta(1))].append(vehicle_id)
    return vehicle_assignments, truck_assignments
