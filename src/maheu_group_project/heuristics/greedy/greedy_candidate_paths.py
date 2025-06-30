from maheu_group_project.solution.encoding import FIXED_PLANNED_DELAY_COST, FIXED_UNPLANNED_DELAY_COST, \
    COST_PER_PLANNED_DELAY_DAY, \
    COST_PER_UNPLANNED_DELAY_DAY, Location, Vehicle, TruckIdentifier, Truck, TruckAssignment, VehicleAssignment
from datetime import date, timedelta
from maheu_group_project.solution.encoding import location_type_from_string
from maheu_group_project.heuristics.common import get_first_last_and_days


def greedy_candidate_path_solver(requested_vehicles: list[Vehicle], trucks_planned: dict[TruckIdentifier, Truck],
                                 location_list: list[Location], trucks_realised: dict[TruckIdentifier, Truck],
                                 candidate_paths: dict[tuple[Location, Location], list[dict]]) \
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

    deterministic_location_urgency_factor: dict[Location, int] = {loc: 0 for loc in location_list}

    def urgency_function(veh_id: int, dayy: date, assignments: list[VehicleAssignment],
                         exp_delayed_veh: list[bool]) -> float:
        """
        Calculate the urgency based on the vehicle's due date and the current day.
        """
        veh = requested_vehicles[veh_id]
        assignment = assignments[veh_id]
        # return 99999
        if veh.due_date - dayy - 1.8 * timedelta(candidate_paths[loc, veh.destination][0]['days']) >= timedelta(1):
            return 0
        elif assignment.planned_delayed:
            return COST_PER_PLANNED_DELAY_DAY * (0.5 + 0.5 * exp_delayed_veh[veh_id])
        else:
            return COST_PER_UNPLANNED_DELAY_DAY * (0.5 + 0.5 * exp_delayed_veh[veh_id]) + FIXED_UNPLANNED_DELAY_COST * (
                    1 - exp_delayed_veh[veh_id])

    for day in days:  # days from start_date to end_date
        for loc in location_list:
            # for every day and every location, if that location is a PLANT, add vehicles that become available there
            if loc.type == location_type_from_string("PLANT"):
                vehicles_at_loc_at_time[(loc, day)] += [vehicle.id for vehicle in requested_vehicles if
                                                        vehicle.origin == loc and vehicle.available_date == day]
            sorted_vehicles_at_loc_at_time = sorted(vehicles_at_loc_at_time[(loc, day)],
                                                    key=lambda vehicle_id: urgency_function(vehicle_id, day,
                                                                                            planned_vehicle_assignments,
                                                                                            deterministic_expected_delayed_vehicles) if loc !=
                                                                                                                                        requested_vehicles[
                                                                                                                                            vehicle_id].destination else 0,
                                                    reverse=True)

            # (requested_vehicles[vehicle_id].due_date - timedelta(candidate_paths[loc, requested_vehicles[vehicle_id].destination][0]['days']))

            if day > first_day:
                # If we are not on the first day, we can check if the number of vehicles at this location has increased
                # compared to the previous day
                vehicles_today = len(vehicles_at_loc_at_time[(loc, day)])
                vehicles_yesterday = len(vehicles_at_loc_at_time[(loc, day - timedelta(1))])
                if vehicles_today > vehicles_yesterday > 0:
                    # If there are more vehicles today than yesterday, we increase the urgency factor for this location
                    deterministic_location_urgency_factor[loc] += 1
                elif vehicles_today < vehicles_yesterday - 15:
                    # If there are far fewer vehicles today than yesterday, we decrease the urgency factor for this location
                    deterministic_location_urgency_factor[loc] = max(0, deterministic_location_urgency_factor[loc] - 1)
            for vehicle_id in sorted_vehicles_at_loc_at_time:
                vehicle = requested_vehicles[vehicle_id]
                if vehicle.destination == loc:
                    # If the vehicle's destination is the current location, we can measure its delay
                    planned_vehicle_assignments[vehicle_id].delayed_by = max(timedelta(0),
                                                                             day - timedelta(1) - vehicle.due_date)
                else:
                    possible_paths = candidate_paths[loc, vehicle.destination]
                    if vehicle.due_date - day - timedelta(possible_paths[0]['days']) < timedelta(0):
                        deterministic_expected_delayed_vehicles[vehicle_id] = True
                        if vehicle.due_date - day >= timedelta(7):
                            planned_vehicle_assignments[vehicle.id].planned_delayed = True
                    # determine how patient we are
                    urgency = urgency_function(vehicle_id, day, planned_vehicle_assignments,
                                               deterministic_expected_delayed_vehicles)
                    assigned = False
                    for truck_option in possible_paths:
                        # If the truck is free or the urgency is high enough, we take the truck
                        if truck_option['is_free'] or urgency >= truck_option['total_cost'] - \
                                possible_paths[
                                    min(len(possible_paths) - 1, deterministic_location_urgency_factor[loc])][
                                    'total_cost']:
                            truck_id = TruckIdentifier(loc, truck_option['next_location'], truck_option['truck_number'],
                                                       day)
                            if truck_id in trucks_planned.keys():
                                truck = trucks_planned[truck_id]
                                if len(planned_truck_assignments[truck_id].load) < truck.capacity:
                                    # If the truck is not full, assign the vehicle to it
                                    planned_truck_assignments[truck_id].load.append(vehicle_id)
                                    planned_vehicle_assignments[vehicle_id].paths_taken.append(truck_id)
                                    vehicles_at_loc_at_time[
                                        (truck_option['next_location'], truck.arrival_date + timedelta(1))].append(
                                        vehicle_id)
                                    if day + timedelta(truck_option['days']) > vehicle.due_date:
                                        if vehicle.due_date - day >= timedelta(7):
                                            planned_vehicle_assignments[vehicle.id].planned_delayed = True
                                        deterministic_expected_delayed_vehicles[vehicle.id] = True
                                    assigned = True
                                    break
                    if not assigned:
                        # If no truck was assigned, the vehicle remains at the current location for another day
                        vehicles_at_loc_at_time[(loc, day + timedelta(1))].append(vehicle_id)
                        if vehicle.due_date - (day + timedelta(1)) - timedelta(possible_paths[0]['days']) < timedelta(
                                0):
                            deterministic_expected_delayed_vehicles[vehicle_id] = True
                            if vehicle.due_date - day >= timedelta(7):
                                planned_vehicle_assignments[vehicle.id].planned_delayed = True
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
    location_urgency_factor: dict[Location, int] = {loc: 0 for loc in location_list}
    for day in days:  # days from start_date to end_date
        for loc in location_list:
            # for every day and every location, if that location is a PLANT, add vehicles that become available there
            if loc.type == location_type_from_string("PLANT"):
                vehicles_at_loc_at_time[(loc, day)] += [vehicle.id for vehicle in requested_vehicles if
                                                        vehicle.origin == loc and vehicle.available_date == day]
            sorted_vehicles_at_loc_at_time = sorted(vehicles_at_loc_at_time[(loc, day)],
                                                    key=lambda vehicle_id: urgency_function(vehicle_id, day,
                                                                                            planned_vehicle_assignments,
                                                                                            deterministic_expected_delayed_vehicles) if loc !=
                                                                                                                                        requested_vehicles[
                                                                                                                                            vehicle_id].destination else 0,
                                                    reverse=True)
            if day > first_day:
                # If we are not on the first day, we can check if the number of vehicles at this location has increased
                # compared to the previous day
                vehicles_today = len(vehicles_at_loc_at_time[(loc, day)])
                vehicles_yesterday = len(vehicles_at_loc_at_time[(loc, day - timedelta(1))])
                if vehicles_today > vehicles_yesterday:
                    # If there are far more vehicles today than yesterday, we increase the urgency factor for this location
                    location_urgency_factor[loc] += 1
                elif vehicles_today < vehicles_yesterday - 15:
                    # If there are far fewer vehicles today than yesterday, we decrease the urgency factor for this location
                    location_urgency_factor[loc] = max(0, location_urgency_factor[loc] - 1)
            for vehicle_id in sorted_vehicles_at_loc_at_time:
                vehicle = requested_vehicles[vehicle_id]
                if vehicle.destination == loc:
                    # If the vehicle's destination is the current location, we can measure its delay
                    vehicle_assignments[vehicle_id].delayed_by = max(timedelta(0),
                                                                     day - timedelta(1) - vehicle.due_date)
                else:
                    possible_paths = candidate_paths[loc, vehicle.destination]
                    if vehicle.due_date - day - timedelta(possible_paths[0]['days']) < timedelta(0):
                        expected_delayed_vehicles[vehicle_id] = True
                        if vehicle.due_date - day >= timedelta(7):
                            vehicle_assignments[vehicle.id].planned_delayed = True
                    # determine how patient we are
                    urgency = urgency_function(vehicle_id, day, vehicle_assignments, expected_delayed_vehicles)
                    assigned = False
                    for truck_option in possible_paths:
                        # If the truck is free or the urgency is high enough, we take the truck
                        if truck_option['is_free'] or urgency >= truck_option['total_cost'] - \
                                possible_paths[min(len(possible_paths) - 1, location_urgency_factor[loc])][
                                    'total_cost']:
                            truck_id = TruckIdentifier(loc, truck_option['next_location'], truck_option['truck_number'],
                                                       day)
                            if truck_id in (trucks_planned.keys() & trucks_realised.keys()):
                                truck = trucks_realised[truck_id]
                                if len(truck_assignments[truck_id].load) < truck.capacity:
                                    # If the truck is not full, assign the vehicle to it
                                    truck_assignments[truck_id].load.append(vehicle_id)
                                    vehicle_assignments[vehicle_id].paths_taken.append(truck_id)
                                    vehicles_at_loc_at_time[
                                        (truck_option['next_location'], truck.arrival_date + timedelta(1))].append(
                                        vehicle_id)
                                    # Add delay if expected travel time is too long
                                    if day + timedelta(truck_option['days']) > vehicle.due_date:
                                        if vehicle.due_date - day >= timedelta(7):
                                            vehicle_assignments[vehicle.id].planned_delayed = True
                                        expected_delayed_vehicles[vehicle.id] = True
                                    assigned = True
                                    break
                    if not assigned:
                        # If no truck was assigned, the vehicle remains at the current location for another day
                        vehicles_at_loc_at_time[(loc, day + timedelta(1))].append(vehicle_id)
                        if vehicle.due_date - (day + timedelta(1)) - timedelta(possible_paths[0]['days']) < timedelta(
                                0):
                            expected_delayed_vehicles[vehicle_id] = True
                            if vehicle.due_date - day >= timedelta(7):
                                vehicle_assignments[vehicle.id].planned_delayed = True
    return vehicle_assignments, truck_assignments
