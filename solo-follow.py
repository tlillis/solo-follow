"""
code initially based off of follow_me DroneKit example:
http://python.dronekit.io/examples/follow_me.html

When you want to stop follow-me, either change vehicle modes or type Ctrl+C to exit the script.

"""

from dronekit import connect, VehicleMode, LocationGlobalRelative, LocationGlobal
from pymavlink import mavutil
import socket
import time
import sys
import math 

# Set up option parsing to get connection string
import argparse  
parser = argparse.ArgumentParser(description='Program for 3DR Solo to track other aircraft')
parser.add_argument('--solo', 
                   help="3DR Solo connection target string.")
parser.add_argument('--ac', 
                   help="Other vehicle connection target string.")
args = parser.parse_args()

solo_connection = args.solo
ac_connection = args.ac

if not solo_connection:
    print("No solo connection provided")
    exit(0)

if not ac_connection:
    print("No other vehicle connection provided")
    exit(0)

# Connect to the Vehicle
print 'Connecting to 3DR Solo on: %s' % solo_connection
solo = connect(solo_connection)


print 'Connecting to other vehicle on: %s' % ac_connection
ac = connect(ac_connection)

# Offsets for solo
x = 0
y = 0
z = 0

print("Connected! Starting script!")


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

def set_solo_roi(location):
    # create the MAV_CMD_DO_SET_ROI command
    msg = solo.message_factory.command_long_encode(
        0, 0,    # target system, target component
        mavutil.mavlink.MAV_CMD_DO_SET_ROI, #command
        0, #confirmation
        0, 0, 0, 0, #params 1-4
        location.lat,
        location.lon,
        location.alt
        )
    # send command to vehicle
    solo.send_mavlink(msg)
# Main Loop
#try:
while True:
    
        #if vehicle.mode.name != "GUIDED":
        #    print "User has changed flight modes - aborting follow-me"
        #    break    
        
    position = get_location_metres(ac.location.global_relative_frame,y,x)
    dest = LocationGlobalRelative(position.lat,position.lon,ac.location.global_relative_frame.alt+z)
    print "Going to: %s" % dest

    solo.simple_goto(dest)
    set_solo_roi(ac.location.global_relative_frame)

    time.sleep(.5)
            
#except:
#    print("oops")
#    sys.exit(1)

# Close vehicle object before exiting script
print("Close solo and other vehicle object")
ac.close()
solo.close()

print("Completed")