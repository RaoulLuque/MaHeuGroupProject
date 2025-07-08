import math

from maheu_group_project.solution.encoding import TruckIdentifier, Truck
from maheu_group_project.parsing import read_history_data
from maheu_group_project.uncertainty.history_data_handling import truck_to_history_dict_key, \
    history_data_by_id_segment_and_weekday
from maheu_group_project.uncertainty.mean import calculate_mean_capacity
from maheu_group_project.uncertainty.quantile import calculate_quantile_capacity
from maheu_group_project.uncertainty.standard_deviation import mean_minus_standard_deviation_capacity, \
    standard_deviation_capacity


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
    new_trucks: dict[TruckIdentifier, Truck] = {}

    truck_history = read_history_data(dataset_dir_name)
    truck_history = history_data_by_id_segment_and_weekday(truck_history)
    std_dev_capacity = standard_deviation_capacity(truck_history)

    for truck_identifier, truck in trucks_planned.items():
        key = truck_to_history_dict_key(truck)
        new_trucks[truck_identifier] = truck
        new_trucks[truck_identifier].capacity -= math.ceil(times_standard_deviation * std_dev_capacity[key])
        if new_trucks[truck_identifier].capacity < 0:
            # Ensure capacity does not go below zero
            new_trucks[truck_identifier].capacity = 0

    return trucks_planned


def assign_mean_minus_standard_deviation_to_planned_capacities(trucks_planned: dict[TruckIdentifier, Truck], dataset_dir_name: str, times_standard_deviation: float) -> dict[TruckIdentifier, Truck]:
    """
    Assigns the mean minus the standard deviation of truck capacities to the planned truck capacities.

    Args:
        trucks_planned (dict[TruckIdentifier, Truck]): Dictionary of planned trucks.
        dataset_dir_name (str): Directory name of the dataset to read history data from.
        times_standard_deviation (float): Factor by which to multiply the standard deviation before subtracting.

    Returns:
        dict[TruckIdentifier, Truck]: Updated dictionary of planned trucks with adjusted capacities.
    """
    new_trucks: dict[TruckIdentifier, Truck] = {}

    truck_history = read_history_data(dataset_dir_name)
    truck_history = history_data_by_id_segment_and_weekday(truck_history)
    mean_std_dev_capacity = mean_minus_standard_deviation_capacity(truck_history, times_standard_deviation)

    for truck_identifier, truck in trucks_planned.items():
        key = truck_to_history_dict_key(truck)
        new_trucks[truck_identifier] = truck
        new_trucks[truck_identifier].capacity = min(int(mean_std_dev_capacity[key]), new_trucks[truck_identifier].capacity)

    return new_trucks


def assign_quantile_based_planned_capacities(trucks_planned: dict[TruckIdentifier, Truck], dataset_dir_name: str, quantile: float) -> dict[TruckIdentifier, Truck]:
    """
    Assigns the quantile-based truck capacities to the planned truck capacities.

    Args:
        trucks_planned (dict[TruckIdentifier, Truck]): Dictionary of planned trucks.
        dataset_dir_name (str): Directory name of the dataset to read history data from.
        quantile (float): Quantile to use for capacity assignment (e.g., 0.95 for the 95th percentile).

    Returns:
        dict[TruckIdentifier, Truck]: Updated dictionary of planned trucks with adjusted capacities.
    """
    new_trucks: dict[TruckIdentifier, Truck] = {}

    truck_history = read_history_data(dataset_dir_name)
    truck_history = history_data_by_id_segment_and_weekday(truck_history)
    quantile_capacity = calculate_quantile_capacity(truck_history, quantile)

    for truck_identifier, truck in trucks_planned.items():
        key = truck_to_history_dict_key(truck)
        new_trucks[truck_identifier] = truck
        new_trucks[truck_identifier].capacity = min(int(quantile_capacity[key]), new_trucks[truck_identifier].capacity)

    return new_trucks
