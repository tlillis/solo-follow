"""
code initially based off of follow_me DroneKit example:
http://python.dronekit.io/examples/follow_me.html

When you want to stop follow-me, either change vehicle modes or type Ctrl+C to exit the script.

"""

from dronekit import connect, VehicleMode, LocationGlobalRelative, LocationGlobal
from pymavlink import mavutil
from fastkml import kml, styles
from fastkml.geometry import Geometry, Point, LineString, Polygon
import json
import socket
import time
import sys
import select
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
print('Connecting to 3DR Solo on: {0}'.format(solo_connection))
solo = connect(solo_connection)


print('Connecting to other vehicle on: {0}'.format(ac_connection))
ac = connect(ac_connection)

# Offsets for solo
x = 0
y = 0
z = 0
rate = 2

print("Connected! Starting script!")

def make_kml(x, y, alt, c, type):

    ns = '{http://www.opengis.net/kml/2.2}'
    if type == "wp":
        p= kml.Placemark(ns, name='WP', styleUrl='wp')
        s = styles.Style(id='wp')
        IS = styles.IconStyle(scale=1.2, icon_href='https://maps.google.com/mapfiles/kml/shapes/capital_big_highlight.png', heading=(int(c) - 90))
        s.append_style(IS)
        d = kml.Document(ns=ns, name='WP')
    elif type == "ac":
        p= kml.Placemark(ns, name='AC', styleUrl='ac')
        s = styles.Style(id='ac')
        IS = styles.IconStyle(scale=1.2, icon_href='https://maps.google.com/mapfiles/kml/shapes/airports.png', heading=(int(c)))
        s.append_style(IS)
        d = kml.Document(ns=ns, name='AC')
    elif type == "solo":
        p= kml.Placemark(ns, name='SOLO', styleUrl='solo')
        s = styles.Style(id='solo')
        IS = styles.IconStyle(scale=1.2, icon_href='https://maps.google.com/mapfiles/kml/shapes/camera.png', heading=(int(c) - 90))
        s.append_style(IS)
        d = kml.Document(ns=ns, name='SOLO')
    else:
        return

    geom = Geometry()
    geom.geometry = Point(float(y), float(x), float(alt))
    geom.altitude_mode = 'relativeToGround'
    p.geometry = geom
    d.append_style(s)
    d.append(p)

    return d

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
while True:
    while sys.stdin in select.select([sys.stdin], [], [], 0)[0]: ## Handle input
        line = sys.stdin.readline()
        if line:
            input_list = line.split()
            if input_list[0] == "set":
                if input_list[1] == "x":
                    x = int(input_list[2])
                if input_list[1] == "y":
                    y = int(input_list[2])
                if input_list[1] == "z":
                    z = int(input_list[2])
                if input_list[1] == "r":
                    rate = int(input_list[2])
                else:
                    print("input not supported {0}".format(input_list[1]))
            else:
                print("input not supported {0}".format(input_list[0]))
        else: # an empty line means stdin has been closed
            print('eof')
            exit(0)

    else: ## Do follow calcs and commands
        #if solo.mode.name != "GUIDED":
            #print "User has changed flight modes - aborting follow-me"
            #break    
        
        position = get_location_metres(ac.location.global_relative_frame,y,x)
        dest = LocationGlobalRelative(position.lat,position.lon,ac.location.global_relative_frame.alt+z)
        print("Going to: {0}".format(dest))
        print("X: {0},Y: {1},Z: {2},Rate: {3}".format(x,y,z,rate))

        solo.simple_goto(dest)
        set_solo_roi(ac.location.global_relative_frame)

        time.sleep(rate)

        ## KML updates
        ns = '{http://www.opengis.net/kml/2.2}'

        ac_k = kml.KML(ns=ns)
        ac_k.append(make_kml(ac.location.global_relative_frame.lat,ac.location.global_relative_frame.lon,ac.location.global_relative_frame.alt,0,"ac"))
        kmlfile = open('FOLLOW.kml',"w")
        kmlfile.write(ac_k.to_string(prettyprint=True))
        kmlfile.close()

        wp_k = kml.KML(ns=ns)
        wp_k.append(make_kml(position.lat,position.lon,position.alt,0,"wp"))
        kmlfile = open('SET_POINT.kml',"w")
        kmlfile.write(wp_k.to_string(prettyprint=True))
        kmlfile.close() 

        solo_k = kml.KML(ns=ns)
        solo_k.append(make_kml(solo.location.global_relative_frame.lat,ac.location.global_relative_frame.lon,ac.location.global_relative_frame.lon,0,"solo"))
        kmlfile = open('SOLO.kml',"w")
        kmlfile.write(solo_k.to_string(prettyprint=True))
        kmlfile.close()

# Close vehicle object before exiting script
print("Close solo and other vehicle object")
ac.close()
solo.close()

print("Completed")