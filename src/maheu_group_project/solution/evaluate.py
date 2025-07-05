from maheu_group_project.solution.encoding import FIXED_PLANNED_DELAY_COST, FIXED_UNPLANNED_DELAY_COST, \
    COST_PER_PLANNED_DELAY_DAY, \
    COST_PER_UNPLANNED_DELAY_DAY, TruckIdentifier, Truck, TruckAssignment, VehicleAssignment, Vehicle
from datetime import date, timedelta


def objective_function(vehicle_assignments: list[VehicleAssignment],
                       truck_assignments: dict[TruckIdentifier, TruckAssignment],
                       trucks: dict[TruckIdentifier, Truck]) -> float:
    """
    Calculates the objective value based on the assigned vehicles and trucks.

    Args:
        vehicle_assignments (list[VehicleAssignment]): List of vehicles with their assigned delays and planned statuses.
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


def remove_horizon(vehicle_assignments: list[VehicleAssignment], requested_vehicles: list[Vehicle],
                   truck_assignments: dict[TruckIdentifier, TruckAssignment],
                   trucks: dict[TruckIdentifier, Truck], front_horizon: int = 0, back_horizon: int = 0) \
        -> tuple[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment]]:
    """
    Removes vehicle and truck assignments for which the corresponding truck/vehicle departs/becomes available
    in the front or back horizon of the time period between availability of the first and last requested vehicles.

    Args:
        vehicle_assignments (list[VehicleAssignment]): List of vehicle assignments to filter.
        requested_vehicles (list[Vehicle]): List of vehicles that are requested for transportation.
        truck_assignments (dict[TruckIdentifier, TruckAssignment]): Dictionary mapping truck identifiers to their assignments.
        trucks (dict[TruckIdentifier, Truck]): Dictionary of trucks available for transportation.
        front_horizon (int): The number of days in the front horizon to consider. Defaults to 0.
        back_horizon (int): The number of days in the back horizon to consider. Defaults to 0.

    Returns:
        tuple[list[VehicleAssignment], dict[TruckIdentifier, TruckAssignment]]:
            Filtered vehicle assignments and truck assignments that do not lie in the front or back horizon.
    """

    first_day = min(vehicle.available_date for vehicle in requested_vehicles)
    last_day = max(vehicle.available_date for vehicle in requested_vehicles)

    # Remove vehicles that become available in front or back horizon
    vehicle_assignments = [va for va in vehicle_assignments if
                           last_day - timedelta(back_horizon) >= requested_vehicles[va.id].available_date >= first_day + timedelta(front_horizon)]
    # Remove trucks that start in the front or back horizon
    truck_assignments = {truck_id: t_a for truck_id, t_a in truck_assignments.items() if
                         last_day - timedelta(back_horizon) >= trucks[truck_id].departure_date >= first_day + timedelta(front_horizon)}
    return vehicle_assignments, truck_assignments
