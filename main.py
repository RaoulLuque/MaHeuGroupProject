# This is a sample Python script.
from encoding import Location, TruckIdentifier, Vehicle, Truck


# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.


def read_data() -> tuple[list[Location], list[Vehicle], dict[TruckIdentifier, Truck]]:
    """
    Reads the data from the files and returns the lists of locations, vehicles, and trucks.
    :return: A tuple containing the lists of locations, vehicles, and trucks.
    """
    return [], [], {}


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi('PyCharm')
# See PyCharm help at https://www.jetbrains.com/help/pycharm/
