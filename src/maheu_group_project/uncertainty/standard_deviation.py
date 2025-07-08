from statistics import stdev

from maheu_group_project.solution.encoding import Location
from maheu_group_project.uncertainty.history_data_handling import Weekday


def standard_deviation_capacity(truck_history: dict[tuple[Weekday, Location, Location, int], list[Truck]]) -> dict[tuple[Weekday, Location, Location, int], float]:
    """
    Calculates the standard deviation of truck capacities for each weekday, segment, and truck number.

    Args:
        truck_history (dict[tuple[Weekday, Location, Location, int], list[Truck]]): A dictionary where the key is a tuple
            of weekday, start and end locations, and truck identifier. The value is a list of trucks for that combination.

    Returns:
        dict[tuple[Weekday, Location, Location, int], float]: A dictionary where the key is a tuple of weekday,
            start and end locations, and truck identifier. The value is the standard deviation of truck capacities for that combination.
    """
    std_dev_capacity_res: dict[tuple[Weekday, Location, Location, int], float] = {}
    for dict_key, trucks in truck_history.items():
        if len(trucks) > 1:
            std_dev = stdev(truck.capacity for truck in trucks)
        else:
            std_dev = 0.0  # Standard deviation is zero if there's only one truck
        std_dev_capacity_res[dict_key] = std_dev
    return std_dev_capacity_res
