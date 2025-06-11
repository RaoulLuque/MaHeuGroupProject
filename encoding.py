import datetime
from enum import Enum
from dataclasses import dataclass


class LocationType(Enum):
    PLANT = 1
    TERMINAL = 2
    DEALER = 3


@dataclass(frozen=True)
class Location:
    name: str
    type: LocationType


@dataclass(frozen=True)
class TruckIdentifier:
    start_location: Location
    end_location: Location
    # This number distinguishes between different trucks on the same segment
    truck_number: int
    departure_date: datetime.datetime


@dataclass
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

    def __init__(self, start_location: Location, end_location: Location, departure_date: datetime.datetime,
                 arrival_date: datetime.datetime, truck_number: int, capacity: int, price: int, load: list[int] = None):
        self.start_location = start_location
        self.end_location = end_location
        self.departure_date = departure_date
        self.arrival_date = arrival_date
        self.truck_number = truck_number
        self.capacity = capacity
        self.price = price
        self.load = load if load is not None else []


@dataclass
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

    def __init__(self, origin: Location, destination: Location, available_date: datetime.datetime,
                 due_date: datetime.datetime, id: int = None, paths_taken: list[TruckIdentifier] = None,
                 planned_delayed: bool = False, delayed_by: datetime.timedelta = datetime.timedelta(0)):
        self.id = id
        self.origin = origin
        self.destination = destination
        self.available_date = available_date
        self.due_date = due_date
        self.paths_taken = paths_taken if paths_taken is not None else []
        self.planned_delayed = planned_delayed
        self.delayed_by = delayed_by
