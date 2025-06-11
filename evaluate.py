# Global variables for delaycosts:
fixed_cost_planned_delay = 200  # Fixed cost for planned delay of a vehicle
fixed_cost_unplanned_delay = 500  # Fixed cost for unplanned delay of a vehicle
cost_per_planned_delay_day = 50  # Cost per day of planned delay
cost_per_unplanned_delay_day = 100  # Cost per day of unplanned delay


def evaluateSolution(vehicle_assignment, truck_assignment):
    objective = 0
    for truck_id in truck_assignment:
        truck = truck_assignment[truck_id]
        if not len(truck.load) == 0:
            objective += truck.price
    for vehicle in vehicle_assignment:
        delay_in_days_float = vehicle.delayed_by.days + vehicle.delayed_by.seconds / (60 * 60 * 24)
        if vehicle.planned_delayed:
            objective += (fixed_cost_planned_delay + delay_in_days_float * cost_per_planned_delay_day)
        else:
            if delay_in_days_float > 0:
                objective += (fixed_cost_unplanned_delay + delay_in_days_float * cost_per_unplanned_delay_day)
    return objective
