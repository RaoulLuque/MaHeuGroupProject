import csv
import datetime
import re
import os

from encoding import Location, TruckIdentifier, Vehicle, Truck, location_type_from_string


def read_data() -> tuple[list[Location], list[Vehicle], dict[TruckIdentifier, Truck]]:
    locations: list[Location] = []
    vehicles: list[Vehicle] = []
    trucks: dict[TruckIdentifier, Truck] = {}

    # import the vehicles from the vehicle_data.csv file
    with open(os.path.join("data", "vehicle_data.csv"), newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        for row in reader:
            if row and row[0] == "TRO":
                vehicle_id = int(row[1])
                origin = Location(name=row[4][:5], type=location_type_from_string(row[4][5:]))
                destination = Location(name=row[5][:5], type=location_type_from_string(row[5][5:]))
                available_date = datetime.datetime.strptime(row[6], "%d/%m/%Y-%H:%M:%S").date()
                due_date = datetime.datetime.strptime(row[8], "%d/%m/%Y-%H:%M:%S").date()
                vehicle = Vehicle(
                    id=vehicle_id,
                    origin=origin,
                    destination=destination,
                    available_date=available_date,
                    due_date=due_date
                )
                vehicles.append(vehicle)

    # import the trucks from the planned_capacity_data.csv file
    with open(os.path.join("data", "planned_capacity_data.csv"), newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        for row in reader:
            if row and row[0] == "PLT":
                path_segment = row[3]

                match = re.match(
                    r"([A-Z]{3}\d{2}(?:PLANT|TERM|DEALER))([A-Z]{3}\d{2}(?:PLANT|TERM|DEAL))-TRUCK-(\d+)",
                    path_segment)

                if match:
                    start_code = match.group(1)
                    end_code = match.group(2)
                    truck_number = int(match.group(3))

                else:
                    print("No match found for path segment:", path_segment)

                start_location = Location(name=start_code[:5], type=location_type_from_string(start_code[5:]))
                end_location = Location(name=end_code[:5], type=location_type_from_string(end_code[5:]))

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
                    load=[],
                )

                trucks[truck_id] = truck

    return locations, vehicles, trucks
