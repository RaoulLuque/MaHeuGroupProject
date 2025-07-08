import csv
import datetime
import re
import os
from pathlib import Path

from maheu_group_project.solution.encoding import Location, TruckIdentifier, Vehicle, Truck, location_from_string, \
    LocationType, location_type_from_string

# Get the project root (2 levels up from this file)
PROJECT_ROOT_PATH = Path(__file__).resolve().parents[2]
PATH_TO_DATA_FOLDER = os.path.join(PROJECT_ROOT_PATH, "data")


def read_data(dataset_dir_name: str,
              realised_capacity_file_name: str) -> tuple[
    list[Location], list[Vehicle], dict[TruckIdentifier, Truck], dict[TruckIdentifier, Truck]]:
    """
    Reads the vehicle, truck, and locations data from CSV files and returns lists of locations, vehicles, and trucks.

    Args:
        dataset_dir_name (str): The name of the directory containing the dataset files. Defaults to "CaseMaHeu25_01".
        realised_capacity_file_name (str): The name of the CSV file containing truck capacity data. Defaults to "realised_capacity_data_001.csv".

    Returns:
        tuple: A tuple containing:
            - list[Location]: List of unique locations.
            - list[Vehicle]: List of vehicles with their details.
            - dict[TruckIdentifier, Truck]: Dictionary mapping truck identifiers to Truck objects. This contains the realised capacity data
                                            for the provided realised_capacity_file_name.
            - dict[TruckIdentifier, Truck]: Dictionary mapping truck identifiers to Truck objects. This contains the planned capacity data
                                            for the trucks.
    """
    locations: list[Location] = []
    vehicles: list[Vehicle] = []

    # import the vehicles from the vehicle_data.csv file
    with open(os.path.join(PATH_TO_DATA_FOLDER, dataset_dir_name, "vehicle_data.csv")) as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        for row in reader:
            if row and row[0] == "TRO":
                vehicle_id = int(row[1])
                origin = location_from_string(row[4])
                destination = location_from_string(row[5])
                available_date = datetime.datetime.strptime(row[6], "%d/%m/%Y-%H:%M:%S").date()
                due_date = datetime.datetime.strptime(row[8], "%d/%m/%Y-%H:%M:%S").date()
                vehicle = Vehicle(
                    # The vehicle_id is 1-based in the CSV, so we subtract 1 to make it 0-based
                    id=vehicle_id - 1,
                    origin=origin,
                    destination=destination,
                    available_date=available_date,
                    due_date=due_date
                )
                vehicles.append(vehicle)

    trucks_realised, locations = read_trucks_from_file(
        os.path.join(PATH_TO_DATA_FOLDER, dataset_dir_name, realised_capacity_file_name), locations)
    trucks_planned, locations = read_trucks_from_file(
        os.path.join(PATH_TO_DATA_FOLDER, dataset_dir_name, "planned_capacity_data.csv"), locations)

    return locations, vehicles, trucks_realised, trucks_planned


def read_trucks_from_file(file_name: str, locations: list[Location]) -> tuple[
    dict[TruckIdentifier, Truck], list[Location]]:
    """
    Reads the truck data from a CSV file and returns a dictionary of trucks and a list of unique locations.
    Can be used for both realised and planned capacity data.

    Args:
        file_name (str): The name of the CSV file containing truck data.
        locations (list[Location]): A list to store unique locations found in the truck data.

    Returns:
        tuple: A tuple containing:
            - dict[TruckIdentifier, Truck]: A dictionary mapping truck identifiers to Truck objects.
            - list[Location]: A list of unique locations found in the truck data.
    """
    trucks: dict[TruckIdentifier, Truck] = {}
    # import the trucks from the realised_capacity_data file
    with open(file_name) as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        for row in reader:
            if row and row[0] == "PLT":
                path_segment = row[3]

                match = re.match(
                    r"([A-Z]{3}\d{2}(?:PLANT|TERM|DEALER))([A-Z]{3}\d{2}(?:PLANT|TERM|DEAL))-(TRUCK|TRAIN)-(\d+)",
                    path_segment)

                if match:
                    start_code = match.group(1)
                    end_code = match.group(2)
                    truck_number = int(match.group(4))
                    if match.group(3) == "TRAIN":
                        truck_number += 10

                else:
                    print("No match found for path segment:", path_segment)

                start_location = location_from_string(start_code)
                end_location = location_from_string(end_code)

                # from all appeared start / end locations make the list locations (without duplicates)
                if start_location not in locations:
                    locations.append(start_location)
                if end_location not in locations:
                    locations.append(end_location)

                departure_date = datetime.datetime.strptime(row[4], "%d/%m/%Y-%H:%M:%S").date()
                arrival_date = datetime.datetime.strptime(row[5], "%d/%m/%Y-%H:%M:%S").date()

                capacity = int(float(row[6]))
                price = int(float(row[7]))

                truck_id = TruckIdentifier(
                    start_location=start_location,
                    end_location=end_location,
                    truck_number=truck_number,
                    departure_date=departure_date,
                )

                truck = Truck(
                    start_location=start_location,
                    end_location=end_location,
                    departure_date=departure_date,
                    arrival_date=arrival_date,
                    truck_number=truck_number,
                    capacity=capacity,
                    price=price,
                )

                trucks[truck_id] = truck

    return trucks, locations


