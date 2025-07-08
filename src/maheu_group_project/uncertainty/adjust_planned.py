import math

from maheu_group_project.solution.encoding import TruckIdentifier, Truck
from maheu_group_project.parsing import read_history_data
from maheu_group_project.uncertainty.history_data_handling import truck_to_history_dict_key, \
    history_data_by_id_segment_and_weekday
from maheu_group_project.uncertainty.standard_deviation import standard_deviation_capacity


def subtract_standard_deviation_from_planned_capacities(trucks_planned: dict[TruckIdentifier, Truck], dataset_dir_name: str, times_standard_deviation: float) -> dict[TruckIdentifier, Truck]:
    """
    Subtracts the standard deviation of truck capacities from the planned truck capacities.

    Args:
        trucks_planned (dict[TruckIdentifier, Truck]): Dictionary of planned trucks.
        dataset_dir_name (str): Directory name of the dataset to read history data from.
        times_standard_deviation (float): Factor by which to multiply the standard deviation before subtracting.

    Returns:
        dict[TruckIdentifier, Truck]: Updated dictionary of planned trucks with adjusted capacities.
    """

    truck_history = read_history_data(dataset_dir_name)
    truck_history = history_data_by_id_segment_and_weekday(truck_history)
    std_dev_capacity = standard_deviation_capacity(truck_history)

    for truck in trucks_planned.values():
        key = truck_to_history_dict_key(truck)
        truck.capacity -= math.ceil(times_standard_deviation * std_dev_capacity[key])
        if truck.capacity < 0:
            truck.capacity = 0  # Ensure capacity does not go below zero

    return trucks_planned
