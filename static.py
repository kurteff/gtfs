# Script for handling BART static GTFS data
import csv
import os
from io import TextIOWrapper

class static_data:
    '''
    Class for loading/storing/manipulating static GTFS data
    '''
    def __init__(self, static_dir='./static'):
        self.static_dir = static_dir
        # Init attributes -- see self.load_all()
        self.stations = None
        self.platforms = None
        self.routes = None
        self.trip_routes = None
        self.trip_directions = None
        self.trip_terminals = None
        self.headsigns = None
        self.station_coords = None
        
    def load_all(self, verbose=False):
        '''
        Populate attributes
        '''
        self.stations = get_stations(static_dir=self.static_dir, verbose=verbose)
        self.platforms = get_platforms(static_dir=self.static_dir)
        self.routes = get_routes(static_dir=self.static_dir)
        self.trip_routes = get_trip_routes(static_dir=self.static_dir)
        self.trip_directions = get_trip_directions(static_dir=self.static_dir)
        self.trip_terminals = get_trip_terminals(static_dir=self.static_dir, verbose=verbose)
        self.headsigns = get_trip_headsigns(static_dir=self.static_dir)
        self.station_coords = get_station_coords(static_dir=self.static_dir)

# # # # # # # # # #
# routes.txt       #
# # # # # # # # # #
def get_routes(static_dir='./static'):
    '''
    Map each route_id to its route names
    
    Returns
    -----------
    routes : nested dict
        key: route ID; value: 2 dicts
        - routes[route_id]['short']
        - routes[route_id]['long']
        ex. route ID: '1'
        ex. short name: 'Yellow-S'
        ex. long name: 'Antioch to SF Int'l Airport SFO/Millbrae'
    '''
    routes = {}
    with open(os.path.join(static_dir, "routes.txt"), "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            routes[row["route_id"]] = {
                "short": row.get("route_short_name"),
                "long": row.get("route_long_name")
            }
    return routes

# # # # # # # # # #
# stops.txt       #
# # # # # # # # # #
def get_stations(static_dir='./static', verbose=False):
    '''
    Map each stop_id to its station name
    
    Returns
    -----------
    stations : dict
        key: stop ID; value: station name
        e.g., {'12TH': '12th Street / Oakland City Center'}
    '''
    with open(os.path.join(static_dir, "stops.txt"), 'rb') as f:
        reader = csv.DictReader(TextIOWrapper(f, "utf-8"))
        stations = dict()
        for row in reader:
            if row.get("parent_station"):
                # Parent stations usually have no parent_station value
                continue
            stop_id = row["stop_id"]
            stop_name = row["stop_name"]
            stations[stop_id] = stop_name
    # Sort alphabetically by station name
    stations = dict(sorted(stations.items()))
    if verbose:
        for k in stations.keys():
            print(k, ':', stations[k])
    return stations