def get_shortest_paths(dataset_dir_name: str, locations: list[Location]) -> dict[
    tuple[Location, Location], list[Location]]:
    """
    Gets all Plants and Dealers from locations list.
    Reads the paths from the base_data.csv file and finds the shortest path for each pair of Plant and Dealer.

    Args:
        dataset_dir_name (str): The name of the directory containing the dataset files. The function will retrieve
                                the base_data.csv file from this directory.
        locations (list[Location]): A list of Location objects representing all locations.

    Returns:
        dict[tuple[Location, Location], list[Location]]: A dictionary where keys are tuples Plant and Dealer locations,
            and values are lists of locations representing the shortest path.
    """
    shortest_paths: dict[tuple[Location, Location], list[Location]] = {}

    # Read the base_data.csv file to get the paths
    with open(os.path.join(PATH_TO_DATA_FOLDER, dataset_dir_name, "base_data.csv")) as csvfile:
        reader = list(csv.reader(csvfile, delimiter=';'))

    plants = [loc for loc in locations if loc.type == LocationType.PLANT]
    dealers = [loc for loc in locations if loc.type == LocationType.DEALER]

    for plant in plants:
        for dealer in dealers:
            for i, row in enumerate(reader):
                if row and row[0] == "PTH" and row[3] == plant.name + "PLANT" and row[4] == dealer.name + "DEAL":
                    path = [plant]
                    offset = 1
                    while i + offset < len(reader):
                        next_row = reader[i + offset]
                        if len(next_row) <= 6:
                            print("malformed row, breaking")
                            break

                        location_as_string = next_row[6]
                        match = re.match(r"([A-Z]{3}\d{2})(PLANT|TERM|DEAL)", location_as_string)
                        if match:
                            name = match.group(1)
                            loc_type = location_type_from_string(match.group(2))
                            location = Location(name=name, type=loc_type)
                            if location in locations:
                                path.append(location)
                            else:
                                path = []
                                break
                        else:
                            print("no match for ", location_as_string)
                            break

                        offset += 1
                        if i + offset >= len(reader) or reader[i + offset][0] != "PTHSG":
                            break
                    if path != [plant] and path != []:
                        if (plant, dealer) not in shortest_paths or shortest_paths[(plant, dealer)] == [plant] or len(
                                path) < len(shortest_paths[(plant, dealer)]):
                            shortest_paths[(plant, dealer)] = path

    return shortest_paths


def read_history_data(dataset_dir_name: str) -> dict[TruckIdentifier, Truck]:
    """
    Reads the truck history data from capacity_history.csv for the given dataset directory.
    Returns a dictionary mapping TruckIdentifier to Truck.
    """
    trucks: dict[TruckIdentifier, Truck] = {}
    file_path = os.path.join(PATH_TO_DATA_FOLDER, dataset_dir_name, "capacity_history.csv")
    with open(file_path) as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        for row in reader:
            # Skip the row with row information/labels
            if row[0] == "#PathSegment":
                continue
            path_segment = row[0]
            match = re.match(
                r"([A-Z]{3}\d{2}(?:PLANT|TERM|DEALER))([A-Z]{3}\d{2}(?:PLANT|TERM|DEAL))-(TRUCK|TRAIN)-(\d+)",
                path_segment)
            if match:
                start_code = match.group(1)
                end_code = match.group(2)
                truck_number = int(match.group(4))
                if match.group(3) == "TRAIN":
                    truck_number += 10
            else:
                print("No match found for path segment:", path_segment)
                continue
            start_location = location_from_string(start_code)
            end_location = location_from_string(end_code)
            departure_date = datetime.datetime.strptime(row[2], "%d/%m/%Y-%H:%M:%S").date()
            capacity = int(float(row[3]))
            price = int(float(row[4]))
            truck_id = TruckIdentifier(
                start_location=start_location,
                end_location=end_location,
                truck_number=truck_number,
                departure_date=departure_date,
            )
            truck = Truck(
                start_location=start_location,
                end_location=end_location,
                departure_date=departure_date,
                arrival_date=None,
                truck_number=truck_number,
                capacity=capacity,
                price=price,
            )
            trucks[truck_id] = truck
    return trucks
