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


def number_of_planned_delayed_cars_which_are_delayed(vehicle_assignments: list[VehicleAssignment]) -> int:
    """
    Counts the number of vehicles that are planned to be delayed and are actually delayed.

    Args:
        vehicle_assignments (list[VehicleAssignment]): A list of vehicle assignments.

    Returns:
        int: The number of vehicles that are planned to be delayed and are actually delayed.
    """
    return sum(1 for va in vehicle_assignments if va.planned_delayed and va.delayed_by > timedelta(days=0))


def number_of_vehicles_transported_in_trucks_which_are_not_free(trucks: dict[TruckIdentifier, Truck],
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
    """
    Calculates the price paid for delays based on the vehicle assignment.

    Args:
        vehicle_assignment (VehicleAssignment): The vehicle assignment object containing delay information.

    Returns:
        int: The price paid for delays.
    """
    if vehicle_assignment.planned_delayed:
        return FIXED_PLANNED_DELAY_COST + vehicle_assignment.delayed_by.days * COST_PER_PLANNED_DELAY_DAY
    else:
        return FIXED_UNPLANNED_DELAY_COST + vehicle_assignment.delayed_by.days * COST_PER_UNPLANNED_DELAY_DAY


def price_paid_for_delays(vehicle_assignments: list[VehicleAssignment]) -> tuple[int, int, int, int, int]:
    """
    Calculates the total prices paid for delays based on the vehicle assignments.

    Args:
        vehicle_assignments (list[VehicleAssignment]): A list of vehicle assignments.

    Returns:
        tuple[int, int, int, int, int]: A tuple containing:
            - Fixed cost for planned delays
            - Summed day cost for planned delays
            - Fixed cost for unplanned delays
            - Summed day cost for unplanned delays
            - Total delay cost
    """
    fixed_planned_delay_cost = sum(FIXED_PLANNED_DELAY_COST for va in vehicle_assignments if va.planned_delayed)
    fixed_unplanned_delay_cost = sum(FIXED_UNPLANNED_DELAY_COST for va in vehicle_assignments if not va.planned_delayed and va.delayed_by > timedelta(days=0))
    summed_day_planned_delay_cost = sum(va.delayed_by.days * COST_PER_PLANNED_DELAY_DAY for va in vehicle_assignments if va.planned_delayed and va.delayed_by > timedelta(days=0))
    summed_day_unplanned_delay_cost = sum(va.delayed_by.days * COST_PER_UNPLANNED_DELAY_DAY for va in vehicle_assignments if not va.planned_delayed and va.delayed_by > timedelta(days=0))

    total_delay_cost = fixed_planned_delay_cost + fixed_unplanned_delay_cost + summed_day_planned_delay_cost + summed_day_unplanned_delay_cost

    return fixed_planned_delay_cost, summed_day_planned_delay_cost, fixed_unplanned_delay_cost, summed_day_unplanned_delay_cost, total_delay_cost

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
    message_length = 65
    num_delayed_cars = number_of_delayed_cars(vehicle_assignments)
    num_planned_delay_cars = number_of_planned_delayed_cars(vehicle_assignments)
    num_actual_planned_delay_cars = number_of_planned_delayed_cars_which_are_delayed(vehicle_assignments)
    num_not_free_trucks = number_of_vehicles_transported_in_trucks_which_are_not_free(trucks, truck_assignments)
    fixed_planned_delay_cost, summed_day_planned_delay_cost, fixed_unplanned_delay_cost, summed_day_unplanned_delay_cost, total_delay_cost = price_paid_for_delays(vehicle_assignments)
    price_paid_trucks = price_paid_for_trucks(trucks, truck_assignments)
    res = ("Metrics:\n" +
           "Number of delayed cars:".ljust(message_length) + f"{num_delayed_cars}\n" +
           "Number (actual/) planned delayed cars:".ljust(message_length) + f"{num_actual_planned_delay_cars}/{num_planned_delay_cars}\n" +
           "Number of cars transported in trucks which are not free:".ljust(message_length) + f"{num_not_free_trucks}\n" +
           "Cost of delays Total, (Pl Fix, Pl Days), (Unpl Fix, Unpl Days):".ljust(message_length) + f"{total_delay_cost:.2f}, ({fixed_planned_delay_cost}, {summed_day_planned_delay_cost}), ({fixed_unplanned_delay_cost}, {summed_day_unplanned_delay_cost})\n" +
           "Price paid for trucks:".ljust(message_length) + f"{price_paid_trucks:.2f}")

    return res
