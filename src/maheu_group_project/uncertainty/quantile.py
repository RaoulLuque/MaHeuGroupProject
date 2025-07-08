import numpy as np

from maheu_group_project.solution.encoding import Location, Truck
from maheu_group_project.uncertainty.history_data_handling import Weekday


def calculate_quantile_capacity(
    truck_history: dict[tuple[Weekday, Location, Location, int], list[Truck]],
    quantile: float
) -> dict[tuple[Weekday, Location, Location, int], float]:
    """
    Computes the capacity such that the provided quantile of capacities from trucks in truck_history have a higher capacity.

    Args:
        truck_history (dict[tuple[Weekday, Location, Location, int], list[Truck]]):
            A dictionary where the key is a tuple of weekday, start and end locations, and truck identifier. The value is a list of trucks for that combination.
        quantile (float): The quantile to compute (e.g., 0.95 for the 95th percentile).

    Returns:
        dict[tuple[Weekday, Location, Location, int], float]: A dictionary where the key is a tuple of weekday,
            start and end locations, and truck identifier. The value is the quantile of truck capacities for that combination.
    """
    # Convert to the right quantile for higher capacities
    assert 0 <= quantile <= 1, "Quantile must be between 0 and 1."
    quantile = 1 - quantile
    quantile_capacity_res: dict[tuple[Weekday, Location, Location, int], float] = {}
    for dict_key, trucks in truck_history.items():
        capacities = [truck.capacity for truck in trucks]
        quantile_value = float(np.quantile(capacities, quantile))
        quantile_capacity_res[dict_key] = quantile_value
    return quantile_capacity_res
