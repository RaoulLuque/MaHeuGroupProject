import networkx as nx
from networkx import DiGraph

from encoding import Vehicle, TruckIdentifier, Truck, Location, LocationType
from datetime import timedelta, date


class NodeIdentifier:
    day: date
    location: Location

    def __init__(self, day: date, location: Location):
        self.day = day
        self.location = location


def solve_as_mip(vehicles: list[Vehicle], trucks: dict[TruckIdentifier, Truck], locations: list[Location]) -> tuple[list[Location], list[Vehicle], dict[TruckIdentifier, Truck]]
    """
    Translates the given vehicles and trucks into a MIP (Mixed Integer Programming) format string.

    Args:
        vehicles (list[Vehicle]): List of vehicles to be transported.
        trucks (dict[TruckIdentifier, Truck]): Dictionary of trucks available for transportation.
        locations (list[Location]): List of locations involved in the transportation.

    Returns:
        tuple: A tuple containing the list of locations, vehicles, and trucks. The trucks and vehicles are adjusted
        to contain their respective plans.
    """
    # Create a list of all days we are considering. The first day is day 0 and the day where the first vehicle is available
    # to be transported from a production site.
    first_day: date = min(min(vehicles, key=lambda vehicle: vehicle.available_date).available_date, min(trucks.values(), key=lambda truck: truck.departure_date).departure_date)
    last_day: date = max(max(vehicles, key=lambda vehicle: vehicle.available_date).available_date, max(trucks.values(), key=lambda truck: truck.arrival_date).arrival_date)

    number_of_days = (last_day - first_day).days + 1
    days = [first_day + timedelta(days=i) for i in range(number_of_days)]

    # Create a Network to model the flow
    flow_network = DiGraph()

    # Create the vertices of the flow network behind the MIP
    # Create a node for each day and each location
    for day in days:
        for location in locations:
            flow_network.add_node(NodeIdentifier(day, location), day=day, location=location, flow=0)

    # Adjust the flow of each node according to the vehicles produced and expected on that day
    for vehicle in vehicles:
        flow_network.nodes[NodeIdentifier(vehicle.available_date, vehicle.origin)]['flow'] += 1
        flow_network.nodes[NodeIdentifier(vehicle.due_date, vehicle.destination)]['flow'] -= 1

    # Create the edges of the flow network for the trucks
    for truck in trucks.values():
        start_node = NodeIdentifier(truck.departure_date, truck.start_location)
        end_node = NodeIdentifier(truck.arrival_date, truck.end_location)

        # Add an edge from the start node to the end node with the truck's capacity as the flow
        flow_network.add_edge(start_node, end_node, capacity=truck.capacity, price=truck.price)

    # Create the helper edges for the flow network
    for day in days:
        for location in locations:
            current_node = NodeIdentifier(day, location)
            # Add edges to the next day for each location
            if day < last_day:
                # Create an edge to the next day node
                next_day_node = NodeIdentifier(day + timedelta(days=1), location)
                flow_network.add_edge(current_node, next_day_node, capacity=float('inf'), price=0)

            # Add helper edges at dealer locations to allow for delays
            if location.type == LocationType.DEALER:
                # Create an edge to the next day node with a delay of 1 day
                next_day_node = NodeIdentifier(day + timedelta(days=1), location)
                flow_network.add_edge(current_node, next_day_node, capacity=float('inf'), price=0)

    nx.draw(flow_network, with_labels=True, node_size=500, node_color='lightblue', font_size=10, font_color='black')

    return locations, vehicles, trucks
