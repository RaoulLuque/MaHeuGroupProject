from datetime import date
from enum import Enum

from maheu_group_project.solution.encoding import Truck, TruckIdentifier


class Weekday(Enum):
    """
    Enum representing the days of the week, starting from Monday.
    """
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7


def get_weekday_from_date(date_in_datetime: date) -> Weekday:
    """
    Converts a date object to a Weekday enum.

    Args:
        date_in_datetime (date): The date to convert.

    Returns:
        Weekday: The corresponding weekday enum.
    """
    return Weekday(date_in_datetime.isoweekday())


def history_data_by_weekday(trucks_history: dict[TruckIdentifier, Truck]) -> dict[Weekday, list[Truck]]:
    """
    Groups the truck history data by the weekday of their departures.

    Args:
        trucks_history (dict[TruckIdentifier, Truck]): The truck history data.

    Returns:
        dict[datetime.date, list[Truck]]: A dictionary where keys are weekdays and values are lists of Trucks which depart on that weekday.
    """
    history_by_day: dict[Weekday, list[Truck]] = {day: [] for day in Weekday}
    print(history_by_day)
    for truck in trucks_history.values():
        weekday = get_weekday_from_date(truck.departure_date)
        history_by_day[weekday].append(truck)
    return history_by_day
