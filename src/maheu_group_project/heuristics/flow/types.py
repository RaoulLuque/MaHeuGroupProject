from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum

from maheu_group_project.solution.encoding import Location, Vehicle, LocationType, TruckIdentifier, VehicleAssignment, \
    Truck


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


class Order(Enum):
    """
    Enum to represent the order in which the commodity groups are stored in the commodity groups dictionary.
    """
    UNORDERED = 0
    ASCENDING = 1
    DESCENDING = 2


def get_current_location_of_vehicle_as_node(vehicle: Vehicle, vehicle_assignments: dict[int, VehicleAssignment],
                                            trucks_realised_by_day_known: dict[
                                                date, dict[TruckIdentifier, Truck]]) -> NodeIdentifier:
    """
    Returns the current location of a vehicle as a NodeIdentifier. It is determined based on the vehicle's assignment.
    If an assignment exists, the last location in the paths taken is used to determine the current location. Otherwise,
    the origin of the vehicle is used.

    The current location is determined based on the vehicle's

    Args:
        vehicle (Vehicle): The vehicle for which to get the current location.
        vehicle_assignments (dict[int, VehicleAssignment]): A dictionary mapping vehicle ids to their final assignments.
        trucks_realised_by_day_known (dict[date, dict[TruckIdentifier, Truck]]): A dictionary mapping each day to the realized trucks for that day.
            Note that this dict only contains entries for days earlier than current_day.

    Returns:
        NodeIdentifier: The current location of the vehicle.
    """
    if len(vehicle_assignments.get(vehicle.id, VehicleAssignment(id=vehicle.id)).paths_taken) > 0:
        # If the vehicle has an assignment, we use the last location in the paths taken
        current_assignment = vehicle_assignments[vehicle.id]
        last_truck_identifier = current_assignment.paths_taken[-1]

        # This is where we access trucks_realised_by_day. We use last_truck_identifier, which has to be in the past,
        # since it was assigned in a previous loop of the solve_flow_in_real_time function.
        # We use get_start_and_end_nodes_for_truck, since this accounts for the one rest-day of the truck if it does
        # not arrive at a DEALER location.
        _, end_node = get_start_and_end_nodes_for_truck(
            trucks_realised_by_day_known[last_truck_identifier.departure_date][last_truck_identifier])
        arrival_date = end_node.day

        return NodeIdentifier(day=arrival_date,
                              location=last_truck_identifier.end_location,
                              type=NodeType.NORMAL)
    else:
        return NodeIdentifier(day=vehicle.available_date,
                              location=vehicle.origin,
                              type=NodeType.NORMAL)


def get_start_and_end_nodes_for_truck(truck: Truck) -> tuple[NodeIdentifier, NodeIdentifier]:
    """
    Returns the start and end nodes for a truck in the flow network.

    Args:
        truck (Truck): The truck for which to get the start and end nodes.

    Returns:
        tuple[NodeIdentifier, NodeIdentifier]: A tuple containing the start and end nodes for the truck.
    """
    start_node = NodeIdentifier(truck.departure_date, truck.start_location, NodeType.NORMAL)

    # If the truck's end location is not a DEALER, we delay the arrival date by one day to account for the
    # one day rest.
    truck_arrival_date = truck.arrival_date
    if truck.end_location.type != LocationType.DEALER:
        truck_arrival_date += timedelta(days=1)

    end_node = NodeIdentifier(truck_arrival_date, truck.end_location, NodeType.NORMAL)

    return start_node, end_node
