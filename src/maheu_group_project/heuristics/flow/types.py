from dataclasses import dataclass
from datetime import date
from enum import Enum

from maheu_group_project.solution.encoding import Location, Vehicle, LocationType, TruckIdentifier


class NodeType(Enum):
    """
    Enum to represent the type of node in the flow network.
    Nodes may be of type NORMAL, which represent a regular node with a day and location,
    or HELPER_NODE which only appear next to DEALER locations to allow for delays.
    """
    NORMAL = 0
    HELPER_NODE_ONE = 1
    HELPER_NODE_TWO = 2

    def to_string(self) -> str:
        """
        Returns a string representation of the node type.
        """
        match self:
            case NodeType.NORMAL:
                return "NORMAL"
            case NodeType.HELPER_NODE_ONE:
                return "HELPER_ONE"
            case NodeType.HELPER_NODE_TWO:
                return "HELPER_TWO"
        # Should be unreachable, just here to make the linter happy
        raise ValueError(f"Invalid NodeType: {self}")


@dataclass(frozen=True)
class NodeIdentifier:
    """
    Unique identifier for a node in the flow network.

    Attributes:
        day (date): The day associated with the node.
        location (Location): The location associated with the node.
        type (NodeType): The type of the node, which can be NORMAL, HELPER_NODE_ONE or HELPER_NODE_TWO.
    """
    day: date
    location: Location
    type: NodeType


@dataclass
class AssignmentToday:
    """
    Represents the assignment of a truck to a vehicle for the current day.

    Attributes:
        assignment (TruckIdentifier): The identifier of the truck assigned to the vehicle.
    """
    assignment: TruckIdentifier


@dataclass
class NoAssignmentToday:
    """
    Represents the case where no truck is assigned to a vehicle for the current day. However, the vehicle is still planned
    to be assigned to a truck in the future.
    """
    next_planned_assignment: TruckIdentifier


@dataclass
class InfeasibleAssignment:
    """
    Represents the case where a vehicle cannot be assigned to any truck for the current day because the flow corresponding
    to the vehicle's commodity group is not feasible.
    """


PlannedVehicleAssignment = AssignmentToday | NoAssignmentToday | InfeasibleAssignment


def vehicle_to_commodity_group(vehicle: Vehicle) -> str:
    """
    Returns the string representation of the commodity group corresponding to a given vehicle.

    The string representation is constructed by concatenating the vehicle's due date and destination name.

    Args:
        vehicle (Vehicle): The vehicle for which to get the corresponding commodity group.

    Returns:
        str: The corresponding commodity group.
    """
    return vehicle.due_date.__str__() + "_" + vehicle.destination.name


def dealership_to_commodity_group(node_identifier: NodeIdentifier) -> str:
    """
    Returns the string representation of the commodity group corresponding to a given dealership node.

    The string representation is constructed by concatenating the node's day and location name.

    Args:
        node_identifier (NodeIdentifier): The node for which to get the corresponding commodity group.

    Returns:
        str: The corresponding commodity group.
    """
    if node_identifier.type != NodeType.NORMAL or node_identifier.location.type != LocationType.DEALER:
        raise ValueError("NodeIdentifier must be of type NORMAL and LocationType DEALER to get a commodity group.")
    return node_identifier.day.__str__() + "_" + node_identifier.location.name


def get_day_and_location_for_commodity_group(commodity_group: str) -> tuple[date, Location]:
    """
    Extracts the day and location from a commodity group string.

    The commodity group string is expected to be in the format "YYYY-MM-DD_location_name".

    Args:
        commodity_group (str): The commodity group string.

    Returns:
        tuple[date, Location]: A tuple containing the day and the corresponding Location object.
    """
    day_str, location_name = commodity_group.split("_", 1)
    return date.fromisoformat(day_str), Location(name=location_name, type=LocationType.DEALER)
