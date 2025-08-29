import asyncio
import os.path
import random
import re
import shutil
import subprocess
import zipfile
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

from client.APClient import run_client, set_client_running
from config.config import AP_BASE_YAML_LOCATION, AP_INSTALL_LOCATION, FREE_LOCATIONS_PER_DEATH
from message.death_message import death_message

REROLL = False

def reroll(reroll):
    global REROLL
    set_client_running(not reroll)
    REROLL = reroll


def read_death_count():
    if not os.path.isfile("death_count.txt"):
        return 0
    with open("death_count.txt", "r") as death_file:
        file_contents = death_file.read()
        return int(file_contents)


def copy_yamls():
    players_dir = os.path.join(AP_INSTALL_LOCATION, "Players")
    output_dir = os.path.join(AP_INSTALL_LOCATION, "output")
    # if os.path.isdir(output_dir):
    #     for (dirpath, dirnames, filenames) in os.walk(output_dir):
    #         for filename in filenames:
    #             os.remove(os.path.join(output_dir, filename))
    #         break
    for (dirpath, dirnames, filenames) in os.walk(players_dir):
        for filename in filenames:
            os.remove(os.path.join(players_dir, filename))
        break
    [shutil.copy(os.path.join(AP_BASE_YAML_LOCATION, filename), players_dir) 
     for filename in os.listdir(AP_BASE_YAML_LOCATION)]


def ap_regenerate():
    file_extension = ""
    if os.name == "nt":
        file_extension = ".exe"
    ap_generate_file = os.path.join(AP_INSTALL_LOCATION, "ArchipelagoGenerate" + file_extension)
    subprocess.call((ap_generate_file,))

def ap_generate():
    output_dir = os.path.join(AP_INSTALL_LOCATION, "output")
    if os.path.isdir(output_dir):
        for (dirpath, dirnames, filenames) in os.walk(output_dir):
            for filename in filenames:
                return
            copy_yamls()
            ap_regenerate()
            break



async def ap_server(death_count, client):
    global REROLL
    REROLL = False
    file_extension = ""
    if os.name == "nt":
        file_extension = ".exe"

    output_dir = os.path.join(AP_INSTALL_LOCATION, "output")
    output_file = ""
    for (dirpath, dirnames, filenames) in os.walk(output_dir):
        for filename in filenames:
            if filename.endswith(".zip"):
                output_file = os.path.join(output_dir, filename)

    ap_output_file = zipfile.ZipFile(output_file)
    ap_spoiler_log = ""

    for file in ap_output_file.namelist():
        if file.endswith(".txt"):
            ap_output_file.extract(file, output_dir)
            ap_spoiler_log = os.path.join(output_dir, file)
            break
    ap_server_file = os.path.join(AP_INSTALL_LOCATION, "ArchipelagoServer" + file_extension)
    p = subprocess.Popen((ap_server_file, "--host", "0.0.0.0", "--port", "6472", "--hint_cost", "10", output_file),
                         stdin=subprocess.PIPE, preexec_fn=os.setsid if os.name != "nt" else None)
    locations_slots = get_locations_from_spoiler(ap_spoiler_log)
    for i in range(0, death_count * FREE_LOCATIONS_PER_DEATH):
        if i > len(locations_slots) - 1:
            break
        index = random.randint(0, len(locations_slots) - 1)
        location_slot = locations_slots[index]
        locations_slots.pop(index)
        p.stdin.write(f"/send_location {location_slot[1]} {location_slot[0]}\n".encode())
    p.stdin.flush()
    await run_client()
    p.terminate()
    if not REROLL:
        print("Death detected. Restarting.")
        await death_message(client, death_count + 1)
        with open("death_count.txt", "w+") as death_file:
            death_file.write(str(death_count + 1))

def get_locations_from_spoiler(ap_spoiler_log):
    locations_slots = []
    with open(ap_spoiler_log, "r") as spoiler:
        line = spoiler.readline()
        while line is not None:
            if line.startswith("Locations:"):
                break
            line = spoiler.readline()
        line = spoiler.readline()
        while line is not None:
            if line.startswith("Playthrough:"):
                break
            if not line.startswith("\r") and not line.startswith("\n"):
                colon_split = line.split(":")
                location_name_slot = ":".join([colon_split[index] for index in range(len(colon_split) - 1)])
                match_list = re.findall("\\([^\\(\\)]*\\)$", location_name_slot)
                if len(match_list) > 0:
                    slot_name_paren = match_list[-1]
                    location_name = location_name_slot[:(len(slot_name_paren) + 1)*-1]
                    slot_name = slot_name_paren[1:-1]
                else:
                    location_name = location_name_slot
                    slot_name = "Player1"
                locations_slots.append((location_name, slot_name))
            line = spoiler.readline()
    return locations_slots


async def server_monitor(client):
    death_count = read_death_count()
    ap_generate()
    await ap_server(death_count, client)
    copy_yamls()
    ap_regenerate()