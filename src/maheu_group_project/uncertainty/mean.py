from maheu_group_project.solution.encoding import Truck, Location
from maheu_group_project.uncertainty.history_data_handling import Weekday


def calculate_mean_capacity(truck_history: dict[tuple[Weekday, Location, Location, int], list[Truck]]) -> dict[tuple[Weekday, Location, Location, int], float]:
    """
    Calculates the mean capacity of trucks for each weekday, segment and truck number.

    Args:
        truck_history (dict[tuple[Weekday, Location, Location, int], list[Truck]]): A dictionary where the key is a tuple
            of weekday, start and end locations, and truck identifier. The value is a list of trucks for that combination.

    Returns:
        dict[tuple[Weekday, Location, Location, int], float]: A dictionary where the key is a tuple of weekday,
            start and end locations, and truck identifier. The value is the mean capacity of trucks for that combination.
    """
    mean_capacity: dict[tuple[Weekday, Location, Location, int], float] = {}
    for dict_key, trucks in truck_history.items():
        mean = sum(truck.capacity for truck in trucks) / len(trucks) if trucks else 0.0
        mean_capacity[dict_key] = mean
    return mean_capacity
