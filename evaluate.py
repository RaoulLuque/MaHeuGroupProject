from encoding import FIXED_PLANNED_DELAY_COST, FIXED_UNPLANNED_DELAY_COST, COST_PER_PLANNED_DELAY_DAY, \
    COST_PER_UNPLANNED_DELAY_DAY, Vehicle, TruckIdentifier, Truck


def evaluate_solution(vehicle_assignment: list[Vehicle], truck_assignment: dict[TruckIdentifier, Truck]) -> float:
    """
    Evaluates a given solution and provides the objective value based on the assigned vehicles and trucks.

    Args:
        vehicle_assignment (list[Vehicle]): List of vehicles with their assigned delays and planned statuses.
        truck_assignment (dict[TruckIdentifier, Truck]): Dictionary mapping truck identifiers to Truck objects,
            which contain their loads and prices.

    Returns:
        float: The objective value of the solution, calculated based on the prices of trucks and costs of delays.
    """
    objective_value = 0  # Initialize the objective value to 0
    for truck in truck_assignment.values():
        if not len(truck.load) == 0:
            # For each truck with non-empty load, add the price to the objective
            objective_value += truck.price
    for vehicle in vehicle_assignment:
        # convert the delay to a float value in days
        delay_in_days = vehicle.delayed_by.days
        if vehicle.planned_delayed:
            # If the vehicle is planned to be delayed, add the fixed cost and the cost per day of delay
            objective_value += (FIXED_PLANNED_DELAY_COST + delay_in_days * COST_PER_PLANNED_DELAY_DAY)
        else:
            if delay_in_days > 0:
                # If the vehicle is delayed unplanned, add the fixed cost and the cost per day of delay
                objective_value += (FIXED_UNPLANNED_DELAY_COST + delay_in_days * COST_PER_UNPLANNED_DELAY_DAY)
    return objective_value