def get_station_coords(static_dir="./static"):
    '''
    Map parent station → (lat, lon)
    '''
    coords = {}
    with open(os.path.join(static_dir, "stops.txt"), "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("parent_station"):
                continue
            coords[row["stop_id"]] = (
                float(row["stop_lat"]),
                float(row["stop_lon"])
            )
    return coords


def parent_station(stop_id, static_dir='./static', verbose=False):
    '''
    Map a stop_id to its parent station
    (may be OK to delete this function btw)
    
    Returns
    -----------
    parent : str
        parent station for input stop_id
        (for many stops these are the same thing)
    '''
    with open(os.path.join(static_dir, "stops.txt"), 'rb') as f:
        reader = csv.DictReader(TextIOWrapper(f, "utf-8"))
        for row in reader:
            if row["stop_id"] == stop_id:
                parent = row.get("parent_station") or stop_id
                if verbose:
                    print(parent)
    return parent

def stop_code(stop_id, static_dir='./static', verbose=False):
    '''
    Map a stop_id to its stop_code
    
    Returns
    -----------
    stop_code : str
        stop code for input stop_id
        usually stop_code can be cast as integer
        e.g., '900109' for stop_id '12TH'
    '''
    with open(os.path.join(static_dir, "stops.txt"), 'rb') as f:
        reader = csv.DictReader(TextIOWrapper(f, "utf-8"))
        for row in reader:
            if row["stop_id"] == stop_id:
                code = row.get("stop_code")
                if verbose:
                    print(code)
    return code

# # # # # # # # # #
# stop_times.txt  #
# # # # # # # # # #
def get_platforms(static_dir='./static'):
    '''
    Map each station to its stop codes.
    Each station usually has multiple of these

    Returns
    -----------
    station_to_platforms : dict
        key: stop ID; value: list of platform codes
        e.g., {'12TH' : ['K10-1', 'K10-2', 'K10-3']}
    '''
    stations = get_stations(static_dir=static_dir)
    station_to_platforms = {k:[] for k in stations.keys()}
    # Read stop_times.txt
    stopping_locations = set()
    with open(os.path.join(static_dir,"stop_times.txt"), "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stopping_locations.add(row["stop_id"])
    stopping_locations = sorted(list(stopping_locations))
    # Read stops.txt
    with open(os.path.join(static_dir,"stops.txt"), "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stop_id = row["stop_id"]
            parent = row.get("parent_station")
            if not parent:
                continue
            # Only keep real train stops
            if stop_id not in stopping_locations:
                continue
            # Only keep stations we care about
            if parent not in stations:
                continue
            station_to_platforms[parent].append(stop_id)
    return station_to_platforms

def get_trip_terminals(static_dir='./static', verbose=False):
    '''
    Maps trip_id to terminal station name
    '''
    stations = get_stations(static_dir=static_dir)
    trip_to_terminal = dict()
    with open(os.path.join(static_dir,"stop_times.txt"), 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trip_id = row['trip_id']
            stop_sequence = int(row['stop_sequence'])
            stop_id = row['stop_id']
            if trip_id not in trip_to_terminal:
                trip_to_terminal[trip_id] = (stop_sequence, stop_id)
            else:
                if stop_sequence > trip_to_terminal[trip_id][0]:
                    trip_to_terminal[trip_id] = (stop_sequence, stop_id)
    # convert stop_id to station name
    return {
        trip_id: parent_station(stop_id, static_dir=static_dir)
        for trip_id, (_, stop_id) in trip_to_terminal.items()
    }

# # # # # # # # # #
# trips.txt  #
# # # # # # # # # #
def get_trip_headsigns(static_dir='./static'):
    '''
    Map each trip_id to its headsign

    Returns
    -----------
    headsigns : dict
        key: trip_id; value: headsign name
        e.g., {'1771625': 'OAK Airport / SF / Daly City'}
        usually, trip_id can be cast as integer
    '''
    headsigns = {}
    with open(os.path.join(static_dir, "trips.txt"), "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            headsigns[row["trip_id"]] = row.get("trip_headsign")
    return headsigns
    
def get_trip_routes(static_dir='./static'):
    '''
    Map each trip_id to its route_id

    Returns
    -----------
    trip_to_route : dict
        key: trip_id; value: route_id
        e.g., {'1771625': '5'}
        usually, trip_id and route_id can be cast as integers
    '''
    trip_to_route = {}
    with open(os.path.join(static_dir,"trips.txt"), "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            trip_to_route[row["trip_id"]] = row["route_id"]
    return trip_to_route

def get_trip_directions(static_dir='./static'):
    '''
    Map each trip_id to its direction, which is a boolean:
    - 0: southbound or westbound, usually
    - 1: northbound or eastbound, usually

    Returns
    -----------
    trip_to_dir : dict
        key: trip_id; value: direction
        e.g., {1771625': '1'}
        usually, direction can be cast as integer/bool
    '''
    trip_to_dir = {}
    with open(os.path.join(static_dir,"trips.txt"), "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            trip_to_dir[row["trip_id"]] = row.get("direction_id")
    return trip_to_dir