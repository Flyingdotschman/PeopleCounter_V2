from tkinter import *
from tkinter import font as font
import socket
# from socket import *
from pythonosc import udp_client
from pythonosc import osc_bundle_builder, osc_message_builder
from pythonosc import dispatcher, osc_server

from omxplayer.player import OMXPlayer

import threading

import platform

import pickle
from time import sleep as sleep

from typing import List, Any

from time import strftime
from time import sleep

import os
import sys
import stat
import subprocess
from pynput.keyboard import Key, Controller

# GPIO Setups Part 1
print("Running on {}".format(platform.system()))
if platform.system() != "Windows":
    import RPi.GPIO as GPIO

# Konfigs

small_window = False

# First Variables definition

max_people_allowed = 0  # Maximale Anzahl drinnen befiindlicher Personen
people_inside = 0  # Momentane Anzahl der drinnen befindlichen Personen

index_video = 0
file_list = []
server = []

video_player = []

keyboard = Controller()
root = Tk()  # TK root

if not small_window:
    root.attributes('-fullscreen', True)
    # root.geometry("1080x1920")

# Bilder werden geladen im Hintergrund
if platform.system() != "Windows":
    background_go = PhotoImage(file="/home/pi/PeopleCounter_V2/GO.png")
    background_stop = PhotoImage(file="/home/pi/PeopleCounter_V2/Stop.png")
else:
    background_go = PhotoImage(file="GO.png")
    background_stop = PhotoImage(file="Stop.png")


# Anfang Funktionen Definition
def load_last_file():  # Laed den letzten Stand der Perseonen
    try:
        with open("/home/pi/PeopleCounter_V2/reset/save.pkl", "rb") as f:
            maximum, inside = pickle.load(f)
            if maximum is None:
                maximum = 20
            if inside is None:
                inside = 0
    except:
        maximum = 20
        inside = 0
    return maximum, inside


def save_last_file(maximum, inside):  # Speicher Anzahl in reset/save.pkl

    with open("/home/pi/PeopleCounter_V2/reset/save.pkl", "wb+") as f:
        pickle.dump([maximum, inside], f)


def inside_plus():
    global people_inside
    if people_inside < 1000:
        people_inside = people_inside + 1
    save_last_file(max_people_allowed, people_inside)
    root.after(1, update_the_screen)


def inside_minus():
    global people_inside
    if people_inside > 0:
        people_inside = people_inside - 1
    save_last_file(max_people_allowed, people_inside)
    root.after(1, update_the_screen)


def set_inside(i):
    global people_inside
    people_inside = i
    save_last_file(max_people_allowed, people_inside)
    root.after(1, update_the_screen)


def maximum_plus():
    global max_people_allowed
    if max_people_allowed < 1000:
        max_people_allowed = max_people_allowed + 1
    save_last_file(max_people_allowed, people_inside)
    root.after(1, update_the_screen)


def maximum_minus():
    global max_people_allowed
    if max_people_allowed > 0:
        max_people_allowed = max_people_allowed - 1
    save_last_file(max_people_allowed, people_inside)
    root.after(1, update_the_screen)


def set_maximum(i):
    global max_people_allowed
    max_people_allowed = i
    save_last_file(max_people_allowed, people_inside)
    root.after(1, update_the_screen)


def max_people_reached():
    global max_people_allowed, people_inside
    if max_people_allowed > people_inside:
        return False
    return True


# OSC Handler
def got_set_inside(address: str, *args: List[Any]) -> None:
    if len(args) > 0:
        print(args)
        inside = args[1]
        set_inside(inside)
        root.after(1, send_counter_info, address[0])


def got_set_maximum(address: str, *args: List[Any]) -> None:
    if len(args) > 0:
        print(args)
        maximum = args[1]
        set_maximum(maximum)
        root.after(1, send_counter_info, address[0])


def got_maximum_plus(address: str, *args: List[Any]) -> None:
    maximum_plus()
    root.after(1, send_counter_info, address[0])


def got_maximum_minus(address: str, *args: List[Any]) -> None:
    maximum_minus()
    root.after(1, send_counter_info, address[0])


def got_inside_plus(address: str, *args: List[Any]) -> None:
    inside_plus()
    root.after(1, send_counter_info, address[0])


def got_inside_minus(address: str, *args: List[Any]) -> None:
    inside_minus()
    root.after(1, send_counter_info, address[0])


def got_counter_info(address: str, *args: List[Any]) -> None:
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
    print("counter_info an {} gesendet mit max {} und inside {}".format(adress_send_to, max_people_allowed,
                                                                        people_inside))

    client.send(bundle)


