from datetime import date, timedelta

from maheu_group_project.solution.encoding import TruckIdentifier, Truck, Vehicle


def get_first_last_and_days(vehicles: list[Vehicle], trucks: dict[TruckIdentifier, Truck]) -> tuple[date, date, list[date]]:
    """
    Returns the first and last day of the planning period and a list of all days in between.

    Args:
        vehicles (list[Vehicle]): List of vehicles involved in the planning.
        trucks (dict[TruckIdentifier, Truck]): Dictionary of trucks involved in the planning.

    Returns:
        tuple[date, date, list[date]]: A tuple containing the first day, last day, and a list of all days in between
        (in ascending order).

    """
    # Create a list of all days we are considering. The first day is day 0 and the day when the first vehicle is available
    first_day: date = min(min(vehicles, key=lambda vehicle: vehicle.available_date).available_date,
                          min(trucks.values(), key=lambda truck: truck.departure_date).departure_date)
    # The last day is the day when the last vehicle is due or the last truck arrives. We add a buffer of 7 days to make
    # sure we catch trucks that arrive after the last vehicle is due and were not planned for that day.
    last_day: date = max(max(vehicles, key=lambda vehicle: vehicle.due_date).due_date,
                         max(trucks.values(), key=lambda truck: truck.arrival_date).arrival_date) + timedelta(days=7)

    number_of_days = (last_day - first_day).days + 1
    days = [first_day + timedelta(days=i) for i in range(number_of_days)]

    return first_day, last_day, days


def convert_trucks_to_dict_by_day(trucks: dict[TruckIdentifier, Truck]) -> dict[date, dict[TruckIdentifier, Truck]]:
    """
    Returns a dictionary mapping each day to a dict of trucks available on that day.

    Args:
        trucks (dict[TruckIdentifier, Truck]): Dictionary of trucks involved in the planning.

    Returns:
        dict[date, list[Truck]]: A dictionary mapping each day to a dict of trucks available on that day.
    """
    truck_dict_by_day: dict[date, dict[TruckIdentifier, Truck]] = {}
    for truck in trucks.values():
        if truck.departure_date not in truck_dict_by_day:
            truck_dict_by_day[truck.departure_date] = {}
        truck_dict_by_day[truck.departure_date][truck.get_identifier()] = truck
    return truck_dict_by_day
