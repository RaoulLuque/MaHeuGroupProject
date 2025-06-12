from encoding import FIXED_PLANNED_DELAY_COST, FIXED_UNPLANNED_DELAY_COST, COST_PER_PLANNED_DELAY_DAY, \
    COST_PER_UNPLANNED_DELAY_DAY


def evaluateSolution(vehicle_assignment, truck_assignment):
    """ Evaluates a given solution
    :param vehicle_assignment: list[Vehicle]
    :param truck_assignment: dict[TruckIdentifier, Truck]"""
    objective = 0  # Initialize the objective value to 0
    for truck_id in truck_assignment:
        truck = truck_assignment[truck_id]
        if not len(truck.load) == 0:
            # For each truck with non-empty load, add the price to the objective
            objective += truck.price
    for vehicle in vehicle_assignment:
        # convert the delay to a float value in days
        delay_in_days_float = vehicle.delayed_by.days + vehicle.delayed_by.seconds / (60 * 60 * 24)
        if vehicle.planned_delayed:
            # If the vehicle is planned to be delayed, add the fixed cost and the cost per day of delay
            objective += (FIXED_PLANNED_DELAY_COST + delay_in_days_float * COST_PER_PLANNED_DELAY_DAY)
        else:
            if delay_in_days_float > 0:
                # If the vehicle is delayed unplanned, add the fixed cost and the cost per day of delay
                objective += (FIXED_UNPLANNED_DELAY_COST + delay_in_days_float * COST_PER_UNPLANNED_DELAY_DAY)
    return objective
