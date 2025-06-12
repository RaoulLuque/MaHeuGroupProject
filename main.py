from encoding import Location, TruckIdentifier, Vehicle, Truck, LocationType
from parsing import read_data
from translate_to_mip import solve_as_mip

if __name__ == '__main__':
    locations, vehicles, trucks = read_data()
    solve_as_mip(vehicles, trucks, locations)
