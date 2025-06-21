from dataclasses import dataclass
from datetime import date
from enum import Enum

from maheu_group_project.solution.encoding import Location


class OldNodeType(Enum):
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
            case OldNodeType.NORMAL:
                return "NORMAL"
            case OldNodeType.HELPER_NODE_ONE:
                return "HELPER_ONE"
            case OldNodeType.HELPER_NODE_TWO:
                return "HELPER_TWO"
        # Should be unreachable, just here to make the linter happy
        raise ValueError(f"Invalid NodeType: {self}")


@dataclass(frozen=True)
class OldNodeIdentifier:
    """
    Unique identifier for a node in the flow network.

    Attributes:
        day (date): The day associated with the node.
        location (Location): The location associated with the node.
        type (OldNodeType): The type of the node, which can be NORMAL, HELPER_NODE_ONE or HELPER_NODE_TWO.
    """
    day: date
    location: Location
    type: OldNodeType
