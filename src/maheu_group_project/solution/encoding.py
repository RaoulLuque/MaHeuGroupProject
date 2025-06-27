from datetime import date, timedelta
from enum import Enum
from dataclasses import dataclass

# Constants for costs of delays
FIXED_PLANNED_DELAY_COST = 200
FIXED_UNPLANNED_DELAY_COST = 500
COST_PER_PLANNED_DELAY_DAY = 50
COST_PER_UNPLANNED_DELAY_DAY = 100


class LocationType(Enum):
    """
    Enum to represent the type of location.

    PLANT: A production site where vehicles are manufactured. \n
    TERMINAL: A terminal where vehicles are stored or transferred. \n
    DEALER: A dealer location where vehicles are sold or distributed. \n
    """
    PLANT = 1
    TERMINAL = 2
    DEALER = 3

    def __str__(self) -> str:
        """
        Returns a string representation of the location type.
        """
        match self:
            case LocationType.PLANT:
                return "PLANT"
            case LocationType.TERMINAL:
                return "TERM"
            case LocationType.DEALER:
                return "DEAL"
        # Should be unreachable, just here to make the linter happy
        raise ValueError(f"Invalid LocationType: {self}")


def location_type_from_string(location_type_str: str) -> LocationType:
    """
    Tries to convert a string to a LocationType enum. Valid strings are 'PLANT', 'TERM', and 'DEAL'.
    Raises ValueError if the string does not match any valid location type.

    Args:
        location_type_str (str): The string representation of the location type.

    Returns:
        LocationType: The corresponding LocationType enum.
    """
    match location_type_str.upper():
        case "PLANT":
            return LocationType.PLANT
        case "TERM":
            return LocationType.TERMINAL
        case "DEAL":
            return LocationType.DEALER
        case _:
            raise ValueError(f"Invalid location type: {location_type_str}")


@dataclass(frozen=True)
class Location:
    """
    Represents a physical location.

    Attributes:
        name (str): The name of the location (e.g., 'GER01', 'FRA01').
        type (LocationType): The type of the location (e.g., PLANT, TERMINAL, DEALER).
    """
    name: str
    type: LocationType


def location_from_string(location_str: str) -> Location:
    """
    Converts a string representation of a location into a Location object.
    The string should be in the format 'NameNumberType', where 'Name' is the three-letter name of the location
    e.g. GER or FRA, 'Number' is a two-digit number, and 'Type' is one of 'PLANT', 'TERM', or 'DEAL'.

    Args:
        location_str (str): The string representation of the location.

    Returns:
        Location: The corresponding Location object.
    """
    name, type_str = location_str[:5], location_str[5:]
    return Location(name=name, type=location_type_from_string(type_str))


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
    departure_date: date


@dataclass
class Truck:
    """
    Represents a truck (or a general transport vehicle) transporting vehicles between locations.

    Attributes:
        start_location (Location): The starting location of the truck.
        end_location (Location): The ending location of the truck.
        departure_date (datetime.datetime): The departure date.
        arrival_date (datetime.datetime): The arrival date.
        truck_number (int): Number distinguishing different trucks on the same segment.
        capacity (int): Maximum number of vehicles the truck can carry.
        price (int): Cost associated with the truck's trip. This cost is only incurred once
                     if the truck is actually booked for a trip.
    """
    start_location: Location
    end_location: Location
    departure_date: date
    arrival_date: date
    # This number distinguishes between different trucks on the same segment
    truck_number: int
    capacity: int
    price: int

    def __init__(self, start_location: Location, end_location: Location, departure_date: date,
                 arrival_date: date, truck_number: int, capacity: int, price: int):
        self.start_location = start_location
        self.end_location = end_location
        self.departure_date = departure_date
        self.arrival_date = arrival_date
        self.truck_number = truck_number
        self.capacity = capacity
        self.price = price

    def get_identifier(self):
        """
        Converts the Truck instance to a TruckIdentifier.

        Returns:
            TruckIdentifier: The identifier for the truck.
        """
        return TruckIdentifier(
            start_location=self.start_location,
            end_location=self.end_location,
            truck_number=self.truck_number,
            departure_date=self.departure_date
        )

    def new_from_self(self, start_location: Location = None, end_location: Location = None,
                      departure_date: date = None, arrival_date: date = None, truck_number: int = None,
                      capacity: int = None, price: int = None) -> 'Truck':
        """
        Returns a new Truck instance from the current instance overwriting exactly those attributes that are provided.

        Args:
            start_location (Location, optional): The new starting location of the truck. Defaults to the current start location.
            end_location (Location, optional): The new ending location of the truck. Defaults to the current end location.
            departure_date (date, optional): The new departure date of the truck. Defaults to the current departure date.
            arrival_date (date, optional): The new arrival date of the truck. Defaults to the current arrival date.
            truck_number (int, optional): The new truck number. Defaults to the current truck number.
            capacity (int, optional): The new capacity of the truck. Defaults to the current capacity.
            price (int, optional): The new price for the truck's trip. Defaults to the current price.

        Returns:
            Truck: A new Truck instance with the updated attributes.
        """
        return Truck(
            start_location=self.start_location if start_location is None else start_location,
            end_location=self.end_location if end_location is None else end_location,
            departure_date=self.departure_date if departure_date is None else departure_date,
            arrival_date=self.arrival_date if arrival_date is None else arrival_date,
            truck_number=self.truck_number if truck_number is None else truck_number,
            capacity=self.capacity if capacity is None else capacity,
            price=self.price if price is None else price,
        )


