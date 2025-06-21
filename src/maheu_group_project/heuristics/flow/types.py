from dataclasses import dataclass
from datetime import date
from enum import Enum

from maheu_group_project.solution.encoding import Location, Vehicle, LocationType


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
