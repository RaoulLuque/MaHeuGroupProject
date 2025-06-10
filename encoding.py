import datetime


class Location:
    name: str


class TruckIdentifier:
    start_location: Location
    end_location: Location
    # This number distinguishes between different trucks on the same segment
    truck_number: int
    departure_date: datetime.datetime


class Truck:
    """
    Note that a truck is just a transportation vehicle, which can also be a train or a ship.
    """
    start_location: Location
    end_location: Location
    departure_date: datetime.datetime
    arrival_date: datetime.datetime
    # This number distinguishes between different trucks on the same segment
    truck_number: int
    capacity: int
    price: int
    # List of vehicle IDs
    load: list[int]


class Vehicle:
    id: int
    origin: Location
    destination: Location
    available_date: datetime.datetime
    due_date: datetime.datetime
    # Possibly add another field for the possible routes (if it is not clear)
    paths_taken: list[TruckIdentifier]

    # Delayment information
    planned_delayed: bool
    delayed_by: datetime.timedelta