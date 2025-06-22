from maheu_group_project.solution.encoding import FIXED_PLANNED_DELAY_COST, FIXED_UNPLANNED_DELAY_COST, \
    COST_PER_PLANNED_DELAY_DAY, \
    COST_PER_UNPLANNED_DELAY_DAY, TruckIdentifier, Truck, TruckAssignment, VehicleAssignment


def objective_function(vehicle_assignments: list[VehicleAssignment],
                       truck_assignments: dict[TruckIdentifier, TruckAssignment],
                       trucks: dict[TruckIdentifier, Truck]) -> float:
    """
    Calculates the objective value based on the assigned vehicles and trucks.

    Args:
        vehicle_assignments (list[Vehicle]): List of vehicles with their assigned delays and planned statuses.
        truck_assignments (dict[TruckIdentifier, Truck]): Dictionary mapping truck identifiers to Truck objects,
            which contain their loads and prices.
        trucks (dict[TruckIdentifier, Truck]): Dictionary of trucks available for transportation.

    Returns:
        float: The objective value of the solution, calculated based on the prices of trucks and costs of delays.
    """
    objective_value = 0  # Initialize the objective value to 0
    for truck_identifier, truck_assignment in truck_assignments.items():
        if not len(truck_assignment.load) == 0:
            # For each truck with a non-empty load, add the corresponding price to the objective value
            objective_value += trucks[truck_identifier].price * len(truck_assignment.load) / trucks[
                truck_identifier].capacity
    for vehicle in vehicle_assignments:
        # Convert the delay to a float value in number of days
        delay_in_days = vehicle.delayed_by.days
        if vehicle.planned_delayed:
            # If the vehicle is planned to be delayed, add the fixed cost and the cost per day of delay
            objective_value += (FIXED_PLANNED_DELAY_COST + delay_in_days * COST_PER_PLANNED_DELAY_DAY)
        else:
            if delay_in_days > 0:
                # If the vehicle is delayed unplanned, add the fixed cost and the cost per day of delay
                objective_value += (FIXED_UNPLANNED_DELAY_COST + delay_in_days * COST_PER_UNPLANNED_DELAY_DAY)
    return objective_value
