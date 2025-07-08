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


def truck_to_history_dict_key(truck: Truck) -> tuple[Weekday, Location, Location, int]:
    """
    Creates a key for the truck based on its weekday, start and end locations, and identifier.

    Args:
        truck (Truck): The truck object.

    Returns:
        tuple[Weekday, Location, Location, int]: A tuple containing the weekday, start location,
            end location, and truck identifier.
    """
    return get_weekday_from_date(truck.departure_date), truck.start_location, truck.end_location, truck.truck_number


def history_data_by_id_segment_and_weekday(trucks_history: dict[TruckIdentifier, Truck]) -> dict[tuple[Weekday, Location, Location, int], list[Truck]]:
    """
    Groups the truck history data by weekday, segment (start and end locations), and truck identifier.

    Args:
        trucks_history (dict[TruckIdentifier, Truck]): The truck history data.

    Returns:
        dict[Weekday, dict[tuple[Location, Location], dict[int, list[Truck]]]]:
            A dictionary where key is a tuple of weekday, start and end locations,
            and the truck number. The value is a list of trucks for that combination of
            weekday, segment and truck number.
    """
    history_by_day: dict[tuple[Weekday, Location, Location, int], list[Truck]] = {}
    for truck in trucks_history.values():
        dict_key = truck_to_history_dict_key(truck)
        if dict_key not in history_by_day:
            history_by_day[dict_key] = []
        history_by_day[dict_key].append(truck)
    return history_by_day
