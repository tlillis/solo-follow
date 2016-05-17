"""
followme - Tracks GPS position of your computer (Linux only).

This example uses the python gps package to read positions from a GPS attached to your 
laptop and sends a new vehicle.simple_goto command every two seconds to move the
vehicle to the current point.

When you want to stop follow-me, either change vehicle modes or type Ctrl+C to exit the script.

Example documentation: http://python.dronekit.io/examples/follow_me.html
"""

from dronekit import connect, VehicleMode, LocationGlobalRelative
import socket
import time
import sys

#Set up option parsing to get connection string
import argparse  
parser = argparse.ArgumentParser(description='Program for 3DR Solo to track other aircraft')
parser.add_argument('--solo', 
                   help="3DR Solo connection target string.")
parser.add_argument('--ac', 
                   help="Other vehicle connection target string.")
args = parser.parse_args()

solo_connection = args.solo
ac_connection = args.ac

#Start SITL if no connection string specified
if not solo_connection:
    print("No solo connection provided")
    exit(0)

if not ac_connection:
    print("No other vehicle connection provided")
    exit(0)

# Connect to the Vehicle
print 'Connecting to 3DR Solo on: %s' % solo_connection
ac = connect(solo_connection, wait_ready=True)

print 'Connecting to other vehicle on: %s' % ac_connection
solo = connect(ac_connection, wait_ready=True)

# offsets for solo
x = 0
y = 0
z = 0


def get_location_metres(original_location, dNorth, dEast):
    """
    Returns a LocationGlobal object containing the latitude/longitude `dNorth` and `dEast` metres from the
    specified `original_location`. The returned LocationGlobal has the same `alt` value
    as `original_location`.

    The function is useful when you want to move the vehicle around specifying locations relative to
    the current vehicle position.

    The algorithm is relatively accurate over small distances (10m within 1km) except close to the poles.

    For more information see:
    http://gis.stackexchange.com/questions/2951/algorithm-for-offsetting-a-latitude-longitude-by-some-amount-of-meters
    """
    earth_radius=6378137.0 #Radius of "spherical" earth
    #Coordinate offsets in radians
    dLat = dNorth/earth_radius
    dLon = dEast/(earth_radius*math.cos(math.pi*original_location.lat/180))

    #New position in decimal degrees
    newlat = original_location.lat + (dLat * 180/math.pi)
    newlon = original_location.lon + (dLon * 180/math.pi)
    if type(original_location) is LocationGlobal:
        targetlocation=LocationGlobal(newlat, newlon,original_location.alt)
    elif type(original_location) is LocationGlobalRelative:
        targetlocation=LocationGlobalRelative(newlat, newlon,original_location.alt)
    else:
        raise Exception("Invalid Location object passed")

    return targetlocation;

try:
    while True:
    
        if vehicle.mode.name != "GUIDED":
            print "User has changed flight modes - aborting follow-me"
            break    
        
        position = get_location_metres(ac.location.global_relative_frame,y,x)
        dest = LocationGlobalRelative(position.lat,position.lon,ac.location.global_relative_frame.alt+z)
        print "Going to: %s" % dest

        solo.simple_goto(dest)
        set_solo_roi(ac.location.global_relative_frame)

        time.sleep(.5)
            
except:
    print("oops")
    sys.exit(1)

#Close vehicle object before exiting script
print("Close solo and other vehicle object")
ac.close()
solo.close()

print("Completed")