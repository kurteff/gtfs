# Script for handing BART realtime GTFS data
import requests
import time
from google.transit import gtfs_realtime_pb2
import warnings

# ---------------------------------------------------------------------
# Terminal-based commuter direction (authoritative)
# ---------------------------------------------------------------------

WESTBOUND_TERMINALS = {
    "DALY",   # Daly City
    "MLBR",   # Millbrae
    "SFIA",   # SFO
}

EASTBOUND_TERMINALS = {
    "ANTC",   # Antioch
    "PITT",   # Pittsburg / Bay Point
    "DUBL",   # Dublin / Pleasanton
    "BERY",   # Berryessa / North San Jose
}

class feed:
    '''
    Class for loading/storing/manipulating realtime GTFS data
    '''
    def __init__(self, feed_url="http://api.bart.gov/gtfsrt/tripupdate.aspx"):
        self.feed_url = feed_url
        self.msg = None
        self.msg_prev = None
        self.reload()
        # Normalize direction inputs
        self.direction_aliases = {
            "west": "west", "westbound": "west", "w": "west",
            "south": "west", "southbound": "west", "s": "west",
            "east": "east", "eastbound": "east", "e": "east",
            "north": "east", "northbound": "east", "n": "east",
        }
    def reload(self, timeout=10):
        '''
        Refreshes the realtime data from feed_url
        '''
        # Save last reload in case it's useful
        self.msg_prev = self.msg
        # Grab RT info from BART server
        response = requests.get(self.feed_url, timeout=timeout)
        response.raise_for_status()
        # Parse it
        self.msg = gtfs_realtime_pb2.FeedMessage()
        self.msg.ParseFromString(response.content)

    def get_arrivals(self, stop_id, static, direction='west', autoreload=False, timeout=10, verbose=False):
        '''
        Returns real-time arrivals info for a given BART stop
        '''     
        if autoreload:
            self.reload(timeout=timeout)

        direction = str(direction).lower()
        if direction not in self.direction_aliases:
            raise ValueError(f"Invalid direction '{direction}'")
        direction = self.direction_aliases[direction]
            
        arrivals = []
        now = int(time.time())

        # Parse static gtfs data
        # See static.py for documentation on this class
        platform_stop_ids = static.platforms[stop_id]
        trip_to_route = static.trip_routes
        trip_to_direction_id = static.trip_directions
        trip_to_terminal = static.trip_terminals

        # Select valid terminal set
        valid_terminals = WESTBOUND_TERMINALS if direction == 'west' else EASTBOUND_TERMINALS

        # Parse realtime info
        for entity in self.msg.entity:
            if not entity.HasField("trip_update"):
                continue
    
            trip_id = entity.trip_update.trip.trip_id
            route_id = trip_to_route.get(trip_id, "UNKNOWN")
            terminal_station = trip_to_terminal.get(trip_id)

            if terminal_station not in valid_terminals:
                continue

            for stu in entity.trip_update.stop_time_update:
                if stu.stop_id not in platform_stop_ids:
                    continue

                if stu.arrival.HasField("time"):
                    minutes = max(0, (stu.arrival.time - now) // 60)
    
                    arrivals.append({
                        "route": route_id,
                        "trip_id": trip_id,
                        "station_id": stop_id,
                        "platform_id": stu.stop_id,
                        "minutes": minutes,
                        "direction": direction,  # authoritative commuter direction
                        "direction_id": trip_to_direction_id.get(trip_id),
                        "terminal_station": terminal_station,
                    })
    
                    if verbose:
                        print(stu.stop_id, minutes)

        return sorted(arrivals, key=lambda x: x["minutes"])

    def format_arrival(self, static, arrival, verbose=False):
        '''
        Formats a single arrival dict into a human-readable string
        '''
        route_id = arrival["route"]
        trip_id = arrival["trip_id"]
        minutes = arrival["minutes"]
        terminal_station_id = arrival["terminal_station"]
        direction = arrival["direction"]
    
        line_name = static.routes.get(route_id, {}).get("short", "Unknown")
        terminal_name = static.stations.get(terminal_station_id, terminal_station_id)
    
        time_str = (
            "now" if minutes == 0 else
            "in 1 minute" if minutes == 1 else
            f"in {minutes} minutes"
        )
    
        msg = f"{line_name} line {direction}bound train toward {terminal_name} {time_str}"
    
        if verbose:
            print(msg)
    
        return msg

    def platform_announcements(self, static, arrivals=None, stop_id=None, direction='west', autoreload=False, timeout=10, limit=3, verbose=False):
        '''
        Human-readable arrivals information for multiple trains (up to limit)
        '''

        # Check inputs
        if arrivals is None:
            if not autoreload:
                raise ValueError("Must pass arrivals or enable autoreload.")
            if stop_id is None:
                raise ValueError("stop_id must be specified when autoreload=True.")
            arrivals = self.get_arrivals(stop_id, static, direction=direction, autoreload=True, timeout=timeout, verbose=verbose)

        if not arrivals:
            return ["No upcoming trains"]

        announcements = [self.format_arrival(static, a, verbose=verbose) for a in arrivals[:limit]]
        return announcements