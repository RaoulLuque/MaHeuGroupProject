from datetime import date
from enum import Enum

from maheu_group_project.solution.encoding import Truck, TruckIdentifier, Location


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


def history_data_by_id_segment_and_weekday(trucks_history: dict[TruckIdentifier, Truck]) -> dict[Weekday, dict[tuple[Location, Location], dict[int, list[Truck]]]]:
    """
    Groups the truck history data by weekday, segment (start and end locations), and truck identifier.

    Args:
        trucks_history (dict[TruckIdentifier, Truck]): The truck history data.

    Returns:
        dict[Weekday, dict[tuple[Location, Location], dict[int, list[Truck]]]]:
            A nested dictionary where the first key is the weekday, the second key is a tuple of start and end locations,
            and the third key is the truck number. The value is a list of trucks for that combination of
            weekday, segment and truck number.
    """
    history_by_day: dict[Weekday, dict[tuple[Location, Location], dict[int, list[Truck]]]] = {}
    print(history_by_day)
    for truck in trucks_history.values():
        weekday = get_weekday_from_date(truck.departure_date)
        segment = (truck.start_location, truck.end_location)
        id = truck.truck_number
        if weekday not in history_by_day:
            history_by_day[weekday] = {}
        if segment not in history_by_day[weekday]:
            history_by_day[weekday][segment] = {}
        if id not in history_by_day[weekday][segment]:
            history_by_day[weekday][segment][id] = []
        history_by_day[weekday][segment][id].append(truck)
    return history_by_day
