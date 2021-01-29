from tkinter import *
from tkinter import font as font

import socket
from pythonosc import udp_client
from pythonosc import osc_bundle_builder, osc_message_builder
from pythonosc import dispatcher, osc_server

import threading

import pickle

from typing import List, Any
import RPi.GPIO as GPIO

from time import strftime
from time import sleep

# Konfigs

small_window = True

pin_people_going = 14
pin_people_comming = 15
pin_reset_something = 12

# First Variables definition

max_people_allowed = 0  # Maximale Anzahl drinnen befiindlicher Personen
people_inside = 0  # Momentane Anzahl der drinnen befindlichen Personen

file_list = []

root = Tk()  # TK root

if not small_window:
    root.attributes('-fullscreen', True)

# GPIO Setups
GPIO.setmode(GPIO.BCM)
GPIO.setup(pin_people_going, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(pin_people_comming, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

GPIO.setup(pin_reset, GPIO.OUT)
GPIO.output(pin_reset, 1)

GPIO.add_event_detect(pin_people_going, GPIO.RISING, callback=inside_minus)
GPIO.add_event_detect(pin_people_comming, GPIO.RISING, callback=inside_plus)


# Anfang Funktionen Definition
def load_last_file():  # Laed den letzten Stand der Perseonen
    try:
        with open("/home/pi/peopleCounter/reset.save.pkl") as f:
            maximum, inside = pickle.load(f)
            if maximum is None:
                maximum = 20
            if inside is None:
                inside = 0
    except:
        maximum = 20
        inside = 0
    return maximum, inside


def save_last_file():  # Speicher Anzahl in reset/save.pkl
    global max_people_allowed, people_inside
    with open("/home/pi/peopleCounter/reset.save.pkl", "w+") as f:
        pickle.dump([max_people_allowed, people_inside], f)


def inside_plus():
    global people_inside
    people_inside = people_inside + 1


def inside_minus():
    global people_inside
    people_inside = people_inside - 1


def set_inside(i):
    global people_inside
    people_inside = i


def maximum_plus():
    global max_people_allowed
    max_people_allowed = max_people_allowed + 1


def maximum_minus():
    global max_people_allowed
    max_people_allowed = max_people_allowed - 1


def set_maximum(i):
    global max_people_allowed
    max_people_allowed = i


# OSC Handler
def got_set_inside(address: str, *args: List[Any]) -> None:
    if len(args) > 0:
        inside = args[0]
        set_inside(inside)
        root.after(1, send_counter_info, address[0])


def got_set_maximum(address: str, *args: List[Any]) -> None:
    if len(args) > 0:
        maximum = args[0]
        set_maximum(maximum)
        root.after(1, send_counter_info, address[0])


# Sende Counter zurück an Sender
def send_counter_info(adress_send_to):
    global max_people_allowed, people_inside
    client = udp_client.SimpleUDPClient(adress_send_to, 9001)
    msg = osc_message_builder.OscMessageBuilder(address="/counter_info")
    bundle = osc_bundle_builder.OscBundleBuilder(osc_bundle_builder.IMMEDIATELY)
    msg.add_arg(max_people_allowed)
    msg.add_arg(people_inside)
    bundle.add_content(msg.build())
    bundle = bundle.build()
    print("counter_info an {} gesendet".format(adress_send_to))
    client.send(bundle)

# Starte Server
def start_osc_server():
    dispat = dispatcher.Dispatcher()
    dispat.map("/counter/reset_inside", got_set_inside, needs_reply_address=True)
    dispat.map("/counter/reset_max", got_set_maximum, needs_reply_address=True)

    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    server = osc_server.ThreadingOSCUDPServer((local_ip, 9001), dispat)
    server.serve_forever()
