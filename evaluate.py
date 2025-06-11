# Global variables for delaycosts:
fixed_cost_planned_delay = 200  # Fixed cost for planned delay of a vehicle
fixed_cost_unplanned_delay = 500  # Fixed cost for unplanned delay of a vehicle
cost_per_planned_delay_day = 50  # Cost per day of planned delay
cost_per_unplanned_delay_day = 100  # Cost per day of unplanned delay


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
            objective += (fixed_cost_planned_delay + delay_in_days_float * cost_per_planned_delay_day)
        else:
            if delay_in_days_float > 0:
                # If the vehicle is delayed unplanned, add the fixed cost and the cost per day of delay
                objective += (fixed_cost_unplanned_delay + delay_in_days_float * cost_per_unplanned_delay_day)
    return objective
