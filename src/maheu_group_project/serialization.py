import json
from datetime import date, timedelta

from maheu_group_project.solution.encoding import TruckAssignment, TruckIdentifier, Location, LocationType, VehicleAssignment


def _truck_identifier_to_dict(truck_id: TruckIdentifier) -> dict:
    """Convert TruckIdentifier to dictionary for JSON serialization."""
    return {
        "start_location": {
            "name": truck_id.start_location.name,
            "type": str(truck_id.start_location.type)
        },
        "end_location": {
            "name": truck_id.end_location.name,
            "type": str(truck_id.end_location.type)
        },
        "truck_number": truck_id.truck_number,
        "departure_date": truck_id.departure_date.isoformat()
    }


def _truck_identifier_from_dict(data: dict) -> TruckIdentifier:
    """Convert dictionary back to TruckIdentifier."""
    start_location = Location(
        name=data["start_location"]["name"],
        type=LocationType[data["start_location"]["type"]]
    )
    end_location = Location(
        name=data["end_location"]["name"],
        type=LocationType[data["end_location"]["type"]]
    )
    return TruckIdentifier(
        start_location=start_location,
        end_location=end_location,
        truck_number=data["truck_number"],
        departure_date=date.fromisoformat(data["departure_date"])
    )


def _truck_assignment_to_dict(assignment: TruckAssignment) -> dict:
    """Convert TruckAssignment to dictionary for JSON serialization."""
    return {
        "load": assignment.load
    }


def _truck_assignment_from_dict(data: dict) -> TruckAssignment:
    """Convert dictionary back to TruckAssignment."""
    return TruckAssignment(load=data["load"])


def _vehicle_assignment_to_dict(assignment: VehicleAssignment) -> dict:
    """Convert VehicleAssignment to dictionary for JSON serialization."""
    return {
        "id": assignment.id,
        "paths_taken": [_truck_identifier_to_dict(truck_id) for truck_id in assignment.paths_taken],
        "planned_delayed": assignment.planned_delayed,
        "delayed_by": assignment.delayed_by.total_seconds()  # Store as seconds for JSON compatibility
    }


def _vehicle_assignment_from_dict(data: dict) -> VehicleAssignment:
    """Convert dictionary back to VehicleAssignment."""
    paths_taken = [_truck_identifier_from_dict(truck_data) for truck_data in data["paths_taken"]]
    delayed_by = timedelta(seconds=data["delayed_by"])
    
    return VehicleAssignment(
        id=data["id"],
        paths_taken=paths_taken,
        planned_delayed=data["planned_delayed"],
        delayed_by=delayed_by
    )


def serialize_truck_assignments(truck_assignments: dict[TruckIdentifier, TruckAssignment], file_path: str):
    """
    Serializes a dictionary of truck assignments to a JSON file.

    Args:
        truck_assignments: Dictionary mapping TruckIdentifier to TruckAssignment
        file_path: Path where to save the serialized data
    """
    serializable_data = {}

    for truck_id, assignment in truck_assignments.items():
        # Convert TruckIdentifier to a string key for JSON
        truck_key = json.dumps(_truck_identifier_to_dict(truck_id), sort_keys=True)
        serializable_data[truck_key] = _truck_assignment_to_dict(assignment)

    with open(file_path, "w") as f:
        json.dump(serializable_data, f, indent=2)


def deserialize_truck_assignments(file_path: str) -> dict[TruckIdentifier, TruckAssignment]:
    """
    Deserializes truck assignments from a JSON file.

    Args:
        file_path: Path to the JSON file containing serialized truck assignments

    Returns:
        Dictionary mapping TruckIdentifier to TruckAssignment
    """
    with open(file_path, "r") as f:
        serialized_data = json.load(f)

    truck_assignments = {}

    for truck_key_str, assignment_data in serialized_data.items():
        # Convert the string key back to TruckIdentifier
        truck_id_dict = json.loads(truck_key_str)
        truck_id = _truck_identifier_from_dict(truck_id_dict)
        assignment = _truck_assignment_from_dict(assignment_data)
        truck_assignments[truck_id] = assignment

    return truck_assignments


def serialize_vehicle_assignments(vehicle_assignments: list[VehicleAssignment], file_path: str):
    """
    Serializes a list of vehicle assignments to a JSON file.
    
    Args:
        vehicle_assignments: list of VehicleAssignment objects
        file_path: Path where to save the serialized data
    """
    serializable_data = [_vehicle_assignment_to_dict(assignment) for assignment in vehicle_assignments]
    
    with open(file_path, "w") as f:
        json.dump(serializable_data, f, indent=2)


def deserialize_vehicle_assignments(file_path: str) -> list[VehicleAssignment]:
    """
    Deserializes vehicle assignments from a JSON file.
    
    Args:
        file_path: Path to the JSON file containing serialized vehicle assignments
        
    Returns:
        list of VehicleAssignment objects
    """
    with open(file_path, "r") as f:
        serialized_data = json.load(f)
    
    return [_vehicle_assignment_from_dict(assignment_data) for assignment_data in serialized_data]