@dataclass
class TruckAssignment:
    """
    Represents the assignment a solution has made for a truck.

    Attributes:
        load (list[int]): List of vehicle IDs assigned to be loaded on the truck.
    """
    load: list[int]

    def __init__(self, load: list[int] = None):
        """
        Initializes a TruckAssignment instance.
        Args:
            load (list[int], optional): List of vehicle IDs assigned to be loaded on the truck.
                If omitted, it defaults to an empty list.
        """
        self.load = load if load is not None else []

    def get_capacity_left(self, truck: Truck) -> int:
        """
        Returns the remaining capacity of the truck after accounting for the vehicles already assigned to it.

        Args:
            truck (Truck): The truck for which to calculate the remaining capacity.

        Returns:
            int: The remaining capacity of the truck.
        """
        capacity_left = truck.capacity - len(self.load)
        assert capacity_left >= 0, f"Truck {truck.get_identifier()} has negative capacity left: {capacity_left}"
        return capacity_left

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
    """
    id: int
    origin: Location
    destination: Location
    available_date: date
    due_date: date

    def __init__(self, id: int, origin: Location, destination: Location, available_date: date,
                 due_date: date):
        self.id = id
        self.origin = origin
        self.destination = destination
        self.available_date = available_date
        self.due_date = due_date


@dataclass
class VehicleAssignment:
    """
    Represents the assignment a solution has made for a single vehicle.

    Attributes:
        id (int): Unique identifier for the vehicle whose assignment is being represented.
        paths_taken (list[TruckIdentifier]): List of truck segments the vehicle is assigned to.
        planned_delayed (bool): Indicates if the vehicle is planned to be delayed.
        delayed_by (datetime.timedelta): Duration by which the vehicle is planned to be delayed.
    """
    id: int
    paths_taken: list[TruckIdentifier]
    planned_delayed: bool
    delayed_by: timedelta

    def __init__(self, id: int, paths_taken: list[TruckIdentifier] = None, planned_delayed: bool = False,
                 delayed_by: timedelta = timedelta(0)):
        """
        Initializes a VehicleAssignment instance.

        Args:
            paths_taken (list[TruckIdentifier], optional): List of truck segments the vehicle is assigned to.
                If omitted, it defaults to an empty list.
            planned_delayed (bool, optional): Indicates if the vehicle is planned to be delayed.
                If omitted, it defaults to False.
            delayed_by (timedelta, optional): Duration by which the vehicle is planned to be delayed.
                If omitted, it defaults to a zero timedelta (no delay).
        """
        self.id = id
        self.paths_taken = paths_taken if paths_taken is not None else []
        self.planned_delayed = planned_delayed
        self.delayed_by = delayed_by


def convert_vehicle_assignments_to_truck_assignments(vehicle_assignments: list[VehicleAssignment],
                                                     trucks: dict[TruckIdentifier, Truck]) -> dict[
    TruckIdentifier, TruckAssignment]:
    """
    Converts a list of VehicleAssignments into a dictionary of TruckAssignments.

    Args:
        vehicle_assignments (list[VehicleAssignment]): List of vehicle assignments to convert.

    Returns:
        dict[TruckIdentifier, TruckAssignment]: Dictionary mapping truck identifiers to their respective assignments.
    """
    truck_assignments: dict[TruckIdentifier, TruckAssignment] = {}
    for vehicle in vehicle_assignments:
        for truck_identifier in vehicle.paths_taken:
            if truck_identifier not in truck_assignments:
                truck_assignments[truck_identifier] = TruckAssignment()
            truck_assignments[truck_identifier].load.append(vehicle.id)

    # Ensure that all trucks are contained in the truck_assignments dictionary
    for truck_id in trucks.keys():
        if truck_id not in truck_assignments:
            truck_assignments[truck_id] = TruckAssignment()

    return truck_assignments
