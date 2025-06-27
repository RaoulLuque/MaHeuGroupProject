from datetime import timedelta

from maheu_group_project.solution.encoding import VehicleAssignment, TruckAssignment, TruckIdentifier, Truck, \
    COST_PER_PLANNED_DELAY_DAY, FIXED_UNPLANNED_DELAY_COST, FIXED_PLANNED_DELAY_COST, COST_PER_UNPLANNED_DELAY_DAY


def number_of_delayed_cars(vehicle_assignments: list[VehicleAssignment]) -> int:
    """
    Counts the number of vehicles that are delayed based on their due dates.

    Args:
        vehicle_assignments (list[VehicleAssignment]): A list of vehicle assignments.

    Returns:
        int: The number of vehicles that are delayed.
    """
    return sum(1 for va in vehicle_assignments if va.delayed_by > timedelta(days=0))


def number_of_planned_delayed_cars(vehicle_assignments: list[VehicleAssignment]) -> int:
    """
    Counts the number of vehicles that are planned to be delayed based on their assignments.

    Args:
        vehicle_assignments (list[VehicleAssignment]): A list of vehicle assignments.

    Returns:
        int: The number of vehicles that are planned to be delayed.
    """
    return sum(1 for va in vehicle_assignments if va.planned_delayed)


def number_of_cars_transported_in_trucks_which_are_not_free(trucks: dict[TruckIdentifier, Truck],
                                                            truck_assignments: dict[
                                                                TruckIdentifier, TruckAssignment]) -> int:
    """
    Counts the number of vehicles that are transported in trucks which are not free.

    Args:
        trucks (dict[TruckIdentifier, Truck]): A dictionary mapping truck identifiers to their Truck objects.
        truck_assignments (dict[TruckIdentifier, TruckAssignment]): A dictionary mapping truck identifiers to their assignments.

    Returns:
        int: The number of vehicles that are transported in trucks which are not free.
    """
    return sum(len(ta.load) for ti, ta in truck_assignments.items() if len(ta.load) > 0 and trucks[ti].price > 0)


def delay_price(vehicle_assignment: VehicleAssignment) -> int:
    if vehicle_assignment.planned_delayed:
        return FIXED_PLANNED_DELAY_COST + vehicle_assignment.delayed_by.days * COST_PER_PLANNED_DELAY_DAY
    else:
        return FIXED_UNPLANNED_DELAY_COST + vehicle_assignment.delayed_by.days * COST_PER_UNPLANNED_DELAY_DAY


def price_paid_for_delays(vehicle_assignments: list[VehicleAssignment]) -> float:
    """
    Calculates the total price paid for delays based on the vehicle assignments.

    Args:
        vehicle_assignments (list[VehicleAssignment]): A list of vehicle assignments.

    Returns:
        float: The total price paid for delays.
    """
    return sum(delay_price(va) for va in vehicle_assignments if va.delayed_by > timedelta(days=0))


def price_paid_for_trucks(trucks: dict[TruckIdentifier, Truck],
                          truck_assignments: dict[TruckIdentifier, TruckAssignment]) -> float:
    """
    Calculates the total price paid for trucks based on their assignments.

    Args:
        trucks (dict[TruckIdentifier, Truck]): A dictionary mapping truck identifiers to their Truck objects.
        truck_assignments (dict[TruckIdentifier, TruckAssignment]): A dictionary mapping truck identifiers to their assignments.

    Returns:
        float: The total price paid for trucks.
    """
    return sum(trucks[ti].price / trucks[ti].capacity * len(ta.load) for ti, ta in truck_assignments.items() if
               len(ta.load) > 0 and trucks[ti].price > 0)


def get_pretty_metrics(trucks: dict[TruckIdentifier, Truck], truck_assignments: dict[TruckIdentifier, TruckAssignment],
                       vehicle_assignments: list[VehicleAssignment]) -> str:
    """
    Returns a string with the pretty metrics for the solution.

    Returns:
        str: A formatted string containing the metrics.
    """
    num_delayed_cars = number_of_delayed_cars(vehicle_assignments)
    num_planned_delay_cars = number_of_planned_delayed_cars(vehicle_assignments)
    num_cars_not_free_trucks = number_of_cars_transported_in_trucks_which_are_not_free(trucks, truck_assignments)
    price_paid_delays = price_paid_for_delays(vehicle_assignments)
    price_paid_trucks = price_paid_for_trucks(trucks, truck_assignments)
    res = ("Metrics:\n" +
           f"Number of delayed cars: {num_delayed_cars}\n" +
           f"Number of planned delayed cars: {num_planned_delay_cars}\n" +
           f"Number of cars transported in trucks which are not free: {num_cars_not_free_trucks}\n" +
           f"Price paid for delays: {price_paid_delays:.2f}\n" +
           f"Price paid for trucks: {price_paid_trucks:.2f}")

    return res
