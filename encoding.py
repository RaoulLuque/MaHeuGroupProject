import datetime
from enum import Enum
from dataclasses import dataclass


class LocationType(Enum):
    """
    Enum to represent the type of a location.

    PLANT: A production site where vehicles are manufactured. \n
    TERMINAL: A terminal where vehicles are stored or transferred. \n
    DEALER: A dealer location where vehicles are sold or distributed. \n
    """
    PLANT = 1
    TERMINAL = 2
    DEALER = 3


@dataclass(frozen=True)
class Location:
    """
    Represents a physical location.

    Attributes:
        name (str): The name of the location.
        type (LocationType): The type of the location (e.g., PLANT, TERMINAL, DEALER).
    """
    name: str
    type: LocationType


@dataclass(frozen=True)
class TruckIdentifier:
    """
    Uniquely identifies a truck (or a general transport vehicle).

    Attributes:
        start_location (Location): The starting location of the truck.
        end_location (Location): The ending location of the truck.
        truck_number (int): Number distinguishing different trucks on the same segment.
        departure_date (datetime.datetime): The departure date and time of the truck.
    """
    start_location: Location
    end_location: Location
    truck_number: int
    departure_date: datetime.datetime


@dataclass
class Truck:
    """
    Represents a truck (or a general transport vehicle) transporting vehicles between locations.

    Attributes:
        start_location (Location): The starting location of the truck.
        end_location (Location): The ending location of the truck.
        departure_date (datetime.datetime): The departure date and time.
        arrival_date (datetime.datetime): The arrival date and time.
        truck_number (int): Number distinguishing different trucks on the same segment.
        capacity (int): Maximum number of vehicles the truck can carry.
        price (int): Cost associated with the truck's trip. This cost is only incurred once
                     if the truck is actually booked for a trip.
        load (list[int]): List of vehicle IDs currently loaded on the truck.
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
    """
    Represents a vehicle to be transported.

    Attributes:
        id (int): Unique identifier for the vehicle.
        origin (Location): The starting location of the vehicle.
        destination (Location): The destination location of the vehicle.
        available_date (datetime.datetime): The date and time when the vehicle is available for transport.
        due_date (datetime.datetime): The latest date and time by which the vehicle should arrive at its destination.
        paths_taken (list[TruckIdentifier]): List of truck segments the vehicle has taken.
        planned_delayed (bool): Indicates if the vehicle is planned to be delayed.
        delayed_by (datetime.timedelta): Duration by which the vehicle is delayed.
    """
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