# Update Screen Display
def update_the_screen():
    global max_people_allowed, people_inside
    global mainCanvas, omx_proc
    if not max_people_reached():
        mainCanvas.create_image(0, 0, image=background_go, anchor="nw")
        my_text1 = 'Personen'
        mainCanvas.create_text(500, 900, anchor=NW, text=my_text1, fill='white', font='ITCAvantGardeStd-Demi 60 bold',
                               state='normal')
        my_text3 = str(max_people_allowed)
        mainCanvas.create_text(310, 900, anchor=NW, text=my_text3, fill='white', font='ITCAvantGardeStd-Demi 60 bold',
                               state='normal')
        my_text3 = str(people_inside) + "/"
        mainCanvas.create_text(310, 900, anchor=NE, text=my_text3, fill='white', font='ITCAvantGardeStd-Demi 60 bold',
                               state='normal')

    else:
        if omx_proc is not None:
            omx_proc.stdin.write('q')
        keyboard.press("q")
        keyboard.release("q")
        mainCanvas.create_image(0, 0, image=background_stop, anchor="nw")


# Starte Server
def start_osc_server():
    global server
    print("*** STARTE OSC SERVER ***")
    dispat = dispatcher.Dispatcher()

    dispat.map("/counter/reset_inside", got_set_inside, needs_reply_address=True)
    dispat.map("/counter/reset_max", got_set_maximum, needs_reply_address=True)
    dispat.map("/counter/inside_plus", got_inside_plus, needs_reply_address=True)
    dispat.map("/counter/inside_minus", got_inside_minus, needs_reply_address=True)
    dispat.map("/counter/max_plus", got_maximum_plus, needs_reply_address=True)
    dispat.map("/counter/max_minus", got_maximum_minus, needs_reply_address=True)
    dispat.map("/counter/counter_info", got_counter_info, needs_reply_address=True)
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "192.168.4.1"
    print(local_ip)
    server = osc_server.ThreadingOSCUDPServer((local_ip, 9001), dispat)

    server.serve_forever()


# Methoden zum Suchen und finden der Videos
def walktree(top, callback):
    """recursively descend the directory tree rooted at top, calling the
    callback function for each regular file. Taken from the module-stat
    example at: http://docs.python.org/lib/module-stat.html
    """
    for f in os.listdir(top):
        pathname = os.path.join(top, f)
        mode = os.stat(pathname)[stat.ST_MODE]
        if stat.S_ISDIR(mode):
            # It's a directory, recurse into it
            walktree(pathname, callback)
        elif stat.S_ISREG(mode):
            # It's a file, call the callback function
            callback(pathname)
        else:
            pass
            # Unknown file type, print a message
            # print('Skipping %s' % pathname)


def addtolist(file, extensions=['.mp4']):
    """Add a file to a global list of image files."""
    global file_list  # ugh
    filename, ext = os.path.splitext(file)
    e = ext.lower()
    # Only add common image types to the list.
    if e in extensions:
        print('Adding to list: ', file)
        file_list.append(file)


def check_usb_stick_exists():
    global index_video
    print("Checking for USB")
    if len(os.listdir("/media/pi")) > 0:
        walktree("/media/pi", addtolist)
        index_video = 0
        start_video_player()
    else:
        root.after(1000, check_usb_stick_exists)


def start_video_player():
    global file_list, video_player, index_video

    if os.path.exists(file_list[index_video]):
        filey = file_list[index_video]
        index_video = index_video + 1
        if index_video > len(file_list) - 1:
            index_video = 0
        video_player = OMXPlayer(filey, args=['--orientation','270','--win','1312,0,1920,1080','--no-osd'], dbus_name='org.mpris.MeidlaPlayer2.omxplayer1')
        video_player.play()
        #player.set_video_pos(1312,0,1920,1080)
        print("playing Video Nr.{}".format(index_video))
        sleep(2)
        video_player.play_sync()

        root.after(2000,start_video_player)
    else:
        root.after(1000, check_usb_stick_exists)


def starte_server_thread():
    run_osc_server = threading.Thread(target=start_osc_server)
    run_osc_server.start()



# GPIO Setup Part2
if platform.system() != "Windows":
    pin_people_going = 14
    pin_people_comming = 15
    pin_reset_something = 12

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin_people_going, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(pin_people_comming, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    GPIO.setup(pin_reset_something, GPIO.OUT)
    GPIO.output(pin_reset_something, 1)

    GPIO.add_event_detect(pin_people_going, GPIO.RISING, callback=inside_minus)
    GPIO.add_event_detect(pin_people_comming, GPIO.RISING, callback=inside_plus)

# Lade Save File und letzte bekannte Besucher
max_people_allowed, people_inside = load_last_file()

# Erstellen der GUI
mainCanvas = Canvas(root)

mainCanvas.pack(fill="both", expand=True)
root.after(1000, check_usb_stick_exists)
root.after(2, starte_server_thread)
mainCanvas.create_image(0, 0, image=background_stop, anchor="nw")
root.after(1, update_the_screen)
# root.after(1, starte_video_player_thread)
root.mainloop()
